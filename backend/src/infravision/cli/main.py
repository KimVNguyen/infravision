"""CLI commands for Infravision."""

import asyncio
from pathlib import Path
import typer
import uvicorn

cli = typer.Typer(
    name="infravision",
    help="Code visualization engine for Python and TypeScript/Node.js apps",
)


@cli.command("init-db")
def init_database() -> None:
    """Initialize PostgreSQL extensions and database tables."""
    from infravision.db.session import init_db

    typer.echo("Initializing database tables & extensions...")
    asyncio.run(init_db())
    typer.secho("Database initialized successfully!", fg=typer.colors.GREEN)


@cli.command("serve")
def serve(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = True,
) -> None:
    """Start the FastAPI backend server."""
    typer.echo(f"Starting Infravision API server on http://{host}:{port}")
    uvicorn.run("infravision.api.app:app", host=host, port=port, reload=reload)


@cli.command("index")
def index_repo(path: str = typer.Argument(".", help="Path to codebase")) -> None:
    """Index a Python or TypeScript/Node.js codebase directly."""
    from infravision.db.session import async_session_factory
    from infravision.indexer.pipeline import IndexingPipeline

    resolved = str(Path(path).resolve())
    typer.echo(f"Scanning and indexing codebase at: {resolved}")

    async def _run() -> None:
        async with async_session_factory() as session:
            pipeline = IndexingPipeline(session)
            repo = await pipeline.get_or_create_repo(resolved)
            stats = await pipeline.index_repository(repo.id)
            typer.secho(
                f"Successfully indexed '{repo.name}'!\n"
                f"  Files:   {stats['files']}\n"
                f"  Symbols: {stats['symbols']}\n"
                f"  Edges:   {stats['edges']}",
                fg=typer.colors.GREEN,
            )

    asyncio.run(_run())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
