"""
Black minimal theme.
"""

from tkinter import font, ttk

BG = "#000000"
PANEL = "#111111"
FIELD = "#000000"
LINE = "#333333"
TEXT = "#ffffff"
TEXT_DIM = "#888888"
BUTTON_BG = "#1a1a1a"
BUTTON_HOVER = "#2a2a2a"
ACCENT = "#ffffff"
ACCENT_HOVER = "#cccccc"
ACCENT_TEXT = "#000000"
SELECT = "#ffffff"
ERROR = "#ff4444"
SUCCESS = "#44ff44"
WARNING = "#ffff44"

bold_font = None
face_name = None


def apply(root):
    global bold_font, face_name
    families = font.families()
    preferred = ["Segoe UI", "Arial", "Helvetica", "Verdana", "Tahoma"]
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

    style.configure(".",
                    background=BG, foreground=TEXT,
                    bordercolor=LINE, focuscolor=ACCENT,
                    troughcolor=PANEL, lightcolor=LINE, darkcolor=LINE,
                    font=(face_name, 10))
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=PANEL)

    style.configure("Muted.TLabel", foreground=TEXT_DIM, background=BG, font=(face_name, 9))
    style.configure("MutedCard.TLabel", foreground=TEXT_DIM, background=PANEL, font=(face_name, 9))
    style.configure("Error.TLabel", foreground=ERROR, background=BG, font=(face_name, 10))
    style.configure("Success.TLabel", foreground=SUCCESS, background=BG, font=(face_name, 10))
    style.configure("Warning.TLabel", foreground=WARNING, background=BG, font=(face_name, 10))

    style.configure("Title.TLabel", font=(face_name, 16, "bold"), foreground=TEXT, background=BG)
    style.configure("Subtitle.TLabel", font=(face_name, 11), foreground=TEXT_DIM, background=BG)
    style.configure("CardTitle.TLabel", font=(face_name, 11, "bold"), foreground=TEXT, background=PANEL)

    style.configure("TButton",
                    background=BUTTON_BG, foreground=TEXT,
                    bordercolor=LINE, relief="flat", padding=(12, 8),
                    font=(face_name, 10))
    style.map("TButton",
              background=[("active", BUTTON_HOVER), ("pressed", PANEL), ("disabled", "#333333")],
              foreground=[("active", TEXT), ("disabled", TEXT_DIM)],
              bordercolor=[("active", LINE), ("focus", ACCENT)])

    style.configure("Accent.TButton",
                    background=ACCENT, foreground=ACCENT_TEXT,
                    bordercolor=ACCENT, relief="flat", padding=(14, 10),
                    font=(face_name, 10, "bold"))
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", "#aaaaaa"), ("disabled", "#888888")],
              foreground=[("active", ACCENT_TEXT), ("disabled", "#555555")],
              bordercolor=[("active", ACCENT_HOVER), ("focus", ACCENT)])

    style.configure("Ghost.TButton",
                    background=PANEL, foreground=TEXT,
                    bordercolor=LINE, relief="flat", padding=(10, 6),
                    font=(face_name, 9))
    style.map("Ghost.TButton",
              background=[("active", BUTTON_HOVER), ("pressed", PANEL)],
              foreground=[("active", TEXT), ("disabled", TEXT_DIM)],
              bordercolor=[("active", ACCENT), ("focus", ACCENT)])

    style.configure("Danger.TButton",
                    background=PANEL, foreground=ERROR,
                    bordercolor=LINE, relief="flat", padding=(10, 6),
                    font=(face_name, 9))
    style.map("Danger.TButton",
              background=[("active", "#220000"), ("pressed", "#110000")],
              foreground=[("active", ERROR), ("disabled", TEXT_DIM)],
              bordercolor=[("active", ERROR), ("focus", ERROR)])

    for widget in ("TEntry", "TCombobox"):
        style.configure(widget,
                        fieldbackground=FIELD, foreground=TEXT, insertcolor=ACCENT,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=6,
                        selectbackground=SELECT, selectforeground=ACCENT_TEXT,
                        font=(face_name, 10))
        style.map(widget,
                  bordercolor=[("focus", ACCENT), ("!focus", LINE)],
                  lightcolor=[("focus", ACCENT)],
                  darkcolor=[("focus", ACCENT)])

    style.configure("TCombobox", arrowcolor=ACCENT, background=FIELD, bordercolor=LINE)
    style.map("TCombobox",
              fieldbackground=[("readonly", FIELD), ("!readonly", FIELD)],
              selectbackground=[("readonly", FIELD)],
              selectforeground=[("readonly", TEXT)],
              bordercolor=[("focus", ACCENT), ("!focus", LINE)],
              arrowcolor=[("focus", ACCENT), ("!focus", ACCENT)])

    style.configure("TRadiobutton", background=BG, foreground=TEXT,
                    font=(face_name, 10))
    style.map("TRadiobutton",
              background=[("active", BG)],
              foreground=[("active", TEXT)])

    style.configure("Treeview",
                    background=FIELD, fieldbackground=FIELD, foreground=TEXT,
                    rowheight=28, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                    font=(face_name, 10))
    style.map("Treeview",
              background=[("selected", SELECT)],
              foreground=[("selected", ACCENT_TEXT)])

    style.configure("Treeview.Heading",
                    background=PANEL, foreground=TEXT, relief="flat",
                    padding=(8, 10), lightcolor=PANEL, darkcolor=PANEL,
                    font=(face_name, 10, "bold"), borderwidth=0)
    style.map("Treeview.Heading",
              background=[("active", BUTTON_HOVER), ("pressed", LINE)])

    style.configure("Vertical.TScrollbar",
                    background=PANEL, troughcolor=BG,
                    bordercolor=BG, arrowcolor=TEXT_DIM, relief="flat",
                    gripcount=0, width=14)
    style.map("Vertical.TScrollbar",
              background=[("active", BUTTON_HOVER)])

    style.configure("Horizontal.TScrollbar",
                    background=PANEL, troughcolor=BG,
                    bordercolor=BG, arrowcolor=TEXT_DIM, relief="flat",
                    gripcount=0, width=14)

    style.configure("TNotebook", background=BG, borderwidth=0, tabposition="n", tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab",
                    background=PANEL, foreground=TEXT_DIM, padding=(20, 10),
                    lightcolor=PANEL, darkcolor=PANEL, bordercolor=LINE,
                    font=(face_name, 10, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", BG), ("active", BUTTON_HOVER)],
              foreground=[("selected", ACCENT), ("active", TEXT)],
              expand=[("selected", (0, 0, 0, 0))])

    style.configure("Card.TLabelframe", background=PANEL, foreground=TEXT,
                    bordercolor=LINE, relief="solid", borderwidth=1)
    style.configure("Card.TLabelframe.Label",
                    background=PANEL, foreground=TEXT,
                    font=(face_name, 10, "bold"))

    style.configure("TSeparator", background=LINE)


def menu_options():
    return {"background": PANEL, "foreground": TEXT, "activebackground": SELECT,
            "activeforeground": ACCENT_TEXT, "borderwidth": 0,
            "font": (face_name, 10), "relief": "flat"}
