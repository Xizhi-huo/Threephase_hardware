from PyQt5 import QtCore, QtWidgets

from domain.fault_scenarios import SCENARIOS
from ui.tabs._step_style import apply_button_tone, set_props
from ui.widgets.gen_wiring_widget import GenWiringWidget
from ui.widgets.pt_wiring_widget import PTWiringWidget
from ui.widgets.step_panels._panel_builders import tone_from_color


def show_blackbox_required_dialog(owner, *, is_assessment, scene_id):
    info = SCENARIOS.get(scene_id, {})
    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("⚠️ 当前流程尚未闭环" if is_assessment else "⚠️ 仍有接线故障未修复")
    dlg.setModal(True)
    dlg.resize(500, 300)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(10)
    title_text = "当前考核尚未闭环" if is_assessment else info.get("title", "故障") + " — 需先完成黑盒修复"
    title_lbl = QtWidgets.QLabel(title_text)
    title_lbl.setStyleSheet("font-size:14px; font-weight:bold; color:#991b1b;")
    lay.addWidget(title_lbl)
    if is_assessment:
        hint_text = "当前考核仍未满足结束条件，暂不能继续后续流程。\n\n请根据前四步已获得的测量结果继续排查并完成闭环。如需进一步确认，可进入黑盒检查，但系统不会提供具体故障位置提示。"
    else:
        hint_text = "当前仍存在未恢复的物理接线错误，不能进入第五步【同步功能测试】。\n\n请先回到当前流程中的黑盒检查区，完成相关接线修复。只有当相关接线全部恢复为正确顺序后，系统才会自动允许进入第五步。"
    hint = QtWidgets.QLabel(hint_text)
    hint.setWordWrap(True)
    hint.setStyleSheet("font-size:12px; color:#1f2937; background:#fff7ed; border:1px solid #fdba74; border-radius:4px; padding:8px;")
    lay.addWidget(hint)
    if not is_assessment:
        symptom_lbl = QtWidgets.QLabel("【当前已记录的异常现象】\n" + info.get("symptom", ""))
        symptom_lbl.setWordWrap(True)
        symptom_lbl.setStyleSheet("font-size:11px; color:#374151; background:#fef3c7; padding:6px; border-radius:4px;")
        lay.addWidget(symptom_lbl)
    btn_ok = QtWidgets.QPushButton("知道了")
    btn_ok.setStyleSheet("background:#334155; color:white; font-weight:bold; padding:6px 14px;")
    btn_ok.clicked.connect(dlg.accept)
    lay.addWidget(btn_ok, alignment=QtCore.Qt.AlignRight)
    dlg.exec_()


def show_blackbox_dialog(owner, *, api, step, target):
    if not api.can_inspect_blackbox():
        return
    sim = api.sim_state
    fc = sim.fault_config
    allow_repair = api.can_repair_in_blackbox()
    assessment_mode = api.is_assessment_mode()
    blackbox_state = api.get_blackbox_runtime_state(target)
    fault_active = blackbox_state["fault_active"]
    dlg = QtWidgets.QDialog(owner)
    set_props(dlg, themedDialog=True)
    dlg.setMinimumWidth(340)
    vlay = QtWidgets.QVBoxLayout(dlg)
    vlay.setSpacing(6)
    vlay.setContentsMargins(12, 10, 12, 10)
    widget = None
    repair_target = None
    initial_order = None
    initial_pri_order = None
    initial_sec_order = None
    initial_sec_polarity = None

    if target in ("G1", "G2"):
        dlg.setWindowTitle(f"发电机 {target} 机端接线检查")
        order = blackbox_state["order"]
        mapping = {"A": order[0], "B": order[1], "C": order[2]}
        repair_target = blackbox_state["repair_target"]
        sub = QtWidgets.QLabel("上方绕组（A黄/B绿/C红）→ 下方接线柱（U/V/W）" + (" [可交互修复]" if allow_repair else " [仅查看]"))
        set_props(sub, dialogCaption=True)
        vlay.addWidget(sub)
        widget = GenWiringWidget(mapping, interactive=allow_repair)
        initial_order = widget.get_order()
        vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
    elif target == "PT1":
        dlg.setWindowTitle("PT1 接线盒检查 [一次/二次侧可交互修复]" if allow_repair else "PT1 接线盒检查 [只读]")
        pri_input_order = blackbox_state["pri_input_order"]
        pri_order = blackbox_state["pri_order"]
        sec_order = blackbox_state["sec_order"]
        sub = QtWidgets.QLabel(
            "PT1 接线按当前物理状态绘制：一次侧与二次侧均可点击互换并分别修复。"
            if allow_repair else "PT1 接线按当前物理状态绘制：当前流程模式仅允许查看，不允许直接修复。"
        )
        set_props(sub, dialogCaption=True)
        vlay.addWidget(sub)
        widget = PTWiringWidget(
            pri_order,
            sec_order,
            pri_input_order=pri_input_order,
            interactive_pri=allow_repair,
            interactive_sec=allow_repair,
        )
        initial_pri_order = widget.get_pri_order()
        initial_sec_order = widget.get_sec_order()
        vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
        repair_target = blackbox_state["repair_target"]
    elif target == "PT3":
        dlg.setWindowTitle("PT3 接线盒检查 [二次侧可交互修复]" if allow_repair else "PT3 接线盒检查 [只读]")
        pri_input_order = blackbox_state["pri_input_order"]
        pri_order = blackbox_state["pri_order"]
        sec_order = blackbox_state["sec_order"]
        sec_polarity = blackbox_state.get("sec_polarity")
        sub = QtWidgets.QLabel(
            "上: 二次侧输出→测量端口 [可互换/可切换极性]  |  下: 一次侧输入←Gen2 [只读]"
            if allow_repair else "上: 二次侧输出→测量端口 [只读]  |  下: 一次侧输入←Gen2 [只读]"
        )
        set_props(sub, dialogCaption=True)
        vlay.addWidget(sub)
        widget = PTWiringWidget(
            pri_order,
            sec_order,
            pri_input_order=pri_input_order,
            sec_polarity=sec_polarity,
            interactive_sec=allow_repair,
            interactive_polarity=allow_repair,
        )
        initial_pri_order = widget.get_pri_order()
        initial_sec_order = widget.get_sec_order()
        initial_sec_polarity = widget.get_sec_polarity()
        vlay.addWidget(widget, alignment=QtCore.Qt.AlignHCenter)
        repair_target = blackbox_state["repair_target"]
        if fault_active and fc.scenario_id == "E03" and not assessment_mode:
            note = QtWidgets.QLabel("⚠ A 相极性反接：A1 正负极颠倒（a2 输出反相）")
            set_props(note, stepBanner=True, tone="warning")
            note.setWordWrap(True)
            vlay.addWidget(note)

    fb_lbl = QtWidgets.QLabel("")
    fb_lbl.setWordWrap(True)
    set_props(fb_lbl, feedbackText=True, tone="neutral")
    fb_lbl.setVisible(False)
    vlay.addWidget(fb_lbl)
    btn_row = QtWidgets.QWidget()
    bh = QtWidgets.QHBoxLayout(btn_row)
    bh.setContentsMargins(0, 0, 0, 0)
    bh.setSpacing(6)

    if repair_target is not None:
        def _on_confirm():
            new_order = widget.get_order() if repair_target in ("G1", "G2") else None
            new_pri = widget.get_pri_order() if repair_target in ("PT1", "PT3") else None
            new_sec = widget.get_sec_order() if repair_target in ("PT1", "PT3") else None
            new_sec_polarity = (
                widget.get_sec_polarity()
                if repair_target in ("PT1", "PT3") and hasattr(widget, "get_sec_polarity")
                else None
            )
            outcome = api.apply_blackbox_repair_attempt(
                repair_target,
                step=step,
                initial_order=initial_order,
                new_order=new_order,
                initial_pri_order=initial_pri_order,
                new_pri_order=new_pri,
                initial_sec_order=initial_sec_order,
                new_sec_order=new_sec,
                initial_sec_polarity=initial_sec_polarity,
                new_sec_polarity=new_sec_polarity,
            )
            if not assessment_mode:
                fb_lbl.setText(outcome.message)
                set_props(fb_lbl, feedbackText=True, tone=tone_from_color(outcome.message_color))
                fb_lbl.setVisible(True)
            else:
                fb_lbl.setText("接线已保存，请关闭黑盒后返回外部测试流程复测。")
                set_props(fb_lbl, feedbackText=True, tone="info")
                fb_lbl.setVisible(True)
            if outcome.disable_repair_button and not assessment_mode:
                btn_repair.setEnabled(False)

        btn_repair = QtWidgets.QPushButton("保存接线" if assessment_mode else "确认修复 ✓")
        apply_button_tone(owner, btn_repair, "success")
        btn_repair.clicked.connect(_on_confirm)
        bh.addWidget(btn_repair, 1)

    btn_ok = QtWidgets.QPushButton("关闭")
    apply_button_tone(owner, btn_ok, "primary")
    btn_ok.clicked.connect(dlg.accept)
    bh.addWidget(btn_ok)
    vlay.addWidget(btn_row)
    dlg.exec_()
