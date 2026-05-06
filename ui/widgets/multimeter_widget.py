"""
ui/widgets/multimeter_widget.py
仿真数字万用表 Widget — QPainter 自绘

外观：机身 + LCD 显示屏 + 旋转表盘 + 表笔插孔
数据由外部每帧调用 update_state() 刷新，表盘指针平滑动画由内部 QTimer 驱动。
"""

import math

from PyQt5 import QtCore, QtGui, QtWidgets

_W = 210   # 宽度 px
_H = 295   # 高度 px


def _shorten_node(node: str) -> str:
    """将节点名缩短为最多 8 字符，便于在小空间内显示。"""
    if not node:
        return '未接'
    if node.startswith('LOOP_'):
        parts = node.split('_')          # LOOP_G1_A → ['LOOP','G1','A']
        return f"{parts[1]}-{parts[2]}" if len(parts) >= 3 else node
    return node.replace('_', '')         # PT1_A → PT1A


class MultimeterWidget(QtWidgets.QWidget):
    """
    仿数字万用表浮动 Widget。
    - 无需独立 timer 驱动数据，只有表盘平滑动画用 QTimer。
    - 外部每帧调用 update_state() 传入最新数据后调用 update() 触发重绘。
    """

    # ── 颜色常量 ─────────────────────────────────────────────────────────
    _LCD_BG     = QtGui.QColor('#0d1a0d')
    _LCD_BORDER = QtGui.QColor('#1a3a1a')
    _LCD_DIGIT  = QtGui.QColor('#a8ff3e')   # 亮绿色——正常读数
    _LCD_DIM    = QtGui.QColor('#2a4a2a')   # 暗绿——无测量
    _LCD_WARN   = QtGui.QColor('#ff8c00')   # 橙色——超量程/危险
    _POINTER    = QtGui.QColor('#ff6600')   # 橙红——指针

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(_W, _H)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                           QtWidgets.QSizePolicy.Fixed)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)

        # ── 状态 ──────────────────────────────────────────────────────
        self._voltage: float | None = None
        self._status  = 'idle'      # idle | ok | danger | invalid
        self._probe1: str | None = None
        self._probe2: str | None = None
        self._mode    = 'voltage_ac'   # voltage_ac | resistance | off

        # ── 表盘动画 ──────────────────────────────────────────────────
        # 角度约定：0°=右(3点)，逆时针为正（标准数学）
        # 三个挡位：OFF=90°(12点), ~V=30°(1点), Ω=150°(11点)
        self._dial_angle  = 30.0
        self._dial_target = 30.0
        self._anim_timer  = QtCore.QTimer(self)
        self._anim_timer.timeout.connect(self._tick_dial)
        self._anim_timer.start(33)   # ~30 fps

    # ── Public API ────────────────────────────────────────────────────────
    def update_state(self,
                     voltage: float | None,
                     status: str,
                     probe1: str | None,
                     probe2: str | None,
                     mode: str) -> None:
        """每帧由电路页渲染逻辑调用，传入最新物理量。"""
        self._voltage = voltage
        self._status  = status
        self._probe1  = probe1
        self._probe2  = probe2
        self._mode    = mode
        self._dial_target = {
            'off':        90.0,
            'voltage_ac': 30.0,
            'resistance': 150.0,
        }.get(mode, 30.0)
        self.update()   # 触发 paintEvent

    # ── 表盘动画 timer ─────────────────────────────────────────────────────
    def _tick_dial(self):
        diff = self._dial_target - self._dial_angle
        if diff >  180: diff -= 360
        if diff < -180: diff += 360
        if abs(diff) < 0.5:
            self._dial_angle = self._dial_target
        else:
            self._dial_angle += diff * 0.18   # 平滑步进
        self.update()

    # ── Paint 入口 ────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        self._draw_body(p)
        self._draw_lcd(p)
        self._draw_dial(p)
        self._draw_probes(p)
        p.end()

    # ─────────────────────────────────────────────────────────────────────
    # 绘制各分区
    # ─────────────────────────────────────────────────────────────────────

    def _draw_body(self, p: QtGui.QPainter):
        W, H = _W, _H
        # 外投影阴影
        for i in range(4, 0, -1):
            shadow = QtGui.QColor(0, 0, 0, 18 * i)
            p.setBrush(shadow)
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(i, i, W - i, H - i, 14, 14)
        # 机身渐变
        grad = QtGui.QLinearGradient(0, 0, 0, H)
        grad.setColorAt(0.0, QtGui.QColor('#3c3c3c'))
        grad.setColorAt(1.0, QtGui.QColor('#1c1c1c'))
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtGui.QPen(QtGui.QColor('#4a4a4a'), 1))
        p.drawRoundedRect(0, 0, W - 3, H - 3, 12, 12)

    def _draw_lcd(self, p: QtGui.QPainter):
        SX, SY, SW, SH = 10, 10, 190, 96   # LCD 外框 (左, 上, 宽, 高)

        # LCD 背景 + 边框
        p.setBrush(self._LCD_BG)
        p.setPen(QtGui.QPen(self._LCD_BORDER, 1.5))
        p.drawRoundedRect(SX, SY, SW, SH, 6, 6)

        # ── 左上：模式指示 ─────────────────────────────────────────────
        ind_r = QtCore.QRect(SX + 6, SY + 5, 40, 16)
        p.setFont(QtGui.QFont('Arial', 8, QtGui.QFont.Bold))
        if self._mode == 'voltage_ac':
            p.setPen(self._LCD_DIGIT)
            p.drawText(ind_r, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "AC~")
        elif self._mode == 'resistance':
            p.setPen(self._LCD_DIGIT)
            p.drawText(ind_r, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, "Ω")

        # ── 右上：AUTO 徽章 ────────────────────────────────────────────
        auto_r = QtCore.QRect(SX + SW - 40, SY + 5, 32, 14)
        p.setBrush(QtGui.QColor('#1a4a1a'))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(auto_r, 3, 3)
        p.setFont(QtGui.QFont('Arial', 7, QtGui.QFont.Bold))
        p.setPen(self._LCD_DIGIT)
        p.drawText(auto_r, QtCore.Qt.AlignCenter, "AUTO")

        # ── 主读数（大字）─────────────────────────────────────────────
        main_txt, main_color = self._main_reading()
        if any(ord(c) > 127 for c in main_txt):
            p.setFont(QtGui.QFont('', 16, QtGui.QFont.Bold))   # 系统默认字体，支持 CJK
        else:
            p.setFont(QtGui.QFont('Courier New', 24, QtGui.QFont.Bold))
        p.setPen(main_color)
        main_r = QtCore.QRect(SX + 4, SY + 22, SW - 12, 50)
        p.drawText(main_r, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                   main_txt)

        # ── 单位（读数右下角）──────────────────────────────────────────
        unit_txt = self._unit()
        p.setFont(QtGui.QFont('Arial', 10, QtGui.QFont.Bold))
        dim_color = self._LCD_DIM if self._status == 'idle' else self._LCD_DIGIT
        p.setPen(dim_color)
        unit_r = QtCore.QRect(SX + 4, SY + 79, SW - 8, 14)
        p.drawText(unit_r, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                   unit_txt)

    def _draw_dial(self, p: QtGui.QPainter):
        cx, cy, r = _W // 2, 173, 36   # 表盘圆心和外半径

        # 金属外环（锥形渐变模拟光泽）
        rim = QtGui.QConicalGradient(cx, cy, 45)
        for t, c in [(0.0, '#999'), (0.25, '#555'),
                     (0.5, '#bbb'), (0.75, '#444'), (1.0, '#999')]:
            rim.setColorAt(t, QtGui.QColor(c))
        p.setBrush(QtGui.QBrush(rim))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - r - 4, cy - r - 4, (r + 4) * 2, (r + 4) * 2)

        # 表盘面（径向渐变，中间亮四周暗）
        face = QtGui.QRadialGradient(cx - 6, cy - 6, r * 1.4)
        face.setColorAt(0, QtGui.QColor('#2e2e2e'))
        face.setColorAt(1, QtGui.QColor('#101010'))
        p.setBrush(QtGui.QBrush(face))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # 刻度和标签：3 个挡位
        positions = [
            (90.0,  'OFF', QtGui.QColor('#777777')),
            (30.0,  '~V',  self._LCD_DIGIT),
            (150.0, 'Ω',   self._LCD_DIGIT),
        ]
        label_r  = r + 14   # 标签到圆心距离
        tick_in  = r - 4    # 刻度线内端
        tick_out = r + 2    # 刻度线外端

        for deg, lbl, color in positions:
            rad  = math.radians(deg)
            cosd = math.cos(rad)
            sind = math.sin(rad)
            # 刻度线
            p.setPen(QtGui.QPen(color, 1.5))
            p.drawLine(
                QtCore.QPointF(cx + tick_in  * cosd, cy - tick_in  * sind),
                QtCore.QPointF(cx + tick_out * cosd, cy - tick_out * sind),
            )
            # 标签文字
            lx = cx + label_r * cosd
            ly = cy - label_r * sind
            p.setFont(QtGui.QFont('Arial', 7, QtGui.QFont.Bold))
            p.setPen(color)
            p.drawText(QtCore.QRectF(lx - 14, ly - 8, 28, 16),
                       QtCore.Qt.AlignCenter, lbl)

        # 指针（三角形，从圆心向当前角度方向伸出）
        ptr_rad  = math.radians(self._dial_angle)
        ptr_len  = r - 9
        tip_x    = cx + ptr_len * math.cos(ptr_rad)
        tip_y    = cy - ptr_len * math.sin(ptr_rad)
        wing_rad = ptr_rad + math.pi / 2
        wing_w   = 3.5
        poly = QtGui.QPolygonF([
            QtCore.QPointF(tip_x, tip_y),
            QtCore.QPointF(cx + wing_w * math.cos(wing_rad),
                           cy - wing_w * math.sin(wing_rad)),
            QtCore.QPointF(cx - wing_w * math.cos(wing_rad),
                           cy + wing_w * math.sin(wing_rad)),
        ])
        p.setBrush(self._POINTER)
        p.setPen(QtCore.Qt.NoPen)
        p.drawPolygon(poly)

        # 中心旋钮（小圆）
        p.setBrush(QtGui.QColor('#3c3c3c'))
        p.setPen(QtGui.QPen(QtGui.QColor('#666'), 1))
        p.drawEllipse(cx - 8, cy - 8, 16, 16)
        p.setBrush(QtGui.QColor('#888'))
        p.setPen(QtCore.Qt.NoPen)
        p.drawEllipse(cx - 3, cy - 3, 6, 6)

    def _draw_probes(self, p: QtGui.QPainter):
        PY, PH, W = 216, 73, _W   # 插孔区域

        # 背景条
        p.setBrush(QtGui.QColor('#181818'))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(10, PY, W - 20, PH, 6, 6)

        com_cx = W // 3       # COM 孔圆心 x（左）
        vo_cx  = W * 2 // 3   # VΩ  孔圆心 x（右）
        jack_y = PY + 24      # 孔圆心 y
        jack_r = 9            # 孔半径

        for cx, label, hole_color, node, is_red in [
            (com_cx, 'COM', QtGui.QColor('#111111'), self._probe2, False),
            (vo_cx,  'VΩ',  QtGui.QColor('#7a1010'), self._probe1, True),
        ]:
            # 插孔外圈
            p.setBrush(QtGui.QColor('#444'))
            p.setPen(QtGui.QPen(QtGui.QColor('#666'), 1))
            p.drawEllipse(cx - jack_r - 2, jack_y - jack_r - 2,
                          (jack_r + 2) * 2, (jack_r + 2) * 2)
            # 插孔本体（颜色圆）
            p.setBrush(hole_color)
            p.setPen(QtCore.Qt.NoPen)
            p.drawEllipse(cx - jack_r, jack_y - jack_r,
                          jack_r * 2, jack_r * 2)
            # 中心孔（深黑小圆）
            p.setBrush(QtGui.QColor('#0a0a0a'))
            p.drawEllipse(cx - 3, jack_y - 3, 6, 6)

            # 插孔标签（COM / VΩ）
            p.setFont(QtGui.QFont('Arial', 7, QtGui.QFont.Bold))
            lbl_color = (QtGui.QColor('#cc3333') if is_red
                         else QtGui.QColor('#aaaaaa'))
            p.setPen(lbl_color)
            p.drawText(
                QtCore.QRect(cx - 14, jack_y + jack_r + 3, 28, 11),
                QtCore.Qt.AlignCenter, label)

            # 节点名称
            p.setFont(QtGui.QFont('Arial', 6))
            if node:
                p.setPen(QtGui.QColor('#22cc66'))
                nd_txt = _shorten_node(node)
            else:
                p.setPen(QtGui.QColor('#444'))
                nd_txt = '未接'
            p.drawText(
                QtCore.QRect(cx - 22, jack_y + jack_r + 15, 44, 11),
                QtCore.Qt.AlignCenter, nd_txt)

    # ─────────────────────────────────────────────────────────────────────
    # 辅助：从状态推算显示值
    # ─────────────────────────────────────────────────────────────────────

    def _main_reading(self) -> tuple[str, QtGui.QColor]:
        """返回 (主读数文字, 颜色)。"""
        st = self._status
        v  = self._voltage

        if self._mode == 'off' or st == 'idle':
            return ('- - - -', self._LCD_DIM)

        if st == 'invalid':
            return ('O.L', self._LCD_WARN)

        if self._mode == 'resistance':
            if st == 'ok':
                return ('≈ 0', self._LCD_DIGIT)
            if st == 'danger':
                return ('未导通', self._LCD_WARN)
            return ('O.L', self._LCD_WARN)

        # voltage_ac
        if v is None:
            return ('- - - -', self._LCD_DIM)
        color = self._LCD_DIGIT if st == 'ok' else self._LCD_WARN
        if v >= 1000.0:
            return (f'{v / 1000:.3f}', color)
        return (f'{v:.1f}', color)

    def _unit(self) -> str:
        if self._mode == 'resistance':
            return 'Ω'
        v = self._voltage
        if v is not None and v >= 1000.0:
            return 'kV'
        return 'V'
