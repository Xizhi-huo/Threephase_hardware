from __future__ import annotations

from datetime import datetime as _RealDateTime
from pathlib import Path

import pytest

import services.assessment_service as assessment_service_module
from domain.assessment import AssessmentContext
from services.assessment_service import AssessmentService
from tests.support.snapshots import assert_json_snapshot
from tests.support.stubs import (
    ControllerStub,
    build_normal_assessment_session,
    build_random_fault_assessment_session,
)


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


class _FixedDateTime(_RealDateTime):
    @classmethod
    def now(cls, tz=None):
        return cls.fromisoformat("2026-04-09T12:00:00")


def _result_payload(result):
    return {
        "session_id": result.session_id,
        "scene_id": result.scene_id,
        "mode": result.mode,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "elapsed_seconds": result.elapsed_seconds,
        "passed": result.passed,
        "total_score": result.total_score,
        "max_score": result.max_score,
        "veto_reason": result.veto_reason,
        "step_scores": result.step_scores,
        "step_max_scores": result.step_max_scores,
        "score_items": result.score_items,
        "penalties": result.penalties,
        "metrics": result.metrics,
        "summary": result.summary,
    }


@pytest.fixture(autouse=True)
def _freeze_assessment_time(monkeypatch):
    monkeypatch.setattr(assessment_service_module, "datetime", _FixedDateTime)


def test_assessment_snapshot_normal():
    ctrl = ControllerStub(assessment_closed_loop_ready=True)
    service = AssessmentService()
    session = build_normal_assessment_session()
    context = AssessmentContext.from_snapshot_and_ctrl(session.state_snapshot or {}, ctrl)
    result = service.build_result(session, context)
    assert_json_snapshot(
        SNAPSHOT_DIR / "assessment_normal.json",
        _result_payload(result),
    )


def test_assessment_snapshot_fault_random():
    ctrl = ControllerStub(assessment_closed_loop_ready=True)
    service = AssessmentService()
    session = build_random_fault_assessment_session()
    context = AssessmentContext.from_snapshot_and_ctrl(session.state_snapshot or {}, ctrl)
    result = service.build_result(session, context)
    assert_json_snapshot(
        SNAPSHOT_DIR / "assessment_fault_random.json",
        _result_payload(result),
    )
