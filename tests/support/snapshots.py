from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tests.support.stubs import normalize_snapshot_value


def assert_json_snapshot(snapshot_path: Path, payload: Any):
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_snapshot_value(payload)
    if not snapshot_path.exists():
        snapshot_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return

    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert normalized == expected
