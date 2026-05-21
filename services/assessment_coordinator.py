from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from domain.assessment import (
    AssessmentContext,
    AssessmentEvent,
    AssessmentEventType,
    AssessmentResult,
    AssessmentSession,
)
from domain.measurement_schema import parse_measurement_id


@dataclass(frozen=True)
class StepProgressSnapshot:
    current_step: int
    ready_for_step5: bool
    block_before_step5: bool
    should_emit_assessment_gate_event: bool
    should_show_blackbox_required_dialog: bool
    random_fault_guess_required: bool
    assessment_result_ready: bool


class AssessmentCoordinator:
    def __init__(
        self,
        *,
        sim_state,
        flow_mgr,
        assessment_svc,
        get_fault_mgr: Callable[[], Any],
        get_assessment_session: Callable[[], Optional[AssessmentSession]],
        set_assessment_session: Callable[[Optional[AssessmentSession]], None],
        set_last_fault_detected: Callable[[bool], None],
        get_loop_test_state: Callable[[], Any],
        get_pt_voltage_check_state: Callable[[], Any],
        get_pt_phase_check_state: Callable[[], Any],
        get_pt_exam_states: Callable[[], dict],
        get_g1_blackbox_order: Callable[[], list],
        get_g2_blackbox_order: Callable[[], list],
        get_pt1_pri_blackbox_order: Callable[[], list],
        get_pt1_sec_blackbox_order: Callable[[], list],
        get_pt2_sec_blackbox_order: Callable[[], list],
        is_loop_test_complete: Callable[[], bool],
        is_pt_voltage_check_complete: Callable[[], bool],
        is_pt_phase_check_complete: Callable[[], bool],
        build_assessment_context: Callable[[Dict[str, Any]], AssessmentContext],
    ):
        self._sim_state = sim_state
        self._flow_mgr = flow_mgr
        self._assessment_svc = assessment_svc
        self._get_fault_mgr = get_fault_mgr
        self._get_assessment_session = get_assessment_session
        self._set_assessment_session = set_assessment_session
        self._set_last_fault_detected = set_last_fault_detected
        self._get_loop_test_state = get_loop_test_state
        self._get_pt_voltage_check_state = get_pt_voltage_check_state
        self._get_pt_phase_check_state = get_pt_phase_check_state
        self._get_pt_exam_states = get_pt_exam_states
        self._get_g1_blackbox_order = get_g1_blackbox_order
        self._get_g2_blackbox_order = get_g2_blackbox_order
        self._get_pt1_pri_blackbox_order = get_pt1_pri_blackbox_order
        self._get_pt1_sec_blackbox_order = get_pt1_sec_blackbox_order
        self._get_pt2_sec_blackbox_order = get_pt2_sec_blackbox_order
        self._is_loop_test_complete = is_loop_test_complete
        self._is_pt_voltage_check_complete = is_pt_voltage_check_complete
        self._is_pt_phase_check_complete = is_pt_phase_check_complete
        self._build_assessment_context = build_assessment_context

    def start_assessment_session(self, scene_id: str, preset_mode: str = 'specified') -> None:
        if not self._flow_mgr.should_record_assessment_metrics():
            self._set_assessment_session(None)
            return
        now = datetime.now().isoformat(timespec='seconds')
        session_id = f"ASM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        fault_selection_mode = 'random' if preset_mode == 'random' else 'specified'
        self._set_assessment_session(
            AssessmentSession(
                session_id=session_id,
                scene_id=scene_id,
                mode=self._flow_mgr.test_flow_mode,
                started_at=now,
                fault_selection_mode=fault_selection_mode,
            )
        )
        self.append_assessment_event(
            AssessmentEventType.ASSESSMENT_STARTED,
            scene_id=scene_id,
            mode=self._flow_mgr.test_flow_mode,
            fault_selection_mode=fault_selection_mode,
        )

    def append_assessment_event(self, event_type: str, step: int = 0, **payload) -> None:
        if not self._flow_mgr.should_record_assessment_metrics():
            return
        session = self._get_assessment_session()
        if session is None or session.finished_at is not None:
            return
        payload = dict(payload)
        measurement_id = payload.get("measurement_id")
        if isinstance(measurement_id, str):
            payload.setdefault("event_schema_version", 2)
            try:
                domain, scope, cell = parse_measurement_id(measurement_id)
            except ValueError:
                domain, scope, cell = "", "", None
            if step == 0:
                step = {
                    "loop": 1,
                    "pt_voltage": 2,
                    "phase_sequence": 3,
                    "pt_diff": 4,
                }.get(domain, 0)
            payload.setdefault("target", "loop" if domain == "loop" else scope)
            payload.setdefault("point", "sequence" if domain == "phase_sequence" else cell)
        session.events.append(
            AssessmentEvent(
                event_type=event_type,
                timestamp=datetime.now().isoformat(timespec='seconds'),
                step=step,
                payload=payload,
            )
        )

    def mark_fault_detected(self, step: int, source: str, **payload) -> bool:
        fc = self._sim_state.fault_config
        if not fc.active or fc.repaired:
            return False

        fc.detected = True
        self._set_last_fault_detected(True)

        if not self._flow_mgr.should_record_assessment_metrics():
            return True

        session = self._get_assessment_session()
        if session is None or session.finished_at is not None:
            return True

        payload = dict(payload)
        payload.setdefault('scene_id', fc.scenario_id)
        payload['source'] = source

        existing = None
        for event in session.events:
            if event.event_type == AssessmentEventType.FAULT_DETECTED:
                existing = event
                break

        if existing is None:
            self.append_assessment_event(AssessmentEventType.FAULT_DETECTED, step=step, **payload)
            return True

        if step > 0 and (existing.step <= 0 or existing.step > step):
            existing.step = step
        existing.payload.update(payload)
        return True

    def capture_assessment_state_snapshot(self) -> Dict[str, Any]:
        loop_state = self._get_loop_test_state()
        voltage_state = self._get_pt_voltage_check_state()
        phase_state = self._get_pt_phase_check_state()
        exam_states = self._get_pt_exam_states()
        fc = self._sim_state.fault_config
        return {
            'loop_records': deepcopy(loop_state.records),
            'voltage_records': deepcopy(voltage_state.records),
            'phase_records': deepcopy(phase_state.records),
            'pt_exam_records': {
                1: deepcopy(exam_states[1].records),
                2: deepcopy(exam_states[2].records),
            },
            'completed': {
                'loop': bool(loop_state.completed),
                'voltage': bool(voltage_state.completed),
                'phase': bool(phase_state.completed),
                'pt_exam_1': bool(exam_states[1].completed),
                'pt_exam_2': bool(exam_states[2].completed),
                'closure': bool(self.is_assessment_closed_loop_ready()),
            },
            'fault': {
                'active': bool(fc.active),
                'repaired': bool(fc.repaired),
                'detected': bool(fc.detected),
                'scene_id': fc.scenario_id,
            },
            'blackbox_orders': {
                'g1': list(self._get_g1_blackbox_order()),
                'g2': list(self._get_g2_blackbox_order()),
                'pt1_primary': list(self._get_pt1_pri_blackbox_order()),
                'pt1_secondary': list(self._get_pt1_sec_blackbox_order()),
                'pt2_secondary': list(self._get_pt2_sec_blackbox_order()),
            },
        }

    def finish_assessment_session(self) -> AssessmentResult | None:
        if not self._flow_mgr.should_auto_score_assessment():
            return None
        session = self._get_assessment_session()
        if session is None:
            return None
        if session.result is not None:
            return session.result
        if not session.state_snapshot:
            session.state_snapshot = self.capture_assessment_state_snapshot()
        self.append_assessment_event(AssessmentEventType.ASSESSMENT_FINISHED)
        context = self._build_assessment_context(session.state_snapshot or {})
        result = self._assessment_svc.build_result(session, context)
        session.finished_at = result.finished_at
        session.result = result
        return result

    def requires_random_fault_identification(self, current_step: int) -> bool:
        session = self._get_assessment_session()
        if session is None or session.finished_at is not None:
            return False
        if not self._flow_mgr.is_assessment_mode():
            return False
        if session.fault_selection_mode != 'random':
            return False
        if session.fault_guess_submitted:
            return False
        if not session.scene_id:
            return False
        if current_step < 4:
            return False
        if not self._flow_mgr.assessment_ends_after_step4_closed_loop():
            return False
        return self.is_assessment_closed_loop_ready()

    def submit_random_fault_identification(self, guessed_scene_id: str) -> bool:
        session = self._get_assessment_session()
        if session is None:
            return False
        guessed_scene_id = (guessed_scene_id or '').strip()
        correct = bool(guessed_scene_id) and guessed_scene_id == session.scene_id
        session.fault_guess_scene_id = guessed_scene_id
        session.fault_guess_submitted = bool(guessed_scene_id)
        session.fault_guess_correct = correct
        self.append_assessment_event(
            AssessmentEventType.FAULT_GUESS_SUBMITTED,
            step=4,
            guessed_scene_id=guessed_scene_id,
            actual_scene_id=session.scene_id,
            correct=correct,
            fault_selection_mode=session.fault_selection_mode,
        )
        return correct

    def mark_assessment_result_shown(self) -> None:
        session = self._get_assessment_session()
        if session is not None:
            session.result_shown = True

    def is_assessment_closed_loop_ready(self) -> bool:
        exam_states = self._get_pt_exam_states()
        if not (
            self._is_loop_test_complete()
            and self._is_pt_voltage_check_complete()
            and self._is_pt_phase_check_complete()
            and exam_states[1].completed
            and exam_states[2].completed
        ):
            return False
        fc = self._sim_state.fault_config
        if fc.active and self._get_fault_mgr().fault_has_repairable_wiring_targets():
            return fc.repaired
        return True

    def get_test_progress_snapshot(
        self,
        current_step: int,
        pre_step5_repair_triggered: bool,
    ) -> StepProgressSnapshot:
        exam_states = self._get_pt_exam_states()
        ready_for_step5 = (
            self._is_loop_test_complete()
            and self._is_pt_voltage_check_complete()
            and self._is_pt_phase_check_complete()
            and exam_states[1].completed
            and exam_states[2].completed
        )
        fc = self._sim_state.fault_config
        block_before_step5 = (
            ready_for_step5
            and self._flow_mgr.should_block_step5_until_blackbox_fixed()
            and self._get_fault_mgr().has_unrepaired_wiring_fault()
            and fc.scenario_id not in ('E01', 'E02', 'E03')
        )
        should_emit_assessment_gate_event = (
            block_before_step5
            and self._flow_mgr.is_assessment_mode()
            and not pre_step5_repair_triggered
        )
        should_show_blackbox_required_dialog = (
            block_before_step5
            and self._flow_mgr.should_show_blackbox_required_dialog_before_step5()
            and not pre_step5_repair_triggered
        )
        session = self._get_assessment_session()
        assessment_result_ready = (
            self._flow_mgr.is_assessment_mode()
            and self._flow_mgr.assessment_ends_after_step4_closed_loop()
            and self.is_assessment_closed_loop_ready()
            and session is not None
            and not self.requires_random_fault_identification(current_step)
            and not session.result_shown
        )
        return StepProgressSnapshot(
            current_step=current_step,
            ready_for_step5=ready_for_step5,
            block_before_step5=block_before_step5,
            should_emit_assessment_gate_event=should_emit_assessment_gate_event,
            should_show_blackbox_required_dialog=should_show_blackbox_required_dialog,
            random_fault_guess_required=self.requires_random_fault_identification(current_step),
            assessment_result_ready=assessment_result_ready,
        )

    def finish_assessment_session_if_ready(self, current_step: int) -> Optional[object]:
        snapshot = self.get_test_progress_snapshot(current_step, pre_step5_repair_triggered=False)
        if not snapshot.assessment_result_ready:
            return None
        return self.finish_assessment_session()
