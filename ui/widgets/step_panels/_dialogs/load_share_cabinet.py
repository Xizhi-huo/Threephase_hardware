from PyQt5 import QtCore, QtWidgets

from ui.tabs._step_style import apply_button_tone, set_props
from ui.widgets.load_share_cabinet_widget import (
    LoadShareCabinetState,
    _LoadShareCabinetWidget,
)


def show_load_share_cabinet_dialog(owner, state: LoadShareCabinetState) -> None:
    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("负载分配接线检查")
    dlg.setModal(True)
    dlg.resize(760, 660)
    set_props(dlg, themedDialog=True)

    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(8)

    title = QtWidgets.QLabel("控制柜负载分配接线")
    set_props(title, dialogCaption=True)
    lay.addWidget(title)

    hint = QtWidgets.QLabel(
        "正常情况下，Gen1 与 Gen2 控制柜接入的端子编号应完全一致。\n"
        "白色圆圈表示未接入，黑色圆点表示已接入。"
    )
    hint.setWordWrap(True)
    set_props(hint, feedbackText=True, tone="info")
    lay.addWidget(hint)

    body = QtWidgets.QWidget()
    body_lay = QtWidgets.QHBoxLayout(body)
    body_lay.setContentsMargins(0, 0, 0, 0)
    body_lay.setSpacing(12)

    gen1_widget = _LoadShareCabinetWidget("Gen1 控制柜", state.gen1_points)
    gen2_widget = _LoadShareCabinetWidget("Gen2 控制柜", state.gen2_points)
    body_lay.addWidget(gen1_widget, 1)
    body_lay.addWidget(gen2_widget, 1)
    lay.addWidget(body, 1)

    gen1_lbl = QtWidgets.QLabel("")
    gen2_lbl = QtWidgets.QLabel("")
    result_lbl = QtWidgets.QLabel("")
    for lbl in (gen1_lbl, gen2_lbl, result_lbl):
        lbl.setWordWrap(True)
        set_props(lbl, feedbackText=True, tone="neutral")
        lay.addWidget(lbl)

    def _fmt(points: set[int]) -> str:
        return "、".join(str(x) for x in sorted(points)) if points else "未接线"

    def _refresh() -> None:
        gen1_lbl.setText(f"Gen1 已接端子: {_fmt(state.gen1_points)}")
        gen2_lbl.setText(f"Gen2 已接端子: {_fmt(state.gen2_points)}")

        if state.is_consistent():
            result_lbl.setText("当前状态: 两侧控制柜接线一致")
            set_props(result_lbl, feedbackText=True, tone="success")
        else:
            only_1 = sorted(state.gen1_points - state.gen2_points)
            only_2 = sorted(state.gen2_points - state.gen1_points)
            result_lbl.setText(
                "当前状态: 两侧控制柜接线不一致\n"
                f"仅 Gen1 接入: {only_1 or '无'}\n"
                f"仅 Gen2 接入: {only_2 or '无'}"
            )
            set_props(result_lbl, feedbackText=True, tone="warning")

    def _on_reset() -> None:
        state.reset_defaults()
        gen1_widget.update()
        gen2_widget.update()
        _refresh()

    gen1_widget.pointsChanged.connect(_refresh)
    gen2_widget.pointsChanged.connect(_refresh)
    _refresh()

    btn_row = QtWidgets.QWidget()
    btn_lay = QtWidgets.QHBoxLayout(btn_row)
    btn_lay.setContentsMargins(0, 0, 0, 0)
    btn_lay.setSpacing(6)

    btn_reset = QtWidgets.QPushButton("重置默认")
    apply_button_tone(owner, btn_reset, "warning")
    btn_reset.clicked.connect(_on_reset)

    btn_close = QtWidgets.QPushButton("关闭")
    apply_button_tone(owner, btn_close, "primary")
    btn_close.clicked.connect(dlg.accept)

    btn_lay.addWidget(btn_reset)
    btn_lay.addStretch()
    btn_lay.addWidget(btn_close)
    lay.addWidget(btn_row)

    dlg.exec_()
