"""Matplotlib configuration for UI plots."""

_CONFIGURED = False


def configure_matplotlib() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    import matplotlib

    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
    matplotlib.rcParams['axes.unicode_minus'] = False
    matplotlib.rcParams['text.antialiased'] = True
    matplotlib.rcParams['lines.antialiased'] = True
    matplotlib.rcParams['patch.antialiased'] = True
    matplotlib.rcParams['figure.dpi'] = 100
    matplotlib.rcParams['savefig.dpi'] = 150
    matplotlib.rcParams['font.size'] = 9
    matplotlib.rcParams['axes.titlesize'] = 11
    matplotlib.rcParams['axes.labelsize'] = 9
    _CONFIGURED = True
