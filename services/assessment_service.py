from datetime import datetime
from typing import Dict, List, Set

from domain.assessment import (
    AssessmentContext,
    AssessmentEvent,
    AssessmentEventType,
    AssessmentPenalty,
    AssessmentResult,
    AssessmentScoreItem,
    AssessmentSession,
)
from domain.fault_scenarios import SCENARIOS
from domain.measurement_schema import is_record_complete
from services.scoring._common import count_present
from services.scoring.blackbox_efficiency import score_blackbox_efficiency
from services.scoring.context import ScoringContext
from services.scoring.discipline import score_discipline
from services.scoring.fault_diagnosis import score_fault_diagnosis
from services.scoring.step_quality import score_step_quality


class AssessmentService:
    """Build a 30-item assessment result from the recorded event stream."""

    def __init__(self):
        pass

    def build_result(self, session: AssessmentSession, context: AssessmentContext) -> AssessmentResult:
        now = datetime.now()
        finished_at = now.isoformat(timespec="seconds")
        started_at_dt = datetime.fromisoformat(session.started_at)
        elapsed_seconds = max(0, int((now - started_at_dt).total_seconds()))

        events = session.events
        penalties: List[AssessmentPenalty] = []
        score_items: List[AssessmentScoreItem] = []
        scene_info = SCENARIOS.get(session.scene_id, {})
        detection_step = scene_info.get("detection_step")
        expected_targets = self._expected_blackbox_targets(scene_info)
        expected_target_set = set(expected_targets)
        expected_device_set = {target.split(".", 1)[0] for target in expected_targets}

        def count(event_type: str) -> int:
            return sum(1 for event in events if event.event_type == event_type)

        def all_events(event_type: str) -> list[AssessmentEvent]:
            return [event for event in events if event.event_type == event_type]

        def first(event_type: str) -> AssessmentEvent | None:
            for event in events:
                if event.event_type == event_type:
                    return event
            return None

        def happened_before(lhs: AssessmentEvent | None, rhs: AssessmentEvent | None) -> bool:
            if lhs is None:
                return False
            if rhs is None:
                return True
            return lhs.timestamp <= rhs.timestamp

        blocked_events = all_events(AssessmentEventType.ADVANCE_BLOCKED)
        finalize_rejected = [
            event for event in all_events(AssessmentEventType.STEP_FINALIZE_ATTEMPTED)
            if not bool(event.payload.get("allowed", False))
        ]
        gate_block_events = all_events(AssessmentEventType.ASSESSMENT_GATE_BLOCKED)
        invalid_events = all_events(AssessmentEventType.MEASUREMENT_INVALID)
        invalid_by_step = {
            1: sum(1 for event in invalid_events if event.step == 1),
            2: sum(1 for event in invalid_events if event.step == 2),
            3: sum(1 for event in invalid_events if event.step == 3),
            4: sum(1 for event in invalid_events if event.step == 4),
        }
        blackbox_failed_confirms = sum(
            1 for event in all_events(AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED)
            if not bool(event.payload.get("success", False))
        )
        blackbox_swap_count = count(AssessmentEventType.BLACKBOX_SWAP)
        serious_misoperations = count(AssessmentEventType.HAZARD_ACTION)
        blackbox_open_events = all_events(AssessmentEventType.BLACKBOX_OPENED)
        opened_targets = []
        for event in blackbox_open_events:
            target = event.payload.get("target")
            if target:
                opened_targets.append(target)
        early_pt_blackbox_open_events = [
            event for event in blackbox_open_events
            if event.step in (1, 2) and event.payload.get("target") in {"PT1", "PT3"}
        ]
        opened_target_set: Set[str] = set(opened_targets)
        touched_layers = set()
        for event in all_events(AssessmentEventType.BLACKBOX_SWAP):
            target = event.payload.get("target")
            layer = event.payload.get("layer")
            if target and layer:
                touched_layers.add(f"{target}.{layer}")
        for event in all_events(AssessmentEventType.BLACKBOX_CONFIRM_ATTEMPTED):
            target = event.payload.get("target")
            for layer in event.payload.get("layers", []):
                touched_layers.add(f"{target}.{layer}")

        step_enter_events = all_events(AssessmentEventType.STEP_ENTERED)
        blocked_by_step = {
            1: sum(1 for event in blocked_events if event.payload.get("from_step") == 1 or event.step == 1),
            2: sum(1 for event in blocked_events if event.payload.get("from_step") == 2 or event.step == 2),
            3: sum(1 for event in blocked_events if event.payload.get("from_step") == 3 or event.step == 3),
            4: sum(1 for event in blocked_events if event.payload.get("from_step") == 4 or event.step == 4),
        }
        finalize_rejected_by_step = {
            1: sum(1 for event in finalize_rejected if event.step == 1),
            2: sum(1 for event in finalize_rejected if event.step == 2),
            3: sum(1 for event in finalize_rejected if event.step == 3),
            4: sum(1 for event in finalize_rejected if event.step == 4),
        }

        fault_detected_event = first(AssessmentEventType.FAULT_DETECTED)
        fault_repaired_event = first(AssessmentEventType.FAULT_REPAIRED)
        first_gate_block = first(AssessmentEventType.ASSESSMENT_GATE_BLOCKED)
        first_blackbox_open = first(AssessmentEventType.BLACKBOX_OPENED)

        detected_before_gate = happened_before(fault_detected_event, first_gate_block)
        blackbox_open_before_gate = happened_before(first_blackbox_open, first_gate_block)
        hidden_fault = bool(session.scene_id) and detection_step is None and bool(expected_targets)

        loop_records = context.loop_records
        voltage_records = context.voltage_records
        phase_records = context.phase_records
        pt_exam_records_1 = context.pt_exam_records_1
        pt_exam_records_2 = context.pt_exam_records_2
        loop_complete = context.loop_complete
        voltage_complete = context.voltage_complete
        phase_complete = context.phase_complete
        pt_exam_complete = context.pt_exam_complete
        closure_complete = context.closure_complete
        repair_required = bool(expected_targets)
        repaired = context.fault_repaired

        def record_present(record) -> bool:
            return record is not None and (
                not isinstance(record, dict)
                or "quality" not in record
                or is_record_complete(record)
            )

        pt1_voltage_count = sum(1 for key in ("PT1_AB", "PT1_BC", "PT1_CA") if record_present(voltage_records.get(key)))
        pt2_voltage_count = sum(1 for key in ("PT2_AB", "PT2_BC", "PT2_CA") if record_present(voltage_records.get(key)))
        pt3_voltage_count = sum(1 for key in ("PT3_AB", "PT3_BC", "PT3_CA") if record_present(voltage_records.get(key)))
        pt1_phase_count = (
            3 if record_present(phase_records.get("PT1"))
            else sum(1 for key in ("PT1_A", "PT1_B", "PT1_C") if record_present(phase_records.get(key)))
        )
        pt3_phase_count = (
            3 if record_present(phase_records.get("PT3"))
            else sum(1 for key in ("PT3_A", "PT3_B", "PT3_C") if record_present(phase_records.get(key)))
        )
        gen1_exam_count = count_present(pt_exam_records_1)
        gen2_exam_count = count_present(pt_exam_records_2)

        score_context = ScoringContext(
            session=session,
            blocked_events=blocked_events,
            blocked_by_step=blocked_by_step,
            finalize_rejected=finalize_rejected,
            finalize_rejected_by_step=finalize_rejected_by_step,
            gate_block_events=gate_block_events,
            invalid_events=invalid_events,
            invalid_by_step=invalid_by_step,
            step_enter_events=step_enter_events,
            fault_detected_event=fault_detected_event,
            loop_records=loop_records,
            loop_complete=loop_complete,
            pt1_voltage_count=pt1_voltage_count,
            pt2_voltage_count=pt2_voltage_count,
            pt3_voltage_count=pt3_voltage_count,
            pt1_phase_count=pt1_phase_count,
            pt3_phase_count=pt3_phase_count,
            gen1_exam_count=gen1_exam_count,
            gen2_exam_count=gen2_exam_count,
            detection_step=detection_step,
            hidden_fault=hidden_fault,
            blackbox_open_before_gate=blackbox_open_before_gate,
            detected_before_gate=detected_before_gate,
            expected_targets=expected_targets,
            expected_target_set=expected_target_set,
            expected_device_set=expected_device_set,
            opened_target_set=opened_target_set,
            touched_layers=touched_layers,
            repair_required=repair_required,
            repaired=repaired,
            blackbox_failed_confirms=blackbox_failed_confirms,
            blackbox_swap_count=blackbox_swap_count,
            elapsed_seconds=elapsed_seconds,
        )
        for scorer in (
            score_discipline,
            score_step_quality,
            score_fault_diagnosis,
            score_blackbox_efficiency,
        ):
            items, domain_penalties = scorer(score_context)
            score_items.extend(items)
            penalties.extend(domain_penalties)

        step_scores, step_max_scores = self._build_step_score_summaries(score_items)
        total_score = sum(step_scores.values())
        max_score = sum(step_max_scores.values())

        extra_deduction_total = self._apply_extra_deductions(
            session=session,
            early_pt_blackbox_open_events=early_pt_blackbox_open_events,
            penalties=penalties,
            finished_at=finished_at,
        )
        total_score = max(0, total_score - extra_deduction_total)

        veto_reason = self._resolve_veto_reason(
            serious_misoperations=serious_misoperations,
            closure_complete=closure_complete,
            loop_complete=loop_complete,
            voltage_complete=voltage_complete,
            phase_complete=phase_complete,
            pt_exam_complete=pt_exam_complete,
        )
        passed = veto_reason is None and total_score >= 60

        metrics = self._build_metrics(
            session=session,
            early_pt_blackbox_open_events=early_pt_blackbox_open_events,
            extra_deduction_total=extra_deduction_total,
            step_enter_events=step_enter_events,
            blocked_events=blocked_events,
            gate_block_events=gate_block_events,
            invalid_events=invalid_events,
            opened_targets=opened_targets,
            blackbox_swap_count=blackbox_swap_count,
            blackbox_failed_confirms=blackbox_failed_confirms,
            fault_detected_event=fault_detected_event,
            fault_repaired_event=fault_repaired_event,
            serious_misoperations=serious_misoperations,
            measurement_count=count(AssessmentEventType.MEASUREMENT_RECORDED),
            finalize_attempt_count=count(AssessmentEventType.STEP_FINALIZE_ATTEMPTED),
        )
        summary = self._build_summary(total_score, veto_reason, extra_deduction_total)

        return AssessmentResult(
            session_id=session.session_id,
            scene_id=session.scene_id,
            mode=session.mode,
            started_at=session.started_at,
            finished_at=finished_at,
            elapsed_seconds=elapsed_seconds,
            passed=passed,
            total_score=total_score,
            max_score=max_score,
            veto_reason=veto_reason,
            step_scores=step_scores,
            step_max_scores=step_max_scores,
            score_items=score_items,
            penalties=penalties,
            metrics=metrics,
            summary=summary,
        )

    @staticmethod
    def _build_step_score_summaries(
        score_items: List[AssessmentScoreItem],
    ) -> tuple[dict[str, int], dict[str, int]]:
        step_scores = {
            "flow_discipline": sum(item.earned_score for item in score_items if item.code.startswith("A")),
            "loop_test": sum(item.earned_score for item in score_items if item.code.startswith("B")),
            "pt_voltage_check": sum(item.earned_score for item in score_items if item.code.startswith("C")),
            "pt_phase_check": sum(item.earned_score for item in score_items if item.code.startswith("D")),
            "pt_exam": sum(item.earned_score for item in score_items if item.code.startswith("E")),
            "anomaly_localization": sum(item.earned_score for item in score_items if item.code.startswith("F")),
            "blackbox_repair": sum(item.earned_score for item in score_items if item.code.startswith("G")),
            "efficiency": sum(item.earned_score for item in score_items if item.code.startswith("H")),
        }
        step_max_scores = {
            "flow_discipline": sum(item.max_score for item in score_items if item.code.startswith("A")),
            "loop_test": sum(item.max_score for item in score_items if item.code.startswith("B")),
            "pt_voltage_check": sum(item.max_score for item in score_items if item.code.startswith("C")),
            "pt_phase_check": sum(item.max_score for item in score_items if item.code.startswith("D")),
            "pt_exam": sum(item.max_score for item in score_items if item.code.startswith("E")),
            "anomaly_localization": sum(item.max_score for item in score_items if item.code.startswith("F")),
            "blackbox_repair": sum(item.max_score for item in score_items if item.code.startswith("G")),
            "efficiency": sum(item.max_score for item in score_items if item.code.startswith("H")),
        }
        return step_scores, step_max_scores

    @staticmethod
    def _apply_extra_deductions(
        session: AssessmentSession,
        early_pt_blackbox_open_events,
        penalties: List[AssessmentPenalty],
        finished_at: str,
    ) -> int:
        extra_deduction_total = 0
        for idx, event in enumerate(early_pt_blackbox_open_events, start=1):
            extra_deduction_total += 10
            penalties.append(
                AssessmentPenalty(
                    code="X1",
                    message=f"前两步第 {idx} 次提前打开 PT 黑盒，属于高危违规，额外扣 10 分。",
                    score_delta=-10,
                    step=event.step,
                    timestamp=event.timestamp,
                )
            )
        if session.fault_selection_mode == "random" and session.scene_id and not session.fault_guess_correct:
            extra_deduction_total += 10
            penalties.append(
                AssessmentPenalty(
                    code="X2",
                    message="随机故障最终场景判定错误，额外扣 10 分。",
                    score_delta=-10,
                    step=4,
                    timestamp=finished_at,
                )
            )
        return extra_deduction_total

    @staticmethod
    def _resolve_veto_reason(
        *,
        serious_misoperations: int,
        closure_complete: bool,
        loop_complete: bool,
        voltage_complete: bool,
        phase_complete: bool,
        pt_exam_complete: bool,
    ) -> str | None:
        if serious_misoperations > 0:
            return "存在严重误操作"
        if not closure_complete:
            return "第四步结束时仍未完成正确修复"
        if not (loop_complete and voltage_complete and phase_complete and pt_exam_complete):
            return "前四步记录不完整，无法形成有效考核"
        return None

    @staticmethod
    def _build_metrics(
        *,
        session: AssessmentSession,
        early_pt_blackbox_open_events,
        extra_deduction_total: int,
        step_enter_events,
        blocked_events,
        gate_block_events,
        invalid_events,
        opened_targets,
        blackbox_swap_count: int,
        blackbox_failed_confirms: int,
        fault_detected_event,
        fault_repaired_event,
        serious_misoperations: int,
        measurement_count: int,
        finalize_attempt_count: int,
    ) -> Dict[str, object]:
        return {
            "fault_selection_mode": "随机故障" if session.fault_selection_mode == "random" else "指定/正常",
            "fault_guess_scene_id": session.fault_guess_scene_id or "-",
            "fault_guess_correct": (
                "-"
                if session.fault_selection_mode != "random"
                else ("正确" if session.fault_guess_correct else "错误")
            ),
            "actual_fault_scene_id": session.scene_id or "-",
            "early_pt_blackbox_opened": len(early_pt_blackbox_open_events),
            "extra_deduction_total": extra_deduction_total,
            "step_entered_order": [event.step for event in step_enter_events],
            "step_finalize_attempts": finalize_attempt_count,
            "blocked_advances": len(blocked_events),
            "gate_blocks": len(gate_block_events),
            "measurements_recorded": measurement_count,
            "invalid_measurements": len(invalid_events),
            "blackboxes_opened": opened_targets,
            "blackbox_swap_count": blackbox_swap_count,
            "blackbox_failed_confirms": blackbox_failed_confirms,
            "fault_detected_at_step": getattr(fault_detected_event, "step", 0),
            "fault_repaired_at": getattr(fault_repaired_event, "timestamp", ""),
            "serious_misoperations": serious_misoperations,
        }

    @staticmethod
    def _build_summary(total_score: int, veto_reason: str | None, extra_deduction_total: int) -> str:
        if veto_reason:
            summary = f"未通过：{veto_reason}"
        elif total_score >= 90:
            summary = "通过：流程规范、判断准确，整体表现优秀。"
        elif total_score >= 75:
            summary = "通过：完成了有效闭环，但过程上仍存在若干扣分点。"
        elif total_score >= 60:
            summary = "通过：达到基本考核要求。"
        else:
            summary = "未通过：总分未达到及格线。"
        if extra_deduction_total > 0:
            summary = f"{summary} 另有额外扣分 {extra_deduction_total} 分。"
        return summary

    @staticmethod
    def _expected_blackbox_targets(scene_info: Dict) -> List[str]:
        params = scene_info.get("params", {}) if scene_info else {}
        targets: List[str] = []
        if params.get("g1_blackbox_order") is not None:
            targets.append("G1.terminal")
        if (params.get("pt1_pri_blackbox_order") is not None
                or params.get("p1_pri_blackbox_order") is not None):
            targets.append("PT1.primary")
        if (params.get("pt1_sec_blackbox_order") is not None
                or params.get("pt2_sec_blackbox_order") is not None):
            targets.append("PT1.secondary")
        if params.get("g2_blackbox_order") is not None:
            targets.append("G2.terminal")
        return targets
