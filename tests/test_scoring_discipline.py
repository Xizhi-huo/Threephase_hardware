from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from services.scoring.discipline import score_discipline
from tests.support.scoring_fixtures import FAULT_CONTEXT, NORMAL_CONTEXT
from tests.support.snapshots import assert_json_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _payload(items, penalties):
    return {
        "items": [asdict(item) for item in items],
        "penalties": [asdict(penalty) for penalty in penalties],
    }


def test_scoring_discipline_normal():
    items, penalties = score_discipline(NORMAL_CONTEXT)
    assert_json_snapshot(
        SNAPSHOT_DIR / "scoring_discipline_normal.json",
        _payload(items, penalties),
    )


def test_scoring_discipline_fault():
    items, penalties = score_discipline(FAULT_CONTEXT)
    assert_json_snapshot(
        SNAPSHOT_DIR / "scoring_discipline_fault.json",
        _payload(items, penalties),
    )
