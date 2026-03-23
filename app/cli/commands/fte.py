import typer
import asyncio
from typing import Optional

app = typer.Typer(help="FTE calculation commands")


@app.command("calculate")
def calculate_fte(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force recalculation"),
):
    """Calculate FTE - orchestrates multiple sub-commands in sequence"""
    typer.echo("Starting FTE calculation pipeline...")

    steps = [
        ("Importing task listing", import_task_listing),
        ("Importing geographic SSU data", import_geographic_ssu_data),
        ("Calculating country FTE", calculate_country_fte),
        ("Calculating site FTE", calculate_site_fte),
        ("Calculating subregion FTE", calculate_subregion_fte),
        ("Generating final forecast", final_forecast),
    ]

    for step_name, step_func in steps:
        typer.echo(f"Step: {step_name}...")
        try:
            asyncio.run(step_func(dry_run=dry_run, force=force))
            typer.echo(f"  ✓ {step_name} completed")
        except Exception as e:
            typer.echo(f"  ✗ {step_name} failed: {e}")
            raise typer.Exit(code=1)

    typer.echo("FTE calculation completed successfully!")


@app.command("import-task-listing")
def import_task_listing_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force reimport"),
):
    """Import task listing data"""
    asyncio.run(import_task_listing(dry_run=dry_run, force=force))
    typer.echo("Task listing imported successfully!")


@app.command("import-geographic-ssu")
def import_geographic_ssu_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force reimport"),
):
    """Import geographic SSU data"""
    asyncio.run(import_geographic_ssu_data(dry_run=dry_run, force=force))
    typer.echo("Geographic SSU data imported successfully!")


@app.command("calculate-country")
def calculate_country_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
):
    """Calculate country-level FTE"""
    asyncio.run(calculate_country_fte(dry_run=dry_run))
    typer.echo("Country FTE calculated successfully!")


@app.command("calculate-site")
def calculate_site_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
):
    """Calculate site-level FTE"""
    asyncio.run(calculate_site_fte(dry_run=dry_run))
    typer.echo("Site FTE calculated successfully!")


@app.command("calculate-subregion")
def calculate_subregion_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
):
    """Calculate subregion-level FTE"""
    asyncio.run(calculate_subregion_fte(dry_run=dry_run))
    typer.echo("Subregion FTE calculated successfully!")


@app.command("final-forecast")
def final_forecast_cmd(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Simulate without making changes"
    ),
):
    """Generate final forecast"""
    asyncio.run(final_forecast(dry_run=dry_run))
    typer.echo("Final forecast generated successfully!")


async def import_task_listing(dry_run: bool = False, force: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.import_task_listing_standalone(dry_run=dry_run, force=force)


async def import_geographic_ssu_data(dry_run: bool = False, force: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.import_geographic_ssu_data_standalone(dry_run=dry_run, force=force)


async def calculate_country_fte(dry_run: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.calculate_country_fte_standalone(dry_run=dry_run)


async def calculate_site_fte(dry_run: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.calculate_site_fte_standalone(dry_run=dry_run)


async def calculate_subregion_fte(dry_run: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.calculate_subregion_fte_standalone(dry_run=dry_run)


async def final_forecast(dry_run: bool = False):
    from app.services.fte import FTEService

    service = FTEService()
    await service.final_forecast_standalone(dry_run=dry_run)
