"""Core snapshot creation logic."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from .git_utils import (
    get_repo_name,
    get_current_branch,
    get_recent_commits,
    get_staged_changes,
    get_unstaged_changes,
    get_recently_modified_files,
    get_file_tree,
)
from .token_budget import TokenBudget, estimate_tokens


@dataclass
class SnapshotConfig:
    """Configuration for creating a snapshot."""
    repo_path: Path
    token_budget: int = 4000
    tag: Optional[str] = None
    max_commits: int = 10
    ctxignore_patterns: List[str] = field(default_factory=list)


@dataclass
class Snapshot:
    """Represents a captured development context snapshot."""
    snapshot_id: str
    timestamp: datetime
    repo_name: str
    repo_path: str
    branch: str
    last_commit: Optional[Dict[str, str]]
    recent_commits: List[Dict[str, str]]
    staged_changes: str
    unstaged_changes: str
    file_tree: str
    key_files: List[Dict[str, str]]
    todos: List[Dict[str, Any]]
    tag: Optional[str]
    token_count: int
    truncated: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert snapshot to dictionary for JSON serialization."""
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp.isoformat(),
            'repo_name': self.repo_name,
            'repo_path': self.repo_path,
            'branch': self.branch,
            'last_commit': self.last_commit,
            'recent_commits': self.recent_commits,
            'staged_changes': self.staged_changes,
            'unstaged_changes': self.unstaged_changes,
            'file_tree': self.file_tree,
            'key_files': self.key_files,
            'todos': self.todos,
            'tag': self.tag,
            'token_count': self.token_count,
            'truncated': self.truncated,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Snapshot':
        """Create snapshot from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


def find_todos_fixmes(file_path: Path, content: str) -> List[Dict[str, Any]]:
    """Find TODO and FIXME comments in file content."""
    todos = []
    lines = content.split('\n')
    
    # Pattern to match TODO/FIXME comments
    pattern = re.compile(r'(TODO|FIXME|XXX|HACK|NOTE)[\s:]*(.+)', re.IGNORECASE)
    
    for line_num, line in enumerate(lines, 1):
        match = pattern.search(line)
        if match:
            todos.append({
                'file': str(file_path),
                'line': line_num,
                'type': match.group(1).upper(),
                'text': match.group(2).strip(),
            })
    
    return todos


def load_ctxignore(repo_path: Path) -> List[str]:
    """Load patterns from .ctxignore file if it exists."""
    ctxignore_path = repo_path / '.ctxignore'
    if not ctxignore_path.exists():
        return []
    
    patterns = []
    with open(ctxignore_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                patterns.append(line)
    
    return patterns


def should_ignore(file_path: Path, patterns: List[str]) -> bool:
    """Check if file should be ignored based on patterns."""
    from fnmatch import fnmatch
    
    path_str = str(file_path)
    for pattern in patterns:
        if fnmatch(path_str, pattern) or fnmatch(file_path.name, pattern):
            return True
    return False


def create_snapshot(config: SnapshotConfig) -> Snapshot:
    """Create a snapshot of the current repository state."""
    import hashlib
    
    repo_path = config.repo_path
    
    # Load .ctxignore patterns
    ctxignore_patterns = load_ctxignore(repo_path)
    all_ignore_patterns = config.ctxignore_patterns + ctxignore_patterns
    
    # Initialize token budget
    budget = TokenBudget(config.token_budget)
    
    # Gather basic git info (always included, high priority)
    repo_name = get_repo_name(repo_path)
    branch = get_current_branch(repo_path)
    recent_commits = get_recent_commits(repo_path, config.max_commits)
    
    last_commit = recent_commits[0] if recent_commits else None
    
    # Reserve tokens for basic info
    basic_info_tokens = estimate_tokens(f"{repo_name}{branch}")
    for commit in recent_commits:
        basic_info_tokens += estimate_tokens(f"{commit['hash']}{commit['message']}")
    
    budget.allocate(basic_info_tokens, "basic_info")
    
    # Get diffs (medium priority)
    staged_changes = get_staged_changes(repo_path)
    unstaged_changes = get_unstaged_changes(repo_path)
    
    staged_tokens = estimate_tokens(staged_changes)
    unstaged_tokens = estimate_tokens(unstaged_changes)
    
    if budget.can_allocate(staged_tokens + unstaged_tokens):
        budget.allocate(staged_tokens, "staged_changes")
        budget.allocate(unstaged_tokens, "unstaged_changes")
    else:
        # Truncate diffs if needed
        if budget.can_allocate(staged_tokens):
            budget.allocate(staged_tokens, "staged_changes")
        else:
            staged_changes = staged_changes[:budget.remaining * 4] + "\n... (truncated)"
            budget.allocate(budget.remaining, "staged_changes")
        unstaged_changes = "(truncated due to token budget)"
    
    # Get file tree
    file_tree = get_file_tree(repo_path)
    tree_tokens = estimate_tokens(file_tree)
    
    if budget.can_allocate(tree_tokens):
        budget.allocate(tree_tokens, "file_tree")
    else:
        file_tree = "(truncated due to token budget)"
    
    # Get recently modified files (low priority, most recently modified first)
    modified_files = get_recently_modified_files(repo_path, limit=20)
    
    key_files = []
    todos = []
    truncated = False
    
    for file_path in modified_files:
        # Skip ignored files
        if should_ignore(file_path, all_ignore_patterns):
            continue
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            file_tokens = estimate_tokens(content)
            
            # Check if we can fit this file
            if budget.can_allocate(file_tokens):
                budget.allocate(file_tokens, f"file:{file_path.name}")
                
                # Determine language for syntax highlighting
                suffix = file_path.suffix.lstrip('.')
                lang = suffix if suffix else 'text'
                
                key_files.append({
                    'path': str(file_path.relative_to(repo_path)),
                    'content': content,
                    'language': lang,
                })
                
                # Extract TODOs/FIXMEs
                file_todos = find_todos_fixmes(file_path.relative_to(repo_path), content)
                todos.extend(file_todos)
            else:
                truncated = True
                break
                
        except Exception:
            # Skip files that can't be read
            continue
    
    # Generate snapshot ID
    timestamp = datetime.now()
    snapshot_data = f"{repo_name}{branch}{timestamp.isoformat()}"
    snapshot_id = hashlib.sha256(snapshot_data.encode()).hexdigest()
    
    return Snapshot(
        snapshot_id=snapshot_id,
        timestamp=timestamp,
        repo_name=repo_name,
        repo_path=str(repo_path),
        branch=branch,
        last_commit=last_commit,
        recent_commits=recent_commits,
        staged_changes=staged_changes,
        unstaged_changes=unstaged_changes,
        file_tree=file_tree,
        key_files=key_files,
        todos=todos,
        tag=config.tag,
        token_count=budget.used,
        truncated=truncated,
    )
