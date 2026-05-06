from PyQt5 import QtWidgets


def refresh_styles(*widgets):
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
    refresh_styles(widget)


def apply_step_shell(tab_outer, scroll, tab, header, desc, banner, *, banner_tone="info"):
    set_props(tab_outer, stepPage=True)
    scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
    scroll.setWidgetResizable(True)
    set_props(tab, stepPage=True)
    set_props(header, stepHeader=True)
    set_props(desc, stepDescription=True)
    set_props(banner, stepBanner=True, tone=banner_tone)


def apply_button_tone(owner, button, tone="primary", *, hero=False, secondary=False, muted=False):
    if hasattr(owner, "_apply_button_tone"):
        owner._apply_button_tone(
            button,
            tone,
            hero=hero,
            secondary=secondary,
            muted=muted,
        )
        return

    for prop in ("secondary", "success", "warning", "danger", "muted", "hero"):
        button.setProperty(prop, False)
    if secondary:
        button.setProperty("secondary", True)
    elif tone in ("success", "warning", "danger"):
        button.setProperty(tone, True)
    elif muted:
        button.setProperty("muted", True)
    button.setProperty("hero", hero)
    refresh_styles(button)


def apply_badge_tone(widget, tone="neutral"):
    widget.setProperty("badge", True)
    widget.setProperty("tone", tone)
    refresh_styles(widget)


def set_live_text(widget, tone="neutral"):
    set_props(widget, liveText=True, tone=tone)


def set_record_value(widget, tone="neutral"):
    set_props(widget, recordValue=True, tone=tone)


def set_step_item(widget, text, done, started):
    widget.setText(("√ " if done else "□ ") + text)
    set_props(widget, stepListItem=True, tone="success" if done else ("active" if started else "muted"))


def tone_from_color(color, fallback="neutral"):
    value = (color or "").lower()
    if value in {"#006400", "#008000", "#15803d", "green"}:
        return "success"
    if value in {"#cc6600", "#92400e", "#f59e0b", "#ff8800", "orange"}:
        return "warning"
    if value in {"red", "#dc2626", "#991b1b", "#b91c1c", "#cc0000"}:
        return "danger"
    if value in {"#264653", "#0369a1", "#0f766e", "#0000cc", "blue"}:
        return "info"
    if value in {"#444444", "#6b7280", "black", "gray", "grey"}:
        return fallback
    return fallback


def normalize_qt_color(color: str) -> str:
    color_map = {
        "gray": "#808080",
        "grey": "#808080",
        "green": "#008000",
        "red": "#cc0000",
        "orange": "#ff8800",
        "blue": "#0000cc",
        "black": "#000000",
        "white": "#ffffff",
        "k": "#000000",
    }
    return color_map.get((color or "").lower(), color or "#000000")
