from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FlowModePolicy:
    allow_continue_with_fault: bool
    # Legacy dead flags retained as comments during dead-code verification:
    # require_all_measurements_before_finalize: bool
    # require_step_pass_to_finalize: bool
    show_fault_detected_banner: bool
    show_diagnostic_hints: bool
    block_step5_until_blackbox_fixed: bool
    hold_at_step4_when_wiring_fault_unrepaired: bool
    show_blackbox_required_dialog_before_step5: bool
    allow_blackbox_inspection: bool
    allow_blackbox_repair: bool
    auto_clear_fault_only_when_all_blackboxes_normal: bool
    allow_admin_shortcuts: bool
    record_assessment_metrics: bool
    auto_score_assessment: bool
    assessment_ends_after_step4_closed_loop: bool


FLOW_MODE_POLICIES = {
    'teaching': FlowModePolicy(
        allow_continue_with_fault=True,
        # require_all_measurements_before_finalize=True,
        # require_step_pass_to_finalize=False,
        show_fault_detected_banner=True,
        show_diagnostic_hints=True,
        block_step5_until_blackbox_fixed=True,
        hold_at_step4_when_wiring_fault_unrepaired=True,
        show_blackbox_required_dialog_before_step5=True,
        allow_blackbox_inspection=True,
        allow_blackbox_repair=True,
        auto_clear_fault_only_when_all_blackboxes_normal=True,
        allow_admin_shortcuts=True,
        record_assessment_metrics=False,
        auto_score_assessment=False,
        assessment_ends_after_step4_closed_loop=False,
    ),
    'engineering': FlowModePolicy(
        allow_continue_with_fault=False,
        # require_all_measurements_before_finalize=True,
        # require_step_pass_to_finalize=True,
        show_fault_detected_banner=True,
        show_diagnostic_hints=True,
        block_step5_until_blackbox_fixed=True,
        hold_at_step4_when_wiring_fault_unrepaired=True,
        show_blackbox_required_dialog_before_step5=True,
        allow_blackbox_inspection=True,
        allow_blackbox_repair=True,
        auto_clear_fault_only_when_all_blackboxes_normal=True,
        allow_admin_shortcuts=True,
        record_assessment_metrics=False,
        auto_score_assessment=False,
        assessment_ends_after_step4_closed_loop=False,
    ),
    'assessment': FlowModePolicy(
        allow_continue_with_fault=False,
        # require_all_measurements_before_finalize=True,
        # require_step_pass_to_finalize=True,
        show_fault_detected_banner=False,
        show_diagnostic_hints=False,
        block_step5_until_blackbox_fixed=True,
        hold_at_step4_when_wiring_fault_unrepaired=True,
        show_blackbox_required_dialog_before_step5=True,
        allow_blackbox_inspection=True,
        allow_blackbox_repair=True,
        auto_clear_fault_only_when_all_blackboxes_normal=True,
        allow_admin_shortcuts=False,
        record_assessment_metrics=True,
        auto_score_assessment=True,
        assessment_ends_after_step4_closed_loop=True,
    ),
}


class FlowModeManager:
    def __init__(self, test_flow_mode: str = 'teaching'):
        self.test_flow_mode = test_flow_mode

    def flow_policy(self) -> FlowModePolicy:
        return FLOW_MODE_POLICIES.get(self.test_flow_mode, FLOW_MODE_POLICIES['teaching'])

    def flow_policy_flag(self, name: str) -> bool:
        return bool(getattr(self.flow_policy(), name))

    def is_teaching_mode(self) -> bool:
        return self.test_flow_mode == 'teaching'

    def is_engineering_mode(self) -> bool:
        return self.test_flow_mode == 'engineering'

    def is_assessment_mode(self) -> bool:
        return self.test_flow_mode == 'assessment'

    def can_advance_with_fault(self) -> bool:
        return self.flow_policy_flag('allow_continue_with_fault')

    # def require_all_measurements_before_finalize(self) -> bool:
    #     return self.flow_policy_flag('require_all_measurements_before_finalize')

    # def require_step_pass_to_finalize(self) -> bool:
    #     return self.flow_policy_flag('require_step_pass_to_finalize')

    def should_show_fault_detected_banner(self) -> bool:
        return self.flow_policy_flag('show_fault_detected_banner')

    def should_show_diagnostic_hints(self) -> bool:
        return self.flow_policy_flag('show_diagnostic_hints')

    def should_block_step5_until_blackbox_fixed(self) -> bool:
        return self.flow_policy_flag('block_step5_until_blackbox_fixed')

    def should_hold_at_step4_when_wiring_fault_unrepaired(self) -> bool:
        return self.flow_policy_flag('hold_at_step4_when_wiring_fault_unrepaired')

    def should_show_blackbox_required_dialog_before_step5(self) -> bool:
        return self.flow_policy_flag('show_blackbox_required_dialog_before_step5')

    def can_inspect_blackbox(self) -> bool:
        return self.flow_policy_flag('allow_blackbox_inspection')

    def can_repair_in_blackbox(self) -> bool:
        return self.flow_policy_flag('allow_blackbox_repair')

    def should_auto_clear_fault_only_when_all_blackboxes_normal(self) -> bool:
        return self.flow_policy_flag('auto_clear_fault_only_when_all_blackboxes_normal')

    def allow_admin_shortcuts(self) -> bool:
        return self.flow_policy_flag('allow_admin_shortcuts')

    def can_use_pt_exam_quick_record(self) -> bool:
        return self.allow_admin_shortcuts() or self.is_assessment_mode()

    def should_record_assessment_metrics(self) -> bool:
        return self.flow_policy_flag('record_assessment_metrics')

    def should_auto_score_assessment(self) -> bool:
        return self.flow_policy_flag('auto_score_assessment')

    def assessment_ends_after_step4_closed_loop(self) -> bool:
        return self.flow_policy_flag('assessment_ends_after_step4_closed_loop')
