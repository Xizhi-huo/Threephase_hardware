from PyQt5 import QtCore, QtWidgets

from domain.fault_scenarios import SCENARIOS
from ui.tabs._step_style import apply_button_tone, set_props


def show_random_fault_identification_dialog(owner, *, submit_guess):
    dlg = QtWidgets.QDialog(owner)
    dlg.setWindowTitle("随机故障判定")
    dlg.resize(520, 260)
    dlg.setModal(True)
    dlg.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.CustomizeWindowHint | QtCore.Qt.WindowTitleHint)
    set_props(dlg, themedDialog=True)
    lay = QtWidgets.QVBoxLayout(dlg)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    title_lbl = QtWidgets.QLabel("请先判断本轮随机故障，再生成第 4 步成绩单")
    set_props(title_lbl, dialogTitle=True)
    lay.addWidget(title_lbl)
    desc_lbl = QtWidgets.QLabel("随机故障考核不会提前公开场景。请根据前四步测量结果，选择你认为最符合当前现象的故障场景。")
    desc_lbl.setWordWrap(True)
    set_props(desc_lbl, dialogCaption=True)
    lay.addWidget(desc_lbl)
    combo = QtWidgets.QComboBox()
    combo.setMinimumHeight(36)
    combo.setStyleSheet(
        "QComboBox{font-size:16px; padding:6px 10px;}"
        "QAbstractItemView{font-size:16px; outline:none;}"
        "QAbstractItemView::item{min-height:30px;}"
    )
    combo.addItem("请选择故障场景", "")
    for scene_id, info in SCENARIOS.items():
        if not scene_id:
            continue
        title_text = info.get("title", scene_id)
        combo.addItem(str(title_text) if str(title_text).startswith(scene_id) else f"{scene_id} - {title_text}", scene_id)
    lay.addWidget(combo)
    hint_lbl = QtWidgets.QLabel("")
    hint_lbl.setWordWrap(True)
    set_props(hint_lbl, feedbackText=True, tone="warning")
    hint_lbl.setVisible(False)
    lay.addWidget(hint_lbl)
    lay.addStretch()
    btn_row = QtWidgets.QHBoxLayout()
    btn_row.addStretch()
    btn_ok = QtWidgets.QPushButton("提交判定并生成成绩单")
    apply_button_tone(owner, btn_ok, "primary")

    def _submit():
        guessed_scene_id = combo.currentData()
        if not guessed_scene_id:
            hint_lbl.setText("请先选择一个故障场景。")
            hint_lbl.setVisible(True)
            return
        submit_guess(guessed_scene_id)
        dlg.accept()

    btn_ok.clicked.connect(_submit)
    btn_row.addWidget(btn_ok)
    lay.addLayout(btn_row)
    dlg.exec_()
