import typer
from typing import Optional
from enum import Enum

app = typer.Typer(help="Enterprise FastAPI Management Commands")

from app.cli.commands import fte, data_import, qc_report  # type: ignore[import-untyped]

typer.add_typer(app, fte.app, name="fte", help="FTE calculation commands")  # type: ignore[union-attr]
typer.add_typer(app, data_import.app, name="import", help="Data import commands")  # type: ignore[union-attr]
typer.add_typer(app, qc_report.app, name="qc", help="QC report commands")  # type: ignore[union-attr]


class LogLevel(str, Enum):
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


if __name__ == "__main__":
    app()
