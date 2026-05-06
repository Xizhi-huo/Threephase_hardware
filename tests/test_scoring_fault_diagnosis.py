from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from services.scoring.fault_diagnosis import score_fault_diagnosis
from tests.support.scoring_fixtures import FAULT_CONTEXT, NORMAL_CONTEXT
from tests.support.snapshots import assert_json_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


def _payload(items, penalties):
    return {
        "items": [asdict(item) for item in items],
        "penalties": [asdict(penalty) for penalty in penalties],
    }


def test_scoring_fault_diagnosis_normal():
    items, penalties = score_fault_diagnosis(NORMAL_CONTEXT)
    assert_json_snapshot(
        SNAPSHOT_DIR / "scoring_fault_diagnosis_normal.json",
        _payload(items, penalties),
    )


def test_scoring_fault_diagnosis_fault():
    items, penalties = score_fault_diagnosis(FAULT_CONTEXT)
    assert_json_snapshot(
        SNAPSHOT_DIR / "scoring_fault_diagnosis_fault.json",
        _payload(items, penalties),
    )
