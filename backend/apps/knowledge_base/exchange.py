import csv
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from zipfile import BadZipFile

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError, transaction
from openpyxl import Workbook, load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)

FORMAT_ID = "interview-ai-assistant-knowledge-base"
FORMAT_VERSION = 1
TABLE_COLUMNS = {
    "categories": ("key", "name"),
    "questions": ("key", "category_key", "question"),
    "answers": ("key", "question_key", "text"),
    "question_variants": ("key", "question_key", "text"),
    "tags": ("key", "name"),
    "professional_experiences": (
        "key",
        "position",
        "company_or_project",
        "start_date",
        "end_date",
        "responsibilities",
        "achievements",
    ),
    "candidate_profiles": (
        "key",
        "name",
        "professional_title",
        "summary",
        "location",
        "linkedin_url",
        "github_url",
        "portfolio_url",
    ),
    "question_tags": ("question_key", "tag_key"),
    "question_experiences": ("question_key", "professional_experience_key"),
}
ENTITY_TABLES = (
    "categories",
    "questions",
    "answers",
    "question_variants",
    "tags",
    "professional_experiences",
    "candidate_profiles",
)
IMPORT_ORDER = (
    "categories",
    "tags",
    "professional_experiences",
    "candidate_profiles",
    "questions",
    "answers",
    "question_variants",
)
TEXT_COLUMNS = {
    "categories": ("name",),
    "questions": ("question",),
    "answers": ("text",),
    "question_variants": ("text",),
    "tags": ("name",),
    "professional_experiences": (
        "position",
        "company_or_project",
        "responsibilities",
        "achievements",
    ),
    "candidate_profiles": (
        "name",
        "professional_title",
        "summary",
        "location",
        "linkedin_url",
        "github_url",
        "portfolio_url",
    ),
}
OPTIONAL_TEXT_COLUMNS = {
    "candidate_profiles": (
        "professional_title",
        "summary",
        "location",
        "linkedin_url",
        "github_url",
        "portfolio_url",
    ),
}
URL_COLUMNS = {
    "candidate_profiles": ("linkedin_url", "github_url", "portfolio_url"),
}
ENTITY_MODELS = {
    "categories": Category,
    "questions": Question,
    "answers": Answer,
    "question_variants": QuestionVariant,
    "tags": Tag,
    "professional_experiences": ProfessionalExperience,
    "candidate_profiles": CandidateProfile,
}


class ExchangeError(Exception):
    """Raised for invalid exchange data or an unsuccessful local operation."""


class _DuplicateJSONKey(ValueError):
    def __init__(self, key: str):
        self.key = key
        super().__init__(key)


@dataclass
class ExchangePayload:
    tables: dict[str, list[dict[str, Any]]]
    locations: dict[str, list[str]]


@dataclass(frozen=True)
class ImportSummary:
    entity_rows: int
    relation_rows: int


def build_payload(using: str = "default") -> ExchangePayload:
    tables: dict[str, list[dict[str, Any]]] = {table: [] for table in TABLE_COLUMNS}

    for category in Category.objects.using(using).order_by("exchange_key"):
        tables["categories"].append(
            {"key": str(category.exchange_key), "name": category.name}
        )

    questions = (
        Question.objects.using(using)
        .select_related("category")
        .prefetch_related("tags", "professional_experiences")
        .order_by("exchange_key")
    )
    for question in questions:
        question_key = str(question.exchange_key)
        tables["questions"].append(
            {
                "key": question_key,
                "category_key": str(question.category.exchange_key),
                "question": question.question,
            }
        )
        for tag in question.tags.all():
            tables["question_tags"].append(
                {"question_key": question_key, "tag_key": str(tag.exchange_key)}
            )
        for experience in question.professional_experiences.all():
            tables["question_experiences"].append(
                {
                    "question_key": question_key,
                    "professional_experience_key": str(experience.exchange_key),
                }
            )

    for answer in (
        Answer.objects.using(using).select_related("question").order_by("exchange_key")
    ):
        tables["answers"].append(
            {
                "key": str(answer.exchange_key),
                "question_key": str(answer.question.exchange_key),
                "text": answer.text,
            }
        )

    for variant in (
        QuestionVariant.objects.using(using)
        .select_related("question")
        .order_by("exchange_key")
    ):
        tables["question_variants"].append(
            {
                "key": str(variant.exchange_key),
                "question_key": str(variant.question.exchange_key),
                "text": variant.text,
            }
        )

    for tag in Tag.objects.using(using).order_by("exchange_key"):
        tables["tags"].append({"key": str(tag.exchange_key), "name": tag.name})

    for experience in ProfessionalExperience.objects.using(using).order_by(
        "exchange_key"
    ):
        tables["professional_experiences"].append(
            {
                "key": str(experience.exchange_key),
                "position": experience.position,
                "company_or_project": experience.company_or_project,
                "start_date": (
                    experience.start_date.isoformat()
                    if experience.start_date is not None
                    else None
                ),
                "end_date": (
                    experience.end_date.isoformat()
                    if experience.end_date is not None
                    else None
                ),
                "responsibilities": experience.responsibilities,
                "achievements": experience.achievements,
            }
        )

    for profile in CandidateProfile.objects.using(using).order_by("exchange_key"):
        tables["candidate_profiles"].append(
            {
                "key": str(profile.exchange_key),
                "name": profile.name,
                "professional_title": profile.professional_title,
                "summary": profile.summary,
                "location": profile.location,
                "linkedin_url": profile.linkedin_url,
                "github_url": profile.github_url,
                "portfolio_url": profile.portfolio_url,
            }
        )

    for table in ("question_tags", "question_experiences"):
        tables[table].sort(key=lambda row: tuple(row.values()))

    return ExchangePayload(
        tables=tables,
        locations={
            table: [f"$.tables.{table}[{index}]" for index in range(len(rows))]
            for table, rows in tables.items()
        },
    )


def export_exchange(
    output: Path,
    format_name: str,
    using: str = "default",
) -> ExchangePayload:
    payload = build_payload(using)
    if format_name == "json":
        _write_json(output, payload)
    elif format_name == "csv":
        _write_csv_directory(output, payload)
    elif format_name == "xlsx":
        _write_xlsx(output, payload)
    else:
        raise ExchangeError(f"Formato no admitido: {format_name}")
    return payload


def import_exchange(
    source: Path,
    format_name: str,
    using: str = "default",
    dry_run: bool = False,
) -> ImportSummary:
    payload = read_exchange(source, format_name)
    _validate_database_conflicts(payload, using)
    summary = ImportSummary(
        entity_rows=sum(len(payload.tables[table]) for table in ENTITY_TABLES),
        relation_rows=sum(
            len(payload.tables[table])
            for table in ("question_tags", "question_experiences")
        ),
    )
    if dry_run:
        return summary

    try:
        with transaction.atomic(using=using):
            mapped_entities: dict[str, dict[uuid.UUID, Any]] = {}
            for table in IMPORT_ORDER:
                mapped_entities[table] = _upsert_entity_table(
                    table,
                    payload,
                    mapped_entities,
                    using,
                )
            _import_relations(payload, mapped_entities)
    except IntegrityError as exc:
        location = "$"
        for table in reversed(tuple(payload.locations)):
            if payload.locations[table]:
                location = payload.locations[table][-1]
                break
        raise ExchangeError(
            f"{location}: la base de datos rechazó una fila por una "
            "restricción de integridad; "
            "la transacción completa se revirtió."
        ) from exc

    return summary


def read_exchange(source: Path, format_name: str) -> ExchangePayload:
    source = Path(source)
    if format_name == "json":
        raw, locations = _read_json(source)
    elif format_name == "csv":
        raw, locations = _read_csv_directory(source)
    elif format_name == "xlsx":
        raw, locations = _read_xlsx(source)
    else:
        raise ExchangeError(f"Formato no admitido: {format_name}")
    return _validate_payload(raw, locations)


def _metadata(version: int = FORMAT_VERSION) -> dict[str, Any]:
    return {"format": FORMAT_ID, "version": version}


def _write_json(output: Path, payload: ExchangePayload) -> None:
    document = {**_metadata(), "tables": payload.tables}
    _atomic_write_text(
        output,
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
    )


def _write_csv_directory(output: Path, payload: ExchangePayload) -> None:
    output = Path(output)
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise ExchangeError(
                f"{output}: la carpeta CSV debe estar vacía o no existir"
            )
    else:
        output.mkdir(parents=True)

    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(_metadata(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    for table, columns in TABLE_COLUMNS.items():
        with (output / f"{table}.csv").open(
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=columns,
                lineterminator="\n",
                extrasaction="raise",
            )
            writer.writeheader()
            for row in payload.tables[table]:
                writer.writerow(
                    {
                        column: _escape_csv_text(row[column])
                        if column in TEXT_COLUMNS.get(table, ())
                        else row[column]
                        if row[column] is not None
                        else ""
                        for column in columns
                    }
                )


def _write_xlsx(output: Path, payload: ExchangePayload) -> None:
    workbook = Workbook()
    manifest = workbook.active
    manifest.title = "manifest"
    _append_xlsx_row(manifest, ("format", "version"))
    _append_xlsx_row(manifest, (FORMAT_ID, FORMAT_VERSION))
    for table, columns in TABLE_COLUMNS.items():
        sheet = workbook.create_sheet(table)
        _append_xlsx_row(sheet, columns)
        for row in payload.tables[table]:
            _append_xlsx_row(sheet, tuple(row[column] for column in columns))

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output.parent,
            suffix=".xlsx",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        workbook.save(temporary_path)
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _append_xlsx_row(sheet: Any, values: tuple[Any, ...]) -> None:
    row_number = (
        1
        if sheet.max_row == 1 and sheet.max_column == 1 and sheet["A1"].value is None
        else sheet.max_row + 1
    )
    for column, value in enumerate(values, start=1):
        cell = sheet.cell(row=row_number, column=column, value=value)
        if isinstance(value, str):
            cell.data_type = "s"


def _atomic_write_text(output: Path, content: str) -> None:
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output.parent,
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _read_json(source: Path) -> tuple[Any, dict[str, list[str]]]:
    try:
        with source.open("r", encoding="utf-8") as json_file:
            document = json.load(json_file, object_pairs_hook=_reject_duplicate_keys)
    except _DuplicateJSONKey as exc:
        raise ExchangeError(f"$: clave JSON duplicada: {exc.key!r}") from exc
    except json.JSONDecodeError as exc:
        raise ExchangeError(
            f"{source}: línea {exc.lineno}, columna {exc.colno}: JSON inválido"
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ExchangeError(f"{source}: no se pudo leer el JSON: {exc}") from exc

    document_tables = document.get("tables") if isinstance(document, dict) else None
    locations = {}
    if isinstance(document_tables, dict):
        for table in TABLE_COLUMNS:
            rows = document_tables.get(table)
            locations[table] = (
                [f"$.tables.{table}[{index}]" for index in range(len(rows))]
                if isinstance(rows, list)
                else []
            )
    return document, locations


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey(key)
        result[key] = value
    return result


def _read_csv_directory(source: Path) -> tuple[Any, dict[str, list[str]]]:
    manifest_path = source / "manifest.json"
    try:
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            metadata = json.load(
                manifest_file,
                object_pairs_hook=_reject_duplicate_keys,
            )
    except _DuplicateJSONKey as exc:
        raise ExchangeError(
            f"{manifest_path}: clave JSON duplicada: {exc.key!r}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise ExchangeError(
            f"{manifest_path}: línea {exc.lineno}, columna {exc.colno}: JSON inválido"
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ExchangeError(
            f"{manifest_path}: no se pudo leer el manifiesto: {exc}"
        ) from exc

    tables: dict[str, list[dict[str, Any]]] = {}
    locations: dict[str, list[str]] = {}
    expected_files = {f"{table}.csv" for table in TABLE_COLUMNS}
    required_files = expected_files - {"candidate_profiles.csv"}
    try:
        found_files = {path.name for path in source.glob("*.csv")}
    except OSError as exc:
        raise ExchangeError(
            f"{source}: no se pudo enumerar la carpeta CSV: {exc}"
        ) from exc
    if not required_files.issubset(found_files) or not found_files.issubset(
        expected_files
    ):
        missing = sorted(required_files - found_files)
        extra = sorted(found_files - expected_files)
        raise ExchangeError(
            f"{source}: archivos CSV incorrectos; faltan {missing}, sobran {extra}"
        )

    for table, expected_columns in TABLE_COLUMNS.items():
        if f"{table}.csv" not in found_files:
            tables[table] = []
            locations[table] = []
            continue
        table_path = source / f"{table}.csv"
        try:
            with table_path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                if reader.fieldnames != list(expected_columns):
                    raise ExchangeError(
                        f"{table_path}: cabeceras inválidas; "
                        f"esperadas {list(expected_columns)}"
                    )
                rows = []
                row_locations = []
                for row in reader:
                    row_location = f"{table_path.name}:fila {reader.line_num}"
                    if None in row:
                        raise ExchangeError(
                            f"{row_location}: hay más valores que cabeceras"
                        )
                    rows.append(
                        {
                            column: (
                                _unescape_csv_text(value)
                                if column in TEXT_COLUMNS.get(table, ())
                                else None
                                if (
                                    table == "professional_experiences"
                                    and column in {"start_date", "end_date"}
                                    and value == ""
                                )
                                else value
                            )
                            for column, value in row.items()
                        }
                    )
                    row_locations.append(row_location)
                tables[table] = rows
                locations[table] = row_locations
        except ExchangeError:
            raise
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            raise ExchangeError(f"{table_path}: no se pudo leer el CSV: {exc}") from exc

    document = (
        {**metadata, "tables": tables} if isinstance(metadata, dict) else metadata
    )
    return document, locations


def _read_xlsx(source: Path) -> tuple[Any, dict[str, list[str]]]:
    try:
        workbook = load_workbook(source, read_only=True, data_only=False)
    except (BadZipFile, InvalidFileException, OSError, ValueError) as exc:
        raise ExchangeError(f"{source}: no se pudo leer el libro XLSX: {exc}") from exc

    expected_sheets = ["manifest", *TABLE_COLUMNS]
    legacy_sheets = [
        "manifest",
        *(table for table in TABLE_COLUMNS if table != "candidate_profiles"),
    ]
    try:
        if workbook.sheetnames not in (expected_sheets, legacy_sheets):
            raise ExchangeError(
                f"{source}: hojas incorrectas; se esperaban "
                f"{expected_sheets} o {legacy_sheets}"
            )
        manifest_rows = list(workbook["manifest"].iter_rows(values_only=True))
        if (
            len(manifest_rows) != 2
            or manifest_rows[0] != ("format", "version")
            or len(manifest_rows[1]) != 2
        ):
            raise ExchangeError(f"{source}:manifest:fila 1: manifiesto inválido")
        document: dict[str, Any] = {
            "format": manifest_rows[1][0],
            "version": manifest_rows[1][1],
            "tables": {},
        }
        locations: dict[str, list[str]] = {}
        for table, expected_columns in TABLE_COLUMNS.items():
            if table not in workbook.sheetnames:
                document["tables"][table] = []
                locations[table] = []
                continue
            sheet = workbook[table]
            rows = sheet.iter_rows(values_only=True)
            headers = next(rows, None)
            if headers != expected_columns:
                raise ExchangeError(
                    f"{source}:{table}:fila 1: cabeceras inválidas; "
                    f"esperadas {expected_columns}"
                )
            table_rows = []
            row_locations = []
            for row_number, values in enumerate(rows, start=2):
                if all(value is None for value in values):
                    continue
                if len(values) > len(expected_columns) and any(
                    value is not None for value in values[len(expected_columns) :]
                ):
                    raise ExchangeError(
                        f"{source}:{table}:fila {row_number}: hay valores "
                        "fuera de las cabeceras"
                    )
                values = values[: len(expected_columns)]
                table_rows.append(dict(zip(expected_columns, values)))
                row_locations.append(f"{source.name}:{table}:fila {row_number}")
            document["tables"][table] = table_rows
            locations[table] = row_locations
        return document, locations
    finally:
        workbook.close()


def _validate_payload(
    document: Any,
    locations: dict[str, list[str]],
) -> ExchangePayload:
    if not isinstance(document, dict):
        raise ExchangeError("$: el documento debe ser un objeto")
    if set(document) != {"format", "version", "tables"}:
        raise ExchangeError("$: se requieren exactamente format, version y tables")
    if document["format"] != FORMAT_ID:
        raise ExchangeError(f"$.format: formato no reconocido: {document['format']!r}")
    if type(document["version"]) is not int or document["version"] != FORMAT_VERSION:
        raise ExchangeError(
            f"$.version: versión no admitida: {document['version']!r}; "
            f"se requiere {FORMAT_VERSION}"
        )
    tables = document["tables"]
    required_tables = set(TABLE_COLUMNS) - {"candidate_profiles"}
    if (
        not isinstance(tables, dict)
        or not required_tables.issubset(tables)
        or set(tables) - set(TABLE_COLUMNS)
    ):
        raise ExchangeError(
            f"$.tables: se requieren exactamente estas tablas: {list(TABLE_COLUMNS)}"
        )
    tables = {**tables, "candidate_profiles": tables.get("candidate_profiles", [])}

    normalized_tables: dict[str, list[dict[str, Any]]] = {}
    for table, columns in TABLE_COLUMNS.items():
        rows = tables[table]
        if not isinstance(rows, list):
            raise ExchangeError(f"$.tables.{table}: se esperaba una lista")
        row_locations = locations.get(table, [])
        if len(row_locations) != len(rows):
            row_locations = [f"$.tables.{table}[{index}]" for index in range(len(rows))]
        normalized_rows = []
        seen_keys: set[str] = set()
        for index, row in enumerate(rows):
            location = row_locations[index]
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ExchangeError(
                    f"{location}: columnas inválidas; se requieren {list(columns)}"
                )
            row = dict(row)
            if "key" in row:
                row["key"] = _normalize_uuid(row["key"], f"{location}.key")
                if row["key"] in seen_keys:
                    raise ExchangeError(
                        f"{location}.key: clave de intercambio duplicada {row['key']}"
                    )
                seen_keys.add(row["key"])
            for column, value in row.items():
                if column == "key" or column.endswith("_key"):
                    row[column] = _normalize_uuid(value, f"{location}.{column}")
                elif table == "professional_experiences" and column in {
                    "start_date",
                    "end_date",
                }:
                    row[column] = _normalize_date(value, f"{location}.{column}")
                else:
                    if not isinstance(value, str):
                        raise ExchangeError(f"{location}.{column}: se esperaba texto")
                    if (
                        column in TEXT_COLUMNS.get(table, ())
                        and column not in OPTIONAL_TEXT_COLUMNS.get(table, ())
                        and value == ""
                    ):
                        raise ExchangeError(
                            f"{location}.{column}: el texto no puede estar vacío"
                        )
                    if table == "categories" and column == "name" and len(value) > 100:
                        raise ExchangeError(f"{location}.name: máximo 100 caracteres")
                    if table == "tags" and column == "name" and len(value) > 100:
                        raise ExchangeError(f"{location}.name: máximo 100 caracteres")
                    if table == "professional_experiences":
                        max_lengths = {"position": 150, "company_or_project": 200}
                        if column in max_lengths and len(value) > max_lengths[column]:
                            raise ExchangeError(
                                f"{location}.{column}: máximo "
                                f"{max_lengths[column]} caracteres"
                            )
                    if table == "candidate_profiles":
                        max_lengths = {
                            "name": 150,
                            "professional_title": 200,
                            "location": 200,
                            "linkedin_url": 500,
                            "github_url": 500,
                            "portfolio_url": 500,
                        }
                        if column in max_lengths and len(value) > max_lengths[column]:
                            raise ExchangeError(
                                f"{location}.{column}: máximo "
                                f"{max_lengths[column]} caracteres"
                            )
                        if column in URL_COLUMNS[table] and value:
                            try:
                                URLValidator()(value)
                            except DjangoValidationError as exc:
                                raise ExchangeError(
                                    f"{location}.{column}: URL inválida"
                                ) from exc
            normalized_rows.append(row)
        normalized_tables[table] = normalized_rows
        locations[table] = row_locations

    payload = ExchangePayload(normalized_tables, locations)
    _validate_duplicates(payload)
    _validate_references(payload)
    _validate_experience_dates(payload)
    return payload


def _normalize_uuid(value: Any, location: str) -> str:
    if not isinstance(value, str):
        raise ExchangeError(f"{location}: se esperaba una clave UUID en texto")
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ExchangeError(f"{location}: UUID inválido {value!r}") from exc


def _normalize_date(value: Any, location: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ExchangeError(f"{location}: se esperaba fecha ISO o null")
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError as exc:
        raise ExchangeError(f"{location}: fecha ISO inválida {value!r}") from exc
    if parsed_date.isoformat() != value:
        raise ExchangeError(f"{location}: la fecha debe usar YYYY-MM-DD")
    return value


def _validate_duplicates(payload: ExchangePayload) -> None:
    if len(payload.tables["candidate_profiles"]) > 1:
        raise ExchangeError(
            "$.tables.candidate_profiles: solo se permite un perfil del candidato"
        )

    for table, column in (("categories", "name"), ("tags", "name")):
        values: set[str] = set()
        for index, row in enumerate(payload.tables[table]):
            location = payload.locations[table][index]
            if row[column] in values:
                raise ExchangeError(
                    f"{location}.{column}: valor duplicado {row[column]!r}"
                )
            values.add(row[column])

    seen_variants: set[tuple[str, str]] = set()
    for index, row in enumerate(payload.tables["question_variants"]):
        pair = (row["question_key"], row["text"])
        if pair in seen_variants:
            raise ExchangeError(
                f"{payload.locations['question_variants'][index]}: "
                "variante duplicada para la pregunta"
            )
        seen_variants.add(pair)

    for table, target_column in (
        ("question_tags", "tag_key"),
        ("question_experiences", "professional_experience_key"),
    ):
        seen_relations: set[tuple[str, str]] = set()
        for index, row in enumerate(payload.tables[table]):
            pair = (row["question_key"], row[target_column])
            if pair in seen_relations:
                raise ExchangeError(
                    f"{payload.locations[table][index]}: relación duplicada"
                )
            seen_relations.add(pair)


def _validate_references(payload: ExchangePayload) -> None:
    keys = {
        table: {row["key"] for row in payload.tables[table]} for table in ENTITY_TABLES
    }
    references = (
        ("questions", "category_key", "categories"),
        ("answers", "question_key", "questions"),
        ("question_variants", "question_key", "questions"),
        ("question_tags", "question_key", "questions"),
        ("question_tags", "tag_key", "tags"),
        ("question_experiences", "question_key", "questions"),
        (
            "question_experiences",
            "professional_experience_key",
            "professional_experiences",
        ),
    )
    for table, column, target_table in references:
        for index, row in enumerate(payload.tables[table]):
            if row[column] not in keys[target_table]:
                raise ExchangeError(
                    f"{payload.locations[table][index]}.{column}: "
                    f"referencia inexistente {row[column]}"
                )


def _validate_experience_dates(payload: ExchangePayload) -> None:
    for index, row in enumerate(payload.tables["professional_experiences"]):
        start = row["start_date"]
        end = row["end_date"]
        if start is not None and end is not None and end < start:
            raise ExchangeError(
                f"{payload.locations['professional_experiences'][index]}.end_date: "
                "no puede preceder a start_date"
            )


def _validate_database_conflicts(payload: ExchangePayload, using: str) -> None:
    for table, model in (("categories", Category), ("tags", Tag)):
        for index, row in enumerate(payload.tables[table]):
            key = uuid.UUID(row["key"])
            manager = model.objects.using(using)
            key_owner = manager.filter(exchange_key=key).first()
            name_owner = manager.filter(name=row["name"]).first()
            if (
                key_owner is not None
                and name_owner is not None
                and key_owner.pk != name_owner.pk
            ):
                raise ExchangeError(
                    f"{payload.locations[table][index]}.name: "
                    f"ya existe en la base con otra clave: {row['name']!r}"
                )

    existing_questions = {
        str(exchange_key): primary_key
        for exchange_key, primary_key in Question.objects.using(using).values_list(
            "exchange_key", "pk"
        )
    }
    for index, row in enumerate(payload.tables["question_variants"]):
        question_id = existing_questions.get(row["question_key"])
        if question_id is None:
            continue
        conflict = (
            QuestionVariant.objects.using(using)
            .filter(question_id=question_id, text=row["text"])
            .exclude(exchange_key=uuid.UUID(row["key"]))
            .exists()
        )
        if conflict:
            raise ExchangeError(
                f"{payload.locations['question_variants'][index]}: "
                "la variante ya existe en la pregunta con otra clave"
            )


def _upsert_entity_table(
    table: str,
    payload: ExchangePayload,
    mapped_entities: dict[str, dict[uuid.UUID, Any]],
    using: str,
) -> dict[uuid.UUID, Any]:
    model = ENTITY_MODELS[table]
    mapped: dict[uuid.UUID, Any] = {}
    for index, row in enumerate(payload.tables[table]):
        key = uuid.UUID(row["key"])
        defaults = _entity_defaults(table, row, mapped_entities)
        try:
            manager = model.objects.using(using)
            instance = manager.filter(exchange_key=key).first()
            if instance is None and table in {"categories", "tags"}:
                instance = manager.filter(name=row["name"]).first()
            if instance is None and table == "candidate_profiles":
                instance = manager.filter(is_singleton=True).first()
            if instance is None:
                instance, _ = manager.update_or_create(
                    exchange_key=key,
                    defaults=defaults,
                )
            else:
                instance.exchange_key = key
                for field, value in defaults.items():
                    setattr(instance, field, value)
                instance.save(using=using)
        except IntegrityError as exc:
            raise ExchangeError(
                f"{payload.locations[table][index]}: conflicto con una "
                "restricción de la base de datos"
            ) from exc
        mapped[key] = instance
    return mapped


def _entity_defaults(
    table: str,
    row: dict[str, Any],
    mapped_entities: dict[str, dict[uuid.UUID, Any]],
) -> dict[str, Any]:
    if table == "categories":
        return {"name": row["name"]}
    if table == "tags":
        return {"name": row["name"]}
    if table == "professional_experiences":
        return {
            "position": row["position"],
            "company_or_project": row["company_or_project"],
            "start_date": (
                date.fromisoformat(row["start_date"])
                if row["start_date"] is not None
                else None
            ),
            "end_date": (
                date.fromisoformat(row["end_date"])
                if row["end_date"] is not None
                else None
            ),
            "responsibilities": row["responsibilities"],
            "achievements": row["achievements"],
        }
    if table == "candidate_profiles":
        return {
            "name": row["name"],
            "professional_title": row["professional_title"],
            "summary": row["summary"],
            "location": row["location"],
            "linkedin_url": row["linkedin_url"],
            "github_url": row["github_url"],
            "portfolio_url": row["portfolio_url"],
        }
    if table == "questions":
        category = mapped_entities["categories"][uuid.UUID(row["category_key"])]
        return {"category": category, "question": row["question"]}
    if table == "answers":
        question = mapped_entities["questions"][uuid.UUID(row["question_key"])]
        return {"question": question, "text": row["text"]}
    if table == "question_variants":
        question = mapped_entities["questions"][uuid.UUID(row["question_key"])]
        return {"question": question, "text": row["text"]}
    raise ExchangeError(f"Tabla de entidad desconocida: {table}")


def _import_relations(
    payload: ExchangePayload,
    mapped_entities: dict[str, dict[uuid.UUID, Any]],
) -> None:
    for index, row in enumerate(payload.tables["question_tags"]):
        question = mapped_entities["questions"][uuid.UUID(row["question_key"])]
        tag = mapped_entities["tags"][uuid.UUID(row["tag_key"])]
        try:
            question.tags.add(tag)
        except IntegrityError as exc:
            raise ExchangeError(
                f"{payload.locations['question_tags'][index]}: "
                "no se pudo guardar la relación"
            ) from exc

    for index, row in enumerate(payload.tables["question_experiences"]):
        question = mapped_entities["questions"][uuid.UUID(row["question_key"])]
        experience = mapped_entities["professional_experiences"][
            uuid.UUID(row["professional_experience_key"])
        ]
        try:
            question.professional_experiences.add(experience)
        except IntegrityError as exc:
            raise ExchangeError(
                f"{payload.locations['question_experiences'][index]}: "
                "no se pudo guardar la relación"
            ) from exc


def _escape_csv_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith("'") or _is_formula_like(value):
        return "'" + value
    return value


def _unescape_csv_text(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith("''"):
        return value[1:]
    if value.startswith("'") and _is_formula_like(value[1:]):
        return value[1:]
    return value


def _is_formula_like(value: str) -> bool:
    return value.lstrip(" \t\r\n").startswith(("=", "+", "-", "@"))
