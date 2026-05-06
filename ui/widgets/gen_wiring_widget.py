from PyQt5 import QtWidgets, QtCore, QtGui


_PC = {'A': '#f59e0b', 'B': '#22c55e', 'C': '#ef4444'}
_PI = {'A': 0, 'B': 1, 'C': 2}


class GenWiringWidget(QtWidgets.QWidget):
    """发电机端子盒接线图：上方三个内部绕组圆（A/B/C 固定色），
    下方三个输出接线柱方块（U/V/W），连线根据 mapping 动态绘制。
    interactive=True 时支持点击两个节点互换接线。"""

    def __init__(self, mapping, interactive=False, parent=None):
        """mapping: dict {terminal('A'/'B'/'C'): actual_phase}"""
        super().__init__(parent)
        self.mapping = mapping
        self.interactive = interactive
        # _order[i] = 第 i 个接线柱（U/V/W）实际连接的绕组相
        phases = ['A', 'B', 'C']
        self._order = [mapping.get(p, p) for p in phases]
        self._selected = None   # (zone, raw_idx): zone='top'|'bot', raw_idx∈{0,1,2}
        self.setFixedSize(320, 250)
        if interactive:
            self.setCursor(QtCore.Qt.PointingHandCursor)

    def get_order(self):
        """返回当前 [ph_at_U, ph_at_V, ph_at_W] 列表（供修复时写入 pt_phase_orders）。"""
        return list(self._order)

    def _xs(self):
        return [int(self.width() * 0.22), int(self.width() * 0.50), int(self.width() * 0.78)]

    def _hit_test(self, pos):
        """返回 (zone, raw_idx) 或 None。top=绕组圆(idx=相序0-2), bot=接线柱(idx=柱0-2)。"""
        xs = self._xs(); r = 13
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - 64) <= r + 4:
                return ('top', i)
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - 186) <= r + 4:
                return ('bot', i)
        return None

    def _resolve_j(self, zone, raw_idx):
        """将点击 (zone, raw_idx) 转换为接线柱下标 j（0/1/2 对应 U/V/W）。"""
        if zone == 'bot':
            return raw_idx
        # top: raw_idx 是绕组序号 → 找到该绕组当前连接的接线柱
        ph = ['A', 'B', 'C'][raw_idx]
        return self._order.index(ph)

    def mousePressEvent(self, event):
        if not self.interactive:
            return
        hit = self._hit_test(event.pos())
        if hit is None:
            self._selected = None
            self.update()
            return
        if self._selected is None:
            self._selected = hit
            self.update()
            return
        # 第二次点击：计算两个接线柱下标并互换
        j1 = self._resolve_j(*self._selected)
        j2 = self._resolve_j(*hit)
        if j1 != j2:
            self._order[j1], self._order[j2] = self._order[j2], self._order[j1]
        self._selected = None
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        xs = self._xs()
        phases = ['A', 'B', 'C']
        term_labels = ['U', 'V', 'W']
        r = 13          # circle/square half-size
        y_src = 64      # 内部绕组圆心 y
        y_dst = 186     # 输出接线柱中心 y

        # 白色背景
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
        qp.drawRoundedRect(0, 0, w, self.height(), 6, 6)

        # 区域标签
        f7 = QtGui.QFont(); f7.setPointSize(8)
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, 8, w, 16), QtCore.Qt.AlignCenter, "── 内闭绕组 ──")
        qp.drawText(QtCore.QRect(0, y_dst + r + 24, w, 16),
                    QtCore.Qt.AlignCenter, "── 输出接线柱 ──")

        # ── 连线（先画，在圆下方）──
        for i in range(3):
            actual = self._order[i]
            sx = xs[_PI[actual]]   # 源：actual 相绕组的固定 x
            dx = xs[i]             # 目标：第 i 个接线柱 x
            c = QtGui.QColor(_PC[actual])
            pen = QtGui.QPen(c, 2.5, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(sx, y_src + r + 1, dx, y_dst - r - 1)

        f9b = QtGui.QFont(); f9b.setPointSize(10); f9b.setBold(True)

        # ── 内部绕组圆（A=黄/B=绿/C=红，位置固定）──
        for i, ph in enumerate(phases):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            # 选中高亮
            sel_top = (self._selected == ('top', i))
            border_c = QtGui.QColor('#1d4ed8') if sel_top else c.darker(130)
            border_w = 3.5 if sel_top else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(c))
            qp.drawEllipse(x - r, y_src - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#ffffff')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_src - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        # ── 输出接线柱方块（U/V/W，颜色跟随实际相）──
        for i in range(3):
            x = xs[i]
            actual = self._order[i]
            c = QtGui.QColor(_PC[actual])
            sel_bot = (self._selected == ('bot', i))
            border_c = QtGui.QColor('#1d4ed8') if sel_bot else QtGui.QColor('#475569')
            border_w = 3 if sel_bot else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#f0f4f8')))
            qp.drawRect(x - r, y_dst - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_dst - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, term_labels[i])
            # 实际相标注（接线柱下方）
            f8 = QtGui.QFont(); f8.setPointSize(9)
            qp.setFont(f8); qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x - 22, y_dst + r + 6, 44, 18),
                        QtCore.Qt.AlignCenter, f"({actual})")
        qp.end()


__all__ = ["GenWiringWidget"]
