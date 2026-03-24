import asyncio

import typer


app = typer.Typer(help="Role management commands")


@app.command("list")
def list_roles():
    """List all roles"""
    roles = asyncio.run(_list_roles())
    for role in roles:
        typer.echo(f"  - {role['id']}: {role['name']} ({role['description'] or 'No description'})")


@app.command("create")
def create_role(
    name: str = typer.Option(..., "--name", "-n", help="Role name"),
    description: str = typer.Option(None, "--description", "-d", help="Role description"),
):
    """Create a new role"""
    role = asyncio.run(_create_role(name, description))
    typer.echo(f"Role created: {role['id']} - {role['name']}")


@app.command("assign")
def assign_role(
    user_id: int = typer.Option(..., "--user-id", "-u", help="User ID"),
    role_id: int = typer.Option(..., "--role-id", "-r", help="Role ID"),
):
    """Assign a role to a user"""
    asyncio.run(_assign_role(user_id, role_id))
    typer.echo(f"Role {role_id} assigned to user {user_id}")


@app.command("remove")
def remove_role(
    user_id: int = typer.Option(..., "--user-id", "-u", help="User ID"),
    role_id: int = typer.Option(..., "--role-id", "-r", help="Role ID"),
):
    """Remove a role from a user"""
    asyncio.run(_remove_role(user_id, role_id))
    typer.echo(f"Role {role_id} removed from user {user_id}")


async def _list_roles():
    from app.db.session import UserSessionLocal
    from app.services.role import role_service

    async with UserSessionLocal() as db:
        roles = await role_service.get_roles(db)
        return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]


async def _create_role(name: str, description: str | None):
    from app.db.session import UserSessionLocal
    from app.schemas.role import RoleCreate
    from app.services.role import role_service

    async with UserSessionLocal() as db:
        role_in = RoleCreate(name=name, description=description)
        role = await role_service.create_role(db, role_in)
        return {"id": role.id, "name": role.name, "description": role.description}


async def _assign_role(user_id: int, role_id: int):
    from app.db.session import UserSessionLocal
    from app.services.role import role_service

    async with UserSessionLocal() as db:
        await role_service.assign_role_to_user(db, user_id, role_id)


async def _remove_role(user_id: int, role_id: int):
    from app.db.session import UserSessionLocal
    from app.services.role import role_service

    async with UserSessionLocal() as db:
        await role_service.remove_role_from_user(db, user_id, role_id)
