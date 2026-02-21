"""CLI interface for ctx-handoff using Typer."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .snapshot import create_snapshot, SnapshotConfig
from .storage import SnapshotStorage, SnapshotNotFoundError
from .formatters import format_markdown, format_json
from .git_utils import get_repo_root, GitError

app = typer.Typer(
    name="ctx",
    help="Capture development context from git repos into portable handoff documents for AI coding assistants.",
    add_completion=False,
)
console = Console()


@app.command()
def snap(
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Tag this snapshot for easy reference"),
    budget: int = typer.Option(4000, "--budget", "-b", help="Token budget for snapshot content"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save snapshot to specific file"),
    json_only: bool = typer.Option(False, "--json", help="Output JSON format only"),
    markdown_only: bool = typer.Option(False, "--markdown", help="Output Markdown format only"),
) -> None:
    """Capture current git repo context into a snapshot."""
    try:
        # Get repo root
        repo_path = get_repo_root()
        
        # Create snapshot config
        config = SnapshotConfig(
            repo_path=repo_path,
            token_budget=budget,
            tag=tag,
        )
        
        # Create snapshot
        with console.status("[bold green]Creating snapshot..."):
            snapshot = create_snapshot(config)
        
        # Save snapshot
        storage = SnapshotStorage()
        snapshot_id = storage.save_snapshot(snapshot)
        
        # Format output
        if json_only:
            output_text = format_json(snapshot)
            format_type = "JSON"
        elif markdown_only:
            output_text = format_markdown(snapshot)
            format_type = "Markdown"
        else:
            # Default: both formats saved, display markdown
            output_text = format_markdown(snapshot)
            format_type = "Markdown"
            # Also save JSON
            json_output = format_json(snapshot)
        
        # Save to file if requested
        if output:
            output.write_text(output_text)
            console.print(f"[green]✓[/green] Snapshot saved to {output}")
        
        # Display summary
        console.print()
        console.print(Panel.fit(
            f"[bold green]Snapshot Created[/bold green]\n\n"
            f"ID: [cyan]{snapshot_id}[/cyan]\n"
            f"Repo: [yellow]{snapshot.repo_name}[/yellow]\n"
            f"Branch: [blue]{snapshot.branch}[/blue]\n"
            f"Tokens: [magenta]{snapshot.token_count}[/magenta] / {budget}\n"
            f"Tag: {tag or '[dim]none[/dim]'}",
            title="Context Snapshot",
        ))
        
        if snapshot.truncated:
            console.print("[yellow]⚠[/yellow]  Content was truncated to fit token budget", style="yellow")
        
        console.print(f"\n[dim]Saved to ~/.ctx-handoff/snapshots/[/dim]")
        console.print(f"[dim]Use 'ctx show {snapshot_id}' to view or 'ctx copy {snapshot_id}' to copy to clipboard[/dim]")
        
    except GitError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="red")
        raise typer.Exit(1)


@app.command()
def show(
    snapshot_id: Optional[str] = typer.Argument(None, help="Snapshot ID to display (default: latest)"),
) -> None:
    """Display a snapshot in the terminal with rich formatting."""
    try:
        storage = SnapshotStorage()
        
        # Get snapshot
        if snapshot_id:
            snapshot = storage.load_snapshot(snapshot_id)
        else:
            snapshot = storage.get_latest_snapshot()
            if not snapshot:
                console.print("[yellow]No snapshots found.[/yellow]")
                raise typer.Exit(0)
        
        # Format and display
        from .formatters import format_rich
        format_rich(snapshot, console)
        
    except SnapshotNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="red")
        raise typer.Exit(1)


@app.command()
def copy(
    snapshot_id: Optional[str] = typer.Argument(None, help="Snapshot ID to copy (default: latest)"),
) -> None:
    """Copy snapshot Markdown to clipboard."""
    import subprocess
    import platform
    
    try:
        storage = SnapshotStorage()
        
        # Get snapshot
        if snapshot_id:
            snapshot = storage.load_snapshot(snapshot_id)
        else:
            snapshot = storage.get_latest_snapshot()
            if not snapshot:
                console.print("[yellow]No snapshots found.[/yellow]")
                raise typer.Exit(0)
        
        # Format as markdown
        markdown = format_markdown(snapshot)
        
        # Determine clipboard command based on platform
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
                process.communicate(markdown.encode('utf-8'))
            elif system == "Linux":
                # Try xclip first, then xsel
                try:
                    process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                    process.communicate(markdown.encode('utf-8'))
                except FileNotFoundError:
                    process = subprocess.Popen(['xsel', '--clipboard', '--input'], stdin=subprocess.PIPE)
                    process.communicate(markdown.encode('utf-8'))
            elif system == "Windows":
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                process.communicate(markdown.encode('utf-16'))
            else:
                console.print(f"[red]Clipboard not supported on {system}[/red]")
                raise typer.Exit(1)
            
            console.print(f"[green]✓[/green] Snapshot copied to clipboard!")
            console.print(f"[dim]ID: {snapshot.snapshot_id}[/dim]")
            
        except FileNotFoundError:
            console.print("[red]Error:[/red] Clipboard utility not found.", style="red")
            console.print("[yellow]On Linux, install xclip or xsel:[/yellow]")
            console.print("  sudo apt-get install xclip")
            console.print("  # or")
            console.print("  sudo apt-get install xsel")
            raise typer.Exit(1)
            
    except SnapshotNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="red")
        raise typer.Exit(1)


@app.command()
def list() -> None:
    """List all saved snapshots."""
    try:
        storage = SnapshotStorage()
        snapshots = storage.list_snapshots()
        
        if not snapshots:
            console.print("[yellow]No snapshots found.[/yellow]")
            return
        
        # Create table
        table = Table(title="Context Snapshots", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Timestamp", style="green")
        table.add_column("Repo", style="yellow")
        table.add_column("Branch", style="blue")
        table.add_column("Tag", style="magenta")
        table.add_column("Tokens", justify="right", style="white")
        
        for snap in snapshots:
            table.add_row(
                snap.snapshot_id[:8],
                snap.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                snap.repo_name,
                snap.branch,
                snap.tag or "[dim]-[/dim]",
                str(snap.token_count),
            )
        
        console.print(table)
        console.print(f"\n[dim]Total: {len(snapshots)} snapshot(s)[/dim]")
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="red")
        raise typer.Exit(1)


@app.command()
def resume(
    snapshot_id: Optional[str] = typer.Argument(None, help="Snapshot ID to resume (default: latest)"),
    tool: str = typer.Option("claude", "--tool", "-t", help="AI tool to optimize for (claude|gpt|gemini)"),
) -> None:
    """Generate a resume prompt optimized for a specific AI tool."""
    try:
        storage = SnapshotStorage()
        
        # Get snapshot
        if snapshot_id:
            snapshot = storage.load_snapshot(snapshot_id)
        else:
            snapshot = storage.get_latest_snapshot()
            if not snapshot:
                console.print("[yellow]No snapshots found.[/yellow]")
                raise typer.Exit(0)
        
        # Generate resume prompt
        from .formatters import format_resume_prompt
        prompt = format_resume_prompt(snapshot, tool)
        
        console.print(Panel(prompt, title=f"Resume Prompt for {tool.upper()}", border_style="green"))
        
    except SnapshotNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}", style="red")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}", style="red")
        raise typer.Exit(1)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
