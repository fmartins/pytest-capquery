"""
Snapshot.
"""
from pathlib import Path
from typing import Optional


class SnapshotManager:
    def __init__(self, nodeid: str, test_path: Path, update_mode: bool):
        self.nodeid = nodeid
        self.update_mode = update_mode

        self.snapshot_dir = test_path.parent / "__capquery_snapshots__" / test_path.stem

        safe_name = nodeid.split("::")[-1].replace("[", "_").replace("]", "").replace("/", "_")
        self.snapshot_file = self.snapshot_dir / f"{safe_name}.sql"

    def save(self, content: str) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.write_text(content, encoding="utf-8")

    def load(self) -> Optional[str]:
        if not self.snapshot_file.exists():
            return None
        return self.snapshot_file.read_text(encoding="utf-8")
