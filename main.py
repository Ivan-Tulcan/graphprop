"""
Synthetic Document Factory — CLI Entrypoint.

Provides a command-line interface to trigger the full document
generation pipeline (seed data → skeleton → prose → PDF).

Usage:
    python main.py --doc-type rfp --project-id PRJ-001 --count 1
    python main.py --doc-type project_history --project-id PRJ-004 --count 3
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = Path(__file__).resolve().parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config.settings import settings
from src.exceptions import SDFError
from src.formatting.renderer import PDFRenderer
from src.logger import setup_logger
from src.workflow.generator import DocumentGenerator

logger = setup_logger("cli")
console = Console()

app = typer.Typer(
    name="sdf",
    help="Synthetic Document Factory — Generate banking-domain documents for GraphRAG.",
    add_completion=False,
)


@app.command()
def generate(
    doc_type: str = typer.Option(
        ...,
        "--doc-type",
        "-t",
        help="Document type: rfp, project_history, meeting_minutes",
    ),
    project_id: str = typer.Option(
        ...,
        "--project-id",
        "-p",
        help="Seed project ID (e.g. PRJ-001)",
    ),
    count: int = typer.Option(
        1,
        "--count",
        "-n",
        help="Number of documents to generate",
        min=1,
        max=100,
    ),
    output_dir: str = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for PDFs (defaults to output/)",
    ),
) -> None:
    """
    Generate synthetic banking documents.

    Triggers the full LangGraph pipeline: seed extraction → skeleton
    generation → prose drafting → compliance audit → PDF rendering.
    """
    console.print(Panel(
        f"[bold blue]Synthetic Document Factory[/bold blue]\n"
        f"Type: [cyan]{doc_type}[/cyan] | "
        f"Project: [cyan]{project_id}[/cyan] | "
        f"Count: [cyan]{count}[/cyan]",
        title="SDF",
        border_style="blue",
    ))

    # Validate doc_type
    valid_types = ["rfp", "project_history", "meeting_minutes", "technical_annex", "rfp_qa"]
    if doc_type not in valid_types:
        console.print(
            f"[red]Error:[/red] Invalid doc-type '{doc_type}'. "
            f"Valid types: {', '.join(valid_types)}"
        )
        raise typer.Exit(code=1)

    # Resolve output directory
    out_path = Path(output_dir) if output_dir else settings.OUTPUT_DIR
    out_path.mkdir(parents=True, exist_ok=True)

    generator = DocumentGenerator()
    renderer = PDFRenderer(output_dir=out_path)

    generated_files: list[Path] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for i in range(1, count + 1):
            task = progress.add_task(
                f"Generating {doc_type} {i}/{count}...", total=None
            )

            try:
                # Run the LangGraph pipeline
                result = generator.generate(
                    project_id=project_id,
                    doc_type=doc_type,
                )

                final_md = result.get("final_markdown", "")
                if not final_md:
                    console.print(f"[yellow]Warning:[/yellow] No content generated for document {i}")
                    progress.update(task, description=f"[yellow]Skipped {i}/{count}[/yellow]")
                    continue

                # Build metadata for XMP injection
                project_data = result.get("project", {})
                skeleton = result.get("skeleton", {})
                xmp_metadata = {
                    "title": skeleton.get("metadata", {}).get("title", f"{doc_type}_{project_id}"),
                    "document_type": doc_type,
                    "project_id": project_id,
                    "bank_id": project_data.get("bank_id", ""),
                    "stakeholder_ids": project_data.get("stakeholder_ids", []),
                }

                # Render PDF
                filename = f"{doc_type}_{project_id}_{i:03d}"
                pdf_path = renderer.render(
                    markdown=final_md,
                    filename=filename,
                    metadata=xmp_metadata,
                )
                generated_files.append(pdf_path)

                # Report token usage
                usage = result.get("token_usage", {})
                progress.update(
                    task,
                    description=(
                        f"[green]Done {i}/{count}[/green] — "
                        f"{usage.get('total_tokens', 0)} tokens"
                    ),
                )

            except SDFError as exc:
                console.print(f"[red]Error generating document {i}:[/red] {exc}")
                logger.exception("Document generation failed: %s", exc)
                progress.update(task, description=f"[red]Failed {i}/{count}[/red]")

    # Summary
    console.print()
    if generated_files:
        console.print(Panel(
            "\n".join(f"  [green]✓[/green] {f.name}" for f in generated_files),
            title=f"[bold green]{len(generated_files)} Document(s) Generated[/bold green]",
            border_style="green",
        ))
        console.print(f"Output directory: [cyan]{out_path.resolve()}[/cyan]")
    else:
        console.print("[yellow]No documents were generated.[/yellow]")


@app.command()
def seed() -> None:
    """Run the database seeder to populate seed entities."""
    console.print("[blue]Seeding database...[/blue]")
    from scripts.seed_db import seed_database
    seed_database()
    console.print("[green]Database seeded successfully.[/green]")


@app.command()
def list_projects() -> None:
    """List all projects in the seed database."""
    from src.database.models import get_session
    from src.database.repository import get_all_projects

    session = get_session()
    try:
        projects = get_all_projects(session)
        if not projects:
            console.print("[yellow]No projects found. Run 'seed' first.[/yellow]")
            return

        console.print(Panel("[bold]Seed Projects[/bold]", border_style="blue"))
        for p in projects:
            console.print(
                f"  [cyan]{p.project_id}[/cyan] | "
                f"{p.name} | "
                f"[dim]{p.status.value}[/dim] | "
                f"Bank: {p.bank_id}"
            )
    finally:
        session.close()


if __name__ == "__main__":
    app()
