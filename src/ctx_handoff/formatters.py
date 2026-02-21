"""Output formatters for snapshots."""

import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

if TYPE_CHECKING:
    from .snapshot import Snapshot


def format_markdown(snapshot: 'Snapshot') -> str:
    """Format snapshot as Markdown."""
    lines = [
        f"# Context Handoff: {snapshot.repo_name}",
        "",
        "## Session Info",
        f"- **Branch:** {snapshot.branch}",
    ]
    
    if snapshot.last_commit:
        lines.append(f"- **Last commit:** {snapshot.last_commit['hash']} - {snapshot.last_commit['message']}")
    
    lines.extend([
        f"- **Timestamp:** {snapshot.timestamp.isoformat()}",
        f"- **Token count:** {snapshot.token_count}",
    ])
    
    if snapshot.tag:
        lines.append(f"- **Tag:** {snapshot.tag}")
    
    lines.extend([
        "",
        "## Recent Commits",
        "",
    ])
    
    if snapshot.recent_commits:
        for commit in snapshot.recent_commits:
            lines.append(f"- `{commit['hash']}` {commit['message']} - *{commit['author']}*")
    else:
        lines.append("*(no commits)*")
    
    lines.extend([
        "",
        "## Working State",
        "",
        "### Staged Changes",
        "```",
        snapshot.staged_changes,
        "```",
        "",
        "### Unstaged Changes",
        "```",
        snapshot.unstaged_changes,
        "```",
        "",
        "## File Tree",
        "```",
        snapshot.file_tree,
        "```",
        "",
    ])
    
    if snapshot.key_files:
        lines.extend([
            "## Key Files (recently modified)",
            "",
        ])
        
        for file_info in snapshot.key_files:
            lines.extend([
                f"### {file_info['path']}",
                f"```{file_info['language']}",
                file_info['content'],
                "```",
                "",
            ])
    
    if snapshot.todos:
        lines.extend([
            "## TODOs & FIXMEs",
            "",
        ])
        
        for todo in snapshot.todos:
            lines.append(f"- **{todo['type']}** ({todo['file']}:{todo['line']}): {todo['text']}")
        
        lines.append("")
    
    if snapshot.truncated:
        lines.extend([
            "",
            "---",
            "*Note: Content was truncated to fit within token budget.*",
        ])
    
    return '\n'.join(lines)


def format_json(snapshot: 'Snapshot') -> str:
    """Format snapshot as JSON."""
    return json.dumps(snapshot.to_dict(), indent=2)


def format_rich(snapshot: 'Snapshot', console: Console) -> None:
    """Format snapshot with Rich formatting for terminal display."""
    # Header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]{snapshot.repo_name}[/bold cyan]\n"
        f"Branch: [yellow]{snapshot.branch}[/yellow]\n"
        f"Timestamp: [green]{snapshot.timestamp.strftime('%Y-%m-%d %H:%M:%S')}[/green]\n"
        f"Tokens: [magenta]{snapshot.token_count}[/magenta]" +
        (f"\nTag: [blue]{snapshot.tag}[/blue]" if snapshot.tag else ""),
        title="Context Snapshot",
        border_style="cyan",
    ))
    
    # Recent commits
    if snapshot.recent_commits:
        console.print("\n[bold]Recent Commits[/bold]")
        for commit in snapshot.recent_commits[:5]:
            console.print(f"  [cyan]{commit['hash']}[/cyan] {commit['message']} [dim]- {commit['author']}[/dim]")
    
    # Staged changes
    if snapshot.staged_changes and snapshot.staged_changes != "(no staged changes)":
        console.print("\n[bold]Staged Changes[/bold]")
        console.print(Panel(snapshot.staged_changes, border_style="green"))
    
    # Unstaged changes
    if snapshot.unstaged_changes and snapshot.unstaged_changes != "(no unstaged changes)":
        console.print("\n[bold]Unstaged Changes[/bold]")
        console.print(Panel(snapshot.unstaged_changes, border_style="yellow"))
    
    # File tree
    if snapshot.file_tree and snapshot.file_tree != "(empty repository)":
        console.print("\n[bold]File Tree[/bold]")
        console.print(Panel(snapshot.file_tree, border_style="blue"))
    
    # Key files
    if snapshot.key_files:
        console.print("\n[bold]Key Files[/bold]")
        for file_info in snapshot.key_files[:3]:  # Show first 3
            console.print(f"\n[cyan]{file_info['path']}[/cyan]")
            syntax = Syntax(
                file_info['content'][:500],  # Truncate for display
                file_info['language'],
                theme="monokai",
                line_numbers=True,
            )
            console.print(syntax)
            if len(file_info['content']) > 500:
                console.print("[dim]... (truncated for display)[/dim]")
    
    # TODOs
    if snapshot.todos:
        console.print("\n[bold]TODOs & FIXMEs[/bold]")
        for todo in snapshot.todos[:10]:  # Show first 10
            console.print(f"  [yellow]{todo['type']}[/yellow] ({todo['file']}:{todo['line']}): {todo['text']}")
    
    if snapshot.truncated:
        console.print("\n[yellow]⚠ Content was truncated to fit within token budget[/yellow]")
    
    console.print()


def format_resume_prompt(snapshot: 'Snapshot', tool: str) -> str:
    """Generate a resume prompt optimized for a specific AI tool."""
    tool = tool.lower()
    
    if tool == "claude":
        prompt = f"""I'm resuming work on {snapshot.repo_name}. Here's the current context:

**Current State:**
- Branch: {snapshot.branch}
- Last commit: {snapshot.last_commit['message'] if snapshot.last_commit else 'N/A'}

**Recent Work:**
"""
        for commit in snapshot.recent_commits[:3]:
            prompt += f"- {commit['message']}\n"
        
        if snapshot.todos:
            prompt += "\n**Outstanding TODOs:**\n"
            for todo in snapshot.todos[:5]:
                prompt += f"- {todo['type']}: {todo['text']} ({todo['file']})\n"
        
        prompt += "\nPlease help me continue development. What should I focus on next?"
        
    elif tool == "gpt":
        prompt = f"""# Resuming Development: {snapshot.repo_name}

## Context
Branch: {snapshot.branch}
Last commit: {snapshot.last_commit['message'] if snapshot.last_commit else 'N/A'}

## Recent commits:
"""
        for commit in snapshot.recent_commits[:3]:
            prompt += f"- {commit['message']}\n"
        
        if snapshot.todos:
            prompt += "\n## Outstanding items:\n"
            for todo in snapshot.todos[:5]:
                prompt += f"- {todo['text']}\n"
        
        prompt += "\nWhat should I work on next?"
        
    elif tool == "gemini":
        prompt = f"""Resuming work on {snapshot.repo_name}

Current branch: {snapshot.branch}
Latest: {snapshot.last_commit['message'] if snapshot.last_commit else 'N/A'}

Recent changes:
"""
        for commit in snapshot.recent_commits[:3]:
            prompt += f"• {commit['message']}\n"
        
        if snapshot.todos:
            prompt += "\nTODOs:\n"
            for todo in snapshot.todos[:5]:
                prompt += f"• {todo['text']}\n"
        
        prompt += "\nSuggest next steps?"
        
    else:
        # Generic format
        prompt = format_markdown(snapshot)
    
    return prompt
