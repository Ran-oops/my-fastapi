from datetime import UTC, datetime
from typing import Any


class FTEService:
    """FTE calculation service - supports both CLI and API calls"""

    @staticmethod
    async def import_task_listing_standalone(
        dry_run: bool = False, force: bool = False
    ) -> dict[str, Any]:
        result = {
            "action": "import_task_listing",
            "dry_run": dry_run,
            "force": force,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def import_geographic_ssu_data_standalone(
        dry_run: bool = False, force: bool = False
    ) -> dict[str, Any]:
        result = {
            "action": "import_geographic_ssu_data",
            "dry_run": dry_run,
            "force": force,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def calculate_country_fte_standalone(dry_run: bool = False) -> dict[str, Any]:
        result = {
            "action": "calculate_country_fte",
            "dry_run": dry_run,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def calculate_site_fte_standalone(dry_run: bool = False) -> dict[str, Any]:
        result = {
            "action": "calculate_site_fte",
            "dry_run": dry_run,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def calculate_subregion_fte_standalone(
        dry_run: bool = False,
    ) -> dict[str, Any]:
        result = {
            "action": "calculate_subregion_fte",
            "dry_run": dry_run,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def final_forecast_standalone(dry_run: bool = False) -> dict[str, Any]:
        result = {
            "action": "final_forecast",
            "dry_run": dry_run,
            "status": "completed",
            "records_processed": 0,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        return result

    @staticmethod
    async def import_task_listing(
        db, dry_run: bool = False, force: bool = False
    ) -> dict[str, Any]:
        return await FTEService.import_task_listing_standalone(
            dry_run=dry_run, force=force
        )

    @staticmethod
    async def import_geographic_ssu_data(
        db, dry_run: bool = False, force: bool = False
    ) -> dict[str, Any]:
        return await FTEService.import_geographic_ssu_data_standalone(
            dry_run=dry_run, force=force
        )

    @staticmethod
    async def calculate_country_fte(db, dry_run: bool = False) -> dict[str, Any]:
        return await FTEService.calculate_country_fte_standalone(dry_run=dry_run)

    @staticmethod
    async def calculate_site_fte(db, dry_run: bool = False) -> dict[str, Any]:
        return await FTEService.calculate_site_fte_standalone(dry_run=dry_run)

    @staticmethod
    async def calculate_subregion_fte(db, dry_run: bool = False) -> dict[str, Any]:
        return await FTEService.calculate_subregion_fte_standalone(dry_run=dry_run)

    @staticmethod
    async def final_forecast(db, dry_run: bool = False) -> dict[str, Any]:
        return await FTEService.final_forecast_standalone(dry_run=dry_run)

    @staticmethod
    async def calculate_fte_full(
        db, dry_run: bool = False, force: bool = False
    ) -> dict[str, Any]:
        """Orchestrator: runs all FTE calculation steps in sequence"""
        steps = [
            ("import_task_listing", FTEService.import_task_listing),
            ("import_geographic_ssu_data", FTEService.import_geographic_ssu_data),
            ("calculate_country_fte", FTEService.calculate_country_fte),
            ("calculate_site_fte", FTEService.calculate_site_fte),
            ("calculate_subregion_fte", FTEService.calculate_subregion_fte),
            ("final_forecast", FTEService.final_forecast),
        ]

        results = []
        for step_name, step_func in steps:
            if "import" in step_name:
                result = await step_func(db, dry_run=dry_run, force=force)
            else:
                result = await step_func(db, dry_run=dry_run)
            results.append(result)

        return {
            "action": "calculate_fte_full",
            "dry_run": dry_run,
            "status": "completed",
            "steps_completed": len(results),
            "results": results,
            "timestamp": datetime.now(UTC).isoformat(),
        }


fte_service = FTEService()
