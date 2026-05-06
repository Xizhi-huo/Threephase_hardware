from PyQt5 import QtCore, QtGui, QtWidgets

from ui.tabs._step_style import apply_button_tone, set_props


def show_assessment_result_dialog(owner, result):
    score_labels = {
        "flow_discipline": "流程纪律",
        "loop_test": "第一步回路测试",
        "pt_voltage_check": "第二步PT电压检查",
        "pt_phase_check": "第三步PT相序检查",
        "pt_exam": "第四步压差考核",
        "anomaly_localization": "异常识别与故障定位",
        "blackbox_repair": "黑盒修复",
        "efficiency": "效率与规范性",
    }
    metric_labels = {
        "step_entered_order": "步骤进入顺序",
        "step_finalize_attempts": "完成本步尝试次数",
        "blocked_advances": "门禁拦截次数",
        "gate_blocks": "闭环门禁触发次数",
        "measurements_recorded": "测量记录总数",
        "invalid_measurements": "无效测量次数",
        "blackboxes_opened": "打开黑盒",
        "blackbox_swap_count": "黑盒交换次数",
        "blackbox_failed_confirms": "错误确认次数",
        "fault_detected_at_step": "首次发现异常步骤",
        "fault_repaired_at": "故障修复时间",
        "serious_misoperations": "严重误操作次数",
    }

    def _table_item(text, align=QtCore.Qt.AlignCenter):
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(int(align | QtCore.Qt.AlignVCenter))
        return item

    def _color_row(table, row, bg, fg="#0f172a"):
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None:
                item.setBackground(QtGui.QColor(bg))
                item.setForeground(QtGui.QColor(fg))

    def _status_palette(status_text: str):
        if status_text == "通过":
            return "#ecfdf5", "#166534", "#bbf7d0"
        if status_text == "未通过":
            return "#fef2f2", "#991b1b", "#fecaca"
        return "#fffbeb", "#92400e", "#fde68a"

    def _make_info_card(title_text: str, body_text: str, accent: str = "#cbd5e1", body_size: int = 20):
        card = QtWidgets.QFrame()
        set_props(card, dialogCard=True)
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(6)
        title_lbl = QtWidgets.QLabel(title_text)
        set_props(title_lbl, dialogCaption=True)
        card_lay.addWidget(title_lbl)
        bar = QtWidgets.QFrame()
        bar.setFixedHeight(4)
        bar.setStyleSheet(f"background:{accent}; border:none; border-radius:2px;")
        card_lay.addWidget(bar)
        body_lbl = QtWidgets.QLabel(body_text)
        body_lbl.setStyleSheet(f"font-size:{body_size}px; color:#0f172a; font-weight:bold;")
        body_lbl.setWordWrap(True)
        card_lay.addWidget(body_lbl)
        card_lay.addStretch()
        return card

    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("考核成绩单")
    dlg.resize(760, 720)
    set_props(dlg, themedDialog=True)
    dlg.setStyleSheet(
        "QLabel{color:#0f172a;}"
        "QHeaderView::section{background:#e2e8f0; color:#0f172a; padding:6px 8px; border:none; font-weight:bold;}"
        "QTableWidget{background:white; border:1px solid #dbe4f0; gridline-color:#eef2f7; border-radius:10px;}"
    )
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(10)
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    content = QtWidgets.QWidget()
    content_lay = QtWidgets.QVBoxLayout(content)
    content_lay.setContentsMargins(0, 0, 0, 0)
    content_lay.setSpacing(12)
    scroll.setWidget(content)
    lay.addWidget(scroll, 1)

    result_tag = "通过" if result.passed else "未通过"
    tag_bg = "#dcfce7" if result.passed else "#fee2e2"
    tag_fg = "#166534" if result.passed else "#991b1b"
    overview = QtWidgets.QFrame()
    set_props(overview, dialogCard=True)
    overview_lay = QtWidgets.QHBoxLayout(overview)
    overview_lay.setContentsMargins(18, 16, 18, 16)
    overview_lay.setSpacing(14)
    hero = QtWidgets.QFrame()
    hero_lay = QtWidgets.QVBoxLayout(hero)
    hero_lay.setContentsMargins(0, 0, 0, 0)
    hero_lay.setSpacing(8)
    kicker = QtWidgets.QLabel("考核结果报告")
    set_props(kicker, dialogKicker=True)
    hero_lay.addWidget(kicker)
    title = QtWidgets.QLabel("考核成绩单")
    set_props(title, dialogTitle=True)
    hero_lay.addWidget(title)
    hero_info = QtWidgets.QLabel(
        f"场景：{result.scene_id or '正常模式'}    模式：考核模式\n完成时间：{result.finished_at.replace('T', ' ')}"
    )
    set_props(hero_info, dialogCaption=True)
    hero_lay.addWidget(hero_info)
    tag = QtWidgets.QLabel(result_tag)
    tag.setAlignment(QtCore.Qt.AlignCenter)
    tag.setFixedWidth(94)
    tag.setStyleSheet(
        f"background:{tag_bg}; color:{tag_fg}; font-size:15px; font-weight:bold; border-radius:16px; padding:7px 12px;"
    )
    hero_lay.addWidget(tag, alignment=QtCore.Qt.AlignLeft)
    overview_lay.addWidget(hero, 2)
    side_cards = QtWidgets.QVBoxLayout()
    side_cards.setContentsMargins(0, 0, 0, 0)
    side_cards.setSpacing(10)
    side_cards.addWidget(_make_info_card("总分", f"{result.total_score} / {result.max_score}", "#f59e0b", 30))
    side_cards.addWidget(_make_info_card("总耗时", f"{result.elapsed_seconds}s", "#0ea5e9", 22))
    overview_lay.addLayout(side_cards, 1)
    content_lay.addWidget(overview)

    summary = QtWidgets.QLabel(result.summary)
    summary.setWordWrap(True)
    set_props(summary, dialogCard=True)
    summary.setContentsMargins(14, 14, 14, 14)
    content_lay.addWidget(summary)
    if result.veto_reason:
        veto = QtWidgets.QLabel(f"否决原因：{result.veto_reason}")
        veto.setWordWrap(True)
        set_props(veto, stepBanner=True, tone="danger")
        content_lay.addWidget(veto)

    section1 = QtWidgets.QLabel("分项汇总")
    set_props(section1, dialogSection=True)
    content_lay.addWidget(section1)
    summary_grid_wrap = QtWidgets.QFrame()
    summary_grid = QtWidgets.QGridLayout(summary_grid_wrap)
    summary_grid.setContentsMargins(0, 0, 0, 0)
    summary_grid.setHorizontalSpacing(10)
    summary_grid.setVerticalSpacing(10)
    for idx, (key, value) in enumerate(result.step_scores.items()):
        max_value = result.step_max_scores.get(key, 0)
        bg, fg, border = _status_palette("通过" if value == max_value else "未通过" if value == 0 else "部分扣分")
        card = QtWidgets.QFrame()
        card.setStyleSheet(f"background:{bg}; border:1px solid {border}; border-radius:14px;")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(14, 12, 14, 12)
        card_lay.setSpacing(4)
        name_lbl = QtWidgets.QLabel(score_labels.get(key, key))
        set_props(name_lbl, dialogCaption=True)
        name_lbl.setStyleSheet(f"color:{fg}; font-weight:bold;")
        card_lay.addWidget(name_lbl)
        score_lbl = QtWidgets.QLabel(f"{value} / {max_value}")
        score_lbl.setStyleSheet("font-size:24px; color:#0f172a; font-weight:bold;")
        card_lay.addWidget(score_lbl)
        note = "表现稳定" if value == max_value else "需要重点关注" if value == 0 else "存在扣分项"
        note_lbl = QtWidgets.QLabel(note)
        set_props(note_lbl, dialogCaption=True)
        card_lay.addWidget(note_lbl)
        summary_grid.addWidget(card, idx // 2, idx % 2)
    content_lay.addWidget(summary_grid_wrap)

    section2 = QtWidgets.QLabel("详细计分点")
    set_props(section2, dialogSection=True)
    content_lay.addWidget(section2)
    detail_hint = QtWidgets.QLabel("以下表格列出每个计分点的通过情况、得分与具体说明。")
    set_props(detail_hint, dialogCaption=True)
    content_lay.addWidget(detail_hint)
    detail_table = QtWidgets.QTableWidget(len(result.score_items), 8)
    detail_table.setHorizontalHeaderLabels(["编号", "计分点", "类别", "结果", "满分", "实得", "步骤", "说明"])
    detail_table.verticalHeader().setVisible(False)
    detail_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    detail_table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
    detail_table.setAlternatingRowColors(False)
    detail_table.setShowGrid(False)
    for col in range(7):
        detail_table.horizontalHeader().setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
    detail_table.horizontalHeader().setSectionResizeMode(7, QtWidgets.QHeaderView.Stretch)
    for row, item in enumerate(result.score_items):
        detail_table.setItem(row, 0, _table_item(item.code))
        detail_table.setItem(row, 1, _table_item(item.title, QtCore.Qt.AlignLeft))
        detail_table.setItem(row, 2, _table_item(item.category))
        detail_table.setItem(row, 3, _table_item(item.status))
        detail_table.setItem(row, 4, _table_item(str(item.max_score)))
        detail_table.setItem(row, 5, _table_item(str(item.earned_score)))
        detail_table.setItem(row, 6, _table_item("-" if item.step <= 0 else str(item.step)))
        detail_table.setItem(row, 7, _table_item(item.detail, QtCore.Qt.AlignLeft))
        if item.status == "通过":
            _color_row(detail_table, row, "#ecfdf5", "#166534")
        elif item.status == "未通过":
            _color_row(detail_table, row, "#fef2f2", "#991b1b")
        else:
            _color_row(detail_table, row, "#fffbeb", "#92400e")
    detail_table.setFixedHeight(detail_table.horizontalHeader().height() + max(6, detail_table.rowCount()) * 30 + 4)
    content_lay.addWidget(detail_table)

    section3 = QtWidgets.QLabel("过程统计")
    set_props(section3, dialogSection=True)
    content_lay.addWidget(section3)
    extra_penalties = [penalty for penalty in result.penalties if penalty.code in {"X1", "X2"}]
    if extra_penalties:
        section_extra = QtWidgets.QLabel("额外扣分说明")
        set_props(section_extra, dialogSection=True)
        content_lay.addWidget(section_extra)
        extra_wrap = QtWidgets.QFrame()
        extra_wrap.setStyleSheet("background:white; border:1px solid #fecaca; border-radius:12px;")
        extra_lay = QtWidgets.QVBoxLayout(extra_wrap)
        extra_lay.setContentsMargins(14, 12, 14, 12)
        extra_lay.setSpacing(8)
        for penalty in extra_penalties:
            step_text = f"第 {penalty.step} 步" if penalty.step > 0 else "流程外"
            item_lbl = QtWidgets.QLabel(f"{step_text}：{penalty.message}（{penalty.score_delta} 分）")
            item_lbl.setWordWrap(True)
            item_lbl.setStyleSheet("font-size:13px; color:#991b1b; font-weight:bold;")
            extra_lay.addWidget(item_lbl)
        content_lay.addWidget(extra_wrap)

    metric_labels.update({
        "fault_selection_mode": "随机出题方式",
        "fault_guess_scene_id": "学员判定故障",
        "fault_guess_correct": "判定结果",
        "actual_fault_scene_id": "实际故障",
        "early_pt_blackbox_opened": "前两步提前打开 PT 黑盒次数",
        "extra_deduction_total": "额外扣分合计",
    })
    metric_rows = []
    for key, value in result.metrics.items():
        if isinstance(value, list):
            value_text = "、".join(str(v) for v in value if v not in (None, "")) or "-"
        else:
            value_text = "-" if value in (None, "", 0) and key == "fault_repaired_at" else str(value)
        metric_rows.append((metric_labels.get(key, key), value_text))
    metrics_wrap = QtWidgets.QFrame()
    metrics_grid = QtWidgets.QGridLayout(metrics_wrap)
    metrics_grid.setContentsMargins(0, 0, 0, 0)
    metrics_grid.setHorizontalSpacing(10)
    metrics_grid.setVerticalSpacing(10)
    for idx, (label, value_text) in enumerate(metric_rows):
        card = QtWidgets.QFrame()
        card.setStyleSheet("background:white; border:1px solid #dbe4f0; border-radius:12px;")
        card_lay = QtWidgets.QVBoxLayout(card)
        card_lay.setContentsMargins(12, 10, 12, 10)
        card_lay.setSpacing(4)
        label_lbl = QtWidgets.QLabel(label)
        set_props(label_lbl, dialogCaption=True)
        card_lay.addWidget(label_lbl)
        value_lbl = QtWidgets.QLabel(value_text)
        value_lbl.setWordWrap(True)
        value_lbl.setStyleSheet("font-size:13px; color:#0f172a; font-weight:bold;")
        card_lay.addWidget(value_lbl)
        metrics_grid.addWidget(card, idx // 2, idx % 2)
    content_lay.addWidget(metrics_wrap)
    content_lay.addStretch()
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    btn_close = QtWidgets.QPushButton("关闭")
    apply_button_tone(owner, btn_close, "primary")
    btn_close.clicked.connect(dlg.accept)
    btn_row.addWidget(btn_close)
    lay.addLayout(btn_row)
    dlg.adjustSize()
    dlg.resize(max(340, dlg.sizeHint().width()), dlg.sizeHint().height())
    dlg.exec_()
