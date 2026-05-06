from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


class _RecordStateLike(Protocol):
    records: Dict[str, Any]


class _PtExamStateLike(Protocol):
    records: Dict[str, Any]
    completed: bool


class _LoopServiceLike(Protocol):
    def is_loop_test_complete(self) -> bool:
        ...


class _VoltageServiceLike(Protocol):
    def is_pt_voltage_check_complete(self) -> bool:
        ...


class _PhaseServiceLike(Protocol):
    def is_pt_phase_check_complete(self) -> bool:
        ...


class _AssessmentCoordinatorLike(Protocol):
    def is_assessment_closed_loop_ready(self) -> bool:
        ...


class _FaultConfigLike(Protocol):
    repaired: bool


class _SimulationStateLike(Protocol):
    fault_config: _FaultConfigLike


class _AssessmentControllerLike(Protocol):
    loop_test_state: _RecordStateLike
    pt_voltage_check_state: _RecordStateLike
    pt_phase_check_state: _RecordStateLike
    pt_exam_states: Dict[int, _PtExamStateLike]
    loop_svc: _LoopServiceLike
    pt_voltage_svc: _VoltageServiceLike
    pt_phase_svc: _PhaseServiceLike
    assessment_coord: _AssessmentCoordinatorLike
    sim_state: _SimulationStateLike


class AssessmentEventType:
    ASSESSMENT_STARTED = "assessment_started"
    ASSESSMENT_FINISHED = "assessment_finished"
    STEP_ENTERED = "step_entered"
    STEP_COMPLETED = "step_completed"
    STEP_FINALIZE_ATTEMPTED = "step_finalize_attempted"
    ADVANCE_BLOCKED = "advance_blocked"
    ASSESSMENT_GATE_BLOCKED = "assessment_gate_blocked"
    MEASUREMENT_INVALID = "measurement_invalid"
    MEASUREMENT_RECORDED = "measurement_recorded"
    FAULT_DETECTED = "fault_detected"
    FAULT_REPAIRED = "fault_repaired"
    FAULT_GUESS_SUBMITTED = "fault_guess_submitted"
    BLACKBOX_OPENED = "blackbox_opened"
    BLACKBOX_SWAP = "blackbox_swap"
    BLACKBOX_CONFIRM_ATTEMPTED = "blackbox_confirm_attempted"
    HAZARD_ACTION = "hazard_action"


@dataclass
class AssessmentEvent:
    event_type: str
    timestamp: str
    step: int = 0
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssessmentPenalty:
    code: str
    message: str
    score_delta: int
    step: int = 0
    timestamp: str = ""


@dataclass
class AssessmentScoreItem:
    code: str
    title: str
    category: str
    status: str
    max_score: int
    earned_score: int
    step: int = 0
    detail: str = ""


@dataclass
class AssessmentResult:
    session_id: str
    scene_id: str
    mode: str
    started_at: str
    finished_at: str
    elapsed_seconds: int
    passed: bool
    total_score: int
    max_score: int
    veto_reason: Optional[str] = None
    step_scores: Dict[str, int] = field(default_factory=dict)
    step_max_scores: Dict[str, int] = field(default_factory=dict)
    score_items: List[AssessmentScoreItem] = field(default_factory=list)
    penalties: List[AssessmentPenalty] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""


@dataclass
class AssessmentSession:
    session_id: str
    scene_id: str
    mode: str
    started_at: str
    fault_selection_mode: str = "specified"
    events: List[AssessmentEvent] = field(default_factory=list)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)
    fault_guess_scene_id: str = ""
    fault_guess_submitted: bool = False
    fault_guess_correct: bool = False
    finished_at: Optional[str] = None
    result: Optional[AssessmentResult] = None
    result_shown: bool = False


@dataclass(frozen=True)
class AssessmentContext:
    loop_records: Dict[str, Any]
    voltage_records: Dict[str, Any]
    phase_records: Dict[str, Any]
    pt_exam_records_1: Dict[str, Any]
    pt_exam_records_2: Dict[str, Any]
    loop_complete: bool
    voltage_complete: bool
    phase_complete: bool
    pt_exam_complete: bool
    closure_complete: bool
    fault_repaired: bool

    @classmethod
    def from_snapshot_and_ctrl(
        cls,
        snapshot: Dict[str, Any],
        ctrl: _AssessmentControllerLike,
    ) -> "AssessmentContext":
        snapshot = snapshot or {}
        pt_exam_records = snapshot.get("pt_exam_records", {})
        completed = snapshot.get("completed", {})
        fault_snapshot = snapshot.get("fault", {})
        return cls(
            loop_records=snapshot.get("loop_records", ctrl.loop_test_state.records),
            voltage_records=snapshot.get("voltage_records", ctrl.pt_voltage_check_state.records),
            phase_records=snapshot.get("phase_records", ctrl.pt_phase_check_state.records),
            pt_exam_records_1=pt_exam_records.get(1, ctrl.pt_exam_states[1].records),
            pt_exam_records_2=pt_exam_records.get(2, ctrl.pt_exam_states[2].records),
            loop_complete=bool(completed.get("loop", ctrl.loop_svc.is_loop_test_complete())),
            voltage_complete=bool(completed.get("voltage", ctrl.pt_voltage_svc.is_pt_voltage_check_complete())),
            phase_complete=bool(completed.get("phase", ctrl.pt_phase_svc.is_pt_phase_check_complete())),
            pt_exam_complete=(
                bool(completed.get("pt_exam_1", ctrl.pt_exam_states[1].completed))
                and bool(completed.get("pt_exam_2", ctrl.pt_exam_states[2].completed))
            ),
            closure_complete=bool(
                completed.get("closure", ctrl.assessment_coord.is_assessment_closed_loop_ready())
            ),
            fault_repaired=bool(fault_snapshot.get("repaired", ctrl.sim_state.fault_config.repaired)),
        )
