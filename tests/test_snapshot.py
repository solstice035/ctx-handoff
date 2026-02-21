"""Tests for snapshot creation."""

import pytest
from pathlib import Path
from ctx_handoff.snapshot import create_snapshot, SnapshotConfig, find_todos_fixmes


def test_find_todos_fixmes():
    """Test TODO/FIXME extraction."""
    content = """
def foo():
    # TODO: implement this
    pass

def bar():
    # FIXME: this is broken
    return None
    
# NOTE: important note here
"""
    
    todos = find_todos_fixmes(Path("test.py"), content)
    
    assert len(todos) == 3
    assert todos[0]['type'] == 'TODO'
    assert todos[0]['line'] == 3
    assert 'implement this' in todos[0]['text']
    
    assert todos[1]['type'] == 'FIXME'
    assert todos[1]['line'] == 7
    
    assert todos[2]['type'] == 'NOTE'


def test_snapshot_config_defaults():
    """Test SnapshotConfig default values."""
    config = SnapshotConfig(repo_path=Path("/tmp/test"))
    
    assert config.token_budget == 4000
    assert config.tag is None
    assert config.max_commits == 10
    assert config.ctxignore_patterns == []


def test_snapshot_to_dict():
    """Test snapshot serialization."""
    from datetime import datetime
    from ctx_handoff.snapshot import Snapshot
    
    snapshot = Snapshot(
        snapshot_id="test123",
        timestamp=datetime.now(),
        repo_name="test-repo",
        repo_path="/tmp/test",
        branch="main",
        last_commit=None,
        recent_commits=[],
        staged_changes="",
        unstaged_changes="",
        file_tree="",
        key_files=[],
        todos=[],
        tag=None,
        token_count=100,
        truncated=False,
    )
    
    data = snapshot.to_dict()
    
    assert data['snapshot_id'] == "test123"
    assert data['repo_name'] == "test-repo"
    assert data['token_count'] == 100
    assert isinstance(data['timestamp'], str)
