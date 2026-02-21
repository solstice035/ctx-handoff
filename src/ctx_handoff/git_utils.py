"""Git operations using GitPython."""

from pathlib import Path
from typing import List, Dict, Optional
import os

from git import Repo, InvalidGitRepositoryError, GitCommandError


class GitError(Exception):
    """Base exception for git-related errors."""
    pass


def get_repo_root(path: Optional[Path] = None) -> Path:
    """Get the root directory of the git repository."""
    if path is None:
        path = Path.cwd()
    
    try:
        repo = Repo(path, search_parent_directories=True)
        return Path(repo.working_dir)
    except InvalidGitRepositoryError:
        raise GitError("Not a git repository (or any parent up to mount point)")


def get_repo_name(repo_path: Path) -> str:
    """Get the repository name."""
    try:
        repo = Repo(repo_path)
        # Try to get name from remote URL
        if repo.remotes:
            url = repo.remotes.origin.url
            # Extract repo name from URL
            name = url.rstrip('/').split('/')[-1]
            if name.endswith('.git'):
                name = name[:-4]
            return name
        # Fall back to directory name
        return repo_path.name
    except Exception:
        return repo_path.name


def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name."""
    try:
        repo = Repo(repo_path)
        if repo.head.is_detached:
            return f"detached@{repo.head.commit.hexsha[:8]}"
        return repo.active_branch.name
    except Exception as e:
        raise GitError(f"Failed to get current branch: {e}")


def get_recent_commits(repo_path: Path, limit: int = 10) -> List[Dict[str, str]]:
    """Get recent commits."""
    try:
        repo = Repo(repo_path)
        commits = []
        
        # Handle empty repository
        try:
            commit_iter = repo.iter_commits(max_count=limit)
        except GitCommandError:
            return []
        
        for commit in commit_iter:
            commits.append({
                'hash': commit.hexsha[:8],
                'message': commit.message.strip().split('\n')[0],
                'author': commit.author.name,
                'date': commit.committed_datetime.isoformat(),
            })
        
        return commits
    except Exception as e:
        raise GitError(f"Failed to get recent commits: {e}")


def get_staged_changes(repo_path: Path) -> str:
    """Get staged changes (diff)."""
    try:
        repo = Repo(repo_path)
        
        # Get staged diff
        try:
            diff = repo.git.diff('--cached', '--stat')
            if not diff:
                return "(no staged changes)"
            return diff
        except GitCommandError:
            return "(no staged changes)"
            
    except Exception as e:
        raise GitError(f"Failed to get staged changes: {e}")


def get_unstaged_changes(repo_path: Path) -> str:
    """Get unstaged changes (diff)."""
    try:
        repo = Repo(repo_path)
        
        # Get unstaged diff
        try:
            diff = repo.git.diff('--stat')
            if not diff:
                return "(no unstaged changes)"
            return diff
        except GitCommandError:
            return "(no unstaged changes)"
            
    except Exception as e:
        raise GitError(f"Failed to get unstaged changes: {e}")


def get_file_tree(repo_path: Path, max_depth: int = 3) -> str:
    """Get a tree representation of the repository files."""
    try:
        repo = Repo(repo_path)
        
        # Use git ls-tree for tracked files
        try:
            tree_output = repo.git.execute(['git', 'ls-tree', '-r', '--name-only', 'HEAD'])
            files = tree_output.strip().split('\n') if tree_output else []
        except GitCommandError:
            # Empty repository
            files = []
        
        if not files:
            return "(empty repository)"
        
        # Build tree structure
        tree_lines = []
        prev_parts = []
        
        for file_path in sorted(files):
            parts = file_path.split('/')
            
            # Only show up to max_depth
            if len(parts) > max_depth:
                continue
            
            # Find common prefix with previous path
            common_len = 0
            for i, (prev, curr) in enumerate(zip(prev_parts, parts)):
                if prev == curr:
                    common_len = i + 1
                else:
                    break
            
            # Add new parts
            for i in range(common_len, len(parts)):
                indent = "  " * i
                prefix = "└─ " if i == len(parts) - 1 else "├─ "
                tree_lines.append(f"{indent}{prefix}{parts[i]}")
            
            prev_parts = parts
        
        return '\n'.join(tree_lines[:100])  # Limit to 100 lines
        
    except Exception as e:
        raise GitError(f"Failed to get file tree: {e}")


def get_recently_modified_files(repo_path: Path, limit: int = 20) -> List[Path]:
    """Get recently modified files in the repository."""
    try:
        repo = Repo(repo_path)
        
        # Get files from recent commits
        files_with_time = {}
        
        try:
            for commit in repo.iter_commits(max_count=50):
                for item in commit.stats.files.keys():
                    file_path = repo_path / item
                    if file_path.exists() and file_path.is_file():
                        if item not in files_with_time:
                            files_with_time[item] = commit.committed_date
        except GitCommandError:
            # Empty repository
            pass
        
        # Also include modified files in working directory
        try:
            changed_files = [item.a_path for item in repo.index.diff(None)]
            for item in changed_files:
                file_path = repo_path / item
                if file_path.exists() and file_path.is_file():
                    files_with_time[item] = os.path.getmtime(file_path)
        except Exception:
            pass
        
        # Sort by modification time (most recent first)
        sorted_files = sorted(
            files_with_time.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return Path objects
        result = []
        for file_rel_path, _ in sorted_files[:limit]:
            file_path = repo_path / file_rel_path
            if file_path.exists():
                result.append(file_path)
        
        return result
        
    except Exception as e:
        raise GitError(f"Failed to get recently modified files: {e}")
