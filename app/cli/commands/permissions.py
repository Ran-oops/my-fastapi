import asyncio

import typer


app = typer.Typer(help="Permission management commands")


@app.command("list")
def list_permissions():
    """List all permissions"""
    permissions = asyncio.run(_list_permissions())
    for perm in permissions:
        typer.echo(f"  - {perm['id']}: {perm['name']} ({perm['code']})")


@app.command("create")
def create_permission(
    name: str = typer.Option(..., "--name", "-n", help="Permission name"),
    code: str = typer.Option(..., "--code", "-c", help="Permission code"),
    description: str = typer.Option(None, "--description", "-d", help="Permission description"),
):
    """Create a new permission"""
    permission = asyncio.run(_create_permission(name, code, description))
    typer.echo(f"Permission created: {permission['id']} - {permission['name']} ({permission['code']})")


@app.command("check")
def check_permission(
    user_id: int = typer.Option(..., "--user-id", "-u", help="User ID"),
    code: str = typer.Option(..., "--code", "-c", help="Permission code"),
):
    """Check if a user has a specific permission"""
    has_permission = asyncio.run(_check_permission(user_id, code))
    if has_permission:
        typer.echo(f"✓ User {user_id} has permission '{code}'")
    else:
        typer.echo(f"✗ User {user_id} does not have permission '{code}'")


async def _list_permissions():
    from app.modules.shared.db import UserSessionLocal
    from app.modules.roles.service import permission_service

    async with UserSessionLocal() as db:
        permissions = await permission_service.get_permissions(db)
        return [{"id": p.id, "name": p.name, "code": p.code} for p in permissions]


async def _create_permission(name: str, code: str, description: str | None):
    from app.modules.shared.db import UserSessionLocal
    from app.modules.roles.schemas import PermissionCreate
    from app.modules.roles.service import permission_service

    async with UserSessionLocal() as db:
        permission_in = PermissionCreate(name=name, code=code, description=description)
        permission = await permission_service.create_permission(db, permission_in)
        return {"id": permission.id, "name": permission.name, "code": permission.code}


async def _check_permission(user_id: int, code: str):
    from app.modules.shared.db import UserSessionLocal
    from app.modules.roles.service import role_service

    async with UserSessionLocal() as db:
        return await role_service.check_user_permission(db, user_id, code)
