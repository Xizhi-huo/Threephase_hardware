from __future__ import annotations

from typing import List, Tuple

from domain.assessment import AssessmentPenalty, AssessmentScoreItem
from services.scoring._common import make_score_item
from services.scoring.context import ScoringContext


def score_fault_diagnosis(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    session = ctx.session
    hidden_fault = ctx.hidden_fault
    blackbox_open_before_gate = ctx.blackbox_open_before_gate
    detected_before_gate = ctx.detected_before_gate
    expected_targets = ctx.expected_targets
    expected_target_set = ctx.expected_target_set
    expected_device_set = ctx.expected_device_set
    opened_target_set = ctx.opened_target_set
    touched_layers = ctx.touched_layers

    if not session.scene_id:
        f1_score = 4
        f1_detail = "正常场景不要求故障识别。"
    else:
        identified = detected_before_gate or (hidden_fault and blackbox_open_before_gate)
        f1_score = 4 if identified else 0
        f1_detail = "已在第四步门禁前识别到异常。" if f1_score else "未在第四步门禁前识别到异常。"
    item, penalty = make_score_item(
        "F1",
        "第四步门禁前识别异常",
        "异常识别与故障定位",
        4,
        f1_score,
        4,
        f1_detail,
        "未在第四步门禁前识别异常。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if hidden_fault:
        f2_score = 4 if blackbox_open_before_gate else 0
        f2_detail = "已主动识别隐性故障。" if f2_score else "依赖系统门禁后才意识到隐性故障。"
    else:
        f2_score = 4
        f2_detail = "本场景不属于隐性故障，或已满足识别要求。"
    item, penalty = make_score_item(
        "F2",
        "隐性故障识别能力",
        "异常识别与故障定位",
        4,
        f2_score,
        4,
        f2_detail,
        "隐性故障识别能力不足。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not expected_targets:
        f3_score = 3
        f3_detail = "本场景无黑盒定位要求。"
    else:
        correct_side_hit = bool(opened_target_set & expected_device_set)
        f3_score = 3 if correct_side_hit else 0
        f3_detail = "已命中正确设备侧。" if f3_score else "未命中正确设备侧。"
    item, penalty = make_score_item(
        "F3",
        "定位到正确设备侧",
        "异常识别与故障定位",
        3,
        f3_score,
        4,
        f3_detail,
        "故障定位未命中正确设备侧。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not expected_targets:
        f4_score = 3
        f4_detail = "本场景无黑盒门禁定位要求。"
    else:
        layer_hit = bool(touched_layers & expected_target_set)
        f4_score = 3 if layer_hit else 0
        f4_detail = "已命中正确故障层级。" if f4_score else "未命中正确故障层级。"
    item, penalty = make_score_item(
        "F4",
        "定位到正确故障层级",
        "异常识别与故障定位",
        3,
        f4_score,
        4,
        f4_detail,
        "故障层级定位不准确。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties
