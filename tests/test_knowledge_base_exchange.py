import csv
import json
import tempfile
import uuid
from copy import deepcopy
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from apps.knowledge_base.exchange import (
    ExchangeError,
    build_payload,
    import_exchange,
    read_exchange,
)
from apps.knowledge_base.models import (
    Answer,
    CandidateProfile,
    Category,
    ProfessionalExperience,
    Question,
    QuestionVariant,
    Tag,
)
from django.core.management import call_command
from django.db import connections
from django.test import TestCase
from openpyxl import load_workbook


class KnowledgeBaseExchangeTests(TestCase):
    databases = {"default"}

    def setUp(self):
        self.category = Category.objects.create(name="Álgebra y café")
        self.question = Question.objects.create(
            category=self.category,
            question="¿Cómo explicarías esto?\n=1+1",
        )
        Answer.objects.create(
            question=self.question,
            text="Respuesta con acento: acción\ny una segunda línea",
        )
        Answer.objects.create(
            question=self.question,
            text="Segunda respuesta",
        )
        Answer.objects.create(
            question=self.question,
            text='=HYPERLINK("local")',
        )
        QuestionVariant.objects.create(
            question=self.question,
            text="Otra formulación",
        )
        QuestionVariant.objects.create(
            question=self.question,
            text="Pregunta alternativa",
        )
        self.tags = [
            Tag.objects.create(name="Café"),
            Tag.objects.create(name="I+D"),
        ]
        self.question.tags.add(*self.tags)
        experience = ProfessionalExperience.objects.create(
            position="Ingeniera",
            company_or_project="Proyecto local",
            start_date=date(2021, 2, 3),
            end_date=date(2024, 5, 6),
            responsibilities="Diseño\nvalidación",
            achievements="Entrega con éxito",
        )
        self.question.professional_experiences.add(experience)
        second_experience = ProfessionalExperience.objects.create(
            position="Analista",
            company_or_project="Otro proyecto",
            responsibilities="Análisis",
            achievements="Mejora de procesos",
        )
        self.question.professional_experiences.add(second_experience)
        second_question = Question.objects.create(
            category=self.category,
            question="¿Cómo medirías el resultado?",
        )
        second_question.professional_experiences.add(experience)
        CandidateProfile.objects.create(
            name="Perfil de prueba",
            professional_title="Ingeniera",
            summary="Resumen de prueba",
            location="Madrid",
            linkedin_url="https://linkedin.example/profile",
            github_url="https://github.example/profile",
            portfolio_url="https://portfolio.example/profile",
        )

    def _new_database(self):
        temporary_directory = tempfile.TemporaryDirectory(
            prefix="knowledge-base-exchange-"
        )
        alias = f"exchange_{uuid.uuid4().hex[:12]}"
        database_settings = deepcopy(connections.databases["default"])
        database_settings["NAME"] = str(
            Path(temporary_directory.name) / "exchange.sqlite3"
        )
        connections.databases[alias] = database_settings
        self.__class__.databases = {*self.__class__.databases, alias}
        self.addCleanup(self._remove_database, alias, temporary_directory)
        call_command(
            "migrate",
            database=alias,
            interactive=False,
            verbosity=0,
        )
        return alias

    def _remove_database(self, alias, temporary_directory):
        connections[alias].close()
        del connections.databases[alias]
        self.__class__.databases = self.__class__.databases - {alias}
        temporary_directory.cleanup()

    @staticmethod
    def _export(format_name, output, database="default"):
        call_command(
            "export_knowledge_base",
            format=format_name,
            output=str(output),
            database=database,
            stdout=StringIO(),
        )

    @staticmethod
    def _import(format_name, source, database, dry_run=False):
        return call_command(
            "import_knowledge_base",
            format=format_name,
            input=str(source),
            database=database,
            dry_run=dry_run,
            stdout=StringIO(),
        )

    def test_round_trip_and_reimport_are_idempotent_for_all_formats(self):
        expected = build_payload().tables
        for format_name in ("json", "csv", "xlsx"):
            with (
                self.subTest(format=format_name),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                output = root / (
                    "bundle.csv" if format_name == "csv" else f"bundle.{format_name}"
                )
                self._export(format_name, output)
                exported = read_exchange(output, format_name)
                self.assertEqual(exported.tables, expected)

                if format_name == "csv":
                    answer_csv = (output / "answers.csv").read_text(encoding="utf-8")
                    self.assertIn("'=HYPERLINK", answer_csv)
                elif format_name == "xlsx":
                    workbook = load_workbook(output, data_only=False)
                    answer_sheet = workbook["answers"]
                    formula_text = next(
                        cell
                        for row in answer_sheet.iter_rows(min_row=2)
                        for cell in row
                        if isinstance(cell.value, str) and "HYPERLINK" in cell.value
                    )
                    self.assertEqual(formula_text.data_type, "s")
                    self.assertTrue(formula_text.value.startswith("="))
                    workbook.close()

                database = self._new_database()
                self._import(format_name, output, database)
                imported = build_payload(database).tables
                self.assertEqual(imported, expected)

                self._import(format_name, output, database)
                self.assertEqual(build_payload(database).tables, expected)

    def test_dry_run_validates_without_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "knowledge-base.json"
            self._export("json", source)
            database = self._new_database()
            before = build_payload(database).tables

            self._import("json", source, database, dry_run=True)

            self.assertEqual(build_payload(database).tables, before)

    def test_previous_v1_exports_without_profile_are_imported_unchanged(self):
        for format_name in ("json", "csv", "xlsx"):
            with (
                self.subTest(format=format_name),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                source = root / (
                    "legacy.csv" if format_name == "csv" else f"legacy.{format_name}"
                )
                self._export(format_name, source)
                if format_name == "json":
                    document = json.loads(source.read_text(encoding="utf-8"))
                    del document["tables"]["candidate_profiles"]
                    source.write_text(
                        json.dumps(document, ensure_ascii=False),
                        encoding="utf-8",
                    )
                elif format_name == "csv":
                    (source / "candidate_profiles.csv").unlink()
                else:
                    workbook = load_workbook(source)
                    del workbook["candidate_profiles"]
                    workbook.save(source)
                    workbook.close()

                legacy_payload = read_exchange(source, format_name)
                self.assertEqual(legacy_payload.tables["candidate_profiles"], [])
                database = self._new_database()
                local_profile = CandidateProfile.objects.using(database).create(
                    name="Perfil local",
                )

                self._import(format_name, source, database)

                imported_profile = CandidateProfile.objects.using(database).get()
                self.assertEqual(imported_profile.pk, local_profile.pk)
                self.assertEqual(imported_profile.name, "Perfil local")
                self.assertEqual(
                    build_payload(database).tables["question_experiences"],
                    build_payload().tables["question_experiences"],
                )

    def test_import_keeps_local_records_absent_from_the_file(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "knowledge-base.json"
            self._export("json", source)
            database = self._new_database()
            local_category = Category.objects.using(database).create(name="Solo local")

            self._import("json", source, database)

            self.assertTrue(
                Category.objects.using(database)
                .filter(pk=local_category.pk, name="Solo local")
                .exists()
            )

    def test_late_failure_rolls_back_all_imported_entities(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "knowledge-base.json"
            self._export("json", source)
            database = self._new_database()
            before = build_payload(database).tables

            with patch(
                "apps.knowledge_base.exchange._import_relations",
                side_effect=RuntimeError("simulated late failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "late failure"):
                    import_exchange(source, "json", using=database)

            self.assertEqual(build_payload(database).tables, before)
            self.assertFalse(
                Category.objects.using(database)
                .filter(name=self.category.name)
                .exists()
            )
            self.assertFalse(
                Question.objects.using(database)
                .filter(question=self.question.question)
                .exists()
            )
            self.assertFalse(Tag.objects.using(database).filter(name="Café").exists())
            self.assertFalse(
                ProfessionalExperience.objects.using(database)
                .filter(company_or_project="Proyecto local")
                .exists()
            )

    def test_dry_run_rejects_bad_version_duplicate_keys_and_references(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "knowledge-base.json"
            self._export("json", source)
            document = json.loads(source.read_text(encoding="utf-8"))

            bad_version = deepcopy(document)
            bad_version["version"] = 2
            source.write_text(json.dumps(bad_version), encoding="utf-8")
            with self.assertRaisesRegex(ExchangeError, r"\$\.version"):
                read_exchange(source, "json")

            malformed_table = deepcopy(document)
            malformed_table["tables"]["categories"] = None
            source.write_text(json.dumps(malformed_table), encoding="utf-8")
            with self.assertRaisesRegex(
                ExchangeError,
                r"\$\.tables\.categories",
            ):
                read_exchange(source, "json")

            duplicate_key = deepcopy(document)
            duplicate_key["tables"]["categories"].append(
                duplicate_key["tables"]["categories"][0]
            )
            source.write_text(json.dumps(duplicate_key), encoding="utf-8")
            with self.assertRaisesRegex(
                ExchangeError,
                r"\$\.tables\.categories\[",
            ):
                read_exchange(source, "json")

            missing_reference = deepcopy(document)
            missing_reference["tables"]["questions"][0]["category_key"] = str(
                uuid.uuid4()
            )
            source.write_text(json.dumps(missing_reference), encoding="utf-8")
            with self.assertRaisesRegex(
                ExchangeError,
                r"\$\.tables\.questions\[0\]\.category_key",
            ):
                read_exchange(source, "json")

    def test_csv_and_xlsx_headers_are_checked_with_locations(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            csv_directory = root / "csv"
            xlsx_file = root / "bundle.xlsx"
            self._export("csv", csv_directory)
            self._export("xlsx", xlsx_file)

            categories_file = csv_directory / "categories.csv"
            with categories_file.open("r", encoding="utf-8", newline="") as stream:
                rows = list(csv.reader(stream))
            rows[0][0] = "unexpected"
            with categories_file.open("w", encoding="utf-8", newline="") as stream:
                csv.writer(stream, lineterminator="\n").writerows(rows)
            with self.assertRaisesRegex(ExchangeError, "categories.csv"):
                read_exchange(csv_directory, "csv")

            workbook = load_workbook(xlsx_file)
            workbook["questions"]["A1"] = "unexpected"
            workbook.save(xlsx_file)
            workbook.close()
            with self.assertRaisesRegex(ExchangeError, "questions:fila 1"):
                read_exchange(xlsx_file, "xlsx")
