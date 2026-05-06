from __future__ import annotations

from PyQt5.QtCore import QObject, pyqtSignal


class ControllerSignals(QObject):
    """控制器到 UI 的轻量信号总线。"""

    step_changed = pyqtSignal(int, int)
    assessment_mode_changed = pyqtSignal(bool)
