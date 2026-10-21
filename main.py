import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from store import Ledger
from ui import theme
from ui.dashboard_tab import DashTab
from ui.trial_tab import TBTab
from ui.chart_tab import COATab
from ui.journal_tab import TxnTab


class MainWin(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Accounting Management System")
        self.geometry("1300x800")
        self.minsize(1000, 650)
        theme.apply(self)
        self.bk = Ledger()

        self.mk_menu()

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.screens = [
            ("Dashboard", DashTab(self.tabs, self.bk, self.redraw)),
            ("Trial Balance", TBTab(self.tabs, self.bk, self.redraw)),
            ("Chart of Accounts", COATab(self.tabs, self.bk, self.redraw)),
            ("Business Transactions", TxnTab(self.tabs, self.bk, "txns", self.redraw)),
            ("Adjustments", TxnTab(self.tabs, self.bk, "adjts", self.redraw)),
        ]

        for title, page in self.screens:
            self.tabs.add(page, text=title)

        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.redraw())
        self.redraw()

    def mk_menu(self):
        m = tk.Menu(self, **theme.menu_options())

        f = tk.Menu(m, tearoff=False, **theme.menu_options())
        f.add_command(label="Import Chart of Accounts…", command=self.imp_coa, accelerator="Ctrl+I")
        f.add_command(label="Load Starter Chart of Accounts", command=self.starter_coa)
        f.add_command(label="Business Information…", command=self.biz_info)
        f.add_command(label="Import Business Transactions…", command=lambda: self.imp_tab("txns"))
        f.add_command(label="Import Adjustments…", command=lambda: self.imp_tab("adjts"))
        f.add_separator()

        tpl = tk.Menu(f, tearoff=False, **theme.menu_options())
        tpl.add_command(label="Transaction Template (Simple)", command=lambda: self.mk_tpl("txns"))
        tpl.add_command(label="Chart of Accounts Template", command=lambda: self.mk_tpl("coa"))
        f.add_cascade(label="Export Template", menu=tpl)

        f.add_separator()
        f.add_command(label="Clear Transactions & Adjustments", command=self.clr_jnls)
        f.add_command(label="Clear All Data", command=self.wipe_all)
        f.add_separator()
        f.add_command(label="Export Current Tab…", command=self.exp, accelerator="Ctrl+E")
        f.add_separator()
        f.add_command(label="Exit", command=self.destroy, accelerator="Ctrl+Q")
        m.add_cascade(label="File", menu=f)

        h = tk.Menu(m, tearoff=False, **theme.menu_options())
        h.add_command(label="Excel Import Guide", command=self.xl_guide)
        h.add_command(label="Keyboard Shortcuts", command=self.keys)
        h.add_separator()
        h.add_command(label="About", command=self.about)
        m.add_cascade(label="Help", menu=h)

        self.configure(menu=m)

        self.bind_all("<Control-i>", lambda e: self.imp_coa())
        self.bind_all("<Control-e>", lambda e: self.exp())
        self.bind_all("<Control-q>", lambda e: self.destroy())

    def redraw(self):
        for _, pg in self.screens:
            if hasattr(pg, 'refresh'):
                pg.refresh()

    def imp_coa(self):
        path = filedialog.askopenfilename(
            title="Import Chart of Accounts",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not path:
            return
        try:
            self._imp_coa_xl(path)
            messagebox.showinfo("Success", "Chart of Accounts imported!")
            self.redraw()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def _imp_coa_xl(self, path):
        import pandas as pd
        df = pd.read_excel(path) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path)
        df.columns = df.columns.str.strip().str.lower()
        req = ['code', 'name', 'type', 'normal']
        missing = [c for c in req if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")
        for _, row in df.iterrows():
            code = str(row['code']).strip()
            if not code:
                continue
            if self.bk.get_acct(code):
                continue
            self.bk.add_acct({
                "code": code,
                "name": str(row['name']).strip(),
                "type": str(row['type']).strip(),
                "normal": str(row['normal']).strip(),
            })

    def starter_coa(self):
        starter = [
            {"code": "101", "name": "Cash", "type": "Asset", "normal": "Debit"},
            {"code": "102", "name": "Accounts Receivable", "type": "Asset", "normal": "Debit"},
            {"code": "103", "name": "Equipment", "type": "Asset", "normal": "Debit"},
            {"code": "104", "name": "Supplies", "type": "Asset", "normal": "Debit"},
            {"code": "105", "name": "Accumulated Depreciation", "type": "Asset", "normal": "Credit"},
            {"code": "201", "name": "Accounts Payable", "type": "Liability", "normal": "Credit"},
            {"code": "301", "name": "Owner's Capital", "type": "Equity", "normal": "Credit"},
            {"code": "302", "name": "Owner's Drawing", "type": "Equity", "normal": "Debit"},
            {"code": "401", "name": "Service Revenue", "type": "Revenue", "normal": "Credit"},
            {"code": "501", "name": "Rent Expense", "type": "Expense", "normal": "Debit"},
            {"code": "502", "name": "Salaries Expense", "type": "Expense", "normal": "Debit"},
            {"code": "503", "name": "Utilities Expense", "type": "Expense", "normal": "Debit"},
            {"code": "504", "name": "Depreciation Expense", "type": "Expense", "normal": "Debit"},
        ]
        added = skipped = 0
        for acct in starter:
            if self.bk.get_acct(acct["code"]):
                skipped += 1
                continue
            try:
                self.bk.add_acct(acct)
                added += 1
            except ValueError:
                skipped += 1
        messagebox.showinfo("Starter Chart of Accounts",
                            f"Added: {added}\nAlready existed (skipped): {skipped}")
        self.redraw()

    def biz_info(self):
        win = tk.Toplevel(self)
        win.title("Business Information")
        win.geometry("420x240")
        win.transient(self)
        win.configure(bg=theme.BG)
        win.grab_set()

        ttk.Label(win, text="Business Information", style="Title.TLabel").pack(pady=(16, 8))

        form = ttk.Frame(win)
        form.pack(padx=24, pady=8, fill="x")

        ttk.Label(form, text="Business name:").grid(row=0, column=0, sticky="w", pady=6)
        biz_var = tk.StringVar(value=self.bk.info.get("business", ""))
        ttk.Entry(form, textvariable=biz_var, width=34).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=6)

        ttk.Label(form, text="Reporting period:").grid(row=1, column=0, sticky="w", pady=6)
        period_var = tk.StringVar(value=self.bk.info.get("period", ""))
        ttk.Entry(form, textvariable=period_var, width=34).grid(row=1, column=1, sticky="w", padx=(12, 0), pady=6)
        period_hint = ttk.Label(form, text='Example: "January 2024" or "2024-01-01 to 2024-01-31"',
                                style="Muted.TLabel")
        period_hint.grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(0, 10))

        def save():
            self.bk.info["business"] = biz_var.get().strip()
            self.bk.info["period"] = period_var.get().strip()
            self.bk.commit()
            self.redraw()
            win.destroy()

        btns = ttk.Frame(win)
        btns.pack(pady=18)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left", padx=8)

    def clr_jnls(self):
        if messagebox.askyesno("Clear Data", "Delete all transactions and adjustments? Chart of Accounts is kept."):
            self.bk.clear_books()
            self.redraw()

    def wipe_all(self):
        if messagebox.askyesno("Clear All Data", "Delete everything including Chart of Accounts?"):
            self.bk.wipe()
            self.redraw()

    def exp(self):
        current = self.tabs.index("current")
        title, page = self.screens[current]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile=title.replace(" ", "_") + ".csv"
        )
        if path:
            page.table.export_csv(path)
            messagebox.showinfo("Exported", f"Data exported to {path}")

    def xl_guide(self):
        guide = """EXCEL IMPORT FORMAT GUIDE

CHART OF ACCOUNTS (required columns):
  code, name, type, normal
  Types: Asset, Liability, Equity, Revenue, Cost of Sales, Expense
  Normal: Debit or Credit

TRANSACTIONS / ADJUSTMENTS (required columns):
  date, description, account, debit, credit

  - Date: YYYY-MM-DD
  - Description: text (groups rows into same entry)
  - Account: account code
  - Debit: number (blank or 0 for credit lines)
  - Credit: number (blank or 0 for debit lines)

TIPS:
  • Column names are case-insensitive
  • Extra spaces in headers are ignored
  • Blank cells treated as 0
  • Rows grouped by Date + Description
  • Entries auto-balanced if needed"""

        win = tk.Toplevel(self)
        win.title("Excel Import Guide")
        win.geometry("650x550")
        win.transient(self)
        win.configure(bg=theme.BG)

        txt = tk.Text(win, wrap="word", padx=20, pady=20, font=("SF Mono", 10),
                      bg=theme.FIELD, fg=theme.TEXT, insertbackground=theme.ACCENT,
                      relief="flat", borderwidth=0)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", guide)
        txt.configure(state="disabled")

    def keys(self):
        shortcuts = """KEYBOARD SHORTCUTS

General:
  Ctrl+I    Import Chart of Accounts
  Ctrl+E    Export Current Tab
  Ctrl+Q    Quit

Navigation:
  Ctrl+Tab       Next Tab
  Ctrl+Shift+Tab Previous Tab

Table:
  Ctrl+A    Select All Rows
  Ctrl+C    Copy Selected Rows
  Double-Click  Edit Entry

Entry Form (Business Transactions / Adjustments):
  Tab          Next Field
  Ctrl+Enter   Post / Update the entry
  F5           Refresh account dropdowns
  Escape       Clear Form"""

        win = tk.Toplevel(self)
        win.title("Keyboard Shortcuts")
        win.geometry("450x400")
        win.transient(self)
        win.configure(bg=theme.BG)

        txt = tk.Text(win, wrap="word", padx=20, pady=20, font=("SF Mono", 10),
                      bg=theme.FIELD, fg=theme.TEXT, insertbackground=theme.ACCENT,
                      relief="flat", borderwidth=0)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", shortcuts)
        txt.configure(state="disabled")

    def about(self):
        messagebox.showinfo("About", "Accounting System v2.0\n\nDouble-entry bookkeeping\nwith Excel import.\n\nBuilt with Python & Tkinter")

    def imp_tab(self, kind):
        tab_index = 3 if kind == "txns" else 4
        self.tabs.select(tab_index)
        pg = self.screens[tab_index][1]
        if hasattr(pg, 'import_from_excel'):
            pg.import_from_excel()

    def mk_tpl(self, tpl_type):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=f"template_{tpl_type}.xlsx"
        )
        if not path:
            return
        try:
            self.bk.mk_tpl(path, tpl_type)
            messagebox.showinfo("Success", f"{tpl_type.title()} template exported!")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


if __name__ == "__main__":
    MainWin().mainloop()
