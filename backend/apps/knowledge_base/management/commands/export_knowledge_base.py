from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from apps.knowledge_base.exchange import ExchangeError, export_exchange


class Command(BaseCommand):
    help = "Exporta la base de conocimiento local a JSON, CSV o XLSX."

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            required=True,
            choices=("json", "csv", "xlsx"),
            help="Formato del contrato de intercambio.",
        )
        parser.add_argument(
            "--output",
            required=True,
            help="Archivo de salida o carpeta de salida para CSV.",
        )
        parser.add_argument(
            "--database",
            default="default",
            help="Alias de la base de datos Django.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        if database not in connections.databases:
            raise CommandError(f"Alias de base de datos desconocido: {database}")
        output = Path(options["output"])
        try:
            payload = export_exchange(output, options["format"], using=database)
        except (ExchangeError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        counts = ", ".join(
            f"{table}={len(rows)}" for table, rows in payload.tables.items()
        )
        self.stdout.write(f"Exportación completada: {output} ({counts})")
