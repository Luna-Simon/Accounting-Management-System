import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from store import Book
from ui import theme
from ui.dashboard_tab import DashboardTab
from ui.trial_tab import TrialTab
from ui.chart_tab import ChartTab
from ui.journal_tab import JournalTab


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Accounting Management System")
        self.geometry("1300x800")
        self.minsize(1000, 650)
        theme.apply(self)
        self.book = Book()

        # Menu bar
        self.build_menu()

        # Notebook with tabs
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.pages = [
            ("Dashboard", DashboardTab(self.tabs, self.book, self.refresh)),
            ("Trial Balance", TrialTab(self.tabs, self.book, self.refresh)),
            ("Chart of Accounts", ChartTab(self.tabs, self.book, self.refresh)),
            ("Business Transactions", JournalTab(self.tabs, self.book, "entries", self.refresh)),
            ("Adjustments", JournalTab(self.tabs, self.book, "adjustments", self.refresh)),
        ]

        for title, page in self.pages:
            self.tabs.add(page, text=title)

        self.refresh()

    def build_menu(self):
        menu = tk.Menu(self, **theme.menu_options())
        
        file_menu = tk.Menu(menu, tearoff=False, **theme.menu_options())
        file_menu.add_command(label="Import Chart of Accounts…", command=self.import_coa, accelerator="Ctrl+I")
        file_menu.add_command(label="Import Business Transactions…", command=lambda: self.import_to_tab("entries"))
        file_menu.add_command(label="Import Adjustments…", command=lambda: self.import_to_tab("adjustments"))
        file_menu.add_separator()
        
        template_menu = tk.Menu(file_menu, tearoff=False, **theme.menu_options())
        template_menu.add_command(label="Transaction Template (Simple)", command=lambda: self.export_template("entries"))
        template_menu.add_command(label="Chart of Accounts Template", command=lambda: self.export_template("coa"))
        file_menu.add_cascade(label="Export Template", menu=template_menu)
        
        file_menu.add_separator()
        file_menu.add_command(label="Clear Transactions & Adjustments", command=self.clear_journals)
        file_menu.add_command(label="Clear All Data", command=self.clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="Export Current Tab…", command=self.export, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy, accelerator="Ctrl+Q")
        menu.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menu, tearoff=False, **theme.menu_options())
        help_menu.add_command(label="Excel Import Guide", command=self.show_excel_guide)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)

        self.configure(menu=menu)

        # Keyboard shortcuts
        self.bind_all("<Control-i>", lambda e: self.import_coa())
        self.bind_all("<Control-e>", lambda e: self.export())
        self.bind_all("<Control-q>", lambda e: self.destroy())

    def refresh(self):
        for _, page in self.pages:
            if hasattr(page, 'refresh'):
                page.refresh()

    def import_coa(self):
        path = filedialog.askopenfilename(
            title="Import Chart of Accounts",
            filetypes=[("Excel Files", "*.xlsx *.xls"), ("CSV Files", "*.csv")]
        )
        if not path:
            return
        try:
            self._import_coa_excel(path)
            messagebox.showinfo("Success", "Chart of Accounts imported!")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Import Failed", str(e))

    def _import_coa_excel(self, path):
        import pandas as pd
        df = pd.read_excel(path) if path.endswith(('.xlsx', '.xls')) else pd.read_csv(path)
        df.columns = df.columns.str.strip().str.lower()
        
        required = ['code', 'name', 'type', 'normal']
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")
        
        for _, row in df.iterrows():
            code = str(row['code']).strip()
            if not code:
                continue
            if self.book.find(code):
                continue
            self.book.add_account({
                "code": code,
                "name": str(row['name']).strip(),
                "type": str(row['type']).strip(),
                "normal": str(row['normal']).strip(),
            })

    def clear_journals(self):
        if messagebox.askyesno("Clear Data", "Delete all transactions and adjustments? Chart of Accounts is kept."):
            self.book.clear_journals()
            self.refresh()

    def clear_all(self):
        if messagebox.askyesno("Clear All Data", "Delete everything including Chart of Accounts?"):
            self.book.clear_all()
            self.refresh()

    def export(self):
        current = self.tabs.index("current")
        title, page = self.pages[current]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv")],
            initialfile=title.replace(" ", "_") + ".csv"
        )
        if path:
            page.table.export_csv(path)
            messagebox.showinfo("Exported", f"Data exported to {path}")

    def show_excel_guide(self):
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
  
  Example:
  Date        | Description       | Account | Debit  | Credit
  2024-01-15  | Office Supplies   | 120     | 500    | 
  2024-01-15  | Office Supplies   | 510     |        | 500

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

    def show_shortcuts(self):
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

Entry Form:
  Tab          Next Field
  Enter        Next Line / Post (when focused)
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

    def show_about(self):
        messagebox.showinfo("About", "Accounting System v2.0\n\nModern double-entry bookkeeping\nwith Excel import and depreciation calculator.\n\nBuilt with Python & Tkinter")

    def import_to_tab(self, kind):
        """Switch to tab and trigger import."""
        tab_index = 3 if kind == "entries" else 4
        self.tabs.select(tab_index)
        page = self.pages[tab_index][1]
        if hasattr(page, 'import_from_excel'):
            page.import_from_excel()

    def export_template(self, template_type):
        """Export an Excel template for import."""
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            initialfile=f"template_{template_type}.xlsx"
        )
        if not path:
            return
        try:
            self.book.export_template(path, template_type)
            messagebox.showinfo("Success", f"{template_type.title()} template exported!")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


if __name__ == "__main__":
    App().mainloop()