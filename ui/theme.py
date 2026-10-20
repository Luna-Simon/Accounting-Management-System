from tkinter import font, ttk

# Apple-inspired dark theme
BG = "#1d1d1f"
PANEL = "#2c2c2e"
FIELD = "#1d1d1f"
LINE = "#3a3a3c"
TEXT = "#f5f5f7"
MUTED = "#8e8e93"
BUTTON_BG = "#2c2c2e"
BUTTON_HOVER = "#3a3a3c"
ACCENT = "#0071e3"
ACCENT_HOVER = "#0077ed"
ACCENT_TEXT = "#ffffff"
SELECT = "#0071e3"
ERROR = "#ff453a"
SUCCESS = "#30d158"
WARNING = "#ff9f0a"

bold_font = None


def apply(root):
    global bold_font
    families = font.families()
    preferred = ["SF Pro Display", "Segoe UI", "Inter", "Roboto", "Helvetica Neue", "Helvetica", "Arial"]
    face_name = next((f for f in preferred if f in families), "TkDefaultFont")
    
    for name in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont"):
        face = font.nametofont(name)
        face.configure(size=10, family=face_name)
    bold_font = font.nametofont("TkDefaultFont").copy()
    bold_font.configure(weight="bold", size=10)

    root.configure(background=BG)
    root.option_add("*TCombobox*Listbox.background", FIELD)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_TEXT)
    root.option_add("*TCombobox*Listbox.font", face_name)

    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Base
    style.configure(".", background=BG, foreground=TEXT, bordercolor=LINE, focuscolor=ACCENT,
                    troughcolor=PANEL, lightcolor=LINE, darkcolor=LINE, font=(face_name, 10))
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Error.TLabel", foreground=ERROR)
    style.configure("Success.TLabel", foreground=SUCCESS)
    style.configure("Title.TLabel", font=(face_name, 20, "bold"), foreground=TEXT)
    style.configure("Subtitle.TLabel", font=(face_name, 12), foreground=MUTED)
    style.configure("CardTitle.TLabel", font=(face_name, 11, "bold"), foreground=TEXT)
    style.configure("CardValue.TLabel", font=(face_name, 24, "bold"), foreground=TEXT)

    # Buttons - Fixed visibility
    style.configure("TButton", background=BUTTON_BG, foreground=TEXT,
                    bordercolor=LINE, relief="flat", padding=(16, 8),
                    font=(face_name, 10))
    style.map("TButton",
              background=[("active", BUTTON_HOVER), ("pressed", LINE)],
              foreground=[("active", TEXT), ("disabled", MUTED)],
              bordercolor=[("active", LINE), ("focus", ACCENT)])

    style.configure("Accent.TButton", background=ACCENT, foreground=ACCENT_TEXT,
                    bordercolor=ACCENT, relief="flat", padding=(16, 8),
                    font=(face_name, 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", "#005bb5"), ("disabled", "#4a90d9")],
              foreground=[("active", ACCENT_TEXT), ("disabled", ACCENT_TEXT)])

    style.configure("Ghost.TButton", background=PANEL, foreground=ACCENT,
                    bordercolor=LINE, relief="flat", padding=(12, 6),
                    font=(face_name, 10))
    style.map("Ghost.TButton",
              background=[("active", ACCENT), ("pressed", "#005bb5")],
              foreground=[("active", ACCENT_TEXT), ("disabled", MUTED)],
              bordercolor=[("active", ACCENT), ("focus", ACCENT)])

    style.configure("Danger.TButton", background=PANEL, foreground=ERROR,
                    bordercolor=LINE, relief="flat", padding=(12, 6),
                    font=(face_name, 10))
    style.map("Danger.TButton",
              background=[("active", ERROR), ("pressed", "#cc372c")],
              foreground=[("active", ACCENT_TEXT), ("disabled", MUTED)],
              bordercolor=[("active", ERROR), ("focus", ERROR)])

    # Entries & Comboboxes
    for widget in ("TEntry", "TCombobox"):
        style.configure(widget, fieldbackground=FIELD, foreground=TEXT, insertcolor=ACCENT,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=8,
                        selectbackground=SELECT, selectforeground=ACCENT_TEXT,
                        font=(face_name, 10))
        style.map(widget,
                  bordercolor=[("focus", ACCENT)],
                  lightcolor=[("focus", ACCENT)],
                  darkcolor=[("focus", ACCENT)])

    style.configure("TCombobox", arrowcolor=MUTED, background=BUTTON_BG)
    style.map("TCombobox",
              fieldbackground=[("readonly", FIELD)],
              selectbackground=[("readonly", FIELD)],
              selectforeground=[("readonly", TEXT)])

    # Radio buttons
    style.configure("TRadiobutton", background=BG, foreground=TEXT, indicatorcolor=FIELD,
                    font=(face_name, 10))
    style.map("TRadiobutton",
              background=[("active", BG)],
              indicatorcolor=[("selected", ACCENT)])

    # Treeview - Excel/Sheets style
    style.configure("Treeview", background=BG, fieldbackground=BG, foreground=TEXT, rowheight=32,
                    bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                    font=(face_name, 10))
    style.map("Treeview",
              background=[("selected", SELECT)],
              foreground=[("selected", ACCENT_TEXT)])

    style.configure("Treeview.Heading", background=PANEL, foreground=TEXT, relief="flat",
                    padding=(12, 10), lightcolor=PANEL, darkcolor=PANEL,
                    font=(face_name, 10, "bold"), borderwidth=0)
    style.map("Treeview.Heading",
              background=[("active", BUTTON_HOVER), ("pressed", LINE)])

    # Scrollbars - thin, Apple style
    style.configure("Vertical.TScrollbar", background=BG, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED, relief="flat",
                    gripcount=0, width=8)
    style.map("Vertical.TScrollbar",
              background=[("active", LINE), ("!active", BG)])

    style.configure("Horizontal.TScrollbar", background=BG, troughcolor=BG,
                    bordercolor=BG, arrowcolor=MUTED, relief="flat",
                    gripcount=0, width=8)

    # Notebook - Horizontal tabs at top (better fit for accounting apps)
    style.configure("TNotebook", background=BG, borderwidth=0, tabposition="n", tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(20, 10),
                    lightcolor=PANEL, darkcolor=PANEL, bordercolor=LINE,
                    font=(face_name, 11))
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", BUTTON_HOVER)],
              foreground=[("selected", TEXT), ("active", TEXT)],
              expand=[("selected", (0, 0, 0, 0))])

    # Labelframe - card style
    style.configure("Card.TLabelframe", background=BG, foreground=TEXT,
                    bordercolor=LINE, relief="solid", borderwidth=1)
    style.configure("Card.TLabelframe.Label", background=BG, foreground=TEXT,
                    font=(face_name, 11, "bold"))

    # Separator
    style.configure("TSeparator", background=LINE)


def menu_options():
    return {"background": PANEL, "foreground": TEXT, "activebackground": SELECT,
            "activeforeground": ACCENT_TEXT, "borderwidth": 0, "font": ("SF Pro Display", 10)}