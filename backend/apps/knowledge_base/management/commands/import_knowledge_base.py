from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from apps.knowledge_base.exchange import ExchangeError, import_exchange


class Command(BaseCommand):
    help = "Importa la base de conocimiento local desde JSON, CSV o XLSX."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            required=True,
            choices=("json", "csv", "xlsx"),
            help="Formato del contrato de intercambio.",
        )
        parser.add_argument(
            "--input",
            required=True,
            help="Archivo de entrada o carpeta de entrada para CSV.",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Alias de la base de datos Django.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida el archivo y las referencias sin escribir en la base.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        if database not in connections.databases:
            raise CommandError(f"Alias de base de datos desconocido: {database}")
        source = Path(options["input"])
        dry_run = options["dry_run"]
        try:
            summary = import_exchange(
                source,
                options["format"],
                using=database,
                dry_run=dry_run,
            )
        except (ExchangeError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Simulación válida: {summary.entity_rows} entidades y "
                    f"{summary.relation_rows} relaciones; no se escribió nada."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Importación completada: {summary.entity_rows} entidades y "
                    f"{summary.relation_rows} relaciones."
                )
            )
