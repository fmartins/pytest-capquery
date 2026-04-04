"""
Disk physical snapshot resolution handlers for pytest-capquery.

This module is responsible for persisting and matching serialized chronological
transaction expectations directly against local `.sql` files enabling rapid
regression catching strategies effortlessly tracking complex system evolutions.
"""
from pathlib import Path
from typing import Optional


class SnapshotManager:
    """
    Handles physical interactions bridging captured SQL timelines mapping directly
    to file storage based on pytest test node invocations. Determines safe
    directory placements and translates update parameters down into physical overwrites.
    """
    def __init__(self, nodeid: str, test_path: Path, update_mode: bool) -> None:
        """
        Initializes the snapshot directory resolution against the host test.

        Args:
            nodeid (str): The unique pytest node identifier for the current test case.
            test_path (Path): The explicit file path to the current test module.
            update_mode (bool): Whether the system is currently instructed to overwrite snapshots.

        Returns:
            None
        """
        self.nodeid = nodeid
        self.update_mode = update_mode

        self.snapshot_dir = test_path.parent / "__capquery_snapshots__" / test_path.stem

        safe_name = nodeid.split("::")[-1].replace("[", "_").replace("]", "").replace("/", "_")
        self.snapshot_file = self.snapshot_dir / f"{safe_name}.sql"

    def save(self, content: str) -> None:
        """
        Ensures target directories exist and flushes string execution content reliably to disk.

        Args:
            content (str): The serialized snapshot payload string mapping assertion data.

        Returns:
            None
        """
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.snapshot_file.write_text(content, encoding="utf-8")

    def load(self) -> Optional[str]:
        """
        Retrieves established baseline markers, returning None seamlessly if expectations
        have not yet been initialized.

        Returns:
            Optional[str]: The raw payload retrieved directly from the disk file, or None if missing.
        """
        if not self.snapshot_file.exists():
            return None
        return self.snapshot_file.read_text(encoding="utf-8")
