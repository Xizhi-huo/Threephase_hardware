from dataclasses import dataclass, field

from PyQt5 import QtCore, QtGui, QtWidgets


_DEFAULT_POINTS = frozenset({7, 8, 10, 11})
_LEFT_SIGNAL_LABELS = {
    7: "KW-",
    8: "KW+",
    10: "KV+",
    11: "KV-",
}


@dataclass
class LoadShareCabinetState:
    gen1_points: set[int] = field(default_factory=lambda: set(_DEFAULT_POINTS))
    gen2_points: set[int] = field(default_factory=lambda: set(_DEFAULT_POINTS))

    def is_consistent(self) -> bool:
        return self.gen1_points == self.gen2_points

    def reset_defaults(self) -> None:
        self.gen1_points.clear()
        self.gen2_points.clear()
        self.gen1_points.update(_DEFAULT_POINTS)
        self.gen2_points.update(_DEFAULT_POINTS)


class _LoadShareCabinetWidget(QtWidgets.QWidget):
    pointsChanged = QtCore.pyqtSignal()

    _POINT_RADIUS = 6
    _LEFT_X = 90
    _RIGHT_X = 186
    _TOP_Y = 54
    _ROW_GAP = 17.2

    def __init__(self, title: str, points: set[int], parent=None):
        super().__init__(parent)
        self._title = title
        self._points = points
        self.setFixedSize(280, 520)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def _point_center(self, terminal_no: int) -> QtCore.QPointF:
        if 1 <= terminal_no <= 25:
            x = self._LEFT_X
            row = terminal_no - 1
        else:
            x = self._RIGHT_X
            row = terminal_no - 26
        return QtCore.QPointF(x, self._TOP_Y + row * self._ROW_GAP)

    def _hit_terminal(self, pos: QtCore.QPoint) -> int | None:
        for terminal_no in range(1, 51):
            center = self._point_center(terminal_no)
            dx = pos.x() - center.x()
            dy = pos.y() - center.y()
            if dx * dx + dy * dy <= self._POINT_RADIUS * self._POINT_RADIUS:
                return terminal_no
        return None

    def mousePressEvent(self, event):
        terminal_no = self._hit_terminal(event.pos())
        if terminal_no is None:
            return

        if terminal_no in self._points:
            self._points.remove(terminal_no)
        else:
            self._points.add(terminal_no)

        self.pointsChanged.emit()
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing)

        panel_rect = self.rect().adjusted(10, 10, -10, -10)
        qp.setPen(QtGui.QPen(QtGui.QColor("#111111"), 2))
        qp.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))
        qp.drawRoundedRect(panel_rect, 8, 8)

        title_font = QtGui.QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        qp.setFont(title_font)
        qp.setPen(QtGui.QPen(QtGui.QColor("#111111")))
        qp.drawText(QtCore.QRect(0, 18, self.width(), 20), QtCore.Qt.AlignCenter, self._title)

        label_font = QtGui.QFont()
        label_font.setPointSize(8)
        qp.setFont(label_font)

        for terminal_no in range(1, 51):
            center = self._point_center(terminal_no)

            qp.setPen(QtGui.QPen(QtGui.QColor("#111111"), 1.5))
            if terminal_no in self._points:
                qp.setBrush(QtGui.QBrush(QtGui.QColor("#111111")))
            else:
                qp.setBrush(QtGui.QBrush(QtGui.QColor("#ffffff")))

            qp.drawEllipse(center, self._POINT_RADIUS, self._POINT_RADIUS)

            if terminal_no <= 25:
                signal_label = _LEFT_SIGNAL_LABELS.get(terminal_no)
                if signal_label is not None:
                    signal_rect = QtCore.QRectF(center.x() - 70, center.y() - 8, 36, 16)
                    qp.drawText(
                        signal_rect,
                        QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter,
                        signal_label,
                    )

                text_rect = QtCore.QRectF(center.x() - 28, center.y() - 8, 18, 16)
                qp.drawText(text_rect, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter, str(terminal_no))
            else:
                text_rect = QtCore.QRectF(center.x() + 10, center.y() - 8, 24, 16)
                qp.drawText(text_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, str(terminal_no))

        qp.end()
