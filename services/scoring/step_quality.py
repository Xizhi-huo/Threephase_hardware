from __future__ import annotations

from typing import List, Tuple

from domain.assessment import AssessmentPenalty, AssessmentScoreItem
from domain.test_states import LOOP_TEST_RECORD_KEYS
from services.scoring._common import count_present, make_score_item, nine_group_completion_score, trio_completion_score
from services.scoring.context import ScoringContext


def _score_loop_test(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    loop_records = ctx.loop_records
    loop_complete = ctx.loop_complete

    for index, pair in enumerate(LOOP_TEST_RECORD_KEYS, start=1):
        recorded = loop_records.get(pair) is not None
        item, penalty = make_score_item(
            f"B{index}",
            f"{pair}回路记录完成",
            "第一步回路测试",
            1,
            1 if recorded else 0,
            1,
            f"{pair}回路已完成记录。" if recorded else f"{pair}回路记录缺失。",
            f"{pair}回路记录缺失。",
        )
        items.append(item)
        if penalty is not None:
            penalties.append(penalty)

    b7_score = 4 if loop_complete else 2 if count_present(loop_records) >= 4 else 0
    item, penalty = make_score_item(
        "B7",
        "第一步结果提交规范",
        "第一步回路测试",
        4,
        b7_score,
        1,
        "第一步已形成完整闭环。" if b7_score == 4 else "第一步存在漏项或未完成确认。",
        "第一步结果提交不规范。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def _score_pt_voltage_check(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    pt1_voltage_count = ctx.pt1_voltage_count
    pt2_voltage_count = ctx.pt2_voltage_count
    pt3_voltage_count = ctx.pt3_voltage_count
    session = ctx.session
    detection_step = ctx.detection_step
    fault_detected_event = ctx.fault_detected_event

    c1_score = trio_completion_score(pt1_voltage_count)
    item, penalty = make_score_item(
        "C1",
        "PT1电压记录完整",
        "第二步PT电压检查",
        3,
        c1_score,
        2,
        f"PT1 已记录 {pt1_voltage_count}/3 项。",
        "PT1 电压记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    c2_score = trio_completion_score(pt2_voltage_count)
    item, penalty = make_score_item(
        "C2",
        "PT2电压记录完整",
        "第二步PT电压检查",
        3,
        c2_score,
        2,
        f"PT2 已记录 {pt2_voltage_count}/3 项。",
        "PT2 电压记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    c3_score = trio_completion_score(pt3_voltage_count)
    item, penalty = make_score_item(
        "C3",
        "PT3电压记录完整",
        "第二步PT电压检查",
        3,
        c3_score,
        2,
        f"PT3 已记录 {pt3_voltage_count}/3 项。",
        "PT3 电压记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not session.scene_id or detection_step != 2:
        c4_score = 3
        c4_detail = "第二步不承担本场景的关键异常识别。"
    else:
        c4_score = 3 if fault_detected_event is not None and fault_detected_event.step <= 2 else 0
        c4_detail = "已在第二步形成有效电压异常判断。" if c4_score else "未在第二步形成有效电压异常判断。"
    item, penalty = make_score_item(
        "C4",
        "第二步结果判读有效",
        "第二步PT电压检查",
        3,
        c4_score,
        2,
        c4_detail,
        "第二步结果判读不足。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def _score_pt_phase_check(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    pt1_phase_count = ctx.pt1_phase_count
    pt3_phase_count = ctx.pt3_phase_count
    invalid_by_step = ctx.invalid_by_step
    session = ctx.session
    detection_step = ctx.detection_step
    fault_detected_event = ctx.fault_detected_event

    d1_score = trio_completion_score(pt1_phase_count)
    item, penalty = make_score_item(
        "D1",
        "PT1相序记录完整",
        "第三步PT相序检查",
        3,
        d1_score,
        3,
        f"PT1 已记录 {pt1_phase_count}/3 项。",
        "PT1 相序记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    d2_score = trio_completion_score(pt3_phase_count)
    item, penalty = make_score_item(
        "D2",
        "PT3相序记录完整",
        "第三步PT相序检查",
        3,
        d2_score,
        3,
        f"PT3 已记录 {pt3_phase_count}/3 项。",
        "PT3 相序记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    d3_score = 2 if invalid_by_step[3] == 0 else 1 if invalid_by_step[3] == 1 else 0
    item, penalty = make_score_item(
        "D3",
        "第三步记录顺序规范",
        "第三步PT相序检查",
        2,
        d3_score,
        3,
        "第三步记录顺序与接线选择规范。" if d3_score == 2 else f"第三步存在 {invalid_by_step[3]} 次无效测量。",
        "第三步记录顺序或接线操作不规范。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not session.scene_id or detection_step != 3:
        d4_score = 4
        d4_detail = "第三步不承担本场景的关键异常识别。"
    else:
        d4_score = 4 if fault_detected_event is not None and fault_detected_event.step <= 3 else 0
        d4_detail = "已在第三步形成有效相序异常判断。" if d4_score else "未在第三步形成有效相序异常判断。"
    item, penalty = make_score_item(
        "D4",
        "第三步能识别相序异常",
        "第三步PT相序检查",
        4,
        d4_score,
        3,
        d4_detail,
        "第三步异常识别不足。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def _score_pt_exam(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    gen1_exam_count = ctx.gen1_exam_count
    gen2_exam_count = ctx.gen2_exam_count
    invalid_by_step = ctx.invalid_by_step
    finalize_rejected_by_step = ctx.finalize_rejected_by_step
    session = ctx.session
    hidden_fault = ctx.hidden_fault
    blackbox_open_before_gate = ctx.blackbox_open_before_gate
    fault_detected_event = ctx.fault_detected_event

    e1_score = nine_group_completion_score(gen1_exam_count)
    item, penalty = make_score_item(
        "E1",
        "Gen1压差记录完整",
        "第四步压差考核",
        4,
        e1_score,
        4,
        f"Gen1 已记录 {gen1_exam_count}/9 组。",
        "Gen1 压差记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    e2_score = nine_group_completion_score(gen2_exam_count)
    item, penalty = make_score_item(
        "E2",
        "Gen2压差记录完整",
        "第四步压差考核",
        4,
        e2_score,
        4,
        f"Gen2 已记录 {gen2_exam_count}/9 组。",
        "Gen2 压差记录不完整。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    e3_score = 2 if invalid_by_step[4] == 0 and finalize_rejected_by_step[4] == 0 else 1 if invalid_by_step[4] <= 1 else 0
    item, penalty = make_score_item(
        "E3",
        "第四步操作顺序规范",
        "第四步压差考核",
        2,
        e3_score,
        4,
        "第四步操作顺序规范。" if e3_score == 2 else "第四步存在无效测量或过早完成尝试。",
        "第四步操作顺序不规范。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    if not session.scene_id:
        e4_score = 6
        e4_detail = "正常场景无需形成故障判断。"
    elif hidden_fault:
        e4_score = 6 if blackbox_open_before_gate else 0
        e4_detail = "已在系统拦截前通过拆检形成判断。" if e4_score else "直到系统门禁拦截后才意识到第四步仍未闭环。"
    else:
        e4_score = 6 if fault_detected_event is not None and fault_detected_event.step <= 4 else 0
        e4_detail = "已在第四步内形成有效判断。" if e4_score else "未在第四步内形成有效判断。"
    item, penalty = make_score_item(
        "E4",
        "第四步形成有效判断",
        "第四步压差考核",
        6,
        e4_score,
        4,
        e4_detail,
        "第四步未形成有效判断。",
    )
    items.append(item)
    if penalty is not None:
        penalties.append(penalty)

    return items, penalties


def score_step_quality(ctx: ScoringContext) -> Tuple[List[AssessmentScoreItem], List[AssessmentPenalty]]:
    items: List[AssessmentScoreItem] = []
    penalties: List[AssessmentPenalty] = []
    for scorer in (_score_loop_test, _score_pt_voltage_check, _score_pt_phase_check, _score_pt_exam):
        scored_items, scored_penalties = scorer(ctx)
        items.extend(scored_items)
        penalties.extend(scored_penalties)
    return items, penalties
