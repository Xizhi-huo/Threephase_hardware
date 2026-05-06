from __future__ import annotations

from domain.test_states import LOOP_TEST_RECORD_KEYS
from ui.widgets._record_view import continuity_to_status, expand_phase_sequence_to_columns


class RecordTablesMixin:
    def _build_record_tables(self, ax) -> None:
        _blank6 = [
            ["PT1 AB", "---"],
            ["PT1 BC", "---"],
            ["PT1 CA", "---"],
            ["PT2 AB", "---"],
            ["PT2 BC", "---"],
            ["PT2 CA", "---"],
        ]
        _blank3 = [["AB", "---"], ["BC", "---"], ["CA", "---"]]
        _hdr = ["测量项", "二次侧(V)"]

        def _mk(blank, bbox, hdr=None, fontsize=6.5, row_labels=False):
            h = hdr if hdr is not None else _hdr
            nc = len(h)
            table = ax.table(cellText=[list(r) for r in blank], colLabels=h, bbox=bbox, cellLoc="center")
            table.auto_set_font_size(False)
            table.set_fontsize(fontsize)
            for c in range(nc):
                cell = table[(0, c)]
                cell.set_facecolor("#334155")
                cell.get_text().set_color("white")
                cell.get_text().set_fontweight("bold")
            for r in range(1, len(blank) + 1):
                for c in range(nc):
                    table[(r, c)].set_facecolor("#f1f5f9")
                    table[(r, c)].set_edgecolor("#cbd5e1")
                if row_labels:
                    cell = table[(r, 0)]
                    cell.set_facecolor("#334155")
                    cell.get_text().set_color("white")
                    cell.get_text().set_fontweight("bold")
            table.set_visible(False)
            return table

        _LX, _LW = 0.00, 0.30
        _RX, _RW = 0.67, 0.31
        _BY = 0.782
        _LC = _LX + _LW / 2
        _RC = _RX + _RW / 2

        self.tbl_left = _mk(_blank6, [_LX, _BY, _LW, 0.175])
        self.tbl_right = _mk(_blank3, [_RX, _BY, _RW, 0.115])
        self.tbl_left_title = ax.text(
            _LC,
            _BY + 0.175 + 0.022,
            "PT1 / PT2 电压记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_right_title = ax.text(
            _RC,
            _BY + 0.115 + 0.022,
            "PT3 电压记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_left_title.set_visible(False)
        self.tbl_right_title.set_visible(False)

        _h2 = ["测点", "状态"]
        _h3 = ["PT", "相序"]
        _h5 = ["轮次", "状态"]

        _b_s1 = [[pair, "---"] for pair in LOOP_TEST_RECORD_KEYS]
        _S1_H = 0.175
        self.tbl_s1 = _mk(_b_s1, [_LX, _BY, _LW, _S1_H], _h2)
        self.tbl_s1_title = ax.text(
            _LC,
            _BY + _S1_H + 0.022,
            "三相回路导通记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s1_title.set_visible(False)

        _b_s3 = [["---", "---"]]
        self.tbl_s3_left = _mk(_b_s3, [_LX, _BY, _LW, 0.070], _h3)
        self.tbl_s3_right = _mk(_b_s3, [_RX, _BY, _RW, 0.070], _h3)
        self.tbl_s3_left_title = ax.text(
            _LC,
            _BY + 0.070 + 0.022,
            "PT1 相序记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s3_right_title = ax.text(
            _RC,
            _BY + 0.070 + 0.022,
            "PT3 相序记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s3_left_title.set_visible(False)
        self.tbl_s3_right_title.set_visible(False)

        _h4_mat = ["机\\母排", "A", "B", "C"]
        _b_s4_mat = [["A", "---", "---", "---"], ["B", "---", "---", "---"], ["C", "---", "---", "---"]]
        _S4_LX, _S4_LW = -0.08, 0.38
        _S4_RX, _S4_RW = 0.67, 0.39
        _S4_H = 0.110
        _S4_LC = _S4_LX + _S4_LW / 2
        _S4_RC = _S4_RX + _S4_RW / 2
        self.tbl_s4_left = _mk(_b_s4_mat, [_S4_LX, _BY, _S4_LW, _S4_H], _h4_mat, fontsize=6.5, row_labels=True)
        self.tbl_s4_right = _mk([list(r) for r in _b_s4_mat], [_S4_RX, _BY, _S4_RW, _S4_H], _h4_mat, fontsize=6.5, row_labels=True)
        self.tbl_s4_left_title = ax.text(
            _S4_LC,
            _BY + _S4_H + 0.022,
            "Gen1 压差记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s4_right_title = ax.text(
            _S4_RC,
            _BY + _S4_H + 0.022,
            "Gen2 压差记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s4_left_title.set_visible(False)
        self.tbl_s4_right_title.set_visible(False)

        _b_s5_l = [["第一轮", "---"]]
        _b_s5_r = [["第二轮", "---"]]
        self.tbl_s5_left = _mk(_b_s5_l, [_LX, _BY, _LW, 0.070], _h5)
        self.tbl_s5_right = _mk(_b_s5_r, [_RX, _BY, _RW, 0.070], _h5)
        self.tbl_s5_left_title = ax.text(
            _LC,
            _BY + 0.070 + 0.022,
            "Gen1 同步记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s5_right_title = ax.text(
            _RC,
            _BY + 0.070 + 0.022,
            "Gen2 同步记录",
            fontsize=7,
            ha="center",
            weight="bold",
            color="#9a3412",
            clip_on=False,
        )
        self.tbl_s5_left_title.set_visible(False)
        self.tbl_s5_right_title.set_visible(False)

    def _render_pt_record_tables(self, p):
        step = 0
        if self._is_test_mode_active_cb():
            try:
                step = self._get_current_test_step_cb()
            except AttributeError:
                step = 1

        for obj in (self.tbl_s1, self.tbl_s1_title):
            obj.set_visible(step == 1)
        for obj in (self.tbl_left, self.tbl_right, self.tbl_left_title, self.tbl_right_title):
            obj.set_visible(step == 2)
        for obj in (self.tbl_s3_left, self.tbl_s3_right, self.tbl_s3_left_title, self.tbl_s3_right_title):
            obj.set_visible(step == 3)
        for obj in (self.tbl_s4_left, self.tbl_s4_right, self.tbl_s4_left_title, self.tbl_s4_right_title):
            obj.set_visible(step == 4)
        for obj in (self.tbl_s5_left, self.tbl_s5_right, self.tbl_s5_left_title, self.tbl_s5_right_title):
            obj.set_visible(step == 5)

        if step == 0:
            return

        if step == 1:
            records = getattr(self._api.loop_test_state, "records", {})
            for row_idx, pair in enumerate(LOOP_TEST_RECORD_KEYS, start=1):
                rec = records.get(pair)
                self.tbl_s1[(row_idx, 0)].get_text().set_text(pair)
                if rec is not None:
                    conductive = continuity_to_status(rec.get("continuity")) == "ok"
                    passed = bool(rec.get("passed", conductive))
                    val = "≈0Ω" if conductive else "∞Ω"
                    label = "导通" if conductive else "断路"
                    self.tbl_s1[(row_idx, 1)].get_text().set_text(f"{label}  {val}")
                    bg = "#dcfce7" if passed else "#fee2e2"
                else:
                    self.tbl_s1[(row_idx, 1)].get_text().set_text("---")
                    bg = "#f1f5f9"
                for c in range(2):
                    self.tbl_s1[(row_idx, c)].set_facecolor(bg)
        elif step == 2:
            state = self._api.pt_voltage_check_state
            records = state.records if state is not None else {}
            left_keys = [("PT1", "AB"), ("PT1", "BC"), ("PT1", "CA"), ("PT2", "AB"), ("PT2", "BC"), ("PT2", "CA")]
            for row_idx, (pt, pair) in enumerate(left_keys, start=1):
                rec = records.get(f"{pt}_{pair}")
                self.tbl_left[(row_idx, 0)].get_text().set_text(f"{pt} {pair}")
                if rec is not None:
                    v_sec = rec.get("voltage_sec", 0.0)
                    ok = rec.get("passed") is True
                    self.tbl_left[(row_idx, 1)].get_text().set_text(f"{v_sec:.1f}")
                    bg = "#dcfce7" if ok else "#fee2e2"
                else:
                    self.tbl_left[(row_idx, 1)].get_text().set_text("---")
                    bg = "#f1f5f9"
                for c in range(2):
                    self.tbl_left[(row_idx, c)].set_facecolor(bg)
            for row_idx, pair in enumerate(["AB", "BC", "CA"], start=1):
                rec = records.get(f"PT3_{pair}")
                self.tbl_right[(row_idx, 0)].get_text().set_text(pair)
                if rec is not None:
                    v_sec = rec.get("voltage_sec", 0.0)
                    ok = rec.get("passed") is True
                    self.tbl_right[(row_idx, 1)].get_text().set_text(f"{v_sec:.1f}")
                    bg = "#dcfce7" if ok else "#fee2e2"
                else:
                    self.tbl_right[(row_idx, 1)].get_text().set_text("---")
                    bg = "#f1f5f9"
                for c in range(2):
                    self.tbl_right[(row_idx, c)].set_facecolor(bg)
        elif step == 3:
            state = self._api.pt_phase_check_state
            records = state.records if state is not None else {}
            for tbl, pt_name in [(self.tbl_s3_left, "PT1"), (self.tbl_s3_right, "PT3")]:
                record = records.get(pt_name)
                expanded = expand_phase_sequence_to_columns(record)
                all_recs = [expanded.get(f"{pt_name}_{ph}") for ph in ("A", "B", "C")]
                tbl[(1, 0)].get_text().set_text(pt_name)
                if all(r is not None for r in all_recs):
                    ok = all(r.get("passed") is True for r in all_recs)
                    seq = self._api.get_pt_phase_sequence(pt_name)
                    if ok:
                        label, bg = "正序", "#dcfce7"
                    elif seq == "FAULT":
                        label, bg = "异常", "#fff3cd"
                    else:
                        label, bg = "反序", "#fee2e2"
                    tbl[(1, 1)].get_text().set_text(label)
                else:
                    tbl[(1, 1)].get_text().set_text("---")
                    bg = "#f1f5f9"
                for c in range(2):
                    tbl[(1, c)].set_facecolor(bg)
        elif step == 4:
            exam_states = self._api.pt_exam_states
            phases = ("A", "B", "C")
            for tbl, gid in [(self.tbl_s4_left, 1), (self.tbl_s4_right, 2)]:
                records = getattr(exam_states.get(gid), "records", {})
                for ri, gp in enumerate(phases, start=1):
                    for ci, bp in enumerate(phases, start=1):
                        rec = records.get(f"{gp}{bp}")
                        if rec is not None:
                            diff = rec.get("voltage_sec", 0.0)
                            tbl[(ri, ci)].get_text().set_text(f"{diff:.1f}")
                            tbl[(ri, ci)].set_facecolor("#e0f2fe")
                        else:
                            tbl[(ri, ci)].get_text().set_text("---")
                            tbl[(ri, ci)].set_facecolor("#f1f5f9")
        elif step == 5:
            state = self._api.sync_test_state
            r1 = getattr(state, "round1_done", False) if state else False
            r2 = getattr(state, "round2_done", False) if state else False
            for tbl, label, done in [
                (self.tbl_s5_left, "第一轮", r1),
                (self.tbl_s5_right, "第二轮", r2),
            ]:
                tbl[(1, 0)].get_text().set_text(label)
                tbl[(1, 1)].get_text().set_text("已记录" if done else "---")
                bg = "#dcfce7" if done else "#f1f5f9"
                for c in range(2):
                    tbl[(1, c)].set_facecolor(bg)
