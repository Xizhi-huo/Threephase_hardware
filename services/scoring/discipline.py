from __future__ import annotations

from typing import List, Tuple

from domain.assessment import AssessmentPenalty, AssessmentScoreItem
from services.scoring._common import first_step_index, make_score_item
from services.scoring.context import ScoringContext


def score_discipline(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    blocked_events = ctx.blocked_events
    finalize_rejected = ctx.finalize_rejected
    gate_block_events = ctx.gate_block_events

    idx1 = first_step_index(ctx.step_enter_events, 1)
    idx2 = first_step_index(ctx.step_enter_events, 2)
    idx3 = first_step_index(ctx.step_enter_events, 3)
    idx4 = first_step_index(ctx.step_enter_events, 4)

    a1_score = 2 if idx1 is not None and idx2 is not None and idx1 < idx2 else 0
    item, penalty = make_score_item(
        "A1",
        "顺序进入第二步",
        "流程纪律",
        2,
        a1_score,
        2,
        "第二步进入顺序正确。" if a1_score else "第二步进入顺序异常。",
        "第二步进入顺序异常。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    a2_score = 2 if idx2 is not None and idx3 is not None and idx2 < idx3 else 0
    item, penalty = make_score_item(
        "A2",
        "顺序进入第三步",
        "流程纪律",
        2,
        a2_score,
        3,
        "第三步进入顺序正确。" if a2_score else "第三步进入顺序异常。",
        "第三步进入顺序异常。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    a3_score = 2 if idx3 is not None and idx4 is not None and idx3 < idx4 else 0
    item, penalty = make_score_item(
        "A3",
        "顺序进入第四步",
        "流程纪律",
        2,
        a3_score,
        4,
        "第四步进入顺序正确。" if a3_score else "第四步进入顺序异常。",
        "第四步进入顺序异常。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    a4_deduction = min(5, len(blocked_events))
    a4_score = 5 - a4_deduction
    item, penalty = make_score_item(
        "A4",
        "不越级推进",
        "流程纪律",
        5,
        a4_score,
        detail=(
            "未出现越级推进尝试。"
            if a4_score == 5
            else f"共发生 {len(blocked_events)} 次越级或门禁拦截。"
        ),
        penalty_message="存在越级推进或门禁拦截记录。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    gate_violations = len(finalize_rejected) + len(gate_block_events)
    a5_deduction = min(5, gate_violations)
    a5_score = 5 - a5_deduction
    item, penalty = make_score_item(
        "A5",
        "遵守异常与闭环门禁",
        "流程纪律",
        5,
        a5_score,
        4,
        (
            "未出现异常后强行完成步骤或闭环未完成仍继续推进。"
            if a5_score == 5
            else f"共发生 {gate_violations} 次违规推进尝试。"
        ),
        "未严格遵守异常停留或闭环门禁。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties
