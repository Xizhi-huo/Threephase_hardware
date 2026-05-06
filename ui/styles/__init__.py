"""
ui/styles/__init__.py
浅色主题的全局样式入口。

策略：
1. 以自定义 QSS 为主，确保当前项目可控演进。
2. 若运行环境安装了 qdarkstyle，则尝试加载其 light 基底后叠加本项目样式；
   若不可用，自动回退为纯自定义主题，不影响运行。
"""

from ._buttons import BUTTONS_QSS
from ._dialogs import DIALOGS_QSS
from ._inputs import INPUTS_QSS
from ._misc import MISC_QSS
from ._panels import PANELS_QSS
from ._theme_palette import LIGHT_THEME

_QSS_TEMPLATE = PANELS_QSS + DIALOGS_QSS + MISC_QSS + BUTTONS_QSS + INPUTS_QSS

APP_QSS = _QSS_TEMPLATE.format(**LIGHT_THEME)


def _load_qdarkstyle_base() -> str:
    try:
        import qdarkstyle
    except Exception:
        return ""

    try:
        from qdarkstyle.light.palette import LightPalette
        return qdarkstyle.load_stylesheet(qt_api="pyqt5", palette=LightPalette)
    except Exception:
        return ""


def build_app_stylesheet() -> str:
    base = _load_qdarkstyle_base()
    return f"{base}\n{APP_QSS}" if base else APP_QSS


def apply_app_theme(app) -> None:
    app.setStyleSheet(build_app_stylesheet())


__all__ = [
    "APP_QSS",
    "LIGHT_THEME",
    "apply_app_theme",
    "build_app_stylesheet",
]
