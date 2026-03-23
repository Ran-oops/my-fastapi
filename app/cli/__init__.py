import asyncio
from enum import StrEnum

import typer


app = typer.Typer(help="Enterprise FastAPI Management Commands")


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@app.callback()
def global_options(
    log_level: LogLevel = typer.Option(
        LogLevel.INFO,
        "--log-level",
        "-l",
        help="Set logging level",
    ),
):
    """Global options for all commands"""
    import logging

    logging.basicConfig(level=log_level.value)


@app.command("calculate-fte")
def calculate_fte(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recalculation"),
):
    """Calculate FTE - orchestrates multiple sub-commands in sequence"""
    from app.services.fte import fte_service

    asyncio.run(fte_service.calculate_fte_full(None, dry_run=dry_run, force=force))
    typer.echo("FTE calculation completed!")


@app.command("import-data")
def import_data(
    source: str = typer.Option(..., "--source", "-s", help="Data source"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate"),
):
    """Import data from source"""
    from app.services.data_import import data_import_service

    asyncio.run(data_import_service.import_all(source, dry_run=dry_run))
    typer.echo("Data import completed!")


@app.command("qc-report")
def qc_report(
    report_type: str = typer.Option(..., "--type", "-t", help="Report type"),
):
    """Generate QC report"""
    from app.services.qc_report import qc_report_service

    result = asyncio.run(qc_report_service.generate(report_type, None, None, "pdf"))
    typer.echo(f"QC Report: {result['file_path']}")


if __name__ == "__main__":
    app()
