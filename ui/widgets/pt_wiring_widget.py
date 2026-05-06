from PyQt5 import QtWidgets, QtCore, QtGui


_PC = {'A': '#f59e0b', 'B': '#22c55e', 'C': '#ef4444'}


def _normalize_polarity(polarity):
    values = list(polarity or [1, 1, 1])
    normalized = []
    for value in values[:3]:
        reversed_value = value is False or value in (-1, '-', 'reversed')
        normalized.append(-1 if reversed_value else 1)
    while len(normalized) < 3:
        normalized.append(1)
    return normalized


class PTWiringWidget(QtWidgets.QWidget):
    """PT 接线盒图：按逐级传播后的实际相别显示每一层端子颜色。

    下方输入电缆显示上游实际来相顺序；
    A1/B1/C1 显示一次侧传播后的实际相别；
    A2/B2/C2 显示二次侧传播后的实际相别；
    最上方测量端仅将二次侧当前结果垂直引出，不再额外重排为 ABC。
    """

    _Y_OUT   = 56
    _Y_SEC   = 176
    _Y_BOXT  = 224
    _Y_BOXB  = 344
    _Y_PRI   = 392
    _Y_CABLE = 496

    def __init__(self, pri_order, sec_order, pri_input_order=None,
                 sec_polarity=None, interactive_pri=False, interactive_sec=False,
                 interactive_polarity=False, parent=None):
        """pri_order/sec_order 为本级置换，pri_input_order 为上游实际来相顺序。"""
        super().__init__(parent)
        self._pri_order = list(pri_order)
        self._sec_order = list(sec_order)
        self._pri_input_order = list(pri_input_order or ['A', 'B', 'C'])
        self._sec_polarity = _normalize_polarity(sec_polarity)
        self.interactive_pri = interactive_pri
        self.interactive_sec = interactive_sec
        self.interactive_polarity = interactive_polarity
        self._sel_sec = None
        self._sel_pri = None
        self.setFixedSize(410, 560)
        if interactive_pri or interactive_sec or interactive_polarity:
            self.setCursor(QtCore.Qt.PointingHandCursor)

    def get_pri_order(self):
        return list(self._pri_order)

    def get_sec_order(self):
        return list(self._sec_order)

    def get_sec_polarity(self):
        return list(self._sec_polarity)

    def _primary_actual_order(self):
        labels = ('A', 'B', 'C')
        return [self._pri_input_order[labels.index(cable_label)] for cable_label in self._pri_order]

    def _secondary_actual_order(self):
        labels = ('A', 'B', 'C')
        primary_actual = self._primary_actual_order()
        return [primary_actual[labels.index(sec_label)] for sec_label in self._sec_order]

    def _xs(self):
        return [int(self.width() * 0.22), int(self.width() * 0.50), int(self.width() * 0.78)]

    def _hit_sec(self, pos):
        """若点击落在二次侧端子圆内，返回下标（0/1/2），否则返回 None。"""
        xs = self._xs(); r = 11
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - self._Y_SEC) <= r + 4:
                return i
        return None

    def _hit_pri(self, pos):
        xs = self._xs(); r = 11
        for i in range(3):
            if abs(pos.x() - xs[i]) <= r + 4 and abs(pos.y() - self._Y_PRI) <= r + 4:
                return i
        return None

    def _hit_sec_polarity(self, pos):
        xs = self._xs()
        for i, x in enumerate(xs):
            rect = QtCore.QRect(x - 15, self._Y_SEC - 42, 30, 18)
            if rect.adjusted(-3, -3, 3, 3).contains(pos):
                return i
        return None

    def mousePressEvent(self, event):
        if not (self.interactive_pri or self.interactive_sec or self.interactive_polarity):
            return
        polarity_hit = self._hit_sec_polarity(event.pos()) if self.interactive_polarity else None
        sec_hit = self._hit_sec(event.pos()) if self.interactive_sec else None
        pri_hit = self._hit_pri(event.pos()) if self.interactive_pri else None
        if polarity_hit is not None:
            self._sel_sec = None
            self._sel_pri = None
            self._sec_polarity[polarity_hit] *= -1
            self.update()
            return
        if sec_hit is not None:
            self._sel_pri = None
            if self._sel_sec is None:
                self._sel_sec = sec_hit
                self.update()
                return
            j1, j2 = self._sel_sec, sec_hit
            if j1 != j2:
                self._sec_order[j1], self._sec_order[j2] = self._sec_order[j2], self._sec_order[j1]
            self._sel_sec = None
            self.update()
            return
        # 第二次点击：互换两个二次侧端子的相
        if pri_hit is not None:
            self._sel_sec = None
            if self._sel_pri is None:
                self._sel_pri = pri_hit
                self.update()
                return
            j1, j2 = self._sel_pri, pri_hit
            if j1 != j2:
                self._pri_order[j1], self._pri_order[j2] = self._pri_order[j2], self._pri_order[j1]
            self._sel_pri = None
            self.update()
            return
        self._sel_sec = None
        self._sel_pri = None
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)
        w = self.width()
        xs = self._xs()
        pri_input = self._pri_input_order
        pri_actual = self._primary_actual_order()
        sec_actual = self._secondary_actual_order()
        r = 11   # 端子半径

        y_out   = self._Y_OUT
        y_sec   = self._Y_SEC
        y_boxt  = self._Y_BOXT
        y_boxb  = self._Y_BOXB
        y_pri   = self._Y_PRI
        y_cable = self._Y_CABLE

        # 白色背景
        qp.setPen(QtCore.Qt.NoPen)
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
        qp.drawRoundedRect(0, 0, w, self.height(), 6, 6)

        # 变压器铁芯盒（中间灰色虚线框）
        qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8'), 1.5, QtCore.Qt.DashLine))
        qp.setBrush(QtGui.QBrush(QtGui.QColor('#f0f9ff')))
        qp.drawRect(16, y_boxt, w - 32, y_boxb - y_boxt)
        f8 = QtGui.QFont(); f8.setPointSize(9)
        qp.setFont(f8); qp.setPen(QtGui.QPen(QtGui.QColor('#64748b')))
        ymid = (y_boxt + y_boxb) // 2
        qp.drawText(QtCore.QRect(0, ymid - 10, w, 20),
                    QtCore.Qt.AlignCenter, "⚡  变压器铁芯（黑盒）")

        f9b = QtGui.QFont(); f9b.setPointSize(10); f9b.setBold(True)
        f7  = QtGui.QFont(); f7.setPointSize(8)

        # ═══════════════════ 二次侧（上半部）═══════════════════

        # 测量端口圆：仅垂直引出二次侧当前实际结果
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        polarity_text = ''.join('+' if p > 0 else '-' for p in self._sec_polarity)
        qp.drawText(QtCore.QRect(0, 12, w, 18), QtCore.Qt.AlignCenter,
                    f"实际输出: {''.join(sec_actual)}    极性: {polarity_text}")
        for i, ph in enumerate(sec_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            qp.setPen(QtGui.QPen(c.darker(120), 1.5))
            qp.setBrush(QtGui.QBrush(c.lighter(140)))
            qp.drawEllipse(x - r, y_out - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(c.darker(140)))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_out - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        # 二次侧输出：从 A2/B2/C2 垂直引出当前实际相别
        for i, ph_out in enumerate(sec_actual):
            sx = xs[i]
            c  = QtGui.QColor(_PC[ph_out])
            pen = QtGui.QPen(c, 2.2, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(sx, y_sec - r - 1, sx, y_out + r + 1)

        # 二次侧端子圆（a2/b2/c2，颜色跟随输出相；选中时蓝边）
        sec_lbl = ['a2', 'b2', 'c2']
        for i, ph_out in enumerate(sec_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph_out])
            selected = (self._sel_sec == i)
            border_c = QtGui.QColor('#1d4ed8') if selected else c.darker(120)
            border_w = 3.5 if selected else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
            qp.drawEllipse(x - r, y_sec - r, 2 * r, 2 * r)
            f7b = QtGui.QFont(); f7b.setPointSize(8); f7b.setBold(True)
            qp.setFont(f7b); qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.drawText(QtCore.QRect(x - r, y_sec - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, sec_lbl[i])
            qp.setFont(f7)
            qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x + r + 6, y_sec - 9, 36, 18),
                        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, f"({ph_out})")
            pol = self._sec_polarity[i]
            pol_c = QtGui.QColor('#15803d' if pol > 0 else '#dc2626')
            pol_rect = QtCore.QRect(x - 15, y_sec - 42, 30, 18)
            qp.setPen(QtGui.QPen(pol_c.darker(115), 1.4))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#f0fdf4' if pol > 0 else '#fef2f2')))
            qp.drawRoundedRect(pol_rect, 3, 3)
            qp.setFont(f7b)
            qp.setPen(QtGui.QPen(pol_c.darker(130)))
            qp.drawText(pol_rect, QtCore.Qt.AlignCenter, '+' if pol > 0 else '-')

        qp.setFont(f7)
        qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, y_sec + r + 10, w, 16), QtCore.Qt.AlignCenter,
                    "── 二次侧测量端口 ──")

        # ═══════════════════ 一次侧（下半部）═══════════════════

        # 一次侧端子圆：显示一次侧端子处的实际相别
        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, y_pri - r - 26, w, 16), QtCore.Qt.AlignCenter,
                    f"一次侧结果: {''.join(pri_actual)}")
        pri_lbl = ['A1', 'B1', 'C1']
        for i, ph_in in enumerate(pri_actual):
            x = xs[i]; c = QtGui.QColor(_PC[ph_in])
            selected = (self._sel_pri == i)
            border_c = QtGui.QColor('#1d4ed8') if selected else c.darker(120)
            border_w = 3.5 if selected else 2
            qp.setPen(QtGui.QPen(border_c, border_w))
            qp.setBrush(QtGui.QBrush(QtGui.QColor('#ffffff')))
            qp.drawEllipse(x - r, y_pri - r, 2 * r, 2 * r)
            f7b = QtGui.QFont(); f7b.setPointSize(8); f7b.setBold(True)
            qp.setFont(f7b); qp.setPen(QtGui.QPen(QtGui.QColor('#1e293b')))
            qp.drawText(QtCore.QRect(x - r, y_pri - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, pri_lbl[i])
            qp.setFont(f7)
            qp.setPen(QtGui.QPen(c))
            qp.drawText(QtCore.QRect(x + r + 6, y_pri - 9, 36, 18),
                        QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, f"({ph_in})")

        # 一次侧交叉连线：从下方来相实际位置连到一次侧端子
        for i, ph_in in enumerate(pri_actual):
            src_x = xs[pri_input.index(ph_in)]
            dst_x = xs[i]
            c = QtGui.QColor(_PC[ph_in])
            pen = QtGui.QPen(c, 2.2, QtCore.Qt.SolidLine,
                             QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin)
            qp.setPen(pen)
            qp.drawLine(src_x, y_cable - r - 1, dst_x, y_pri + r + 1)

        # 输入电缆圆：继承上游实际来相顺序
        for i, ph in enumerate(pri_input):
            x = xs[i]; c = QtGui.QColor(_PC[ph])
            qp.setPen(QtGui.QPen(c.darker(120), 2))
            qp.setBrush(QtGui.QBrush(c))
            qp.drawEllipse(x - r, y_cable - r, 2 * r, 2 * r)
            qp.setPen(QtGui.QPen(QtGui.QColor('#ffffff')))
            qp.setFont(f9b)
            qp.drawText(QtCore.QRect(x - r, y_cable - r, 2 * r, 2 * r),
                        QtCore.Qt.AlignCenter, ph)

        qp.setFont(f7); qp.setPen(QtGui.QPen(QtGui.QColor('#94a3b8')))
        qp.drawText(QtCore.QRect(0, self.height() - 30, w, 16),
                    QtCore.Qt.AlignCenter, "── 一次侧输入电缆 ──")
        qp.drawText(QtCore.QRect(0, y_cable + r + 8, w, 16), QtCore.Qt.AlignCenter,
                    f"实际来相: {''.join(pri_input)}")
        qp.end()


__all__ = ["PTWiringWidget"]
