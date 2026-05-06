from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from domain.assessment import AssessmentEvent, AssessmentSession


@dataclass(frozen=True)
class ScoringContext:
    session: AssessmentSession
    blocked_events: List[AssessmentEvent]
    blocked_by_step: Dict[int, int]
    finalize_rejected: List[AssessmentEvent]
    finalize_rejected_by_step: Dict[int, int]
    gate_block_events: List[AssessmentEvent]
    invalid_events: List[AssessmentEvent]
    invalid_by_step: Dict[int, int]
    step_enter_events: List[AssessmentEvent]
    fault_detected_event: Optional[AssessmentEvent]
    loop_records: Dict[str, Any]
    loop_complete: bool
    pt1_voltage_count: int
    pt2_voltage_count: int
    pt3_voltage_count: int
    pt1_phase_count: int
    pt3_phase_count: int
    gen1_exam_count: int
    gen2_exam_count: int
    detection_step: Optional[int]
    hidden_fault: bool
    blackbox_open_before_gate: bool
    detected_before_gate: bool
    expected_targets: List[str]
    expected_target_set: Set[str]
    expected_device_set: Set[str]
    opened_target_set: Set[str]
    touched_layers: Set[str]
    repair_required: bool
    repaired: bool
    blackbox_failed_confirms: int
    blackbox_swap_count: int
    elapsed_seconds: int
