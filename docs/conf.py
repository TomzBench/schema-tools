from pathlib import Path

project = "Jsmn Tools"
copyright = "2025, Altronix"
author = "Altronix"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxext.opengraph",
    "sphinxcontrib.mermaid",
]

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = ["colon_fence"]

exclude_patterns = [
    "_build",
    # Included inline into index.md via {include}; not built as standalone pages.
    "how-it-works.md",
    "custom-render.md",
    "plugins.md",
    "bundle.md",
    "reference.md",
]

# Gracefully handle missing ai/local (gitignored, absent on fresh clone)
if not (Path(__file__).parent / "ai" / "local").is_dir():
    exclude_patterns.append("ai/local")

html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/logo.png"
templates_path = ["_templates"]

html_theme = "furo"
html_theme_options = {
    "light_css_variables": {
        # Altronix blue — matches the box face
        "color-brand-primary": "#0072CE",
        "color-brand-content": "#005DA6",
        # Sidebar: Altronix blue (mesh pattern applied via custom CSS)
        "color-sidebar-background": "#0072CE",
        "color-sidebar-background-border": "#005DA6",
        "color-sidebar-brand-text": "#FFFFFF",
        "color-sidebar-text": "#E0E8F0",
        "color-sidebar-link-text": "#E0E8F0",
        "color-sidebar-link-text--top-level": "#FFFFFF",
        "color-sidebar-item-background--hover": "rgba(255, 255, 255, 0.15)",
        "color-sidebar-item-expander-color": "#E0E8F0",
        "color-sidebar-item-expander-color--hover": "#FFFFFF",
        "color-sidebar-search-background": "rgba(255, 255, 255, 0.15)",
        "color-sidebar-search-border": "rgba(255, 255, 255, 0.25)",
        "color-sidebar-search-foreground": "#FFFFFF",
        "color-sidebar-search-icon": "#E0E8F0",
        # Content area — subtle cool tint to pair with blue sidebar
        "color-background-primary": "#F7F9FC",
        "color-background-secondary": "#EDF1F7",
        "color-background-hover": "#E4EAF2",
        "color-background-border": "#D0D9E4",
        "color-foreground-primary": "#1A2A3A",
        "color-foreground-secondary": "#3A4A5A",
        "color-foreground-border": "#C4CDD8",
        "color-code-background": "#EBF0F7",
        "color-code-foreground": "#1A2A3A",
        "color-highlight-on-target": "#D6E4F5",
        "color-admonition-background": "#E8EEF6",
    },
    "dark_css_variables": {
        # Altronix blue accents on dark navy
        "color-brand-primary": "#4DA6E8",
        "color-brand-content": "#5BB0EC",
        # Sidebar: deep navy — the box's bottom band
        "color-sidebar-background": "#0A0F1E",
        "color-sidebar-background-border": "#0A0F1E",
        "color-sidebar-brand-text": "#FFFFFF",
        "color-sidebar-text": "#8899B0",
        "color-sidebar-link-text": "#8899B0",
        "color-sidebar-link-text--top-level": "#C0D0E0",
        "color-sidebar-item-background--hover": "rgba(77, 166, 232, 0.12)",
        "color-sidebar-item-expander-color": "#8899B0",
        "color-sidebar-item-expander-color--hover": "#C0D0E0",
        "color-sidebar-search-background": "rgba(255, 255, 255, 0.05)",
        "color-sidebar-search-border": "rgba(255, 255, 255, 0.10)",
        "color-sidebar-search-foreground": "#C0D0E0",
        "color-sidebar-search-icon": "#8899B0",
        # Content area: dark blue-black, not neutral gray
        "color-background-primary": "#0E1525",
        "color-background-secondary": "#131C2E",
        "color-background-hover": "#1A2540",
        "color-background-border": "#1E2A42",
        "color-foreground-primary": "#D0DCE8",
        "color-foreground-secondary": "#8899B0",
        "color-foreground-border": "#253350",
        "color-code-background": "#111A2C",
        "color-code-foreground": "#C8D8E8",
        "color-highlight-on-target": "#1A2A4A",
        "color-admonition-background": "#131C2E",
    },
}
