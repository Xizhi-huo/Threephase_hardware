from __future__ import annotations

import matplotlib.patheffects as pe
import numpy as np

from domain.constants import CT_RATIO
from domain.node_map import NODES
from matplotlib.patches import Circle, FancyBboxPatch
from ui.tabs._step_style import normalize_qt_color


_LOOP_CB_BOT = 0.24
_LOOP_CB_TOP = 0.31
_LOOP_PROBE_Y = 0.405
_LOOP_BUS_Y = {"A": 0.115, "B": 0.090, "C": 0.065}


class DrawTopologyMixin:
    def _draw_circuit_content(self):
        ax = self.ax_circuit
        ax.cla()

        pt_orders = self._api.pt_phase_orders

        ax.axis("off")
        ax.set_xlim(0.0, 1.0)
        ax.set_ylim(-0.10, 1.02)
        ax.set_title("Switchgear Bus Topology", pad=8, weight="bold", fontsize=12)

        bus_y = {"A": 0.115, "B": 0.090, "C": 0.065, "N": 0.040}
        bus_yl = [bus_y["A"], bus_y["B"], bus_y["C"]]
        bus_phases = ["A", "B", "C"]
        bus_colors = ["#b45309", "#1a9c3c", "#d62828"]
        neutral_color = "#111111"

        g1_cx, g2_cx = 0.28, 0.72
        phase_dx = 0.04
        g1_x = [g1_cx - phase_dx, g1_cx, g1_cx + phase_dx]
        g2_x = [g2_cx - phase_dx, g2_cx, g2_cx + phase_dx]

        cb_bot, cb_top = 0.24, 0.31
        cb_lbl_y = 0.195
        gen_cy, gen_r = 0.52, 0.065

        gnd_bot_y = gen_cy + gen_r
        gnd_merge_y = gnd_bot_y + 0.05
        gnd_res_y1 = gnd_merge_y + 0.025
        gnd_res_y2 = gnd_res_y1 + 0.075
        gnd_earth_y = gnd_res_y2 + 0.015

        pt_size = 0.030
        pt2_cx = 0.50
        pt2_cy = 0.205
        pt1_cx = 0.10
        pt3_cx = 0.90
        pt_gen_cy = 0.355

        ct_x_left = 0.23
        ct_x_right = 0.78
        ct_y_top = 0.752
        ct_dy = 0.055

        def draw_pt_y_symbol(cx, cy, size, color="#9a3412", yn_side="right"):
            arm_a = (cx - size * 0.90, cy + size * 0.85)
            arm_b = (cx, cy + size)
            arm_c = (cx + size * 0.90, cy + size * 0.85)
            neutral = (cx, cy - size)
            for tip in (arm_a, arm_b, arm_c):
                ax.plot([cx, tip[0]], [cy, tip[1]], color=color, lw=2.0)
            ax.plot([cx, neutral[0]], [cy, neutral[1]], color=color, lw=1.6, ls="--")
            ax.plot(*neutral, "o", color=color, markersize=3)
            yn_x = neutral[0] + (0.012 if yn_side == "right" else -0.012)
            yn_ha = "left" if yn_side == "right" else "right"
            ax.text(yn_x, neutral[1], "Yn", fontsize=6, color="#888", va="center", ha=yn_ha)
            return {"A": arm_a, "B": arm_b, "C": arm_c, "N": neutral, "C_xy": (cx, cy)}

        def draw_pt_wired(src_x, src_y, arm_tip, color, ls="-"):
            tx, ty = arm_tip
            ax.plot([src_x, tx], [src_y, src_y], color=color, lw=1.2, alpha=0.85, ls=ls)
            ax.plot([tx, tx], [src_y, ty], color=color, lw=1.2, alpha=0.85, ls=ls)
            ax.plot(src_x, src_y, "o", color="k", markersize=3)

        def draw_pt_full(cx, cy, src_xs, src_ys, label, phase_order, ls="-", side="right"):
            sym = draw_pt_y_symbol(cx, cy, pt_size, yn_side=side if side in ("left", "right") else "right")
            terminals = [sym["A"], sym["B"], sym["C"]]
            for sx, sy, ph, color in zip(src_xs, src_ys, bus_phases, bus_colors):
                draw_pt_wired(sx, sy, terminals[phase_order.index(ph)], color, ls=ls)
            offset = pt_size * 1.5
            if side == "right":
                lbl_x, lbl_ha = cx + offset, "left"
            elif side == "left":
                lbl_x, lbl_ha = cx - offset, "right"
            else:
                lbl_x, lbl_ha = cx, "center"
            ax.text(lbl_x, cy + pt_size * 0.4, label, fontsize=7, ha=lbl_ha, color="#9a3412", weight="bold")
            ax.text(lbl_x, cy - pt_size * 0.4, "PT本体", fontsize=6, ha=lbl_ha, color="#555")
            ax.text(lbl_x, cy - pt_size * 1.1, "一次侧", fontsize=6, ha=lbl_ha, color="#666")
            return sym

        def draw_pt_secondary_terminal_strip(cx, cy, prefix, section_y, line_y, color="#9a3412"):
            node_keys = [f"{prefix}_{ph}" for ph in ("A", "B", "C")]
            xs = [NODES[key][0] for key in node_keys]
            y = NODES[node_keys[0]][1]
            box_left = min(xs) - 0.020
            box_bottom = y - 0.018
            box_w = (max(xs) - min(xs)) + 0.040
            box_h = 0.040
            ax.add_patch(
                FancyBboxPatch(
                    (box_left, box_bottom),
                    box_w,
                    box_h,
                    boxstyle="round,pad=0.004,rounding_size=0.006",
                    facecolor="#fffdf5",
                    edgecolor=color,
                    lw=1.2,
                    linestyle="--",
                    alpha=0.95,
                )
            )
            ax.plot([box_left, box_left + box_w], [line_y, line_y], color="#888", lw=1.0, ls=":")
            ax.text(cx, line_y + 0.045, "二次端子排", fontsize=6, ha="center", color=color, weight="bold")
            source_y = cy + pt_size * 0.75
            for phase, x in zip(("A", "B", "C"), xs):
                ax.plot([cx, x], [source_y, section_y], color=color, lw=1.0, alpha=0.9)
                ax.plot([x, x], [section_y, y], color=color, lw=1.0, alpha=0.9)
                ax.plot(x, y, "o", color="k", markersize=4, zorder=6)
                ax.text(x, y - 0.017, phase, fontsize=6, ha="center", color=color)

        def draw_gen_cabinet(gx_list, ls):
            artists = []
            for ph_idx, (x, color) in enumerate(zip(gx_list, bus_colors)):
                bus_y_ph = bus_yl[ph_idx]
                line1, = ax.plot([x, x], [bus_y_ph, cb_bot], color=color, lw=2, ls=ls)
                dot1, = ax.plot([x], [bus_y_ph], "o", color="k", markersize=5)
                dot2, = ax.plot([x], [cb_bot], "o", color="k", markersize=4)
                dot3, = ax.plot([x], [cb_top], "o", color="k", markersize=4)
                line2, = ax.plot([x, x], [cb_top, gen_cy - gen_r], color=color, lw=2, ls=ls)
                artists.extend([line1, dot1, dot2, dot3, line2])
            return artists

        def draw_generator_neutral_ground(cx):
            fan_xs = [cx - 0.030, cx, cx + 0.030]
            fan_y = gnd_bot_y + 0.06
            stub_gap_y = gnd_bot_y + 0.03
            lower_stubs = []
            upper_stubs = []
            for fx in fan_xs:
                line, = ax.plot([fx, fx], [gnd_bot_y, stub_gap_y], color="k", lw=1.4)
                lower_stubs.append(line)
                line, = ax.plot([fx, fx], [stub_gap_y, fan_y], color="k", lw=1.4)
                upper_stubs.append(line)
            conn_lines = []
            line, = ax.plot([fan_xs[0], fan_xs[-1]], [fan_y, fan_y], color="k", lw=1.4)
            conn_lines.append(line)
            dot, = ax.plot([cx], [fan_y], "ko", markersize=4)
            conn_lines.append(dot)
            line, = ax.plot([cx, cx], [fan_y, gnd_res_y1], "k-", lw=1.4)
            conn_lines.append(line)
            bypass_ln, = ax.plot([cx, cx], [fan_y, gnd_earth_y], "k-", lw=1.4, visible=False)
            ry = np.linspace(gnd_res_y1, gnd_res_y2, 13)
            rx = [cx + (0.012 if i % 2 == 1 else -0.012) for i in range(len(ry))]
            rx[0] = rx[-1] = cx
            res_zigzag, = ax.plot(rx, ry, "k-", lw=1.4)
            rn_text = ax.text(cx + 0.030, (gnd_res_y1 + gnd_res_y2) / 2, "Rn", fontsize=7, color="#555", va="center")
            post_res_ln, = ax.plot([cx, cx], [gnd_res_y2, gnd_earth_y], "k-", lw=1.4)
            for i, half in enumerate([0.022, 0.015, 0.008]):
                ey = gnd_earth_y + i * 0.013
                ax.plot([cx - half, cx + half], [ey, ey], "k-", lw=2.0 - i * 0.4)
            return {
                "lower_stubs": lower_stubs,
                "upper_stubs": upper_stubs,
                "conn": conn_lines,
                "bypass": bypass_ln,
                "resistor": [res_zigzag, rn_text, post_res_ln],
            }

        bus_x_l, bus_x_r = 0.02, 0.98
        stroke = [pe.withStroke(linewidth=2.5, foreground="black")]
        for ph, color in zip(bus_phases, bus_colors):
            y = bus_y[ph]
            ax.plot([bus_x_l, bus_x_r], [y, y], color=color, lw=5, solid_capstyle="round")
            for xpos in (bus_x_l - 0.018, bus_x_r + 0.018):
                ax.text(xpos, y, ph, fontsize=13, ha="center", va="center", weight="bold", color=color, path_effects=stroke)
        neutral_y = bus_y["N"]
        ax.plot([bus_x_l, bus_x_r], [neutral_y, neutral_y], color=neutral_color, lw=4, solid_capstyle="round")
        for xpos in (bus_x_l - 0.018, bus_x_r + 0.018):
            ax.text(xpos, neutral_y, "N", fontsize=12, ha="center", va="center", weight="bold", color=neutral_color, path_effects=stroke)
        self.txt_bus_source = ax.text(
            0.50,
            0,
            "Dead Bus (无电)",
            weight="bold",
            ha="center",
            fontsize=10,
            color="#1e293b",
            bbox=dict(facecolor="#f8fafc", edgecolor="#cbd5e1", boxstyle="round,pad=0.3", alpha=0.92),
        )

        self._g1_wire_artists = draw_gen_cabinet(g1_x, "--")
        self._g2_wire_artists = draw_gen_cabinet(g2_x, "-.")
        self.sw1_pack = [ax.plot([], [], "k-", lw=4)[0] for _ in range(3)]
        self.sw2_pack = [ax.plot([], [], "k-", lw=4)[0] for _ in range(3)]

        for cx, label in ((g1_cx, "Gen1 CB"), (g2_cx, "Gen2 CB")):
            ax.text(cx, cb_lbl_y, label, fontsize=8, ha="center", color="#222", weight="bold")

        gen_stroke = [pe.withStroke(linewidth=3, foreground="white")]
        side_stroke = [pe.withStroke(linewidth=2, foreground="white")]
        self._gen_ring_artists = {}
        self._gen_label_artists = {}

        for gen_id, cx, label in ((1, g1_cx, "G1"), (2, g2_cx, "G2")):
            ring = Circle((cx, gen_cy), gen_r, fill=False, ec="#111", lw=2.5)
            ax.add_patch(ring)
            txt = ax.text(cx, gen_cy, label, fontsize=13, ha="center", va="center", weight="bold", color="#111", path_effects=gen_stroke)
            self._gen_ring_artists[gen_id] = ring
            self._gen_label_artists[gen_id] = txt

        for cx, side, ha in ((g1_cx, -1, "right"), (g2_cx, 1, "left")):
            xpos = cx + side * (gen_r + 0.025)
            ax.text(xpos, gen_cy, "机端", fontsize=9, ha=ha, va="center", weight="bold", color="#444", path_effects=side_stroke)

        for node_name in ("LOOP_G1_A", "LOOP_G1_B", "LOOP_G1_C", "LOOP_G2_A", "LOOP_G2_B", "LOOP_G2_C"):
            x, y, _, phase, _ = NODES[node_name]
            phase_color = {"A": "#b45309", "B": "#1a9c3c", "C": "#d62828"}[phase]
            ax.plot(x, y, "o", color="k", markersize=4.5, zorder=6)
            ax.text(x, y + 0.018, phase, fontsize=6, ha="center", color=phase_color, weight="bold")
        ax.text(0.50, 0.438, "三相回路连通测点", fontsize=7, ha="center", color="#444")

        self.loop_anim_wire_ok, = ax.plot([], [], "-", lw=2.5, alpha=0.55, zorder=9)
        self.loop_anim_dots, = ax.plot([], [], "o", markersize=7, alpha=0.90, zorder=12)
        self.loop_anim_gap_l, = ax.plot([], [], "-", lw=2.0, color="#94a3b8", zorder=9)
        self.loop_anim_gap_r, = ax.plot([], [], "-", lw=2.0, color="#94a3b8", zorder=9)
        self.loop_anim_x1, = ax.plot([], [], "-", lw=2.5, color="#ef4444", zorder=12)
        self.loop_anim_x2, = ax.plot([], [], "-", lw=2.5, color="#ef4444", zorder=12)

        self.gnd_data1 = draw_generator_neutral_ground(g1_cx)
        self.gnd_data2 = draw_generator_neutral_ground(g2_cx)

        pt_gen_channels = {"A": cb_bot - 0.015, "B": cb_bot - 0.030, "C": cb_bot - 0.045}
        draw_pt_full(
            cx=pt1_cx,
            cy=pt_gen_cy,
            src_xs=g1_x,
            src_ys=[pt_gen_channels["A"], pt_gen_channels["B"], pt_gen_channels["C"]],
            label="PT1",
            phase_order=pt_orders["PT1"],
            ls="--",
            side="right",
        )
        draw_pt_secondary_terminal_strip(pt1_cx, pt_gen_cy, "PT1", section_y=0.512, line_y=0.500)

        sym2 = draw_pt_y_symbol(pt2_cx, pt2_cy, pt_size, yn_side="right")
        arms2 = [sym2["A"], sym2["B"], sym2["C"]]
        for ph, bus_y_val, color in zip(bus_phases, bus_yl, bus_colors):
            arm_tx, arm_ty = arms2[pt_orders["PT2"].index(ph)]
            ax.plot(arm_tx, bus_y_val, "o", color="k", markersize=3)
            ax.plot([arm_tx, arm_tx], [bus_y_val, arm_ty], color=color, lw=1.2, alpha=0.85)
        pt2_lbl_x = pt2_cx + pt_size * 2.8
        ax.text(pt2_lbl_x, pt2_cy + pt_size * 0.4, "PT2", fontsize=7, ha="left", color="#9a3412", weight="bold")
        ax.text(pt2_lbl_x, pt2_cy - pt_size * 0.4, "母排", fontsize=6, ha="left", color="#666")
        draw_pt_secondary_terminal_strip(pt2_cx, pt2_cy, "PT2", section_y=0.372, line_y=0.360)

        draw_pt_full(
            cx=pt3_cx,
            cy=pt_gen_cy,
            src_xs=g2_x,
            src_ys=[pt_gen_channels["A"], pt_gen_channels["B"], pt_gen_channels["C"]],
            label="PT3",
            phase_order=pt_orders["PT3"],
            ls="-.",
            side="left",
        )
        draw_pt_secondary_terminal_strip(pt3_cx, pt_gen_cy, "PT3", section_y=0.512, line_y=0.500)

        pt_v_lbl_y = pt_gen_cy + pt_size + 0.245
        bbox_pt = dict(facecolor="#f8fafc", edgecolor="#9a3412", boxstyle="round,pad=0.25", alpha=0.90)
        self.txt_pt1_v = ax.text(pt1_cx, pt_v_lbl_y - 0.03, "PT1: -- V", fontsize=7, ha="center", color="#0066cc", bbox=bbox_pt)
        self.txt_pt2_v = ax.text(pt2_cx + pt_size * 2.8, pt2_cy - 0.035, "PT2: -- V", fontsize=7, ha="left", va="center", color="#0066cc", bbox=bbox_pt)
        self.txt_pt3_v = ax.text(pt3_cx, pt_v_lbl_y - 0.03, "PT3: -- V", fontsize=7, ha="center", color="#0066cc", bbox=bbox_pt)

        self.txt_i1 = ax.text(ct_x_left, ct_y_top, "Gen1  CT: 0.00 A", color="#cc2200", ha="right", weight="bold", fontsize=8, clip_on=False)
        self.txt_ip1 = ax.text(ct_x_left, ct_y_top - ct_dy, "Ip = 0.00 A  (有功)", color="#0055aa", ha="right", fontsize=7, clip_on=False)
        self.txt_iq1 = ax.text(ct_x_left, ct_y_top - 2 * ct_dy, "Iq = 0.00 A  (无功)", color="#aa00aa", ha="right", fontsize=7, clip_on=False)
        self.txt_grounding = ax.text(
            0.50,
            1.01,
            "N线: 未接地",
            color="gray",
            ha="center",
            fontsize=8,
            clip_on=False,
            bbox=dict(facecolor="#f5f5f5", edgecolor="gray", boxstyle="round,pad=0.3", alpha=0.9),
        )
        self.txt_i2 = ax.text(ct_x_right, ct_y_top, "Gen2  CT: 0.00 A", color="#cc2200", ha="left", weight="bold", fontsize=8, clip_on=False)
        self.txt_ip2 = ax.text(ct_x_right, ct_y_top - ct_dy, "Ip = 0.00 A  (有功)", color="#0055aa", ha="left", fontsize=7, clip_on=False)
        self.txt_iq2 = ax.text(ct_x_right, ct_y_top - 2 * ct_dy, "Iq = 0.00 A  (无功)", color="#aa00aa", ha="left", fontsize=7, clip_on=False)
        self.txt_circ_flow = ax.text(
            0.50,
            -0.045,
            "机组间无环流",
            color="gray",
            ha="center",
            weight="bold",
            fontsize=9,
            bbox=dict(facecolor="#ffffff", edgecolor="gray", alpha=0.9, boxstyle="round,pad=0.3"),
        )
        self.txt_meter = ax.text(
            0.50,
            -0.095,
            "万用表未开启",
            color="black",
            ha="center",
            weight="bold",
            fontsize=9,
            bbox=dict(facecolor="#ffffcc", edgecolor="black", boxstyle="round,pad=0.4"),
            clip_on=False,
        )
        self.probe1_plot, = ax.plot([], [], "ro", markersize=12, alpha=0.8)
        self.probe2_plot, = ax.plot([], [], "ko", markersize=12, alpha=0.8)

        self._psm_terminal_markers = {}
        for pt_name, edge in (("PT1", "#1d4ed8"), ("PT3", "#7c3aed")):
            for phase in ("A", "B", "C"):
                node_name = f"{pt_name}_{phase}"
                x, y = NODES[node_name][:2]
                ring, = ax.plot(
                    [x],
                    [y],
                    "o",
                    markersize=12,
                    markerfacecolor="none",
                    markeredgecolor=edge,
                    markeredgewidth=2.0,
                    visible=False,
                    zorder=7,
                )
                fill, = ax.plot(
                    [x],
                    [y],
                    "o",
                    markersize=7.5,
                    markerfacecolor="#22c55e",
                    markeredgecolor="white",
                    markeredgewidth=0.8,
                    visible=False,
                    zorder=8,
                )
                self._psm_terminal_markers[node_name] = {"ring": ring, "fill": fill}

        self._build_record_tables(ax)

    def _sidebar_label(self, name: str):
        return self._sidebar_badges[name]

    def _render_ct_readings(self, p):
        self.txt_i1.set_text(f"Gen1  CT: {p.i1_rms / CT_RATIO:.2f} A")
        self.txt_ip1.set_text(f"  Ip = {p.ip1 / CT_RATIO:.2f} A  (有功)")
        self.txt_iq1.set_text(f"  Iq = {p.iq1 / CT_RATIO:.2f} A  (无功)")
        self.txt_i2.set_text(f"Gen2  CT: {p.i2_rms / CT_RATIO:.2f} A")
        self.txt_ip2.set_text(f"  Ip = {p.ip2 / CT_RATIO:.2f} A  (有功)")
        self.txt_iq2.set_text(f"  Iq = {p.iq2 / CT_RATIO:.2f} A  (无功)")
        self.txt_circ_flow.set_text(p.circ_msg)
        self.txt_circ_flow.set_color(p.circ_color)
        self.txt_circ_flow.get_bbox_patch().set_edgecolor(p.circ_color)

    def _render_bus_status(self, p):
        bus_status_lbl = self._sidebar_label("bus_status_lbl")
        bus_reference_lbl = self._sidebar_label("bus_reference_lbl")
        bus_status_lbl.setText(p.bus_status_msg)
        self._apply_badge_tone_cb(bus_status_lbl, "success" if p.bus_live else "warning")
        bus_reference_lbl.setText(p.bus_reference_msg)
        self._apply_badge_tone_cb(bus_reference_lbl, "success" if p.bus_live else "neutral")
        src_map = {
            1: "Bus <- Gen 1",
            2: "Bus <- Gen 2",
            "both": p.bus_reference_msg.replace("参考基准: ", "Bus Ref <- "),
            "grid": "Grid Source",
        }
        self.txt_bus_source.set_text(src_map.get(p.bus_source, "Dead Bus (无电)"))

    def _render_breakers(self, p):
        arbitrator_lbl = self._sidebar_label("arbitrator_lbl")
        relay_lbl = self._sidebar_label("relay_lbl")
        arbitrator_lbl.setText(p.arb_msg)
        self._apply_badge_tone_cb(arbitrator_lbl, "info")
        relay_lbl.setText(p.relay_msg)
        relay_tone = {
            "#cc0000": "danger",
            "#ff8800": "warning",
            "#0000cc": "primary",
            "#008000": "success",
        }.get(normalize_qt_color(p.relay_color), "primary")
        self._apply_badge_tone_cb(relay_lbl, relay_tone)

        for lbl_attr, text, bg in [("status1_lbl", p.brk1_text, p.brk1_bg), ("status2_lbl", p.brk2_text, p.brk2_bg)]:
            lbl = self._sidebar_label(lbl_attr)
            lbl.setText(text)
            bg_str = normalize_qt_color(bg)
            if bg_str in ("#00cc00", "#009900", "#006600", "#00ff00"):
                tone = "success"
            elif bg_str in ("#cc0000", "#ff0000", "#990000", "#ff3333"):
                tone = "danger"
            elif bg_str in ("#ffaa00", "#ffcc00", "#ff9900", "#d97706"):
                tone = "warning"
            elif bg_str in ("#333399", "#0000ff", "#1d4ed8"):
                tone = "info"
            else:
                tone = "neutral"
            self._apply_badge_tone_cb(lbl, tone)

        for lines, xs, y_bot, y_top, is_closed in [
            (self.sw1_pack, [0.24, 0.28, 0.32], 0.24, 0.31, p.brk1_visual),
            (self.sw2_pack, [0.68, 0.72, 0.76], 0.24, 0.31, p.brk2_visual),
        ]:
            color1 = p.color_sw1 if lines is self.sw1_pack else p.color_sw2
            for line, x in zip(lines, xs):
                line.set_color(color1)
                if is_closed:
                    line.set_data([x, x], [y_bot, y_top])
                else:
                    line.set_data([x, x + 0.02], [y_bot, y_top - 0.02])

    def _generator_state_color(self, gen) -> str:
        if gen.breaker_closed and not gen.running:
            return "#f59e0b"
        if not gen.running:
            return "#111111"
        if gen.breaker_closed:
            return "#7c3aed"
        return "#2563eb"

    def _render_generators(self) -> None:
        for gen_id, gen in ((1, self._api.sim_state.gen1), (2, self._api.sim_state.gen2)):
            color = self._generator_state_color(gen)
            self._gen_ring_artists[gen_id].set_edgecolor(color)
            self._gen_label_artists[gen_id].set_color(color)

    def _render_grounding_and_pt(self, p):
        self.txt_grounding.set_text(p.ground_msg)
        self.txt_grounding.set_color(p.ground_color)
        self.txt_grounding.get_bbox_patch().set_edgecolor(p.ground_color)
        gnd_mode = self._api.sim_state.grounding_mode
        disconnected = gnd_mode == "断开"
        direct = gnd_mode == "直接接地"
        for gnd in (self.gnd_data1, self.gnd_data2):
            for line in gnd["lower_stubs"]:
                line.set_visible(not disconnected)
            for line in gnd["upper_stubs"]:
                line.set_visible(True)
            for line in gnd["conn"]:
                line.set_visible(True)
            gnd["bypass"].set_visible(not disconnected and direct)
            for art in gnd["resistor"]:
                art.set_visible(not direct)
        for txt, label, value in [(self.txt_pt1_v, "PT1", p.pt1_v), (self.txt_pt2_v, "PT2", p.pt2_v), (self.txt_pt3_v, "PT3", p.pt3_v)]:
            txt.set_text(f"{label}: {value:.1f}V")
            txt.set_color("#15803d" if value > 90.0 else "#9a3412" if value > 10.0 else "#94a3b8")

    def _render_gen_wire_visibility(self):
        visible = self._api.sim_state.show_gen_wires
        if self._api.is_assessment_mode() and not self._api.is_loop_test_complete():
            visible = False
        for art in self._g1_wire_artists + self._g2_wire_artists:
            art.set_visible(visible)
        for line in self.sw1_pack + self.sw2_pack:
            line.set_visible(visible)

    def _mm_canvas_center(self):
        """将电路坐标 (0.50, 0.72) 转换为 canvas2 像素坐标，供万用表定位。"""
        try:
            bbox = self.ax_circuit.get_position()
            xlim = self.ax_circuit.get_xlim()
            ylim = self.ax_circuit.get_ylim()
            ax_fx = (0.50 - xlim[0]) / (xlim[1] - xlim[0])
            ax_fy = (0.72 - ylim[0]) / (ylim[1] - ylim[0])
            fig_fx = bbox.x0 + ax_fx * (bbox.x1 - bbox.x0)
            fig_fy = bbox.y0 + ax_fy * (bbox.y1 - bbox.y0)
            cw = self.canvas2.width()
            ch = self.canvas2.height()
            return int(fig_fx * cw), int((1.0 - fig_fy) * ch)
        except Exception:
            return self.canvas2.width() // 2, self.canvas2.height() // 2

    def _render_multimeter(self, p):
        sim = self._api.sim_state
        if sim.multimeter_mode:
            if sim.probe1_node:
                nx, ny = NODES[sim.probe1_node][:2]
                self.probe1_plot.set_data([nx], [ny])
            else:
                self.probe1_plot.set_data([], [])
            if sim.probe2_node:
                nx, ny = NODES[sim.probe2_node][:2]
                self.probe2_plot.set_data([nx], [ny])
            else:
                self.probe2_plot.set_data([], [])
            self.txt_meter.set_visible(False)

            n1 = sim.probe1_node
            mode = "resistance" if (n1 and n1.startswith("LOOP_")) else "voltage_ac"
            mw, mh = self.multimeter_widget.width(), self.multimeter_widget.height()
            px, py = self._mm_canvas_center()
            cw, ch = self.canvas2.width(), self.canvas2.height()
            mx = max(0, min(px - mw // 2, cw - mw))
            my = max(0, min(py - mh // 2, ch - mh))
            self.multimeter_widget.update_state(
                voltage=getattr(p, "meter_voltage", None),
                status=getattr(p, "meter_status", "idle"),
                probe1=sim.probe1_node,
                probe2=sim.probe2_node,
                mode=mode,
            )
            self.multimeter_widget.move(mx, my)
            self.multimeter_widget.setVisible(True)
            self.multimeter_widget.raise_()
        else:
            self.txt_meter.set_visible(False)
            self.probe1_plot.set_data([], [])
            self.probe2_plot.set_data([], [])
            self.multimeter_widget.setVisible(False)

        self._clear_loop_anim()

    def _clear_loop_anim(self):
        self._loop_anim_offset = 0.0
        self.loop_anim_wire_ok.set_data([], [])
        self.loop_anim_dots.set_data([], [])
        self.loop_anim_gap_l.set_data([], [])
        self.loop_anim_gap_r.set_data([], [])
        self.loop_anim_x1.set_data([], [])
        self.loop_anim_x2.set_data([], [])
