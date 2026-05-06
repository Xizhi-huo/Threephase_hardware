PANELS_QSS = """
QMainWindow {{
    background: {bg_app};
    color: {text_body};
}}

QWidget#appRoot,
QWidget[panelSurface="true"] {{
    background: {bg_app};
    color: {text_body};
    font-size: 13px;
}}

QWidget#controlSidebar,
QWidget#controlPage0,
QWidget#controlPage1 {{
    background: {bg_panel};
    color: {text_body};
    font-size: 13px;
}}

QWidget {{
    color: {text_body};
    selection-background-color: {primary};
    selection-color: #ffffff;
}}

QScrollArea,
QStackedWidget,
QFrame {{
    border: none;
    background: transparent;
}}

QScrollArea#controlSidebarScroll {{
    background: {bg_panel};
}}

QWidget#panelSwitcher,
QWidget[toolbarStrip="true"] {{
    background: transparent;
}}

QLabel {{
    background: transparent;
    color: {text_body};
}}

QLabel[sidebarTitle="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 12px 14px;
    color: {text_main};
    font-size: 16px;
    font-weight: 700;
}}

QLabel[mutedText="true"] {{
    color: {text_muted};
}}

QWidget[waveformPage="true"] {{
    background: {bg_app};
}}

QLabel[sectionTitle="true"] {{
    color: {text_main};
    font-size: 17px;
    font-weight: 800;
}}

QLabel[sectionCaption="true"] {{
    color: {text_muted};
    font-size: 12px;
}}

QFrame[metricCard="true"],
QFrame[plotCard="true"],
QFrame[wavePanelCard="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 14px;
}}

QFrame[metricCard="true"][tone="success"] {{
    border-color: #bbf7d0;
    background: #f8fdf9;
}}

QFrame[metricCard="true"][tone="warning"] {{
    border-color: #fed7aa;
    background: #fffdf8;
}}

QFrame[metricCard="true"][tone="danger"] {{
    border-color: #fecaca;
    background: #fff9f9;
}}

QFrame[metricCard="true"][tone="primary"],
QFrame[metricCard="true"][tone="info"] {{
    border-color: #d7e4ff;
    background: #fbfdff;
}}

QFrame[criteriaRow="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
}}

QLabel[metricTitle="true"] {{
    color: {text_muted};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.2px;
}}

QLabel[metricValue="true"] {{
    color: {text_main};
    font-size: 22px;
    font-weight: 800;
    min-height: 30px;
    padding: 2px 0;
}}

QLabel[metricValue="true"][tone="neutral"] {{
    color: {text_main};
}}

QLabel[metricValue="true"][tone="primary"],
QLabel[metricValue="true"][tone="info"] {{
    color: {primary};
}}

QLabel[metricValue="true"][tone="success"] {{
    color: {success};
}}

QLabel[metricValue="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[metricValue="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[metricCaption="true"] {{
    color: {text_muted};
    font-size: 10px;
}}

QLabel[syncStateHero="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    color: {text_main};
    font-size: 18px;
    font-weight: 800;
    min-height: 52px;
}}

QLabel[syncStateHero="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    border-color: {border};
    color: {text_muted};
}}

QLabel[syncStateHero="true"][tone="info"] {{
    background: {info_soft};
    border-color: #bfdbfe;
    color: {info};
}}

QLabel[syncStateHero="true"][tone="primary"] {{
    background: {primary_soft};
    border-color: #bfdbfe;
    color: {primary};
}}

QLabel[syncStateHero="true"][tone="success"] {{
    background: {success_soft};
    border-color: #bbf7d0;
    color: {success};
}}

QLabel[syncStateHero="true"][tone="warning"] {{
    background: {warning_soft};
    border-color: #fed7aa;
    color: {warning};
}}

QLabel[syncStateHero="true"][tone="danger"] {{
    background: {danger_soft};
    border-color: #fecaca;
    color: {danger};
}}

QLabel[stepHeader="true"] {{
    color: {text_main};
    font-size: 20px;
    font-weight: 800;
    padding: 2px 0 4px 0;
}}

QLabel[stepDescription="true"] {{
    color: {text_muted};
    font-size: 13px;
    padding: 0 0 4px 0;
}}

QLabel[badge="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 8px 12px;
    color: {text_body};
    font-size: 12px;
    font-weight: 700;
}}

QLabel[badge="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border-color: {border};
}}

QLabel[badge="true"][tone="primary"] {{
    background: {primary_soft};
    color: {primary};
    border-color: #bfdbfe;
}}

QLabel[badge="true"][tone="info"] {{
    background: {info_soft};
    color: {info};
    border-color: #bfdbfe;
}}

QLabel[badge="true"][tone="success"] {{
    background: {success_soft};
    color: {success};
    border-color: #bbf7d0;
}}

QLabel[badge="true"][tone="warning"] {{
    background: {warning_soft};
    color: {warning};
    border-color: #fed7aa;
}}

QLabel[badge="true"][tone="danger"] {{
    background: {danger_soft};
    color: {danger};
    border-color: #fecaca;
}}

QLabel[badge="true"][criteriaBadge="true"] {{
    border-radius: 9px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 600;
    min-height: 22px;
}}

QLabel[stepBanner="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 10px 12px;
    color: {text_body};
    font-size: 13px;
    font-weight: 700;
}}

QLabel[stepBanner="true"][tone="neutral"] {{
    background: {bg_surface_alt};
    color: {text_muted};
    border-color: {border};
}}

QLabel[stepBanner="true"][tone="primary"] {{
    background: {primary_soft};
    color: {primary};
    border-color: #bfdbfe;
}}

QLabel[stepBanner="true"][tone="info"] {{
    background: {info_soft};
    color: {info};
    border-color: #bfdbfe;
}}

QLabel[stepBanner="true"][tone="success"] {{
    background: {success_soft};
    color: {success};
    border-color: #bbf7d0;
}}

QLabel[stepBanner="true"][tone="warning"] {{
    background: {warning_soft};
    color: {warning};
    border-color: #fed7aa;
}}

QLabel[stepBanner="true"][tone="danger"] {{
    background: {danger_soft};
    color: {danger};
    border-color: #fecaca;
}}

QLabel[stepListItem="true"] {{
    color: {text_muted};
    font-size: 12px;
    padding: 1px 0;
}}

QLabel[stepListItem="true"][tone="success"] {{
    color: {success};
}}

QLabel[stepListItem="true"][tone="active"] {{
    color: {text_body};
}}

QLabel[stepListItem="true"][tone="muted"] {{
    color: {text_soft};
}}

QLabel[stepHint="true"] {{
    color: {text_muted};
    font-size: 12px;
}}

QLabel[stepStatus="true"] {{
    color: {text_body};
    font-size: 13px;
}}

QLabel[noteText="true"] {{
    color: {text_muted};
    font-size: 11px;
    padding: 1px 0;
}}

QLabel[noteText="true"][tone="warning"] {{
    color: {warning};
    font-weight: 700;
}}

QLabel[noteText="true"][tone="primary"] {{
    color: {primary};
    font-weight: 700;
}}

QLabel[noteText="true"][tone="danger"] {{
    color: {danger};
    font-weight: 700;
}}

QLabel[feedbackText="true"] {{
    color: {text_body};
    font-size: 12px;
    font-weight: 700;
    padding: 2px 0;
}}

QLabel[feedbackText="true"][tone="neutral"] {{
    color: {text_muted};
}}

QLabel[feedbackText="true"][tone="success"] {{
    color: {success};
}}

QLabel[feedbackText="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[feedbackText="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[feedbackText="true"][tone="info"] {{
    color: {info};
}}

QLabel[liveText="true"] {{
    color: {text_body};
    font-size: 15px;
}}

QLabel[liveText="true"][tone="neutral"] {{
    color: #444444;
}}

QLabel[liveText="true"][tone="muted"] {{
    color: #999999;
}}

QLabel[liveText="true"][tone="success"] {{
    color: {success};
}}

QLabel[liveText="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[liveText="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[liveText="true"][tone="info"] {{
    color: {info};
}}

QLabel[recordValue="true"] {{
    color: {text_muted};
    font-size: 14px;
}}

QLabel[recordValue="true"][tone="neutral"] {{
    color: {text_soft};
}}

QLabel[recordValue="true"][tone="success"] {{
    color: {success};
}}

QLabel[recordValue="true"][tone="warning"] {{
    color: {warning};
}}

QLabel[recordValue="true"][tone="danger"] {{
    color: {danger};
}}

QLabel[testPanelTitle="true"] {{
    color: {text_main};
    font-size: 16px;
    font-weight: 800;
}}

QWidget[testPanelRoot="true"] {{
    background: {bg_panel};
}}

QWidget[testPanelBar="true"] {{
    background: {bg_surface};
    border-bottom: 1px solid {border};
}}

QWidget[testPanelBar="true"][barRole="footer"] {{
    border-top: 1px solid {border};
    border-bottom: none;
}}

QWidget[stepPage="true"] {{
    background: {bg_app};
}}

QWidget[actionRow="true"] {{
    background: transparent;
}}

QWidget[inlineRow="true"] {{
    background: {bg_surface_alt};
    border: 1px solid {border};
    border-radius: 10px;
}}

QWidget[recordRow="true"] {{
    background: {bg_surface};
    border: 1px solid {border};
    border-radius: 10px;
}}

QLabel[valueChip="true"] {{
    background: {bg_hover};
    border: 1px solid {border};
    border-radius: 8px;
    color: {text_main};
    font-size: 11px;
    font-weight: 700;
    padding: 2px 6px;
}}

"""
