"""
ui/widgets/phase_seq_meter.py
相序仪 Widget — 追光圆点式

12 个圆点排成一圈，亮点依次追逐产生视觉旋转感：
  · 顺时针追逐 → 正序
  · 逆时针追逐 → 反序
  · 静止（暗淡） → 未接入
中心显示相序文字，底部两个氖灯指示正序/逆序。
"""

import math
from typing import Literal

from PyQt5 import QtWidgets, QtCore, QtGui

_N       = 12          # 圆点数量
_ABC_FWD = {'ABC', 'BCA', 'CAB'}   # 所有正序循环排列
_TAIL    = 5           # 亮尾长度（含头部）
_FPS     = 25          # 动画帧率
_ROT_HZ  = 1.5         # 转速（圈/秒），与 50Hz 频率基准对应
_SPEED   = _N * _ROT_HZ / _FPS   # 每帧推进的点数


class PhaseSeqMeterWidget(QtWidgets.QWidget):
    """追光圆点式相序仪。"""

    # 颜色
    _BG       = QtGui.QColor('#1e272e')
    _RING_DIM = QtGui.QColor('#2c3e50')   # 暗点
    _ABC_BRIGHT = QtGui.QColor('#2ecc71') # 正序亮色
    _ACB_BRIGHT = QtGui.QColor('#e74c3c') # 逆序亮色
    _UNK_BRIGHT = QtGui.QColor('#7f8c8d') # 未知
    _LAMP_A_ON  = QtGui.QColor('#00ff88')
    _LAMP_A_OFF = QtGui.QColor('#0d3b26')
    _LAMP_B_ON  = QtGui.QColor('#ff4444')
    _LAMP_B_OFF = QtGui.QColor('#3b0d0d')

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pos: float = 0.0
        self._direction: int = 0        # +1=CW/正序, -1=CCW/逆序, 0=静止
        self._sequence: str = 'unknown'
        self._connected_pt: str | None = None
        self._freq: float = 50.0
        self._status: Literal["hidden", "waiting", "connected"] = "hidden"
        self._waiting_text: str = ""

        self._timer: QtCore.QTimer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // _FPS)

        self.setFixedSize(180, 200)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setToolTip("相序仪\n顺时针=正序  逆时针=反序")

    # ── Public API ────────────────────────────────────────────────────────
    def set_waiting(self, pt_name: str, n: int = 0, total: int = 3) -> None:
        self._connected_pt = pt_name
        self._sequence     = 'unknown'
        self._direction    = 0
        self._status       = "waiting"
        self._waiting_text = f"待接线 {n}/{total}"
        self.update()

    def connect_pt(self, pt_name: str, sequence: str) -> None:
        self._connected_pt = pt_name
        self._sequence     = sequence
        is_valid = (len(sequence) == 3 and sequence not in ('unknown', 'FAULT'))
        self._direction = 1 if sequence in _ABC_FWD else -1 if is_valid else 0
        self._status = "connected"
        self._waiting_text = ""
        self.update()

    def disconnect(self) -> None:
        self._connected_pt = None
        self._sequence     = 'unknown'
        self._direction    = 0
        self._status       = "hidden"
        self._waiting_text = ""
        self.update()

    def current_sequence(self) -> str:
        """返回当前应当对外暴露的相序结果。"""
        if self._status == "connected":
            return self._sequence
        return "unknown"

    def set_freq(self, freq_hz: float) -> None:
        self._freq = max(freq_hz, 1.0)

    # ── Timer ─────────────────────────────────────────────────────────────
    def _tick(self):
        if self._direction != 0:
            speed = _SPEED * (self._freq / 50.0)
            self._pos = (self._pos + self._direction * speed) % _N
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)

        W, H = self.width(), self.height()
        cx = W // 2

        # 背景
        p.fillRect(self.rect(), self._BG)

        # ── 圆点环 ──────────────────────────────────────────────────────
        ring_cy  = H // 2 - 14
        ring_r   = min(W, H) // 2 - 22
        dot_r    = 7

        bright_color = (self._ABC_BRIGHT if self._sequence in _ABC_FWD else
                        self._ACB_BRIGHT if self._direction == -1 else
                        self._UNK_BRIGHT)

        for i in range(_N):
            ang = math.radians(i * 360 / _N - 90)   # 从12点钟开始
            dx  = int(cx     + ring_r * math.cos(ang))
            dy  = int(ring_cy + ring_r * math.sin(ang))

            if self._direction == 0:
                t = 0.08   # 全部暗淡
            else:
                dist = (self._pos - i) % _N
                t    = max(0.0, 1.0 - dist / _TAIL) if dist < _TAIL else 0.0

            color = self._lerp(self._RING_DIM, bright_color, t)

            # 外圈光晕
            if t > 0.5:
                glow = QtGui.QRadialGradient(dx, dy, dot_r * 2)
                gc   = QtGui.QColor(bright_color)
                gc.setAlpha(int(100 * t))
                glow.setColorAt(0, gc)
                glow.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
                p.setBrush(QtGui.QBrush(glow))
                p.setPen(QtCore.Qt.NoPen)
                p.drawEllipse(dx - dot_r * 2, dy - dot_r * 2,
                              dot_r * 4, dot_r * 4)

            # 圆点本体
            p.setBrush(color)
            p.setPen(QtGui.QPen(color.lighter(120), 1))
            p.drawEllipse(dx - dot_r, dy - dot_r, dot_r * 2, dot_r * 2)

        # ── 中心文字 ─────────────────────────────────────────────────────
        if self._status == "waiting" and self._connected_pt:
            line1 = self._connected_pt
            line2, c2 = self._waiting_text or "接待线 0/3", "#f59e0b"
        elif self._connected_pt and self._status == "connected":
            line1 = self._connected_pt
            if self._sequence in _ABC_FWD:
                line2, c2 = "正序 ↻", '#2ecc71'
            elif self._direction == -1:
                line2, c2 = "反序 ↺", '#e74c3c'
            else:
                line2, c2 = "异常", '#aaaaaa'
        else:
            line1, line2, c2 = "未接入", "—", '#555555'

        p.setFont(QtGui.QFont('SimHei', 9, QtGui.QFont.Bold))
        p.setPen(QtGui.QColor('#aaa'))
        p.drawText(QtCore.QRect(0, ring_cy - 12, W, 16),
                   QtCore.Qt.AlignCenter, line1)
        p.setFont(QtGui.QFont('SimHei', 10, QtGui.QFont.Bold))
        p.setPen(QtGui.QColor(c2))
        p.drawText(QtCore.QRect(0, ring_cy + 2, W, 18),
                   QtCore.Qt.AlignCenter, line2)

        # ── 氖灯 ─────────────────────────────────────────────────────────
        lamp_y  = ring_cy + ring_r + 14
        lamp_r  = 10
        lamp_ax = W // 3
        lamp_bx = W * 2 // 3

        glow_a = bool(self._status == "connected" and self._connected_pt and self._sequence in _ABC_FWD)
        glow_b = bool(self._status == "connected" and self._connected_pt and self._direction == -1)
        self._draw_lamp(p, lamp_ax, lamp_y, lamp_r,
                        self._LAMP_A_ON if glow_a else self._LAMP_A_OFF, glow_a)
        self._draw_lamp(p, lamp_bx, lamp_y, lamp_r,
                        self._LAMP_B_ON if glow_b else self._LAMP_B_OFF, glow_b)

        p.setFont(QtGui.QFont('SimHei', 7))
        p.setPen(QtGui.QColor('#2ecc71') if glow_a else QtGui.QColor('#555'))
        p.drawText(QtCore.QRect(lamp_ax - 18, lamp_y + lamp_r + 2, 36, 12),
                   QtCore.Qt.AlignCenter, "正序")
        p.setPen(QtGui.QColor('#e74c3c') if glow_b else QtGui.QColor('#555'))
        p.drawText(QtCore.QRect(lamp_bx - 18, lamp_y + lamp_r + 2, 36, 12),
                   QtCore.Qt.AlignCenter, "逆序")

        p.end()

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _lerp(c1: QtGui.QColor, c2: QtGui.QColor, t: float) -> QtGui.QColor:
        """在两色之间线性插值，t=0→c1，t=1→c2。"""
        t = max(0.0, min(1.0, t))
        return QtGui.QColor(
            int(c1.red()   + t * (c2.red()   - c1.red())),
            int(c1.green() + t * (c2.green() - c1.green())),
            int(c1.blue()  + t * (c2.blue()  - c1.blue())),
        )

    @staticmethod
    def _draw_lamp(painter, cx, cy, r, color, glowing):
        if glowing:
            g = QtGui.QRadialGradient(cx, cy, r * 2)
            gc = QtGui.QColor(color)
            gc.setAlpha(120)
            g.setColorAt(0, gc)
            g.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            painter.setBrush(QtGui.QBrush(g))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(cx - r*2, cy - r*2, r*4, r*4)
        painter.setBrush(color)
        painter.setPen(QtGui.QPen(color.lighter(130), 1))
        painter.drawEllipse(cx - r, cy - r, r*2, r*2)
        if glowing:
            hr = max(r//3, 2)
            painter.setBrush(QtGui.QColor(255, 255, 255, 160))
            painter.setPen(QtCore.Qt.NoPen)
            painter.drawEllipse(cx - hr, cy - r + 2, hr*2, hr*2)
