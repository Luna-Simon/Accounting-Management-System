"""
Dashboard Tab - Modern Apple-style overview with stat cards and quick actions.
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

        # Welcome header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 32))
        ttk.Label(header, text="Accounting System", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="Record transactions, manage accounts, and generate financial statements", style="Subtitle.TLabel").pack(anchor="w")

        # Quick stats cards
        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill="x", pady=(0, 24))
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        stats = [
            ("Accounts", "accounts", "📊"),
            ("Transactions", "entries", "📝"),
            ("Adjustments", "adjustments", "⚙️"),
            ("Net Income", "net_income", "💰"),
        ]
        self.stat_cards = {}
        for i, (label, key, icon) in enumerate(stats):
            card = Card(stats_frame, title="")
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 12, 0))
            stats_frame.columnconfigure(i, weight=1)
            
            icon_lbl = ttk.Label(card, text=icon, font=("Segoe UI", 24))
            icon_lbl.pack(anchor="w")
            ttk.Label(card, text=label, style="Muted.TLabel").pack(anchor="w", pady=(4, 8))
            
            var = tk.StringVar(value="0")
            self.stat_cards[key] = var
            ttk.Label(card, textvariable=var, style="CardValue.TLabel").pack(anchor="w")

        # Quick actions
        actions_frame = Card(self, title="Quick Actions")
        actions_frame.pack(fill="x", pady=(0, 24))
        for i in range(3):
            actions_frame.columnconfigure(i, weight=1)

        actions = [
            ("Add Account", "Chart of Accounts", 1),
            ("Record Transaction", "Business Transactions", 2),
            ("Record Adjustment", "Adjustments", 4),
            ("Calculate Depreciation", "Depreciation", 5),
            ("View Trial Balance", "Trial Balance", 3),
            ("View Income Statement", "Income Statement", 7),
        ]
        
        for i, (btn_text, desc, tab_idx) in enumerate(actions):
            row = i // 3
            col_idx = i % 3
            btn_frame = ttk.Frame(actions_frame)
            btn_frame.grid(row=row, column=col_idx, padx=8, pady=8, sticky="ew")
            actions_frame.columnconfigure(col_idx, weight=1)
            
            ttk.Button(btn_frame, text=btn_text, style="Accent.TButton",
                       command=lambda t=tab_idx: self.quick_action(t)).pack(fill="x")
            ttk.Label(btn_frame, text=desc, style="Muted.TLabel").pack(pady=(4, 0))

        # Recent entries preview
        recent_frame = Card(self, title="Recent Entries")
        recent_frame.pack(fill="both", expand=True)
        
        self.recent_table = Table(recent_frame, [
            col("Type", 110, "center"),
            col("Date", 110, "center"),
            col("Description", 350, stretch=True),
            col("Debit", 140, "e"),
            col("Credit", 140, "e"),
        ], height=6)
        self.recent_table.pack(fill="both", expand=True)

    def quick_action(self, tab_index):
        """Navigate to the appropriate tab."""
        if hasattr(self.master, 'master') and hasattr(self.master.master, 'tabs'):
            notebook = self.master.master.tabs
            notebook.select(tab_index)

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

        # Update recent entries
        self.recent_table.clear()
        all_entries = []
        for entry in self.book.entries:
            all_entries.append(("Transaction", entry["date"], entry["description"], 
                              sum(l["debit"] for l in entry["lines"]),
                              sum(l["credit"] for l in entry["lines"])))
        for entry in self.book.adjustments:
            all_entries.append(("Adjustment", entry["date"], entry["description"],
                              sum(l["debit"] for l in entry["lines"]),
                              sum(l["credit"] for l in entry["lines"])))
        
        all_entries.sort(key=lambda x: x[1], reverse=True)
        for entry in all_entries[:10]:
            tags = ("debit",) if entry[3] > 0 else ("credit",) if entry[4] > 0 else ()
            self.recent_table.add((
                entry[0],
                entry[1],
                entry[2],
                money.fmt(entry[3]),
                money.fmt(entry[4]),
            ), tags)