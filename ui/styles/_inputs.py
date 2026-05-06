INPUTS_QSS = """QCheckBox,
QRadioButton {{
    color: {text_body};
    spacing: 8px;
    font-size: 13px;
}}

QCheckBox::indicator,
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator {{
    border-radius: 5px;
    border: 1px solid {border_strong};
    background: {bg_surface};
}}

QRadioButton::indicator {{
    border-radius: 9px;
    border: 1px solid {border_strong};
    background: {bg_surface};
}}

QCheckBox::indicator:checked,
QRadioButton::indicator:checked {{
    background: {primary};
    border-color: {primary};
}}

QCheckBox[cardToggle="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    font-weight: 700;
}}

QCheckBox[cardToggle="true"][tone="success"] {{
    background: #f4fbf6;
    color: {success};
    border-color: #ccebd8;
}}

QCheckBox[cardToggle="true"][tone="warning"] {{
    background: #fffaf2;
    color: {warning};
    border-color: #f8dfbf;
}}

QCheckBox[cardToggle="true"][tone="info"] {{
    background: #f6faff;
    color: #0369a1;
    border-color: #cfe7f5;
}}

QCheckBox[cardToggle="true"][tone="primary"] {{
    background: #f7faff;
    color: {primary};
    border-color: #d8e3f4;
}}

QLineEdit,
QComboBox,
QAbstractSpinBox {{
    background: {bg_surface};
    color: {text_main};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: {primary};
}}

QLineEdit:focus,
QComboBox:focus,
QAbstractSpinBox:focus {{
    border-color: {primary};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    selection-background-color: {primary_soft};
    selection-color: {primary};
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: #dbe4f0;
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: #93c5fd;
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 8px;
    border: 2px solid {bg_surface};
    background: {primary};
}}

QProgressBar {{
    min-height: 10px;
    background: #e7edf5;
    color: {text_muted};
    border: 1px solid {border};
    border-radius: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background: {primary};
    border-radius: 5px;
}}

QScrollBar:vertical {{
    width: 10px;
    background: transparent;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: #b4c2d4;
    border-radius: 5px;
    min-height: 28px;
}}

QScrollBar::handle:vertical:hover {{
    background: #90a4ba;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    height: 10px;
    background: transparent;
    margin: 2px;
}}

QScrollBar::handle:horizontal {{
    background: #b4c2d4;
    border-radius: 5px;
    min-width: 28px;
}}

QScrollBar::handle:horizontal:hover {{
    background: #90a4ba;
}}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0;
}}

QToolTip {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 8px;
}}

QMenu {{
    background: {bg_surface};
    color: {text_body};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 6px;
}}

QMenu::item {{
    padding: 8px 14px;
    border-radius: 8px;
}}

QMenu::item:selected {{
    background: {bg_hover};
    color: {text_main};
}}

"""
