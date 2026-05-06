from PyQt5 import QtCore, QtWidgets


def refresh_widget_styles(*widgets):
    for widget in widgets:
        if widget is None:
            continue
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()


def set_props(widget, **props):
    for key, value in props.items():
        widget.setProperty(key, value)


def apply_button_tone(button, tone="primary", *, hero=False, secondary=False, muted=False):
    for prop in ("secondary", "success", "warning", "danger", "muted", "hero"):
        button.setProperty(prop, False)
    if secondary:
        button.setProperty("secondary", True)
    elif tone in ("success", "warning", "danger"):
        button.setProperty(tone, True)
    elif muted:
        button.setProperty("muted", True)
    button.setProperty("hero", hero)
    refresh_widget_styles(button)


def apply_badge_tone(widget, tone="neutral"):
    widget.setProperty("badge", True)
    widget.setProperty("tone", tone)
    refresh_widget_styles(widget)


def apply_toggle_tone(widget, tone="primary"):
    widget.setProperty("cardToggle", True)
    widget.setProperty("tone", tone)
    refresh_widget_styles(widget)


def make_slider(vmin, vmax, init) -> QtWidgets.QSlider:
    slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
    slider.setRange(vmin, vmax)
    slider.setValue(init)
    return slider


def slider_row(slider, label) -> QtWidgets.QWidget:
    widget = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(slider, 1)
    layout.addWidget(label)
    return widget
