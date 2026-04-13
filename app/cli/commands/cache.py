"""Cache management CLI commands.

Usage:
    manage cache info          # Show cache statistics
    manage cache clear       # Clear all cache (use with caution!)
    manage cache delete <key>  # Delete specific cache key
    manage cache delete-pattern <pattern>  # Delete keys by pattern
"""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from app.core.cache import (
    cache_manager,
    clear_cache,
    delete_cache,
    delete_cache_pattern,
    get_cache,
    get_cache_info,
    init_cache,
)

app = typer.Typer(help="Cache management commands")
console = Console()


@app.callback()
def callback():
    """Cache management commands."""
    pass


@app.command("info")
def cache_info():
    """Show cache connection information and statistics."""

    async def _show_info():
        await init_cache()
        try:
            info = await get_cache_info()

            table = Table(title="Cache Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            for key, value in info.items():
                table.add_row(key, str(value))

            console.print(table)

            # Show Redis URL (sanitized)
            from app.core.config import settings

            redis_url = settings.REDIS_CACHE_URL
            if "@" in redis_url:
                redis_url = redis_url.split("@")[-1]
            console.print(f"\n[yellow]Redis URL:[/yellow] redis://{redis_url}")
            console.print(f"[yellow]Serializer:[/yellow] {settings.CACHE_SERIALIZER}")
            console.print(f"[yellow]Default TTL:[/yellow] {settings.CACHE_DEFAULT_TTL}s")

        finally:
            await cache_manager.close()

    asyncio.run(_show_info())


@app.command("get")
def cache_get(
    key: str = typer.Argument(..., help="Cache key to retrieve"),
):
    """Get value from cache by key."""

    async def _get():
        await init_cache()
        try:
            value = await get_cache(key)
            if value is not None:
                console.print(f"[green]Cache hit![/green]")
                console.print(f"[cyan]Key:[/cyan] {key}")
                console.print(f"[cyan]Value:[/cyan] {value}")
            else:
                console.print(f"[yellow]Cache miss[/yellow] - key '{key}' not found")
        finally:
            await cache_manager.close()

    asyncio.run(_get())


@app.command("set")
def cache_set(
    key: str = typer.Argument(..., help="Cache key"),
    value: str = typer.Argument(..., help="Cache value (JSON string)"),
    ttl: int = typer.Option(300, "--ttl", "-t", help="Time-to-live in seconds"),
):
    """Set a cache key with value."""
    import json

    async def _set():
        await init_cache()
        try:
            # Try to parse as JSON
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value

            success = await cache_manager.redis.setex(
                key,
                ttl,
                json.dumps(parsed_value),
            )
            if success:
                console.print(f"[green]Cache set successfully![/green]")
                console.print(f"[cyan]Key:[/cyan] {key}")
                console.print(f"[cyan]TTL:[/cyan] {ttl}s")
            else:
                console.print(f"[red]Failed to set cache[/red]")
        finally:
            await cache_manager.close()

    asyncio.run(_set())


@app.command("delete")
def cache_delete(
    key: str = typer.Argument(..., help="Cache key to delete"),
):
    """Delete a specific cache key."""

    async def _delete():
        await init_cache()
        try:
            existed = await delete_cache(key)
            if existed:
                console.print(f"[green]Deleted key:[/green] {key}")
            else:
                console.print(f"[yellow]Key not found:[/yellow] {key}")
        finally:
            await cache_manager.close()

    asyncio.run(_delete())


@app.command("delete-pattern")
def cache_delete_pattern(
    pattern: str = typer.Argument(..., help="Pattern to match (e.g., 'users:*')"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show keys that would be deleted without deleting"),
):
    """Delete cache keys matching a pattern."""

    async def _delete_pattern():
        await init_cache()
        try:
            if dry_run:
                # Scan and show matching keys
                cursor = 0
                keys = []
                while True:
                    cursor, batch = await cache_manager.redis.scan(cursor, match=pattern, count=100)
                    keys.extend(batch)
                    if cursor == 0:
                        break

                if keys:
                    console.print(f"[yellow]Keys matching '{pattern}' (dry run):[/yellow]")
                    for key in keys:
                        console.print(f"  - {key.decode() if isinstance(key, bytes) else key}")
                    console.print(f"\n[green]Total: {len(keys)} keys[/green]")
                else:
                    console.print(f"[yellow]No keys matching pattern: {pattern}[/yellow]")
            else:
                deleted = await delete_cache_pattern(pattern)
                if deleted > 0:
                    console.print(f"[green]Deleted {deleted} keys matching pattern:[/green] {pattern}")
                else:
                    console.print(f"[yellow]No keys matching pattern: {pattern}[/yellow]")
        finally:
            await cache_manager.close()

    asyncio.run(_delete_pattern())


@app.command("clear")
def cache_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Force clear without confirmation"),
):
    """Clear all cache entries (use with extreme caution!)."""

    if not force:
        confirm = typer.confirm("Are you sure you want to clear ALL cache entries? This cannot be undone!")
        if not confirm:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit()

    async def _clear():
        await init_cache()
        try:
            success = await clear_cache()
            if success:
                console.print("[green]Cache cleared successfully![/green]")
            else:
                console.print("[red]Failed to clear cache[/red]")
        finally:
            await cache_manager.close()

    asyncio.run(_clear())


@app.command("keys")
def cache_keys(
    pattern: str = typer.Argument("*", help="Pattern to match (default: '*')"),
    limit: int = typer.Option(100, "--limit", "-n", help="Maximum number of keys to show"),
):
    """List cache keys matching a pattern."""

    async def _list_keys():
        await init_cache()
        try:
            cursor = 0
            keys = []
            while len(keys) < limit:
                cursor, batch = await cache_manager.redis.scan(cursor, match=pattern, count=min(100, limit - len(keys)))
                keys.extend(batch)
                if cursor == 0:
                    break

            if keys:
                table = Table(title=f"Cache Keys (pattern: {pattern})")
                table.add_column("#", style="dim")
                table.add_column("Key", style="cyan")
                table.add_column("TTL", style="green")
                table.add_column("Size", style="yellow")

                for i, key in enumerate(keys[:limit], 1):
                    key_str = key.decode() if isinstance(key, bytes) else key
                    ttl = await cache_manager.redis.ttl(key)
                    size = await cache_manager.redis.memory_usage(key) or 0
                    table.add_row(
                        str(i),
                        key_str,
                        f"{ttl}s" if ttl > 0 else "no expiry",
                        f"{size} bytes",
                    )

                console.print(table)
                if len(keys) > limit:
                    console.print(f"[dim]... and {len(keys) - limit} more keys[/dim]")
            else:
                console.print(f"[yellow]No keys matching pattern: {pattern}[/yellow]")
        finally:
            await cache_manager.close()

    asyncio.run(_list_keys())


@app.command("stats")
def cache_stats():
    """Show detailed cache statistics."""

    async def _stats():
        await init_cache()
        try:
            # Get Redis INFO
            info = await cache_manager.redis.info()

            table = Table(title="Cache Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            # Memory
            table.add_row("Used Memory", info.get("used_memory_human", "N/A"))
            table.add_row("Peak Memory", info.get("used_memory_peak_human", "N/A"))
            table.add_row("Memory Fragmentation", f"{info.get('mem_fragmentation_ratio', 'N/A')}x")

            # Connections
            table.add_row("Connected Clients", str(info.get("connected_clients", "N/A")))
            table.add_row("Blocked Clients", str(info.get("blocked_clients", "N/A")))

            # Statistics
            table.add_row("Total Commands", str(info.get("total_commands_processed", "N/A")))
            table.add_row("Keyspace Hits", str(info.get("keyspace_hits", "N/A")))
            table.add_row("Keyspace Misses", str(info.get("keyspace_misses", "N/A")))

            # Calculate hit rate
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            total = hits + misses
            if total > 0:
                hit_rate = (hits / total) * 100
                table.add_row("Hit Rate", f"{hit_rate:.2f}%")

            # Uptime
            uptime_seconds = info.get("uptime_in_seconds", 0)
            uptime_hours = uptime_seconds // 3600
            table.add_row("Uptime", f"{uptime_hours} hours")

            console.print(table)
        finally:
            await cache_manager.close()

    asyncio.run(_stats())
