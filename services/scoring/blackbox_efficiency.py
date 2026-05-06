from __future__ import annotations

from typing import List, Tuple

from domain.assessment import AssessmentPenalty, AssessmentScoreItem
from services.scoring._common import make_score_item
from services.scoring.context import ScoringContext


def _score_blackbox_repair(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    expected_targets = ctx.expected_targets
    expected_target_set = ctx.expected_target_set
    expected_device_set = ctx.expected_device_set
    opened_target_set = ctx.opened_target_set
    touched_layers = ctx.touched_layers
    repair_required = ctx.repair_required
    repaired = ctx.repaired
    blackbox_failed_confirms = ctx.blackbox_failed_confirms
    blackbox_swap_count = ctx.blackbox_swap_count

    if not expected_targets:
        g1_score = 3
        g1_detail = "本场景无黑盒范围控制要求。"
    else:
        extra_targets = len(opened_target_set - expected_device_set)
        missing_targets = len(expected_device_set - opened_target_set)
        if extra_targets == 0 and missing_targets == 0:
            g1_score = 3
        elif extra_targets <= 1 and missing_targets <= 1:
            g1_score = 1
        else:
            g1_score = 0
        g1_detail = (
            "黑盒开启范围与场景需求一致。"
            if g1_score == 3
            else f"存在额外打开 {extra_targets} 个、缺失 {missing_targets} 个目标。"
        )
    item, penalty = make_score_item(
        "G1",
        "黑盒开启范围合理",
        "黑盒修复",
        3,
        g1_score,
        4,
        g1_detail,
        "黑盒开启范围不合理。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not repair_required:
        g2_score = 5
        g2_detail = "本场景不依赖黑盒修复闭环。"
    else:
        g2_score = 5 if repaired else 0
        g2_detail = "最终修复结果正确。" if g2_score else "考核结束时仍未完成正确修复。"
    item, penalty = make_score_item(
        "G2",
        "最终修复结果正确",
        "黑盒修复",
        5,
        g2_score,
        4,
        g2_detail,
        "最终修复结果不正确。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not repair_required:
        g3_score = 4
        g3_detail = "本场景无黑盒修复路径要求。"
    elif not repaired:
        g3_score = 0
        g3_detail = "未形成有效修复闭环。"
    else:
        g3_score = 4
        if not touched_layers.issuperset(expected_target_set):
            g3_score -= 2
        g3_score -= min(1, blackbox_failed_confirms)
        g3_score -= min(1, max(0, blackbox_swap_count - max(1, len(expected_target_set))))
        g3_score = max(0, g3_score)
        g3_detail = (
            "修复路径合理，操作效率正常。"
            if g3_score == 4
            else f"存在黑盒操作折返：交换 {blackbox_swap_count} 次，错误确认 {blackbox_failed_confirms} 次。"
        )
    item, penalty = make_score_item(
        "G3",
        "修复路径合理",
        "黑盒修复",
        4,
        g3_score,
        4,
        g3_detail,
        "黑盒修复路径合理性不足。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def _score_efficiency(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    elapsed_seconds = ctx.elapsed_seconds
    blocked_events = ctx.blocked_events
    finalize_rejected = ctx.finalize_rejected
    invalid_events = ctx.invalid_events

    if elapsed_seconds <= 300:
        h1_score = 4
    elif elapsed_seconds <= 480:
        h1_score = 3
    elif elapsed_seconds <= 660:
        h1_score = 2
    elif elapsed_seconds <= 900:
        h1_score = 1
    else:
        h1_score = 0
    h1_detail = {
        4: "总耗时控制优秀。",
        3: "总耗时控制良好。",
        2: "总耗时偏长。",
        1: "总耗时明显偏长。",
        0: "总耗时严重超标。",
    }[h1_score]
    item, penalty = make_score_item(
        "H1",
        "总耗时控制",
        "效率与规范性",
        4,
        h1_score,
        detail=h1_detail,
        penalty_message="总耗时控制未达到理想水平。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    invalid_operation_count = len(blocked_events) + len(finalize_rejected) + len(invalid_events)
    if invalid_operation_count <= 2:
        h2_score = 4
    elif invalid_operation_count <= 4:
        h2_score = 3
    elif invalid_operation_count <= 6:
        h2_score = 2
    elif invalid_operation_count <= 8:
        h2_score = 1
    else:
        h2_score = 0
    h2_detail = (
        "无效测量与违规操作控制良好。"
        if h2_score == 4
        else f"累计无效/违规操作 {invalid_operation_count} 次。"
    )
    item, penalty = make_score_item(
        "H2",
        "无效操作控制",
        "效率与规范性",
        4,
        h2_score,
        detail=h2_detail,
        penalty_message="无效测量或违规操作次数偏多。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def score_blackbox_efficiency(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    for scorer in (_score_blackbox_repair, _score_efficiency):
        scored_items, scored_penalties = scorer(ctx)
        items.extend(scored_items)
        penalties.extend(scored_penalties)
    return items, penalties
