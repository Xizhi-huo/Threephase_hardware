MISC_QSS = """QTabWidget::pane {{
    border: 1px solid {border};
    background: {bg_surface};
    border-radius: 12px;
    top: -1px;
}}

QTabBar::tab {{
    background: {bg_surface_alt};
    color: {text_muted};
    border: 1px solid transparent;
    border-radius: 10px;
    padding: 10px 18px;
    margin-right: 6px;
    min-width: 148px;
    font-size: 13px;
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background: {bg_hover};
    color: {text_body};
}}

QTabBar::tab:selected {{
    background: {bg_surface};
    color: {primary};
    border-color: {border};
}}

QGroupBox {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 14px;
    color: {text_body};
    font-size: 13px;
    font-weight: 700;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    background: {bg_surface};
    color: {text_body};
}}

QGroupBox[cardTone="warning"] {{
    background: #fffdf7;
    border-color: #f6d7a5;
    color: {warning};
}}

QGroupBox[cardTone="warning"]::title {{
    background: #fffdf7;
    color: {warning};
}}

QGroupBox[cardTone="info"] {{
    background: #f8fbff;
    border-color: #d5e5ff;
}}

"""
