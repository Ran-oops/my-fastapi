import asyncio
from datetime import date, datetime

import typer


app = typer.Typer(help="QC report commands")


@app.command("generate")
def generate_report(
    report_type: str = typer.Option(..., "--type", "-t", help="Report type"),
    start_date: str = typer.Option(
        ..., "--start", "-s", help="Start date (YYYY-MM-DD)"
    ),
    end_date: str = typer.Option(..., "--end", "-e", help="End date (YYYY-MM-DD)"),
    output: str = typer.Option(
        "pdf", "--output", "-o", help="Output format: pdf, excel, json"
    ),
):
    """Generate QC report"""
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    result = asyncio.run(_generate_report(report_type, start, end, output))
    typer.echo(f"Report generated: {result['file_path']}")


@app.command("list")
def list_reports(
    report_type: str | None = typer.Option(
        None, "--type", "-t", help="Filter by report type"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of reports to show"),
):
    """List generated QC reports"""
    reports = asyncio.run(_list_reports(report_type, limit))
    for report in reports:
        typer.echo(f"  - {report['id']}: {report['type']} ({report['created_at']})")


async def _generate_report(
    report_type: str, start_date: date, end_date: date, output: str
):
    from app.services.qc_report import QCReportService

    service = QCReportService()
    return await service.generate(report_type, start_date, end_date, output)


async def _list_reports(report_type: str | None, limit: int):
    from app.services.qc_report import QCReportService

    service = QCReportService()
    return await service.list_reports(report_type, limit)
