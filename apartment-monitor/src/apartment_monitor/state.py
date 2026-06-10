from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load_seen(self) -> set[str]:
        if not self.path.exists():
            return set()
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return set(data.get("seen_listing_ids", []))

    def save_seen(self, seen: set[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump({"seen_listing_ids": sorted(seen)}, handle, indent=2)
            handle.write("\n")
