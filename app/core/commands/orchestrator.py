from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar


class CommandStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CommandResult:
    command_name: str
    status: CommandStatus
    result: dict | None = None
    error: str | None = None


class CommandRegistry:
    """Registry for managing CLI commands"""

    _commands: ClassVar[dict[str, Callable]] = {}
    _orchestrations: ClassVar[dict[str, list[str]]] = {}

    @classmethod
    def register(cls, name: str, func: Callable) -> None:
        cls._commands[name] = func

    @classmethod
    def register_orchestration(cls, name: str, steps: list[str]) -> None:
        cls._orchestrations[name] = steps

    @classmethod
    def get(cls, name: str) -> Callable | None:
        return cls._commands.get(name)

    @classmethod
    def get_orchestration(cls, name: str) -> list[str] | None:
        return cls._orchestrations.get(name)

    @classmethod
    def list_commands(cls) -> list[str]:
        return list(cls._commands.keys())

    @classmethod
    def list_orchestrations(cls) -> list[str]:
        return list(cls._orchestrations.keys())


class CommandOrchestrator:
    """Orchestrator for running multiple commands in sequence"""

    @staticmethod
    async def run_sequence(
        commands: list[str],
        db=None,
        **kwargs,
    ) -> list[CommandResult]:
        results = []
        for command_name in commands:
            func = CommandRegistry.get(command_name)
            if func is None:
                results.append(
                    CommandResult(
                        command_name=command_name,
                        status=CommandStatus.FAILED,
                        error=f"Command '{command_name}' not found",
                    )
                )
                break

            try:
                if db:
                    result = await func(db, **kwargs)
                else:
                    result = await func(**kwargs)
                results.append(
                    CommandResult(
                        command_name=command_name,
                        status=CommandStatus.COMPLETED,
                        result=result,
                    )
                )
            except Exception as e:
                results.append(
                    CommandResult(
                        command_name=command_name,
                        status=CommandStatus.FAILED,
                        error=str(e),
                    )
                )
                break

        return results

    @staticmethod
    async def run_orchestration(
        orchestration_name: str,
        db=None,
        **kwargs,
    ) -> list[CommandResult]:
        steps = CommandRegistry.get_orchestration(orchestration_name)
        if steps is None:
            raise ValueError(f"Orchestration '{orchestration_name}' not found")
        return await CommandOrchestrator.run_sequence(steps, db=db, **kwargs)


registry = CommandRegistry()
orchestrator = CommandOrchestrator()


def register_fte_commands():
    from app.services.fte import FTEService

    CommandRegistry.register("import_task_listing", FTEService.import_task_listing)
    CommandRegistry.register("import_geographic_ssu_data", FTEService.import_geographic_ssu_data)
    CommandRegistry.register("calculate_country_fte", FTEService.calculate_country_fte)
    CommandRegistry.register("calculate_site_fte", FTEService.calculate_site_fte)
    CommandRegistry.register("calculate_subregion_fte", FTEService.calculate_subregion_fte)
    CommandRegistry.register("final_forecast", FTEService.final_forecast)

    CommandRegistry.register_orchestration(
        "calculate_fte",
        [
            "import_task_listing",
            "import_geographic_ssu_data",
            "calculate_country_fte",
            "calculate_site_fte",
            "calculate_subregion_fte",
            "final_forecast",
        ],
    )


register_fte_commands()
