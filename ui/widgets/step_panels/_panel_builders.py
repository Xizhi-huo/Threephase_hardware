from PyQt5 import QtCore, QtWidgets
from domain.enums import BreakerPosition
from ui.tabs._step_style import apply_badge_tone, apply_button_tone, set_props

_SECTION_BG = "#ffffff"
_GRP_STYLE = (
    "QGroupBox{{background:{bg}; color:#0f172a; font-size:13px; font-weight:bold;"
    " border:1px solid #dbe4f0; border-radius:12px; margin-top:12px; padding-top:14px;}}"
    "QGroupBox::title{{subcontrol-origin:margin; left:10px;"
    " background:{bg}; color:#1e293b; padding:0 6px;}}"
    "QGroupBox *{{font-size:12px; color:#334155; font-weight:normal;}}"
)
def make_group(title, bg=_SECTION_BG):
    grp = QtWidgets.QGroupBox(title)
    if bg != _SECTION_BG:
        grp.setStyleSheet(_GRP_STYLE.format(bg=bg))
    return grp


def make_button(owner, text, bg="#1d4ed8"):
    btn = QtWidgets.QPushButton(text)
    if bg == "#64748b":
        apply_button_tone(owner, btn, "primary", secondary=True)
        return btn
    apply_button_tone(owner, btn, {"#16a34a": "success", "#dc2626": "danger", "#7c3aed": "primary"}.get(bg, "warning" if bg in {"#d97706", "#92400e"} else "primary"))
    return btn
def tone_from_color(color):
    raw = str(color or "").lower()
    if raw in {"#15803d", "#16a34a", "green", "darkgreen"}:
        return "success"
    if raw in {"#dc2626", "#b91c1c", "#991b1b", "red", "darkred"}:
        return "danger"
    if raw in {"#1d4ed8", "#2563eb", "blue"}:
        return "info"
    if raw in {"#d97706", "#b45309", "#92400e", "orange", "yellow"}:
        return "warning"
    return "neutral"
def make_note_label(text, tone="neutral", *, italic=False):
    lbl = QtWidgets.QLabel(text)
    set_props(lbl, noteText=True, tone=tone)
    if italic:
        font = lbl.font(); font.setItalic(True); lbl.setFont(font)
    return lbl


def make_inline_row():
    row = QtWidgets.QWidget(); set_props(row, inlineRow=True); return row


def make_feedback_label(text):
    lbl = QtWidgets.QLabel(text); lbl.setWordWrap(True); set_props(lbl, feedbackText=True, tone="success"); return lbl


def set_feedback_label(label, text, color):
    label.setText(text); set_props(label, feedbackText=True, tone=tone_from_color(color))


def set_step_list_label(label, text, done, in_mode):
    label.setText(f"{'✓' if done else '□'} {text}"); set_props(label, stepListItem=True, tone="success" if done else ("active" if in_mode else "muted"))


def make_step_list(parent_lay, n_steps):
    grp = make_group("测试步骤"); lay = QtWidgets.QVBoxLayout(grp); lay.setSpacing(2); labels = []
    for _ in range(n_steps):
        lbl = QtWidgets.QLabel(""); lbl.setWordWrap(True); set_props(lbl, stepListItem=True); lay.addWidget(lbl); labels.append(lbl)
    parent_lay.addWidget(grp)
    return labels


def _set_gen_mode(api, gen_id, val, checked):
    if checked:
        (api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2).mode = val


def _set_breaker_position(api, gen_id, val, checked):
    if checked:
        (api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2).breaker_position = val


def _make_radio_row(owner, current_value, options, checked_fn):
    row = make_inline_row()
    hlay = QtWidgets.QHBoxLayout(row)
    hlay.setContentsMargins(0, 0, 0, 0)
    hlay.setSpacing(4)
    group = QtWidgets.QButtonGroup(owner)
    refs = {}
    for txt, val in options:
        rb = QtWidgets.QRadioButton(txt)
        set_props(rb, inlineRadio=True)
        rb.setChecked(current_value == val)
        rb.toggled.connect(checked_fn(val))
        group.addButton(rb)
        hlay.addWidget(rb)
        refs[val] = rb
    return row, refs


def make_gen_block(parent_lay, *, owner, api, gen_refs, step_key, gen_id, mode_options=None, show_pos=False, show_engine=True):
    gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
    inner = QtWidgets.QGroupBox(f"Gen {gen_id}")
    ilay = QtWidgets.QVBoxLayout(inner)
    ilay.setSpacing(2)
    ilay.setContentsMargins(4, 4, 4, 4)
    brk_lbl = QtWidgets.QLabel("--")
    apply_badge_tone(brk_lbl, "neutral")
    brk_lbl.setAlignment(QtCore.Qt.AlignCenter)
    ilay.addWidget(brk_lbl)
    mode_rbs = {}
    if mode_options:
        ilay.addWidget(make_note_label("PCC 模式:"))
        row, mode_rbs = _make_radio_row(owner, gen.mode, mode_options, lambda val: (lambda chk, gid=gen_id, v=val: _set_gen_mode(api, gid, v, chk)))
        ilay.addWidget(row)
    if show_pos:
        ilay.addWidget(make_note_label("开关柜位置:"))
        row, pos_rbs = _make_radio_row(
            owner,
            gen.breaker_position,
            [("脱开", BreakerPosition.DISCONNECTED), ("工作", BreakerPosition.WORKING)],
            lambda val: (lambda chk, gid=gen_id, v=val: _set_breaker_position(api, gid, v, chk)),
        )
        ilay.addWidget(row)
    else:
        pos_rbs = {}
    btn_row = QtWidgets.QWidget()
    br = QtWidgets.QHBoxLayout(btn_row)
    br.setContentsMargins(0, 0, 0, 0)
    br.setSpacing(4)
    eng_btn = None
    if show_engine:
        eng_btn = make_button(owner, "起机", "#16a34a")
        eng_btn.clicked.connect(lambda _, gid=gen_id: api.toggle_engine(gid))
        br.addWidget(eng_btn)
    brk_btn = make_button(owner, "合闸", "#1d4ed8")
    brk_btn.clicked.connect(lambda _, gid=gen_id: api.toggle_breaker(gid))
    br.addWidget(brk_btn)
    ilay.addWidget(btn_row)
    parent_lay.addWidget(inner)
    gen_refs[(step_key, gen_id)] = (brk_lbl, eng_btn, brk_btn, mode_rbs, pos_rbs)


def make_gen_fap_block(parent_lay, *, api, gen_id, read_only=False):
    gen = api.sim_state.gen1 if gen_id == 1 else api.sim_state.gen2
    grp = QtWidgets.QGroupBox(f"Gen {gen_id} 频率/幅值/相位")
    glay = QtWidgets.QVBoxLayout(grp)
    glay.setSpacing(2)
    glay.setContentsMargins(4, 4, 4, 4)
    entry_map = {}
    for label, vmin, vmax, init, scale, attr, clo, chi in [
        ("频率(Hz)", 450, 550, int(gen.freq * 10), 10, "freq", 48.0, 52.0),
        ("幅值(V)", 0, 15000, int(gen.amp), 1, "amp", 0.0, 15000.0),
        ("相位(°)", -1800, 1800, int(gen.phase_deg * 10), 10, "phase_deg", -180.0, 180.0),
    ]:
        row_w = make_inline_row()
        rh = QtWidgets.QHBoxLayout(row_w)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(3)
        lbl = QtWidgets.QLabel(label)
        lbl.setFixedWidth(66)
        set_props(lbl, noteText=True)
        sl = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        sl.setRange(vmin, vmax)
        sl.setValue(init)
        sl.setFixedHeight(16)
        sl.setEnabled(not read_only)
        entry = QtWidgets.QLineEdit(f"{getattr(gen, attr):.1f}")
        entry.setFixedWidth(56)
        entry.setEnabled(not read_only)
        entry.setReadOnly(read_only)
        set_props(entry, compactInput=True, readonlyTone=read_only)

        def _sl_ch(val, _a=attr, _sc=scale, _e=entry, _gid=gen_id):
            v = round(val / _sc, 3)
            setattr(api.sim_state.gen1 if _gid == 1 else api.sim_state.gen2, _a, v)
            _e.setText(f"{v:.1f}")

        def _en_ch(_a=attr, _sc=scale, _sl=sl, _gid=gen_id, _clo=clo, _chi=chi, _e=entry):
            try:
                v = max(_clo, min(_chi, float(_e.text())))
            except ValueError:
                return
            setattr(api.sim_state.gen1 if _gid == 1 else api.sim_state.gen2, _a, v)
            _sl.blockSignals(True); _sl.setValue(int(v * _sc)); _sl.blockSignals(False); _e.setText(f"{v:.1f}")

        if not read_only:
            sl.valueChanged.connect(_sl_ch)
            entry.returnPressed.connect(_en_ch)
            entry.editingFinished.connect(_en_ch)
        rh.addWidget(lbl); rh.addWidget(sl, 1); rh.addWidget(entry)
        glay.addWidget(row_w)
        entry_map[attr] = (sl, entry)
    parent_lay.addWidget(grp)
    return entry_map


def add_blackbox_section(lay, *, owner, api, show_blackbox_dialog):
    lay.addWidget(make_note_label("物理接线检查 / 手动修复 (开盖查线):"))
    allow_blackbox = api.can_inspect_blackbox()
    for entries in (
        (("G1 机端接线", "G1", "#92400e"), ("G2 机端接线", "G2", "#92400e")),
        (("PT1 接线盒", "PT1", "#1e40af"), ("PT2 接线盒", "PT2", "#0f766e")),
        (("PT3 接线盒", "PT3", "#1e40af"),),
    ):
        row = make_inline_row()
        hlay = QtWidgets.QHBoxLayout(row)
        hlay.setContentsMargins(0, 0, 0, 0)
        hlay.setSpacing(4)
        for text, target, bg in entries:
            btn = make_button(owner, text, bg)
            btn.setEnabled(allow_blackbox)
            btn.clicked.connect(lambda _, t=target: show_blackbox_dialog(t))
            hlay.addWidget(btn)
        lay.addWidget(row)


def add_load_share_cabinet_section(lay, *, owner, show_load_share_cabinet_dialog):
    lay.addWidget(make_note_label("控制柜负载分配接线检查:"))
    row = make_inline_row()
    hlay = QtWidgets.QHBoxLayout(row)
    hlay.setContentsMargins(0, 0, 0, 0)
    hlay.setSpacing(4)

    btn = make_button(owner, "打开控制柜", "#7c3aed")
    btn.clicked.connect(show_load_share_cabinet_dialog)
    hlay.addWidget(btn)
    hlay.addStretch()

    lay.addWidget(row)


def build_test_panel_title_bar(owner, *, on_reset, on_toggle_admin, on_exit):
    top = QtWidgets.QWidget()
    set_props(top, testPanelBar=True)
    top.setFixedHeight(44)
    row = QtWidgets.QHBoxLayout(top)
    row.setContentsMargins(8, 4, 8, 4)
    title = QtWidgets.QLabel("🔬 合闸前测试模式")
    set_props(title, testPanelTitle=True)
    btn_reset = QtWidgets.QPushButton("⚠️ 重置本步")
    btn_reset.clicked.connect(on_reset)
    apply_button_tone(owner, btn_reset, "danger")
    btn_admin = QtWidgets.QPushButton("🔧 管理员")
    btn_admin.setCheckable(True)
    set_props(btn_admin, adminButton=True)
    btn_admin.clicked.connect(on_toggle_admin)
    btn_exit = QtWidgets.QPushButton("退出测试")
    btn_exit.clicked.connect(on_exit)
    apply_button_tone(owner, btn_exit, "primary", secondary=True)
    row.addWidget(title, 1); row.addWidget(btn_admin); row.addWidget(btn_reset); row.addWidget(btn_exit)
    return top, btn_reset, btn_admin


def build_test_panel_step_dots(owner, *, on_step_clicked):
    step_bar = QtWidgets.QWidget()
    set_props(step_bar, testPanelBar=True)
    step_bar.setFixedHeight(52)
    row = QtWidgets.QHBoxLayout(step_bar)
    row.setContentsMargins(8, 6, 8, 6)
    buttons = []
    for step_num, name in enumerate(["①回路", "②线压", "③相序", "④压差", "⑤同步"], start=1):
        btn = QtWidgets.QPushButton(f"●\n{name}")
        btn.setFlat(True); btn.setCheckable(True); btn.setCursor(QtCore.Qt.ArrowCursor); btn.setStyleSheet(tp_dot_style("idle"))
        btn.clicked.connect(lambda _chk, s=step_num: on_step_clicked(s))
        row.addWidget(btn, 1)
        buttons.append(btn)
    return step_bar, buttons


def build_test_panel_scroll_skeleton():
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    content = QtWidgets.QWidget()
    set_props(content, testPanelRoot=True)
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(6)
    return scroll, content, layout


def build_test_panel_status_area(owner, content_layout, *, on_toggle_multimeter):
    fault_banner = QtWidgets.QLabel("")
    set_props(fault_banner, stepBanner=True, tone="danger")
    fault_banner.setAlignment(QtCore.Qt.AlignCenter); fault_banner.setWordWrap(True); fault_banner.setMinimumHeight(40); fault_banner.setVisible(False)
    bus_lbl = QtWidgets.QLabel("母排: --")
    bus_lbl.setAlignment(QtCore.Qt.AlignCenter)
    apply_badge_tone(bus_lbl, "warning")
    mm_btn = QtWidgets.QPushButton("🔌 开启 / 关闭万用表")
    mm_btn.clicked.connect(on_toggle_multimeter)
    apply_button_tone(owner, mm_btn, "warning")
    meter_lbl = QtWidgets.QLabel("万用表: 关闭")
    set_props(meter_lbl, stepStatus=True, mutedText=True)
    meter_lbl.setWordWrap(True); meter_lbl.setMaximumWidth(320); meter_lbl.setMinimumHeight(36)
    for widget in (fault_banner, bus_lbl, mm_btn, meter_lbl):
        content_layout.addWidget(widget)
    return {"fault_banner": fault_banner, "bus_lbl": bus_lbl, "mm_btn": mm_btn, "meter_lbl": meter_lbl}


def build_test_panel_bottom_bar(owner, *, on_start, on_complete):
    bottom = QtWidgets.QWidget()
    set_props(bottom, testPanelBar=True, barRole="footer")
    row = QtWidgets.QHBoxLayout(bottom)
    row.setContentsMargins(8, 6, 8, 6); row.setSpacing(6)
    btn_start = QtWidgets.QPushButton("开始测试"); btn_start.clicked.connect(on_start); apply_button_tone(owner, btn_start, "warning", hero=True)
    btn_complete = QtWidgets.QPushButton("完成本步 ✓"); btn_complete.clicked.connect(on_complete); apply_button_tone(owner, btn_complete, "success", hero=True)
    row.addWidget(btn_start, 1); row.addWidget(btn_complete, 1)
    return bottom, btn_start, btn_complete


def tp_dot_style(state):
    base = "border:none; border-radius:4px; font-size:11px; padding:2px;"
    if state == "done":
        return f"QPushButton{{{base} color:#16a34a; background:#dcfce7;}}"
    if state == "active":
        return f"QPushButton{{{base} color:#1d4ed8; background:#dbeafe; font-weight:bold; font-size:12px;}}"
    if state == "admin_idle":
        return f"QPushButton{{{base} color:#7c3aed; background:#ede9fe;}}" "QPushButton:hover{background:#c4b5fd;}" "QPushButton:checked{background:#7c3aed; color:white;}"
    if state == "admin_active":
        return f"QPushButton{{{base} color:white; background:#7c3aed; font-weight:bold;}}" "QPushButton:hover{background:#6d28d9;}"
    return f"QPushButton{{{base} color:#94a3b8; background:transparent;}}"


def refresh_tp_gen_refs(owner, gen_refs, sim, step):
    for (step_key, gen_id), (brk_lbl, eng_btn, brk_btn, mode_rbs, pos_rbs) in gen_refs.items():
        gen = sim.gen1 if gen_id == 1 else sim.gen2
        pos = {0: "脱开", 1: "试验", 2: "工作"}.get(getattr(gen, "breaker_position", None), str(gen.breaker_position))
        brk_lbl.setText(f"{'运行' if gen.running else '停机'} | {pos} | {'合闸' if gen.breaker_closed else '断路'}")
        apply_badge_tone(brk_lbl, "success" if gen.breaker_closed else "danger")
        if eng_btn is not None:
            allow_engine_toggle = gen.running or gen.mode == "manual"
            eng_btn.setEnabled(allow_engine_toggle)
            eng_btn.setText("停机" if gen.running else "起机")
            apply_button_tone(owner, eng_btn, "warning" if gen.running else "success" if allow_engine_toggle else "primary", muted=not allow_engine_toggle)
        brk_btn.setText("分闸" if gen.breaker_closed else ("合闸（测试）" if step_key == "s1" and step == 1 else "合闸"))
        apply_button_tone(owner, brk_btn, "danger" if gen.breaker_closed else "primary")
        for val, rb in mode_rbs.items():
            rb.blockSignals(True); rb.setChecked(gen.mode == val); rb.blockSignals(False)
        for val, rb in pos_rbs.items():
            rb.blockSignals(True); rb.setChecked(gen.breaker_position == val); rb.blockSignals(False)


def refresh_tp_bottom(owner, api, btn_start, btn_complete, step, sim):
    name = {1: "回路检查", 2: "线电压检查", 3: "相序检查", 4: "压差测试", 5: "同步测试"}.get(step, f"第{step}步")
    started = {1: sim.loop_test_mode, 2: api.pt_voltage_check_state.started, 3: api.pt_phase_check_state.started, 4: api.pt_exam_states[1].started and api.pt_exam_states[2].started, 5: api.sync_test_state.started}[step]
    btn_start.setText(f"{'退出' if started else '开始'}{name}")
    apply_button_tone(owner, btn_start, "danger" if started else "warning", hero=True)


def _toggle_step(api, started, start_fn, stop_fn):
    getattr(api, stop_fn if started else start_fn)()


def _toggle_pt_exam(api, **_):
    for gen_id in (1, 2):
        getattr(api, "stop_pt_exam" if api.pt_exam_states[1].started and api.pt_exam_states[2].started else "start_pt_exam")(gen_id)


STEP_ACTION_TABLE = {
    "reset": {1: lambda api, **_: api.reset_loop_test(), 2: lambda api, **_: api.reset_pt_voltage_check(), 3: lambda api, **_: api.reset_pt_phase_check(), 4: lambda api, gen_id=1, **_: api.reset_pt_exam(gen_id), 5: lambda api, **_: api.reset_sync_test()},
    "start": {1: lambda api, **_: _toggle_step(api, api.sim_state.loop_test_mode, "enter_loop_test_mode", "exit_loop_test_mode"), 2: lambda api, **_: _toggle_step(api, api.pt_voltage_check_state.started, "start_pt_voltage_check", "stop_pt_voltage_check"), 3: lambda api, **_: _toggle_step(api, api.pt_phase_check_state.started, "start_pt_phase_check", "stop_pt_phase_check"), 4: _toggle_pt_exam, 5: lambda api, **_: _toggle_step(api, api.sync_test_state.started, "start_sync_test", "stop_sync_test")},
    "complete": {1: lambda api, **_: api.finalize_loop_test(), 2: lambda api, **_: api.finalize_pt_voltage_check(), 3: lambda api, **_: api.finalize_pt_phase_check(), 4: lambda api, **_: api.finalize_all_pt_exams(), 5: lambda api, **_: api.finalize_sync_test()},
}


def dispatch_step_action(api, step, action, **kwargs):
    handler = STEP_ACTION_TABLE.get(action, {}).get(step)
    if handler is not None:
        handler(api, **kwargs)
