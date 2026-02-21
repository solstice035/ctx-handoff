"""Snapshot storage and retrieval."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from .snapshot import Snapshot


class SnapshotNotFoundError(Exception):
    """Raised when a snapshot cannot be found."""
    pass


class SnapshotStorage:
    """Handles saving and loading snapshots."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize storage with base path."""
        if base_path is None:
            base_path = Path.home() / '.ctx-handoff'
        
        self.base_path = base_path
        self.snapshots_path = base_path / 'snapshots'
        self.index_path = base_path / 'index.json'
        
        # Ensure directories exist
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the snapshot index."""
        if not self.index_path.exists():
            return {'snapshots': []}
        
        with open(self.index_path, 'r') as f:
            return json.load(f)
    
    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save the snapshot index."""
        with open(self.index_path, 'w') as f:
            json.dump(index, f, indent=2)
    
    def save_snapshot(self, snapshot: Snapshot) -> str:
        """
        Save a snapshot to storage.
        Returns the snapshot ID.
        """
        # Create repo-specific directory
        repo_dir = self.snapshots_path / snapshot.repo_name
        repo_dir.mkdir(exist_ok=True)
        
        # Create filename with timestamp
        timestamp_str = snapshot.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp_str}_{snapshot.snapshot_id[:8]}.json"
        snapshot_path = repo_dir / filename
        
        # Save snapshot
        with open(snapshot_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2)
        
        # Update index
        index = self._load_index()
        index['snapshots'].append({
            'id': snapshot.snapshot_id,
            'short_id': snapshot.snapshot_id[:8],
            'timestamp': snapshot.timestamp.isoformat(),
            'repo_name': snapshot.repo_name,
            'branch': snapshot.branch,
            'tag': snapshot.tag,
            'token_count': snapshot.token_count,
            'path': str(snapshot_path.relative_to(self.base_path)),
        })
        self._save_index(index)
        
        return snapshot.snapshot_id[:8]
    
    def load_snapshot(self, snapshot_id: str) -> Snapshot:
        """Load a snapshot by ID (full or short)."""
        index = self._load_index()
        
        # Find snapshot in index
        snapshot_entry = None
        for entry in index['snapshots']:
            if entry['id'].startswith(snapshot_id) or entry['short_id'] == snapshot_id:
                snapshot_entry = entry
                break
        
        if not snapshot_entry:
            raise SnapshotNotFoundError(f"Snapshot '{snapshot_id}' not found")
        
        # Load snapshot file
        snapshot_path = self.base_path / snapshot_entry['path']
        if not snapshot_path.exists():
            raise SnapshotNotFoundError(f"Snapshot file not found: {snapshot_path}")
        
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        
        return Snapshot.from_dict(data)
    
    def get_latest_snapshot(self) -> Optional[Snapshot]:
        """Get the most recent snapshot."""
        index = self._load_index()
        
        if not index['snapshots']:
            return None
        
        # Sort by timestamp (most recent first)
        sorted_snapshots = sorted(
            index['snapshots'],
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        latest = sorted_snapshots[0]
        return self.load_snapshot(latest['short_id'])
    
    def list_snapshots(self) -> List[Snapshot]:
        """List all snapshots, sorted by timestamp (most recent first)."""
        index = self._load_index()
        
        # Sort by timestamp
        sorted_entries = sorted(
            index['snapshots'],
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        # Load snapshots
        snapshots = []
        for entry in sorted_entries:
            try:
                snapshot = self.load_snapshot(entry['short_id'])
                snapshots.append(snapshot)
            except SnapshotNotFoundError:
                # Skip missing snapshots
                continue
        
        return snapshots
    
    def delete_snapshot(self, snapshot_id: str) -> None:
        """Delete a snapshot by ID."""
        index = self._load_index()
        
        # Find and remove from index
        snapshot_entry = None
        for i, entry in enumerate(index['snapshots']):
            if entry['id'].startswith(snapshot_id) or entry['short_id'] == snapshot_id:
                snapshot_entry = index['snapshots'].pop(i)
                break
        
        if not snapshot_entry:
            raise SnapshotNotFoundError(f"Snapshot '{snapshot_id}' not found")
        
        # Delete file
        snapshot_path = self.base_path / snapshot_entry['path']
        if snapshot_path.exists():
            snapshot_path.unlink()
        
        # Save updated index
        self._save_index(index)
