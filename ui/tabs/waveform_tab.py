"""
ui/tabs/waveform_tab.py
实时波形与同期表 Tab（独立 QWidget 组件）
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from PyQt5 import QtCore, QtWidgets

from ui.matplotlib_config import configure_matplotlib

configure_matplotlib()

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator

from domain.constants import (
    GRID_AMP,
    GRID_FREQ,
    SYNC_FREQ_OK_HZ,
    SYNC_PHASE_OK_DEG,
    SYNC_VOLT_OK_V,
)


PLOT_THEME = {
    "figure_bg": "#ffffff",
    "axes_bg": "#fbfdff",
    "grid": "#dbe4f0",
    "spine": "#c7d4e5",
    "text": "#0f172a",
    "muted": "#64748b",
    "phase_a": "#d4aa00",
    "phase_b": "#1a9c3c",
    "phase_c": "#d62828",
}

SYNC_WARN_FREQ_HZ = 0.75
SYNC_WARN_VOLT_V = 700.0
SYNC_WARN_PHASE_DEG = 22.0


class MplCanvas(FigureCanvas):
    def __init__(self, fig: Figure, min_size=(320, 220)):
        super().__init__(fig)
        self._min_size = QtCore.QSize(*min_size)
        self.setMinimumSize(*min_size)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Expanding,
        )

    def minimumSizeHint(self):
        return self._min_size

    def sizeHint(self):
        return self._min_size


class WaveformTabAPI(Protocol):
    @property
    def sim_state(self) -> object: ...

    @property
    def physics(self) -> object: ...


class WaveformTab(QtWidgets.QWidget):
    def __init__(self, api: WaveformTabAPI, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._api = api
        self._build()
        self._init_lines()

    def _build(self) -> None:
        self.setProperty("waveformPage", True)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        root.addLayout(self._build_waveform_header())
        root.addLayout(self._build_waveform_metrics())

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(12)
        root.addLayout(content, stretch=1)

        content.addWidget(self._build_waveform_left_column(), stretch=3)
        content.addWidget(self._build_waveform_right_column(), stretch=2)

    def render(self, rs) -> None:
        d = rs.plot_data or {}
        deg = rs.fixed_deg
        bus_a_display = rs.bus_amp if rs.bus_live else 0.0

        self._render_waveforms(d, deg, bus_a_display)
        self._render_phasors(d, bus_a_display)
        self._render_waveform_dashboard(rs)

    def redraw_canvases(self) -> None:
        self.canvas_wave.draw_idle()
        self.canvas_bus.draw_idle()
        self.canvas_phasor.draw_idle()

    def _build_waveform_header(self):
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(8)

        title = QtWidgets.QLabel("实时波形与同期表")
        title.setProperty("sectionTitle", True)
        layout.addWidget(title)

        subtitle = QtWidgets.QLabel("先看同期结论，再看波形和相量收敛。")
        subtitle.setProperty("sectionCaption", True)
        layout.addWidget(subtitle)

        badges = QtWidgets.QHBoxLayout()
        badges.setSpacing(8)

        self.wave_bus_badge = self._make_badge("母线状态", "neutral")
        self.wave_ref_badge = self._make_badge("参考源", "info")
        self.wave_mode_badge = self._make_badge("运行模式", "primary")
        self.wave_sync_badge = self._make_badge("同期判定", "warning")

        badges.addWidget(self.wave_bus_badge)
        badges.addWidget(self.wave_ref_badge)
        badges.addWidget(self.wave_mode_badge)
        badges.addWidget(self.wave_sync_badge)
        badges.addStretch(1)
        layout.addLayout(badges)
        return layout

    def _build_waveform_metrics(self):
        layout = QtWidgets.QHBoxLayout()
        layout.setSpacing(10)
        self.wave_metric_cards = {}

        cards = [
            ("delta_f", "Δf", "频差"),
            ("delta_v", "ΔV", "压差"),
            ("delta_theta", "Δθ", "相角差"),
            ("sync_state", "同期判定", "当前可否合闸"),
            ("mode", "运行模式", "机组状态"),
        ]
        for key, title, caption in cards:
            card, value_label, caption_label = self._make_metric_card(title, caption)
            self.wave_metric_cards[key] = {
                "value": value_label,
                "caption": caption_label,
                "card": card,
            }
            layout.addWidget(card, stretch=1)
        return layout

    def _build_waveform_left_column(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        wave_card = self._make_plot_card(
            "三相实时波形",
            "观察母线、Gen1、Gen2 三组波形是否持续收敛。",
        )
        wave_layout = wave_card.layout()
        self._setup_waveform_figure()
        wave_layout.addWidget(self.canvas_wave, stretch=1)
        layout.addWidget(wave_card, stretch=5)

        overview_card = self._make_plot_card(
            "母线总览",
            "仅保留母线三相总览，作为次级趋势信息。",
        )
        overview_layout = overview_card.layout()
        self._setup_bus_figure()
        overview_layout.addWidget(self.canvas_bus, stretch=1)
        layout.addWidget(overview_card, stretch=2)
        return container

    def _build_waveform_right_column(self):
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        phasor_card = self._make_plot_card(
            "相量图",
            "独立相量图只负责展示相位关系。",
        )
        phasor_layout = phasor_card.layout()
        self._setup_phasor_figure()
        phasor_layout.addWidget(self.canvas_phasor, stretch=1)
        layout.addWidget(phasor_card, stretch=3)

        sync_card = self._make_panel_card()
        sync_layout = sync_card.layout()

        sync_title = QtWidgets.QLabel("同期判定面板")
        sync_title.setProperty("sectionTitle", True)
        sync_layout.addWidget(sync_title)

        self.sync_state_hero = QtWidgets.QLabel("未开始监视")
        self.sync_state_hero.setProperty("syncStateHero", True)
        self.sync_state_hero.setProperty("tone", "neutral")
        self.sync_state_hero.setWordWrap(True)
        self.sync_state_hero.setMinimumHeight(56)
        sync_layout.addWidget(self.sync_state_hero)

        self.sync_state_hint = QtWidgets.QLabel("直接展示三项差值和是否允许合闸。")
        self.sync_state_hint.setProperty("sectionCaption", True)
        self.sync_state_hint.setWordWrap(True)
        sync_layout.addWidget(self.sync_state_hint)

        criteria_title = QtWidgets.QLabel("同期条件")
        criteria_title.setProperty("sectionTitle", True)
        sync_layout.addWidget(criteria_title)

        self.sync_criteria = {}
        for key, name, limit in (
            ("freq", "频差", f"≤ {SYNC_FREQ_OK_HZ:.1f} Hz"),
            ("volt", "压差", f"≤ {SYNC_VOLT_OK_V:.0f} V"),
            ("phase", "相角差", f"≤ {SYNC_PHASE_OK_DEG:.0f}°"),
        ):
            row, value_label, limit_label, status_badge = self._make_criteria_row(name, limit)
            self.sync_criteria[key] = {
                "value": value_label,
                "limit": limit_label,
                "badge": status_badge,
            }
            sync_layout.addWidget(row)

        sync_layout.addStretch(1)
        layout.addWidget(sync_card, stretch=6)
        return container

    def _setup_waveform_figure(self):
        self.fig_wave = Figure(figsize=(8.8, 6.0), dpi=100)
        self.fig_wave.patch.set_facecolor(PLOT_THEME["figure_bg"])
        self.ax_a, self.ax_b, self.ax_c = self.fig_wave.subplots(3, 1, sharex=True)

        deg_end = self._api.physics.fixed_deg[-1]
        for ax, title in zip(
            (self.ax_a, self.ax_b, self.ax_c),
            ("A 相", "B 相", "C 相"),
        ):
            self._style_axis(ax)
            ax.set_title(
                title,
                loc="left",
                fontsize=10,
                color=PLOT_THEME["text"],
                fontweight="bold",
            )
            ax.set_ylim(-13000, 13000)
            ax.set_xlim(0, deg_end)
            ax.xaxis.set_major_locator(MultipleLocator(90))

        self.ax_b.set_ylabel("电压 (V)", fontsize=9, color=PLOT_THEME["muted"])
        self.ax_c.set_xlabel("窗口角度 (°)", fontsize=9, color=PLOT_THEME["muted"])
        self.fig_wave.subplots_adjust(top=0.90, bottom=0.12, left=0.10, right=0.98, hspace=0.38)
        self.canvas_wave = MplCanvas(self.fig_wave, min_size=(520, 330))

    def _setup_bus_figure(self):
        self.fig_bus = Figure(figsize=(8.8, 2.8), dpi=100)
        self.fig_bus.patch.set_facecolor(PLOT_THEME["figure_bg"])
        self.ax_all = self.fig_bus.add_subplot(111)
        self._style_axis(self.ax_all)
        self.ax_all.set_title(
            "母线总览",
            loc="left",
            fontsize=10,
            color=PLOT_THEME["text"],
            fontweight="bold",
        )
        self.ax_all.set_ylim(-13000, 13000)
        self.ax_all.set_xlim(0, self._api.physics.fixed_deg[-1])
        self.ax_all.xaxis.set_major_locator(MultipleLocator(90))
        self.ax_all.set_xlabel("窗口角度 (°)", fontsize=9, color=PLOT_THEME["muted"])
        self.ax_all.set_ylabel("V", fontsize=8, color=PLOT_THEME["muted"])
        self.fig_bus.tight_layout(pad=1.2)
        self.canvas_bus = MplCanvas(self.fig_bus, min_size=(520, 200))

    def _setup_phasor_figure(self):
        self.fig_phasor = Figure(figsize=(4.4, 4.2), dpi=100)
        self.fig_phasor.patch.set_facecolor(PLOT_THEME["figure_bg"])
        self.ax_p = self.fig_phasor.add_subplot(111, projection="polar")
        self.ax_p.set_facecolor(PLOT_THEME["axes_bg"])
        self.ax_p.set_rmax(13000)
        self.ax_p.set_rticks([3500, 10500])
        self.ax_p.set_rlabel_position(22)
        self.ax_p.grid(color=PLOT_THEME["grid"], linestyle="--", linewidth=0.8, alpha=0.9)
        self.ax_p.tick_params(axis="x", colors=PLOT_THEME["muted"], labelsize=8, pad=2)
        self.ax_p.tick_params(axis="y", colors=PLOT_THEME["muted"], labelsize=8)
        self.ax_p.spines["polar"].set_color(PLOT_THEME["spine"])
        self.ax_p.set_thetagrids(
            np.arange(0, 360, 90),
            labels=["0°", "90°", "180°", "270°"],
        )
        self.fig_phasor.subplots_adjust(top=0.88, bottom=0.10, left=0.08, right=0.94)
        self.canvas_phasor = MplCanvas(self.fig_phasor, min_size=(320, 220))

    def _init_lines(self):
        self._init_waveform_lines()
        self._init_phasor_lines()
        self._sync_last_metrics = None

    def _init_waveform_lines(self):
        self.line_ga, = self.ax_a.plot([], [], color=PLOT_THEME["phase_a"], lw=2.2, label="Busbar")
        self.line_gen1_a, = self.ax_a.plot(
            [],
            [],
            color=PLOT_THEME["phase_a"],
            ls="--",
            lw=1.4,
            alpha=0.78,
            label="Gen1",
        )
        self.line_gen2_a, = self.ax_a.plot(
            [],
            [],
            color=PLOT_THEME["phase_a"],
            ls="-.",
            lw=1.4,
            alpha=0.78,
            label="Gen2",
        )

        self.line_gb, = self.ax_b.plot([], [], color=PLOT_THEME["phase_b"], lw=2.2, label="Busbar")
        self.line_gen1_b, = self.ax_b.plot(
            [],
            [],
            color=PLOT_THEME["phase_b"],
            ls="--",
            lw=1.4,
            alpha=0.78,
            label="Gen1",
        )
        self.line_gen2_b, = self.ax_b.plot(
            [],
            [],
            color=PLOT_THEME["phase_b"],
            ls="-.",
            lw=1.4,
            alpha=0.78,
            label="Gen2",
        )

        self.line_gc, = self.ax_c.plot([], [], color=PLOT_THEME["phase_c"], lw=2.2, label="Busbar")
        self.line_gen1_c, = self.ax_c.plot(
            [],
            [],
            color=PLOT_THEME["phase_c"],
            ls="--",
            lw=1.4,
            alpha=0.78,
            label="Gen1",
        )
        self.line_gen2_c, = self.ax_c.plot(
            [],
            [],
            color=PLOT_THEME["phase_c"],
            ls="-.",
            lw=1.4,
            alpha=0.78,
            label="Gen2",
        )

        self.line_all_a, = self.ax_all.plot([], [], color=PLOT_THEME["phase_a"], lw=2.2, label="A 相")
        self.line_all_b, = self.ax_all.plot([], [], color=PLOT_THEME["phase_b"], lw=2.2, label="B 相")
        self.line_all_c, = self.ax_all.plot([], [], color=PLOT_THEME["phase_c"], lw=2.2, label="C 相")

        self.ax_a.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, 1.08),
            ncol=3,
            fontsize=8,
            frameon=False,
        )
        self.ax_all.legend(loc="upper right", fontsize=8, frameon=False)

    def _init_phasor_lines(self):
        self.p_ga, = self.ax_p.plot([], [], color=PLOT_THEME["phase_a"], lw=3.0, alpha=0.65, marker="o", markersize=7)
        self.p_g1a, = self.ax_p.plot([], [], color=PLOT_THEME["phase_a"], ls="--", lw=1.5, marker="X", markersize=5)
        self.p_g2a, = self.ax_p.plot([], [], color=PLOT_THEME["phase_a"], ls="-.", lw=1.5, marker="*", markersize=7)

        self.p_gb, = self.ax_p.plot([], [], color=PLOT_THEME["phase_b"], lw=3.0, alpha=0.65, marker="o", markersize=7)
        self.p_g1b, = self.ax_p.plot([], [], color=PLOT_THEME["phase_b"], ls="--", lw=1.5, marker="X", markersize=5)
        self.p_g2b, = self.ax_p.plot([], [], color=PLOT_THEME["phase_b"], ls="-.", lw=1.5, marker="*", markersize=7)

        self.p_gc, = self.ax_p.plot([], [], color=PLOT_THEME["phase_c"], lw=3.0, alpha=0.65, marker="o", markersize=7)
        self.p_g1c, = self.ax_p.plot([], [], color=PLOT_THEME["phase_c"], ls="--", lw=1.5, marker="X", markersize=5)
        self.p_g2c, = self.ax_p.plot([], [], color=PLOT_THEME["phase_c"], ls="-.", lw=1.5, marker="*", markersize=7)

    def _render_waveforms(self, d, deg, bus_a_display):
        self.line_ga.set_data(deg, d["ga"])
        self.line_gb.set_data(deg, d["gb"])
        self.line_gc.set_data(deg, d["gc"])
        self.line_gen1_a.set_data(deg, d["g1a"])
        self.line_gen1_b.set_data(deg, d["g1b"])
        self.line_gen1_c.set_data(deg, d["g1c"])
        self.line_gen2_a.set_data(deg, d["g2a"])
        self.line_gen2_b.set_data(deg, d["g2b"])
        self.line_gen2_c.set_data(deg, d["g2c"])
        self.line_all_a.set_data(deg, d["ga"])
        self.line_all_b.set_data(deg, d["gb"])
        self.line_all_c.set_data(deg, d["gc"])

    def _render_phasors(self, d, bus_a_display):
        self.p_ga.set_data([0, d["ang_grid"]], [0, bus_a_display])
        self.p_g1a.set_data([0, d["ang_g1"]], [0, d["a1"]])
        self.p_g2a.set_data([0, d["ang_g2"]], [0, d["a2"]])

        self.p_gb.set_data([0, d["ang_grid"] - 2 * np.pi / 3], [0, bus_a_display])
        self.p_g1b.set_data([0, d["ang_g1"] - 2 * np.pi / 3], [0, d["a1"]])
        self.p_g2b.set_data([0, d["ang_g2"] + d["shift_b"]], [0, d["a2"]])

        self.p_gc.set_data([0, d["ang_grid"] + 2 * np.pi / 3], [0, bus_a_display])
        self.p_g1c.set_data([0, d["ang_g1"] + 2 * np.pi / 3], [0, d["a1"]])
        self.p_g2c.set_data([0, d["ang_g2"] + d["shift_c"]], [0, d["a2"]])

    def _render_waveform_dashboard(self, rs):
        d = rs.plot_data or {}
        sim = self._api.sim_state
        if not rs.bus_live:
            self._render_waveform_dashboard_no_reference(rs, sim)
            return

        ref_info = self._resolve_sync_reference(rs, sim, d)
        ref_freq = ref_info["freq"]
        ref_amp = ref_info["amp"]
        target_freq = sim.gen2.freq
        target_amp = self._resolve_gen2_display_amp(sim, d)

        delta_f = target_freq - ref_freq
        delta_v = abs(target_amp - ref_amp)
        delta_theta = self._compute_phase_delta_deg(sim.gen2.phase_deg, ref_info["phase_deg"])

        freq_tone = self._metric_tone(abs(delta_f), ok=SYNC_FREQ_OK_HZ, warn=SYNC_WARN_FREQ_HZ)
        volt_tone = self._metric_tone(abs(delta_v), ok=SYNC_VOLT_OK_V, warn=SYNC_WARN_VOLT_V)
        phase_tone = self._metric_tone(abs(delta_theta), ok=SYNC_PHASE_OK_DEG, warn=SYNC_WARN_PHASE_DEG)
        sync_state, sync_tone, sync_hint = self._sync_state(rs, sim, delta_f, delta_v, delta_theta)

        mode_text = f"G1 {self._mode_text(sim.gen1.mode)} / G2 {self._mode_text(sim.gen2.mode)}"
        bus_text = rs.bus_status_msg or ("母线带电" if rs.bus_live else "母线未带电")
        ref_badge_text = ref_info["badge_text"]

        self._set_badge(self.wave_bus_badge, bus_text, "success" if rs.bus_live else "neutral")
        self._set_badge(self.wave_ref_badge, ref_badge_text, "info")
        self._set_badge(self.wave_mode_badge, mode_text, "primary")
        self._set_badge(self.wave_sync_badge, f"同期判定：{sync_state}", sync_tone)

        self._update_metric_card("delta_f", f"{delta_f:+.2f} Hz", "相对参考频率", freq_tone)
        self._update_metric_card("delta_v", f"{delta_v:.0f} V", "相对参考电压", volt_tone)
        self._update_metric_card("delta_theta", f"{delta_theta:.1f}°", "相对参考相角", phase_tone)
        self._update_metric_card("sync_state", sync_state, sync_hint, sync_tone)
        self._update_metric_card("mode", mode_text, "当前机组方式", "primary")

        self._update_sync_criteria("freq", delta_f, "Hz", SYNC_FREQ_OK_HZ, SYNC_WARN_FREQ_HZ)
        self._update_sync_criteria("volt", delta_v, "V", SYNC_VOLT_OK_V, SYNC_WARN_VOLT_V)
        self._update_sync_criteria("phase", delta_theta, "°", SYNC_PHASE_OK_DEG, SYNC_WARN_PHASE_DEG)

        self.sync_state_hero.setText(sync_state)
        self._set_widget_props(self.sync_state_hero, syncStateHero=True, tone=sync_tone)
        self.sync_state_hint.setText(sync_hint)

    def _render_waveform_dashboard_no_reference(self, rs, sim):
        mode_text = f"G1 {self._mode_text(sim.gen1.mode)} / G2 {self._mode_text(sim.gen2.mode)}"
        bus_text = rs.bus_status_msg or "母线未带电"

        self._set_badge(self.wave_bus_badge, bus_text, "neutral")
        self._set_badge(self.wave_ref_badge, "参考基准: 无", "neutral")
        self._set_badge(self.wave_mode_badge, mode_text, "primary")
        self._set_badge(self.wave_sync_badge, "同期判定: 无参考源", "neutral")

        self._update_metric_card("delta_f", "--", "当前无母排参考", "neutral")
        self._update_metric_card("delta_v", "--", "当前无母排参考", "neutral")
        self._update_metric_card("delta_theta", "--", "当前无母排参考", "neutral")
        self._update_metric_card("sync_state", "无参考源", "需先建立母排参考后再判定。", "neutral")
        self._update_metric_card("mode", mode_text, "当前机组方式", "primary")

        self._set_sync_criteria_unavailable("freq")
        self._set_sync_criteria_unavailable("volt")
        self._set_sync_criteria_unavailable("phase")

        self.sync_state_hero.setText("无参考源")
        self._set_widget_props(self.sync_state_hero, syncStateHero=True, tone="neutral")
        self.sync_state_hint.setText("母排未带电，Δf / ΔV / Δθ 暂不计算。")

    def _resolve_sync_reference(self, rs, sim, d):
        ref_id = rs.bus_reference_gen
        if rs.bus_live and ref_id == 1:
            return {
                "freq": sim.gen1.freq,
                "amp": d.get("a1", sim.gen1.actual_amp or sim.gen1.amp),
                "phase_deg": sim.gen1.phase_deg,
                "badge_text": "参考基准: Gen1",
            }
        if rs.bus_live and ref_id == 2:
            return {
                "freq": sim.gen2.freq,
                "amp": d.get("a2", sim.gen2.actual_amp or sim.gen2.amp),
                "phase_deg": sim.gen2.phase_deg,
                "badge_text": "参考基准: Gen2",
            }
        if rs.bus_live:
            return {
                "freq": getattr(self._api.physics, "bus_freq", GRID_FREQ),
                "amp": rs.bus_amp,
                "phase_deg": np.degrees(getattr(self._api.physics, "bus_phase", 0.0)),
                "badge_text": rs.bus_reference_msg or "参考基准: 母排",
            }
        return {
            "freq": GRID_FREQ,
            "amp": GRID_AMP,
            "phase_deg": 0.0,
            "badge_text": "参考基准: 额定值",
        }

    def _resolve_gen2_display_amp(self, sim, d):
        return d.get("a2", sim.gen2.actual_amp or sim.gen2.amp)

    def _compute_phase_delta_deg(self, target_phase_deg, ref_phase_deg):
        raw = abs(target_phase_deg - ref_phase_deg) % 360.0
        return min(raw, 360.0 - raw)

    def _make_metric_card(self, title, caption):
        card = self._make_panel_card(metric=True)
        layout = card.layout()

        title_label = QtWidgets.QLabel(title)
        title_label.setProperty("metricTitle", True)
        layout.addWidget(title_label)

        value_label = QtWidgets.QLabel("--")
        value_label.setProperty("metricValue", True)
        value_label.setProperty("tone", "neutral")
        layout.addWidget(value_label)

        caption_label = QtWidgets.QLabel(caption)
        caption_label.setProperty("metricCaption", True)
        caption_label.setWordWrap(True)
        layout.addWidget(caption_label)
        layout.addStretch(1)
        return card, value_label, caption_label

    def _make_plot_card(self, title, caption):
        card = self._make_panel_card(plot=True)
        layout = card.layout()

        title_label = QtWidgets.QLabel(title)
        title_label.setProperty("sectionTitle", True)
        layout.addWidget(title_label)

        caption_label = QtWidgets.QLabel(caption)
        caption_label.setProperty("sectionCaption", True)
        caption_label.setWordWrap(True)
        layout.addWidget(caption_label)
        return card

    def _make_panel_card(self, metric=False, plot=False):
        frame = QtWidgets.QFrame()
        if metric:
            frame.setProperty("metricCard", True)
            frame.setMinimumHeight(108)
        elif plot:
            frame.setProperty("plotCard", True)
        else:
            frame.setProperty("wavePanelCard", True)
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        return frame

    def _make_criteria_row(self, name, limit_text):
        frame = QtWidgets.QFrame()
        frame.setProperty("criteriaRow", True)
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        frame.setMinimumHeight(42)

        name_label = QtWidgets.QLabel(f"{name} {limit_text}")
        name_label.setProperty("metricCaption", True)
        name_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        layout.addWidget(name_label, stretch=1)

        value_label = QtWidgets.QLabel("--")
        value_label.setProperty("recordValue", True)
        value_label.setProperty("tone", "neutral")
        value_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        value_label.setMinimumWidth(92)
        layout.addWidget(value_label)

        badge = self._make_badge("待评估", "neutral")
        badge.setProperty("criteriaBadge", True)
        badge.setAlignment(QtCore.Qt.AlignCenter)
        badge.setMinimumWidth(78)
        layout.addWidget(badge)
        return frame, value_label, name_label, badge

    def _make_badge(self, text, tone):
        label = QtWidgets.QLabel(text)
        label.setProperty("badge", True)
        label.setProperty("tone", tone)
        return label

    def _set_badge(self, label, text, tone):
        label.setText(text)
        self._set_widget_props(label, badge=True, tone=tone)

    def _update_metric_card(self, key, value_text, caption_text, tone):
        card = self.wave_metric_cards[key]
        card["value"].setText(value_text)
        self._set_widget_props(card["value"], metricValue=True, tone=tone)
        card["caption"].setText(caption_text)
        self._set_widget_props(card["card"], metricCard=True, tone=tone)

    def _update_sync_criteria(self, key, value, unit, ok_limit, warn_limit):
        row = self.sync_criteria[key]
        tone = self._metric_tone(abs(value), ok=ok_limit, warn=warn_limit)
        if unit == "Hz":
            text = f"{value:+.2f} {unit}"
        elif unit == "°":
            text = f"{abs(value):.1f}{unit}"
        else:
            text = f"{abs(value):.0f} {unit}"
        row["value"].setText(text)
        self._set_widget_props(row["value"], recordValue=True, tone=tone)
        badge_text = "通过" if tone == "success" else "接近" if tone == "warning" else "未通过"
        self._set_badge(row["badge"], badge_text, tone)

    def _set_sync_criteria_unavailable(self, key):
        row = self.sync_criteria[key]
        row["value"].setText("--")
        self._set_widget_props(row["value"], recordValue=True, tone="neutral")
        self._set_badge(row["badge"], "--", "neutral")

    def _style_axis(self, ax):
        ax.set_facecolor(PLOT_THEME["axes_bg"])
        for side in ax.spines.values():
            side.set_color(PLOT_THEME["spine"])
        ax.grid(color=PLOT_THEME["grid"], linestyle="--", linewidth=0.8, alpha=0.85)
        ax.tick_params(axis="x", colors=PLOT_THEME["muted"], labelsize=8)
        ax.tick_params(axis="y", colors=PLOT_THEME["muted"], labelsize=8)

    def _metric_tone(self, value, ok, warn):
        if value <= ok:
            return "success"
        if value <= warn:
            return "warning"
        return "danger"

    def _sync_state(self, rs, sim, delta_f, delta_v, delta_theta):
        if sim.gen2.mode == "stop":
            return "Gen2 未运行", "neutral", "先启动 Gen2，再观察三项同期条件是否进入允许范围。"
        if not rs.bus_live:
            return "母线未带电", "info", "当前母线未带电，本页按额定值进行参考监视。"

        freq_ok = abs(delta_f) <= SYNC_FREQ_OK_HZ
        volt_ok = abs(delta_v) <= SYNC_VOLT_OK_V
        phase_ok = abs(delta_theta) <= SYNC_PHASE_OK_DEG
        if freq_ok and volt_ok and phase_ok:
            return "允许合闸", "success", "三项条件均已进入允许范围，可执行同期合闸。"
        if (
            abs(delta_f) <= SYNC_WARN_FREQ_HZ
            and abs(delta_v) <= SYNC_WARN_VOLT_V
            and abs(delta_theta) <= SYNC_WARN_PHASE_DEG
        ):
            return "接近就绪", "warning", "条件正在收敛，但相角差或压差仍需继续观察。"
        return "未就绪", "danger", "当前仍不满足同期合闸条件，应继续调整或等待自动收敛。"

    def _build_trend_text(self, delta_f, delta_v, delta_theta):
        current = {
            "freq": abs(delta_f),
            "volt": abs(delta_v),
            "phase": abs(delta_theta),
        }
        if not self._sync_last_metrics:
            self._sync_last_metrics = current
            return "趋势：等待第二个采样点后开始判断收敛方向。"

        parts = []
        labels = {"freq": "Δf", "volt": "ΔV", "phase": "Δθ"}
        for key in ("freq", "volt", "phase"):
            prev = self._sync_last_metrics[key]
            now = current[key]
            if now < prev - 1e-6:
                trend = "收敛"
            elif now > prev + 1e-6:
                trend = "放大"
            else:
                trend = "持平"
            parts.append(f"{labels[key]} {trend}")
        self._sync_last_metrics = current
        return "趋势：" + " / ".join(parts)

    def _normalize_diff_deg(self, value):
        value = (value + 180.0) % 360.0 - 180.0
        return value

    def _mode_text(self, mode):
        mapping = {
            "auto": "自动",
            "manual": "手动",
            "stop": "停止",
        }
        return mapping.get(mode, str(mode))

    def _tone_from_color(self, color, fallback="neutral"):
        color = (color or "").lower()
        if color in {"#16a34a", "#15803d", "green"}:
            return "success"
        if color in {"#dc2626", "#b91c1c", "red"}:
            return "danger"
        if color in {"#d97706", "#b45309", "orange"}:
            return "warning"
        if color in {"#0369a1", "#2563eb", "blue"}:
            return "info"
        if color in {"gray", "grey"}:
            return "neutral"
        return fallback

    def _set_widget_props(self, widget, **props):
        for key, value in props.items():
            widget.setProperty(key, value)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
