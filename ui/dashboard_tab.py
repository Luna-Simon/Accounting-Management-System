"""
Dashboard Tab - Clean Apple-style overview with key metrics and recent activity.
"""

import tkinter as tk
from tkinter import ttk

import money

from .widgets import Table, col, Card


class DashboardTab(ttk.Frame):
    def __init__(self, parent, book, on_change):
        super().__init__(parent, padding=24)
        self.book = book
        self.on_change = on_change

        # Welcome header - clean and minimal
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 32))
        ttk.Label(header, text="Accounting Management System", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Overview of your financial data", style="Subtitle.TLabel").pack(anchor="w")

        # Key metrics cards - simplified
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", pady=(0, 24))
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        stats = [
            ("Accounts", "accounts"),
            ("Transactions", "entries"),
            ("Adjustments", "adjustments"),
            ("Net Income", "net_income"),
        ]
        self.stat_cards = {}
        for i, (label, key) in enumerate(stats):
            card = Card(stats_frame, title="")
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            stats_frame.columnconfigure(i, weight=1)
            
            ttk.Label(card, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
            
            var = tk.StringVar(value="0")
            self.stat_cards[key] = var
            ttk.Label(card, textvariable=var, style="CardValue.TLabel").pack(anchor="w")

        # Recent activity - simplified table
        recent_frame = Card(self, title="Recent Activity")
        recent_frame.pack(fill="both", expand=True)
        
        self.recent_table = Table(recent_frame, [
            col("Date", 120, "center"),
            col("Type", 110, "center"),
            col("Description", 400, stretch=True),
            col("Amount", 160, "e"),
        ], height=8)
        self.recent_table.pack(fill="both", expand=True)

    def refresh(self):
        # Update stats
        self.stat_cards["accounts"].set(str(len(self.book.accounts)))
        self.stat_cards["entries"].set(str(len(self.book.entries)))
        self.stat_cards["adjustments"].set(str(len(self.book.adjustments)))
        
        # Calculate net income
        from accounting import income_statement
        try:
            is_data = income_statement(self.book)
            net = is_data["net"]
            self.stat_cards["net_income"].set(money.fmt(net, False))
        except:
            self.stat_cards["net_income"].set("$0.00")

        # Update recent entries with capitalized descriptions
        self.recent_table.clear()
        all_entries = []
        for entry in self.book.entries:
            desc = entry["description"].strip()
            if desc:
                desc = desc[0].upper() + desc[1:] if len(desc) > 1 else desc.upper()
            total = sum(l["debit"] for l in entry["lines"])
            all_entries.append(("Transaction", entry["date"], desc, total))
        for entry in self.book.adjustments:
            desc = entry["description"].strip()
            if desc:
                desc = desc[0].upper() + desc[1:] if len(desc) > 1 else desc.upper()
            total = sum(l["debit"] for l in entry["lines"])
            all_entries.append(("Adjustment", entry["date"], desc, total))
        
        all_entries.sort(key=lambda x: x[1], reverse=True)
        for entry in all_entries[:10]:
            # entry: (type, date, description, amount)
            self.recent_table.add((
                entry[1],           # Date
                entry[0],           # Type
                entry[2],           # Description (capitalized)
                money.fmt(entry[3]), # Amount
            ))