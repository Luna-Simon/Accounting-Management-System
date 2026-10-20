"""
Worksheet Tab - Modern 10-column worksheet.
"""

from tkinter import ttk

import accounting
import money

from .widgets import Table, col, Card

HEADINGS = ("TB Debit", "TB Credit", "Adj Debit", "Adj Credit", "Adj Debit",
            "Adj Credit", "IS Debit", "IS Credit", "BS Debit", "BS Credit")


class WorksheetTab(ttk.Frame):
    def __init__(self, parent, book):
        super().__init__(parent, padding=16)
        self.book = book
        
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Worksheet", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="10-column worksheet: Trial Balance → Adjustments → Adjusted → Financial Statements", style="Subtitle.TLabel").pack(side="left", padx=(12, 0))

        table_card = Card(self, title="")
        table_card.pack(fill="both", expand=True)
        
        columns = [col("Account", 220, stretch=True)] + [col(title, 120, "e") for title in HEADINGS]
        self.table = Table(table_card, columns)
        self.table.pack(fill="both", expand=True)

    def refresh(self):
        rows = accounting.worksheet(self.book)
        totals, net, final = accounting.worksheet_summary(rows)
        self.table.clear()
        for account, *amounts in rows:
            self.table.add((account["name"], *(money.fmt(value) for value in amounts)))
        self.table.add(("Totals", *(money.fmt(value, False) for value in totals)), ("total",))
        cells = [""] * 10
        if net >= 0:
            cells[6] = cells[9] = money.fmt(net, False)
        else:
            cells[7] = cells[8] = money.fmt(-net, False)
        self.table.add(("Net Income" if net >= 0 else "Net Loss", *cells))
        self.table.add(("", *(money.fmt(value, False) for value in final)), ("total",))