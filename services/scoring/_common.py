from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from domain.assessment import AssessmentEvent, AssessmentPenalty, AssessmentScoreItem
from domain.measurement_schema import is_record_complete


def make_score_item(
    code: str,
    title: str,
    category: str,
    max_score: int,
    earned_score: int,
    step: int = 0,
    detail: str = "",
    penalty_message: str = "",
) -> Tuple[AssessmentScoreItem, Optional[AssessmentPenalty]]:
    earned_score = max(0, min(max_score, earned_score))
    if earned_score >= max_score:
        status = "通过"
    elif earned_score <= 0:
        status = "未通过"
    else:
        status = "部分扣分"

    item = AssessmentScoreItem(
        code=code,
        title=title,
        category=category,
        status=status,
        max_score=max_score,
        earned_score=earned_score,
        step=step,
        detail=detail,
    )

    lost_score = max_score - earned_score
    if lost_score > 0 and penalty_message:
        penalty = AssessmentPenalty(
            code=code,
            message=penalty_message,
            score_delta=-lost_score,
            step=step,
        )
        return item, penalty
    return item, None


def count_present(records: Dict[str, object]) -> int:
    return sum(
        1
        for value in records.values()
        if value is not None and (
            not isinstance(value, dict)
            or "quality" not in value
            or is_record_complete(value)
        )
    )


def trio_completion_score(count_value: int) -> int:
    if count_value >= 3:
        return 3
    if count_value == 2:
        return 2
    if count_value == 1:
        return 1
    return 0


def nine_group_completion_score(count_value: int) -> int:
    if count_value >= 9:
        return 4
    if count_value >= 7:
        return 3
    if count_value >= 5:
        return 2
    if count_value >= 3:
        return 1
    return 0


def first_step_index(step_enter_events: List[AssessmentEvent], step: int) -> Optional[int]:
    for idx, event in enumerate(step_enter_events):
        if event.step == step:
            return idx
    return None
