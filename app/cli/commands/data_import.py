import asyncio

import typer


app = typer.Typer(help="Data import commands")


@app.command("all-data")
def import_all_data(
    source: str = typer.Option(..., "--source", "-s", help="Data source identifier"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without making changes"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reimport"),
):
    """Import all data from specified source"""
    asyncio.run(_import_all_data(source, dry_run=dry_run, force=force))
    typer.echo("All data imported successfully!")


@app.command("validate")
def validate_data(
    source: str = typer.Option(..., "--source", "-s", help="Data source to validate"),
):
    """Validate imported data"""
    result = asyncio.run(_validate_data(source))
    if result["valid"]:
        typer.echo(f"✓ Data validation passed: {result['message']}")
    else:
        typer.echo(f"✗ Data validation failed: {result['message']}")
        raise typer.Exit(code=1)


async def _import_all_data(source: str, dry_run: bool = False, force: bool = False):
    from app.services.data_import import DataImportService

    service = DataImportService()
    await service.import_all(source, dry_run=dry_run, force=force)


async def _validate_data(source: str):
    from app.services.data_import import DataImportService

    service = DataImportService()
    return await service.validate(source)
