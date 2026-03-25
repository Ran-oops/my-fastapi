from datetime import UTC, datetime
from enum import StrEnum

import typer

from app.cli.commands import permissions, roles


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


app.add_typer(roles.app, name="roles", help="Role management commands")
app.add_typer(permissions.app, name="permissions", help="Permission management commands")


@app.command("calculate-fte")
def calculate_fte(
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
    force: bool = typer.Option(False, "--force", "-f", help="Force recalculation"),
):
    """Calculate FTE - orchestrates multiple sub-commands in sequence"""
    # Placeholder: returns mock data
    result = {
        "action": "calculate_fte_full",
        "dry_run": dry_run,
        "force": force,
        "status": "completed",
        "steps_completed": 6,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    typer.echo(f"FTE calculation completed: {result['status']}")


@app.command("import-data")
def import_data(
    source: str = typer.Option(..., "--source", "-s", help="Data source"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate"),
):
    """Import data from source"""
    # Placeholder: returns mock data
    result = {
        "action": "import_data",
        "source": source,
        "dry_run": dry_run,
        "status": "completed",
        "records_processed": 0,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    typer.echo(f"Data import completed: {result['records_processed']} records")


@app.command("qc-report")
def qc_report(
    report_type: str = typer.Option(..., "--type", "-t", help="Report type"),
):
    """Generate QC report"""
    # Placeholder: returns mock data
    result = {
        "action": "generate_qc_report",
        "report_type": report_type,
        "status": "completed",
        "file_path": f"reports/qc_{report_type}_{datetime.now(UTC).strftime('%Y%m%d')}.pdf",
        "timestamp": datetime.now(UTC).isoformat(),
    }
    typer.echo(f"QC Report: {result['file_path']}")


if __name__ == "__main__":
    app()
