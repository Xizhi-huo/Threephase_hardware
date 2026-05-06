BUTTONS_QSS = """QPushButton {{
    background: {primary};
    color: #ffffff;
    border: 1px solid {primary};
    border-radius: 8px;
    padding: 7px 14px;
    min-height: 18px;
    font-size: 13px;
    font-weight: 700;
}}

QPushButton:hover {{
    background: {primary_hover};
    border-color: {primary_hover};
}}

QPushButton:pressed {{
    background: #1e3a8a;
    border-color: #1e3a8a;
}}

QPushButton:disabled {{
    background: #e8eef6;
    color: {text_soft};
    border-color: {border};
}}

QPushButton[hero="true"] {{
    min-height: 24px;
    font-size: 14px;
    border-radius: 10px;
    padding: 10px 16px;
}}

QPushButton[secondary="true"] {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border_strong};
}}

QPushButton[secondary="true"]:hover {{
    background: {bg_hover};
    border-color: #b6c5d9;
}}

QPushButton[success="true"] {{
    background: {success};
    border-color: {success};
}}

QPushButton[success="true"]:hover {{
    background: #166534;
    border-color: #166534;
}}

QPushButton[warning="true"] {{
    background: {warning};
    border-color: {warning};
}}

QPushButton[warning="true"]:hover {{
    background: #92400e;
    border-color: #92400e;
}}

QPushButton[danger="true"] {{
    background: {danger};
    border-color: {danger};
}}

QPushButton[danger="true"]:hover {{
    background: #b91c1c;
    border-color: #b91c1c;
}}

QPushButton[muted="true"] {{
    background: #e8eef6;
    color: {text_muted};
    border-color: {border};
}}

QPushButton[adminButton="true"] {{
    background: #7c3aed;
    color: #ffffff;
    border-color: #7c3aed;
}}

QPushButton[adminButton="true"]:hover {{
    background: #6d28d9;
    border-color: #6d28d9;
}}

QPushButton[adminButton="true"]:checked {{
    background: #4c1d95;
    border-color: #4c1d95;
}}

QRadioButton[inlineRadio="true"] {{
    background: transparent;
    color: {text_body};
    font-size: 12px;
}}

QLineEdit[compactInput="true"],
QSpinBox[compactInput="true"] {{
    min-height: 18px;
    font-size: 11px;
    padding: 3px 6px;
    border-radius: 8px;
}}

QLineEdit[compactInput="true"][readonlyTone="true"] {{
    background: #eef2f7;
    color: {text_muted};
}}

QProgressBar[metricBar="true"] {{
    background: #e2e8f0;
    border: none;
    border-radius: 6px;
}}

QProgressBar[metricBar="true"]::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #16a34a,
        stop:0.5 #d97706,
        stop:1 #dc2626
    );
    border-radius: 6px;
}}

QPushButton[segment="true"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px 10px;
}}

QPushButton[segment="true"]:hover {{
    background: {bg_hover};
    border-color: {border_strong};
    color: {text_body};
}}

QPushButton[segment="true"]:checked {{
    background: {primary};
    color: #ffffff;
    border-color: {primary};
}}

QPushButton[segment="true"][segmentTone="warning"]:checked {{
    background: {warning};
    border-color: {warning};
}}

QPushButton[segment="true"][segmentTone="danger"]:checked {{
    background: {danger};
    border-color: {danger};
}}

"""
