DIALOGS_QSS = """QDialog[themedDialog="true"] {{
    background: {bg_panel};
}}

QFrame[dialogCard="true"],
QWidget[dialogCard="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 14px;
}}

QLabel[dialogKicker="true"] {{
    color: {warning};
    font-size: 11px;
    font-weight: 700;
}}

QLabel[dialogTitle="true"] {{
    color: {text_main};
    font-size: 26px;
    font-weight: 800;
}}

QLabel[dialogSection="true"] {{
    color: {text_main};
    font-size: 16px;
    font-weight: 700;
    padding-top: 4px;
}}

QLabel[dialogCaption="true"] {{
    color: {text_muted};
    font-size: 11px;
}}

"""
