"""
Depreciation Tab - Modern calculator with schedule preview.
"""

import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox, ttk

from depreciation import calculate_depreciation, calculate_depreciation_schedule, create_depreciation_entry
from .widgets import Table, col, Card


class DepreciationTab(ttk.Frame):
    def __init__(self, parent, book, on_change):
        super().__init__(parent, padding=16)
        self.book = book
        self.on_change = on_change
        self.current_asset = None

        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 16))
        ttk.Label(header, text="Depreciation Calculator", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Straight-line depreciation with automatic entry posting", style="Subtitle.TLabel").pack(side="left", padx=(12, 0))

        # Asset selection
        asset_card = Card(self, title="Select Asset")
        asset_card.pack(fill="x", pady=(0, 16))
        asset_card.columnconfigure(1, weight=1)
        
        ttk.Label(asset_card, text="Asset Account:").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self.asset_var = tk.StringVar()
        self.asset_combo = ttk.Combobox(asset_card, textvariable=self.asset_var, state="readonly", width=55)
        self.asset_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=8)
        self.asset_combo.bind("<<ComboboxSelected>>", self.on_asset_selected)
        
        ttk.Button(asset_card, text="Refresh", style="Ghost.TButton", command=self.refresh_assets).grid(row=0, column=2, pady=8)

        # Parameters
        params_card = Card(self, title="Depreciation Parameters")
        params_card.pack(fill="x", pady=(0, 16))
        for i in range(4):
            params_card.columnconfigure(i, weight=1)
        
        ttk.Label(params_card, text="Asset Cost:").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self.cost_var = tk.StringVar()
        ttk.Entry(params_card, textvariable=self.cost_var, state="readonly", width=18).grid(row=0, column=1, sticky="w", padx=(0, 16), pady=8)
        
        ttk.Label(params_card, text="Salvage %:").grid(row=0, column=2, sticky="w", padx=(0, 12), pady=8)
        self.salvage_var = tk.StringVar(value="5")
        ttk.Entry(params_card, textvariable=self.salvage_var, width=12).grid(row=0, column=3, sticky="w", pady=8)
        
        ttk.Label(params_card, text="Useful Life (years):").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)
        self.life_var = tk.StringVar(value="5")
        ttk.Entry(params_card, textvariable=self.life_var, width=12).grid(row=1, column=1, sticky="w", pady=8)
        
        ttk.Label(params_card, text="Method:").grid(row=1, column=2, sticky="w", padx=(0, 12), pady=8)
        self.method_var = tk.StringVar(value="Straight-Line")
        ttk.Combobox(params_card, textvariable=self.method_var, values=["Straight-Line"], state="readonly", width=18).grid(row=1, column=3, sticky="w", pady=8)
        
        calc_frame = ttk.Frame(params_card)
        calc_frame.grid(row=2, column=0, columnspan=4, pady=(12, 0))
        ttk.Button(calc_frame, text="Calculate", style="Accent.TButton", command=self.calculate).pack(side="left")
        ttk.Button(calc_frame, text="Clear", style="Ghost.TButton", command=self.clear_params).pack(side="left", padx=8)

        # Results
        results_card = Card(self, title="Calculated Depreciation")
        results_card.pack(fill="x", pady=(0, 16))
        for i in range(4):
            results_card.columnconfigure(i, weight=1)
        
        self.result_vars = {}
        results = [
            ("Depreciable Base", "depreciable_base"),
            ("Salvage Value", "salvage_value"),
            ("Annual Depreciation", "annual"),
            ("Monthly Depreciation", "monthly"),
        ]
        for i, (label, key) in enumerate(results):
            ttk.Label(results_card, text=label, style="Muted.TLabel").grid(row=0, column=i*2, sticky="w", padx=(0, 8), pady=8)
            var = tk.StringVar(value="$0.00")
            self.result_vars[key] = var
            ttk.Label(results_card, textvariable=var, style="CardValue.TLabel").grid(row=1, column=i*2, sticky="w", padx=(0, 8), pady=(0, 8))

        # Schedule preview
        schedule_card = Card(self, title="Monthly Schedule (First 12 Months)")
        schedule_card.pack(fill="both", expand=True, pady=(0, 16))
        
        self.schedule_table = Table(schedule_card, [
            col("Month", 70, "center"),
            col("Monthly Depreciation", 180, "e"),
            col("Accumulated", 160, "e"),
            col("Book Value", 160, "e"),
        ], height=6)
        self.schedule_table.pack(fill="both", expand=True)

        # Post entry
        post_card = Card(self, title="Record Depreciation Entry")
        post_card.pack(fill="x")
        post_card.columnconfigure(1, weight=1)
        
        ttk.Label(post_card, text="Date:").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(post_card, textvariable=self.date_var, width=15).grid(row=0, column=1, sticky="w", padx=(0, 16), pady=8)
        
        ttk.Label(post_card, text="Description:").grid(row=0, column=2, sticky="w", padx=(0, 12), pady=8)
        self.desc_var = tk.StringVar(value="Monthly depreciation")
        ttk.Entry(post_card, textvariable=self.desc_var).grid(row=0, column=3, sticky="ew", pady=8)
        
        ttk.Label(post_card, text="Accum. Depr. Account:").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)
        self.accum_var = tk.StringVar()
        self.accum_combo = ttk.Combobox(post_card, textvariable=self.accum_var, state="readonly", width=55)
        self.accum_combo.grid(row=1, column=1, columnspan=3, sticky="ew", pady=8)
        
        ttk.Label(post_card, text="Depreciation Expense Account:").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=8)
        self.expense_var = tk.StringVar()
        self.expense_combo = ttk.Combobox(post_card, textvariable=self.expense_var, state="readonly", width=55)
        self.expense_combo.grid(row=2, column=1, columnspan=3, sticky="ew", pady=8)
        
        btn_frame = ttk.Frame(post_card)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=(12, 0))
        ttk.Button(btn_frame, text="Post Single Month", style="Accent.TButton", command=self.post_entry).pack(side="left")
        ttk.Button(btn_frame, text="Post Full Year (12 Months)", style="Ghost.TButton", command=self.post_full_year).pack(side="left", padx=8)
    
    def refresh_assets(self):
        """Refresh the asset dropdown with Asset-type accounts."""
        assets = [a for a in self.book.accounts if a["type"] == "Asset" and a["normal"] == "Debit"]
        asset_labels = [f"{a['code']} — {a['name']}" for a in assets]
        self.asset_combo["values"] = asset_labels
        self.asset_lookup = {f"{a['code']} — {a['name']}": a for a in assets}
        
        # Also populate accumulated depreciation and expense accounts
        contra_assets = [a for a in self.book.accounts if a["type"] == "Asset" and a["normal"] == "Credit"]
        contra_labels = [f"{a['code']} — {a['name']}" for a in contra_assets]
        self.accum_combo["values"] = contra_labels
        
        expenses = [a for a in self.book.accounts if a["type"] == "Expense"]
        expense_labels = [f"{a['code']} — {a['name']}" for a in expenses]
        self.expense_combo["values"] = expense_labels
    
    def on_asset_selected(self, event=None):
        """Auto-fill cost when asset is selected."""
        label = self.asset_var.get()
        if label in self.asset_lookup:
            asset = self.asset_lookup[label]
            self.current_asset = asset
            cost = self.estimate_asset_cost(asset["code"])
            if cost > 0:
                self.cost_var.set(f"{cost:,.2f}")
    
    def estimate_asset_cost(self, asset_code):
        """Estimate asset cost from existing debit entries to this account."""
        total = 0
        for entry in self.book.entries:
            for line in entry["lines"]:
                if line["account"] == asset_code and line["debit"] > 0:
                    total += line["debit"]
        return total / 100.0
    
    def calculate(self):
        """Calculate depreciation based on inputs."""
        try:
            cost = float(self.cost_var.get().replace(",", ""))
            salvage_pct = float(self.salvage_var.get())
            life_years = int(self.life_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for cost, salvage %, and useful life.")
            return
        
        if cost <= 0:
            messagebox.showerror("Error", "Asset cost must be greater than zero.")
            return
        if life_years <= 0:
            messagebox.showerror("Error", "Useful life must be greater than zero.")
            return
        if salvage_pct < 0 or salvage_pct >= 100:
            messagebox.showerror("Error", "Salvage percentage must be between 0 and 100.")
            return
        
        result = calculate_depreciation(cost, salvage_pct, life_years)
        
        self.result_vars["depreciable_base"].set(f"${result['depreciable_base']:,.2f}")
        self.result_vars["salvage_value"].set(f"${result['salvage_value']:,.2f}")
        self.result_vars["annual"].set(f"${result['annual']:,.2f}")
        self.result_vars["monthly"].set(f"${result['monthly']:,.2f}")
        
        # Generate schedule
        schedule = calculate_depreciation_schedule(cost, salvage_pct, life_years, months=12)
        self.schedule_table.clear()
        for row in schedule:
            self.schedule_table.add((
                str(row["month"]),
                f"${row['depreciation']:,.2f}",
                f"${row['accumulated']:,.2f}",
                f"${row['book_value']:,.2f}",
            ))
    
    def clear_params(self):
        self.cost_var.set("")
        self.salvage_var.set("5")
        self.life_var.set("5")
        for var in self.result_vars.values():
            var.set("$0.00")
        self.schedule_table.clear()
    
    def post_entry(self):
        """Post a single monthly depreciation entry."""
        if not self.current_asset:
            messagebox.showerror("Error", "Please select an asset first.")
            return
        
        if not self.accum_var.get() or not self.expense_var.get():
            messagebox.showerror("Error", "Please select both accumulated depreciation and expense accounts.")
            return
        
        try:
            monthly = float(self.result_vars["monthly"].get().replace("$", "").replace(",", ""))
        except ValueError:
            messagebox.showerror("Error", "Please calculate depreciation first.")
            return
        
        if monthly <= 0:
            messagebox.showerror("Error", "No depreciation amount to post.")
            return
        
        accum_code = self.accum_var.get().split(" — ")[0]
        expense_code = self.expense_var.get().split(" — ")[0]
        date_val = self.date_var.get().strip()
        desc = self.desc_var.get().strip()
        
        entry = create_depreciation_entry(
            self.current_asset["code"],
            accum_code,
            expense_code,
            monthly,
            date_val,
            desc
        )
        
        try:
            self.book.save_entry("adjustments", entry)
            messagebox.showinfo("Success", "Depreciation entry posted to Adjustments.")
            self.on_change()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post entry: {e}")
    
    def post_full_year(self):
        """Post 12 monthly depreciation entries."""
        if not self.current_asset:
            messagebox.showerror("Error", "Please select an asset first.")
            return
        
        if not self.accum_var.get() or not self.expense_var.get():
            messagebox.showerror("Error", "Please select both accumulated depreciation and expense accounts.")
            return
        
        try:
            monthly = float(self.result_vars["monthly"].get().replace("$", "").replace(",", ""))
            cost = float(self.cost_var.get().replace(",", ""))
            salvage_pct = float(self.salvage_var.get())
            life_years = int(self.life_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please calculate depreciation first.")
            return
        
        if monthly <= 0:
            messagebox.showerror("Error", "No depreciation amount to post.")
            return
        
        accum_code = self.accum_var.get().split(" — ")[0]
        expense_code = self.expense_var.get().split(" — ")[0]
        base_date = self.date_var.get().strip()
        desc = self.desc_var.get().strip()
        
        try:
            base = datetime.strptime(base_date, "%Y-%m-%d")
            
            for month in range(12):
                entry_date = (base + timedelta(days=30*month)).strftime("%Y-%m-%d")
                entry = create_depreciation_entry(
                    self.current_asset["code"],
                    accum_code,
                    expense_code,
                    monthly,
                    entry_date,
                    f"{desc} — Month {month+1}"
                )
                self.book.save_entry("adjustments", entry)
            
            messagebox.showinfo("Success", "12 monthly depreciation entries posted to Adjustments.")
            self.on_change()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to post entries: {e}")
    
    def refresh(self):
        self.refresh_assets()