from __future__ import annotations

from domain.assessment import AssessmentEvent, AssessmentEventType, AssessmentSession
from services.scoring.context import ScoringContext


def _loop_records():
    def record(pair: str):
        continuity = "closed" if pair[0] == pair[1] else "open"
        return {
            "measurement_id": f"loop.global.{pair}",
            "value": continuity,
            "unit": None,
            "origin": "simulated",
            "instrument": "multimeter",
            "instrument_id": "sim:multimeter",
            "node_ids": [f"LOOP_G1_{pair[0]}", f"LOOP_G2_{pair[1]}"],
            "terminal_ids": [f"LOOP_G1_{pair[0]}", f"LOOP_G2_{pair[1]}"],
            "channel_ids": [],
            "timestamp": 0.0,
            "quality": "ok",
            "reading": "通路" if continuity == "closed" else "断路",
            "passed": True,
            "continuity": continuity,
        }

    return {pair: record(pair) for pair in ("AA", "BB", "CC", "AB", "AC", "BC")}


def _step_enter_events(*steps: int, start_minute: int):
    return [
        AssessmentEvent(
            event_type=AssessmentEventType.STEP_ENTERED,
            timestamp=f"2026-04-09T11:{start_minute + index:02d}:00",
            step=step,
        )
        for index, step in enumerate(steps)
    ]


def build_normal_scoring_context() -> ScoringContext:
    step_enter_events = _step_enter_events(1, 2, 3, 4, start_minute=55)
    session = AssessmentSession(
        session_id="ASM-SCORING-NORMAL",
        scene_id="",
        mode="assessment",
        started_at="2026-04-09T11:55:00",
        events=[
            AssessmentEvent(
                event_type=AssessmentEventType.ASSESSMENT_STARTED,
                timestamp="2026-04-09T11:55:00",
            ),
            *step_enter_events,
            AssessmentEvent(
                event_type=AssessmentEventType.STEP_FINALIZE_ATTEMPTED,
                timestamp="2026-04-09T11:58:30",
                step=4,
                payload={"allowed": True},
            ),
        ],
    )
    return ScoringContext(
        session=session,
        blocked_events=[],
        blocked_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        finalize_rejected=[],
        finalize_rejected_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        gate_block_events=[],
        invalid_events=[],
        invalid_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        step_enter_events=step_enter_events,
        fault_detected_event=None,
        loop_records=_loop_records(),
        loop_complete=True,
        pt1_voltage_count=3,
        pt2_voltage_count=3,
        pt3_voltage_count=3,
        pt1_phase_count=3,
        pt3_phase_count=3,
        gen1_exam_count=9,
        gen2_exam_count=9,
        detection_step=None,
        hidden_fault=False,
        blackbox_open_before_gate=False,
        detected_before_gate=False,
        expected_targets=[],
        expected_target_set=set(),
        expected_device_set=set(),
        opened_target_set=set(),
        touched_layers=set(),
        repair_required=False,
        repaired=False,
        blackbox_failed_confirms=0,
        blackbox_swap_count=0,
        elapsed_seconds=300,
    )


def build_fault_scoring_context() -> ScoringContext:
    step_enter_events = _step_enter_events(1, 2, 3, 4, start_minute=50)
    fault_detected_event = AssessmentEvent(
        event_type=AssessmentEventType.FAULT_DETECTED,
        timestamp="2026-04-09T11:50:20",
        step=1,
        payload={"scene_id": "E02"},
    )
    session = AssessmentSession(
        session_id="ASM-SCORING-FAULT",
        scene_id="E02",
        mode="assessment",
        started_at="2026-04-09T11:50:00",
        fault_selection_mode="random",
        fault_guess_scene_id="E01",
        fault_guess_submitted=True,
        fault_guess_correct=False,
        events=[
            AssessmentEvent(
                event_type=AssessmentEventType.ASSESSMENT_STARTED,
                timestamp="2026-04-09T11:50:00",
                payload={"fault_selection_mode": "random"},
            ),
            step_enter_events[0],
            fault_detected_event,
            step_enter_events[1],
            step_enter_events[2],
            step_enter_events[3],
            AssessmentEvent(
                event_type=AssessmentEventType.BLACKBOX_OPENED,
                timestamp="2026-04-09T11:53:20",
                step=4,
                payload={"target": "G2"},
            ),
            AssessmentEvent(
                event_type=AssessmentEventType.BLACKBOX_SWAP,
                timestamp="2026-04-09T11:53:40",
                step=4,
                payload={"target": "G2", "layer": "terminal"},
            ),
            AssessmentEvent(
                event_type=AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED,
                timestamp="2026-04-09T11:54:00",
                step=4,
                payload={"target": "G2", "layers": ["terminal"], "success": True},
            ),
            AssessmentEvent(
                event_type=AssessmentEventType.FAULT_REPAIRED,
                timestamp="2026-04-09T11:54:20",
                step=4,
                payload={"scene_id": "E02"},
            ),
            AssessmentEvent(
                event_type=AssessmentEventType.STEP_FINALIZE_ATTEMPTED,
                timestamp="2026-04-09T11:54:30",
                step=4,
                payload={"allowed": True},
            ),
        ],
    )
    return ScoringContext(
        session=session,
        blocked_events=[],
        blocked_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        finalize_rejected=[],
        finalize_rejected_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        gate_block_events=[],
        invalid_events=[],
        invalid_by_step={1: 0, 2: 0, 3: 0, 4: 0},
        step_enter_events=step_enter_events,
        fault_detected_event=fault_detected_event,
        loop_records=_loop_records(),
        loop_complete=True,
        pt1_voltage_count=3,
        pt2_voltage_count=3,
        pt3_voltage_count=3,
        pt1_phase_count=3,
        pt3_phase_count=3,
        gen1_exam_count=9,
        gen2_exam_count=9,
        detection_step=1,
        hidden_fault=False,
        blackbox_open_before_gate=True,
        detected_before_gate=True,
        expected_targets=["G2.terminal"],
        expected_target_set={"G2.terminal"},
        expected_device_set={"G2"},
        opened_target_set={"G2"},
        touched_layers={"G2.terminal"},
        repair_required=True,
        repaired=True,
        blackbox_failed_confirms=0,
        blackbox_swap_count=1,
        elapsed_seconds=600,
    )


NORMAL_CONTEXT = build_normal_scoring_context()
FAULT_CONTEXT = build_fault_scoring_context()
