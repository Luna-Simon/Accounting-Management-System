import json
import sqlite3
import re
from datetime import date, datetime
from pathlib import Path
from contextlib import contextmanager

import pandas as pd

from logic import balance_journal_rows, clean_float, scale_money

PATH = Path(__file__).with_name("accounting.db")

# Standardized account name to code mapping for XYZ Laundry Shop (and similar formats)
# This ensures COA import and GL import use the SAME codes
XYZ_ACCOUNT_CODES = {
    'cash': '101',
    'accounts receivable': '102',
    'furniture & fixtures': '103',
    'furniture and fixtures': '103',  # variation
    'laundry equipment': '103',
    'laundy equipment': '103',  # typo in source
    'laundry supplies': '104',
    'laundy supplies': '104',  # typo in source
    'accounts payable': '201',
    'utilities payable - electricity': '211',
    'utilities payable - water': '212',
    'utilites payable - electricity': '211',  # typo in source
    'utilites payable - water': '212',  # typo in source
    'utilties payable - electricity': '211',  # typo in source (one L)
    'utilties payable - water': '212',  # typo in source (one L)
    'mav, capital': '301',
    'mav, drawing': '302',
    'service revenue': '401',
    'salaries expense': '501',
    'utilities expen': '511',  # typo in source
    'utilities expense - electricity': '511',
    'utilities expense - water': '512',
    'utilites expense - electricity': '511',  # typo in source
    'utilites expense - water': '512',  # typo in source
    'utilties expense - electricity': '511',  # typo in source (one L)
    'utilties expense - water': '512',  # typo in source (one L)
    'utilities expense': '511',  # generic
    'utilites expense': '511',  # typo
    'utilties expense': '511',  # typo (one L)
    'utilities expense - electricity': '511',
    'utilities expense - water': '512',
    'utilites expense - electricity': '511',
    'utilites expense - water': '512',
    'utilties expense - electricity': '511',  # typo (one L)
    'utilties expense - water': '512',  # typo (one L)
    'utilities expen': '511',  # typo
    'utilities expense electricity': '511',  # missing dash
    'utilities expense water': '512',  # missing dash
    'utilites expense electricity': '511',  # typo no dash
    'utilites expense water': '512',  # typo no dash
    'utilties expense electricity': '511',  # typo no dash (one L)
    'utilties expense water': '512',  # typo no dash (one L)
    'utilities expen electricity': '511',  # typo no dash
    'utilities expen water': '512',  # typo no dash
    'utilities expense electricity': '511',
    'utilities expense water': '512',
    'laundry supplies expense': '521',
    'laundy supplies expense': '521',  # typo in source
    'depreciation expense': '531',
    'tax expense': '541',
    'tax payable': '221',
    'accumulated depreciation': '103a',
}


class Book:
    def __init__(self, path=PATH):
        self.path = Path(path)
        self.accounts = []
        self.entries = []
        self.adjustments = []
        self.meta = {"business": "", "period": ""}
        self._initialize_db()
        self._load()

    @contextmanager
    def _connect(self):
        """Short-lived connection context manager to avoid locking issues."""
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    code TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    normal TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entries (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    lines TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS adjustments (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    description TEXT NOT NULL,
                    lines TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )

    def _load(self):
        with self._connect() as conn:
            self.accounts = [dict(row) for row in conn.execute(
                "SELECT code, name, type, normal FROM accounts ORDER BY code"
            )]
            self.entries = self._load_journal(conn, "entries")
            self.adjustments = self._load_journal(conn, "adjustments")
            self.meta = {"business": "", "period": ""}
            for row in conn.execute("SELECT key, value FROM meta"):
                self.meta[row["key"]] = row["value"]

    def _load_journal(self, conn, kind):
        rows = []
        for row in conn.execute(
            f"SELECT id, date, description, lines FROM {kind} ORDER BY date, id"
        ):
            entry = {
                "id": row["id"],
                "date": row["date"],
                "description": row["description"],
                "lines": json.loads(row["lines"]),
            }
            rows.append(entry)
        return rows

    def save(self):
        with self._connect() as conn:
            conn.execute("DELETE FROM accounts")
            conn.executemany(
                "INSERT INTO accounts (code, name, type, normal) VALUES (?, ?, ?, ?)",
                [
                    (account["code"], account["name"], account["type"], account["normal"])
                    for account in self.accounts
                ],
            )
            for kind in ("entries", "adjustments"):
                conn.execute(f"DELETE FROM {kind}")
                for entry in getattr(self, kind):
                    conn.execute(
                        f"INSERT INTO {kind} (id, date, description, lines) VALUES (?, ?, ?, ?)",
                        (
                            entry["id"],
                            entry["date"],
                            entry["description"],
                            json.dumps(entry["lines"]),
                        ),
                    )
            for key, value in self.meta.items():
                conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, value),
                )
        self._load()

    def reset(self, data):
        self.accounts = sorted(data.get("accounts", []), key=lambda a: a["code"])
        self.entries = data.get("entries", [])
        self.adjustments = data.get("adjustments", [])
        self.meta = data.get("meta", {"business": "", "period": ""})
        self.save()

    def clear_all(self):
        self.accounts = []
        self.entries = []
        self.adjustments = []
        self.meta = {"business": "", "period": ""}
        self.save()

    def clear_journals(self):
        self.entries = []
        self.adjustments = []
        self.save()

    def find(self, code):
        return next((a for a in self.accounts if a["code"] == code), None)

    def name_of(self, code):
        account = self.find(code)
        return account["name"] if account else code

    def is_posted(self, code):
        return any(
            line["account"] == code
            for journal in (self.entries, self.adjustments)
            for entry in journal
            for line in entry["lines"]
        )

    def add_account(self, account):
        if self.find(account["code"]):
            raise ValueError("That account code is already in use.")
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO accounts (code, name, type, normal) VALUES (?, ?, ?, ?)",
                (account["code"], account["name"], account["type"], account["normal"]),
            )
        self._load()

    def update_account(self, old_code, account):
        if account["code"] != old_code and self.find(account["code"]):
            raise ValueError("That account code is already in use.")
        with self._connect() as conn:
            conn.execute(
                "UPDATE accounts SET code = ?, name = ?, type = ?, normal = ? WHERE code = ?",
                (account["code"], account["name"], account["type"], account["normal"], old_code),
            )
            if account["code"] != old_code:
                for kind in ("entries", "adjustments"):
                    for entry in self._load_journal(conn, kind):
                        lines = []
                        for line in entry["lines"]:
                            updated = dict(line)
                            if updated["account"] == old_code:
                                updated["account"] = account["code"]
                            lines.append(updated)
                        conn.execute(
                            f"UPDATE {kind} SET lines = ? WHERE id = ?",
                            (json.dumps(lines), entry["id"]),
                        )
        self._load()

    def delete_account(self, code):
        if self.is_posted(code):
            raise ValueError("This account has postings and cannot be deleted.")
        with self._connect() as conn:
            conn.execute("DELETE FROM accounts WHERE code = ?", (code,))
        self._load()

    def entry(self, kind, entry_id):
        return next((e for e in getattr(self, kind) if e["id"] == entry_id), None)

    def save_entry(self, kind, entry):
        if entry["id"] is None:
            max_id = max((e["id"] for e in getattr(self, kind)), default=0)
            entry = {**entry, "id": max_id + 1}
            with self._connect() as conn:
                conn.execute(
                    f"INSERT INTO {kind} (id, date, description, lines) VALUES (?, ?, ?, ?)",
                    (entry["id"], entry["date"], entry["description"], json.dumps(entry["lines"])),
                )
        else:
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE {kind} SET date = ?, description = ?, lines = ? WHERE id = ?",
                    (entry["date"], entry["description"], json.dumps(entry["lines"]), entry["id"]),
                )
        self._load()

    def delete_entry(self, kind, entry_id):
        with self._connect() as conn:
            conn.execute(f"DELETE FROM {kind} WHERE id = ?", (entry_id,))
        self._load()

    def import_from_excel(self, file_path, entry_type="entries"):
        """
        Import journal entries from an Excel file.
        
        Supported formats:
        1. Simple format (columns: Date, Description, Account, Debit, Credit)
        2. General Ledger T-account format (from accounting worksheets)
        3. Chart of Accounts (columns: Code, Name, Type, Normal)
        
        The importer auto-detects the format based on sheet names and columns.
        """
        if not file_path.lower().endswith((".xlsx", ".xls")):
            raise ValueError("Only .xlsx and .xls files are supported.")

        # Read all sheets
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names
        
        # Try to detect format and import
        imported = False
        
        # 1. Try Chart of Accounts import (if COA-related sheet)
        coa_sheets = [s for s in sheet_names if any(k in s.lower() for k in ["chart", "account", "coa"])]
        if coa_sheets and entry_type == "entries":
            imported = self._import_coa_from_sheet(xls, coa_sheets[0])
            if imported:
                return
        
        # Also check first sheet for COA columns (Code, Name, Type, Normal)
        if entry_type == "entries":
            first_sheet = pd.read_excel(file_path, sheet_name=0)
            first_sheet.columns = first_sheet.columns.str.strip().str.lower()
            if all(c in first_sheet.columns for c in ['code', 'name', 'type', 'normal']):
                imported = self._import_coa_from_sheet(xls, sheet_names[0])
                if imported:
                    return
        
        # 2. Try General Ledger T-account format
        # Prefer "General Ledger" over "General Journal" for T-account format
        gl_sheets = [s for s in sheet_names if "ledger" in s.lower()]
        if not gl_sheets:
            gl_sheets = [s for s in sheet_names if "general" in s.lower() and "journal" not in s.lower()]
        if gl_sheets:
            # First, try to import Chart of Accounts from Effects of Accounts or Trial Balance
            self._import_coa_from_effects(xls)
            imported = self._import_general_ledger(xls, gl_sheets[0], entry_type)
            if imported:
                return
        
        # 3. Try simple format on first sheet
        df = pd.read_excel(file_path, sheet_name=0)
        imported = self._import_simple_format(df, entry_type)
        if imported:
            return
        
        # 4. Try all sheets with simple format
        for sheet in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet)
            imported = self._import_simple_format(df, entry_type)
            if imported:
                return
        
        # If nothing worked, show helpful error with template info
        raise ValueError(
            "Could not import. Expected formats:\n\n"
            "1. SIMPLE FORMAT (any sheet):\n"
            "   Columns: Date, Description, Account, Debit, Credit\n"
            "   Example:\n"
            "   Date       | Description      | Account | Debit | Credit\n"
            "   2024-01-15 | Office Supplies  | 120     | 500   | \n"
            "   2024-01-15 | Office Supplies  | 510     |       | 500\n\n"
            "2. CHART OF ACCOUNTS:\n"
            "   Columns: Code, Name, Type, Normal\n"
            "   Types: Asset, Liability, Equity, Revenue, Cost of Sales, Expense\n"
            "   Normal: Debit or Credit\n\n"
            "3. GENERAL LEDGER (T-account format):\n"
            "   Sheet named 'General Ledger' or 'Ledger' with T-account layout\n\n"
            "Use File → Import Chart of Accounts for COA, or\n"
            "Business Transactions/Adjustments → Import from Excel for entries."
        )

    def _import_simple_format(self, df, entry_type):
        """Import from simple column format."""
        df.columns = df.columns.str.strip().str.lower()
        required = ["date", "description", "account", "debit", "credit"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            return False
        
        df = df.fillna({"debit": 0.0, "credit": 0.0, "description": "", "account": "", "date": ""})
        ledger = []
        for row in df.to_dict(orient="records"):
            date_value = str(row.get("date", "")).strip()
            description_value = str(row.get("description", "")).strip()
            account_value = str(row.get("account", "")).strip()
            if not date_value or not account_value:
                continue
            debit_value = clean_float(row.get("debit", 0.0))
            credit_value = clean_float(row.get("credit", 0.0))
            ledger.append({
                "date": date_value,
                "description": description_value,
                "account": account_value,
                "debit": debit_value,
                "credit": credit_value,
            })
        
        if not ledger:
            return False
        
        grouped = {}
        for row in ledger:
            key = (row["date"], row["description"])
            grouped.setdefault(key, []).append({
                "account": row["account"],
                "debit": row["debit"],
                "credit": row["credit"],
            })
        
        for (date_value, description_value), rows in grouped.items():
            balanced = balance_journal_rows(rows)
            entry = {"id": None, "date": date_value, "description": description_value, "lines": balanced}
            self.save_entry(entry_type, entry)
        
        self._load()
        return True

    def _import_coa_from_sheet(self, xls, sheet_name):
        """Import Chart of Accounts from a sheet."""
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = df.columns.str.strip().str.lower()
        required = ["code", "name", "type", "normal"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return False
        
        count = 0
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            if not code:
                continue
            if self.find(code):
                continue
            self.add_account({
                "code": code,
                "name": str(row.get("name", "")).strip(),
                "type": str(row.get("type", "")).strip(),
                "normal": str(row.get("normal", "")).strip(),
            })
            count += 1
        return count > 0

    def _import_coa_from_effects(self, xls):
        """Import Chart of Accounts from 'Effects of Accounts' sheet, using standardized account codes."""
        sheet_names = xls.sheet_names
        effects_sheets = [s for s in sheet_names if "effect" in s.lower()]
        if not effects_sheets:
            # Try Trial Balance sheet
            tb_sheets = [s for s in sheet_names if "trial" in s.lower() and "balance" in s.lower()]
            if tb_sheets:
                return self._import_coa_from_trial_balance(xls, tb_sheets[0])
            return False
        
        try:
            df = pd.read_excel(xls, sheet_name=effects_sheets[0], header=None)
        except Exception:
            return False
        
        # Parse the Effects of Accounts sheet
        # Format: Col 2=Classification, Col 3=Account Name, Col 4=Effect (Increase/Decrease)
        # Classification appears on first row of each group, then blank for subsequent rows
        
        class_map = {
            "asset": "Asset",
            "assets": "Asset",
            "liability": "Liability",
            "liabilities": "Liability",
            "owner's equity": "Equity",
            "equity": "Equity",
            "revenue": "Revenue",
            "expense": "Expense",
            "expenses": "Expense",
        }
        
        # Normal balance by account type
        type_normal = {
            "Asset": "Debit",
            "Liability": "Credit", 
            "Equity": "Credit",
            "Revenue": "Credit",
            "Expense": "Debit",
        }
        
        # Use standardized account codes
        name_to_code = XYZ_ACCOUNT_CODES
        
        accounts_added = 0
        current_classification = None
        rows, cols = df.shape
        
        for r in range(rows):
            row_data = df.iloc[r]
            
            # Check column 2 for classification (section header)
            class_cell = str(row_data.iloc[2]).strip() if 2 < cols else ''
            if class_cell and class_cell.lower() != 'nan':
                current_classification = class_map.get(class_cell.lower(), current_classification)
            
            # Check column 3 for account name
            account_cell = str(row_data.iloc[3]).strip() if 3 < cols else ''
            if not account_cell or account_cell.lower() == 'nan':
                continue
            
            # Skip header row
            if account_cell.lower() in ['accounts affected', 'classification', 'effect']:
                continue
            
            if current_classification and account_cell:
                account_key = account_cell.lower()
                code = name_to_code.get(account_key)
                
                existing = None
                for a in self.accounts:
                    if a["name"].lower() == account_cell.lower() or (code and a["code"] == code):
                        existing = a
                        break
                
                if not existing:
                    normal = type_normal.get(current_classification, "Debit")
                    
                    if code is None:
                        prefix = {"Asset": 100, "Liability": 200, "Equity": 300, "Revenue": 400, "Expense": 500}.get(current_classification, 900)
                        existing_count = len([a for a in self.accounts if a["type"] == current_classification])
                        code = str(prefix + existing_count)
                    
                    self.add_account({
                        "code": code,
                        "name": account_cell,
                        "type": current_classification,
                        "normal": normal,
                    })
                    accounts_added += 1
                else:
                    pass
        
        return accounts_added > 0

    def _import_coa_from_trial_balance(self, xls, sheet_name):
        """Import Chart of Accounts from Trial Balance sheet."""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            return False
        
        accounts_added = 0
        code_counter = {"Asset": 100, "Liability": 200, "Equity": 300, "Revenue": 400, "Expense": 500}
        
        # Known account types from the TB
        type_map = {
            "cash": "Asset", "accounts receivable": "Asset", "furniture": "Asset", 
            "laundry equipment": "Asset", "laundy supplies": "Asset", "laundry supplies": "Asset",
            "accounts payable": "Liability", "utilities payable": "Liability", "tax payable": "Liability",
            "mav, capital": "Equity", "mav, drawing": "Equity",
            "service revenue": "Revenue",
            "salaries expense": "Expense", "utilities expense": "Expense", 
            "laundry supplies expense": "Expense", "depreciation expense": "Expense", "tax expense": "Expense",
        }
        
        rows, cols = df.shape
        for r in range(rows):
            row_data = df.iloc[r]
            account_cell = str(row_data.iloc[3]).strip() if 3 < cols else ''
            if not account_cell or account_cell.lower() == 'nan':
                continue
            
            # Skip header/total rows
            if account_cell.lower() in ['account titles', 'total', 'xyz laundry shop', 'trial balance']:
                continue
            
            # Determine type
            acc_lower = account_cell.lower()
            acc_type = None
            for key, val in type_map.items():
                if key in acc_lower:
                    acc_type = val
                    break
            
            if acc_type and not self.find(account_cell):
                prefix = code_counter.get(acc_type, 900)
                code = str(prefix + len([a for a in self.accounts if a["type"] == acc_type]))
                code_counter[acc_type] += 1
                
                if acc_type in ["Asset", "Expense"]:
                    normal = "Debit"
                else:
                    normal = "Credit"
                
                self.add_account({
                    "code": code,
                    "name": account_cell,
                    "type": acc_type,
                    "normal": normal,
                })
                accounts_added += 1
        
        return accounts_added > 0

    def _import_general_ledger(self, xls, sheet_name, entry_type):
        """Parse General Ledger T-account format (like XYZ Laundry Shop)."""
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            return False
        
        ledger = []
        rows, cols = df.shape
        
        # Known account names to detect sections (from XYZ Laundry Shop)
        known_accounts = [
            'cash', 'accounts receivable', 'furniture', 'laundry equipment',
            'laundry supplies', 'accounts payable', 'utilities payable',
            'mav, capital', 'mav, drawing', 'service revenue', 'salaries expense',
            'utilities expense', 'laundry supplies expense', 'depreciation expense',
            'tax expense', 'tax payable', 'accumulated depreciation',
            'furniture & fixtures', 'utilities expen'  # partial match for typos
        ]
        
        # Use standardized account codes
        name_to_code = XYZ_ACCOUNT_CODES
        
        import re
        
        # Scan all rows for account section headers
        # In XYZ format: row has account name in col 4 and "Account No. XXX" in col 9
        account_sections = []  # list of (start_row, account_code, account_name)
        
        for r in range(rows):
            # Check column 4 (account name) and column 9 (account no)
            for c in [4, 9]:
                if c >= cols:
                    continue
                cell = str(df.iloc[r, c]).strip()
                if not cell or cell.lower() == 'nan':
                    continue
                
                # Check for "Account No. XXX" pattern
                code_match = re.search(r'[Aa]ccount\s+[Nn]o\.?\s*(\d+)', cell)
                if code_match:
                    account_code = code_match.group(1)
                    # Get account name from column 4
                    name_cell = str(df.iloc[r, 4]).strip() if 4 < cols else cell
                    account_sections.append({
                        'row': r,
                        'code': account_code,
                        'name': name_cell
                    })
                    break
                
                # Check for known account names
                if any(acc in cell.lower() for acc in known_accounts):
                    # Try to find account code in column 9
                    code_match = re.search(r'[Aa]ccount\s+[Nn]o\.?\s*(\d+)', str(df.iloc[r, 9]).strip()) if 9 < cols else None
                    if code_match:
                        account_code = code_match.group(1)
                    else:
                        # Infer from account name using mapping
                        account_code = name_to_code.get(cell.lower(), '')
                    account_sections.append({
                        'row': r,
                        'code': account_code,
                        'name': cell
                    })
                    break
        
        if not account_sections:
            return False
        
        # Parse each account section
        # Format: 
        # - Header row (account name + account no)
        # - Blank row
        # - Column header row: Date, Item, P/R, Debit | Date, Item, P/R, Credit
        # - Data rows with debit on cols 0-4, credit on cols 5-9
        
        for section in account_sections:
            r = section['row']
            account_code = section['code']
            
            # Find column header row (usually 2 rows after header)
            header_row_idx = None
            for hr in range(r + 1, min(r + 5, rows)):
                row_data = df.iloc[hr]
                # Look for "Date" and "Debit" / "Credit" in the row
                cells = [str(row_data.iloc[c]).strip().lower() for c in range(cols)]
                if 'date' in cells and ('debit' in cells or 'credit' in cells):
                    header_row_idx = hr
                    break
            
            if header_row_idx is None:
                continue
            
            # Identify debit and credit column indices
            header_cells = [str(df.iloc[header_row_idx, c]).strip().lower() for c in range(cols)]
            debit_col = None
            credit_col = None
            date_col_debit = None
            item_col_debit = None
            date_col_credit = None
            item_col_credit = None
            
            for c in range(cols):
                cell = header_cells[c]
                if 'debit' in cell:
                    debit_col = c
                    # Date is typically 4 cols before, Item is 1 col before
                    date_col_debit = c - 4
                    item_col_debit = c - 2
                elif 'credit' in cell:
                    credit_col = c
                    date_col_credit = c - 4
                    item_col_credit = c - 2
            
            if debit_col is None and credit_col is None:
                continue
            
            # Parse data rows until next account section or totals
            for data_row in range(header_row_idx + 1, rows):
                row_data = df.iloc[data_row]
                
                # Check if we hit next account section
                first_cell = str(row_data.iloc[0]).strip().lower()
                if first_cell and ('account no' in first_cell or any(acc in first_cell for acc in known_accounts)):
                    break
                
                # Parse debit side
                if debit_col is not None:
                    date_val = str(row_data.iloc[date_col_debit]).strip() if date_col_debit >= 0 and date_col_debit < cols else ''
                    day_val = str(row_data.iloc[date_col_debit + 1]).strip() if date_col_debit + 1 < cols else ''
                    item_val = str(row_data.iloc[item_col_debit]).strip() if item_col_debit >= 0 and item_col_debit < cols else ''
                    debit_val = clean_float(row_data.iloc[debit_col])
                    
                    if debit_val > 0 and date_val and date_val.lower() != 'nan':
                        # Combine date and day cells for parsing
                        combined_date = f"{date_val} {day_val}"
                        parsed_date = self._parse_ledger_date(combined_date)
                        if parsed_date:
                            ledger.append({
                                'date': parsed_date,
                                'description': item_val if item_val.lower() != 'nan' else '',
                                'account': account_code,
                                'debit': debit_val,
                                'credit': 0.0,
                            })
                
                # Parse credit side
                if credit_col is not None:
                    date_val = str(row_data.iloc[date_col_credit]).strip() if date_col_credit >= 0 and date_col_credit < cols else ''
                    day_val = str(row_data.iloc[date_col_credit + 1]).strip() if date_col_credit + 1 < cols else ''
                    item_val = str(row_data.iloc[item_col_credit]).strip() if item_col_credit >= 0 and item_col_credit < cols else ''
                    credit_val = clean_float(row_data.iloc[credit_col])
                    
                    if credit_val > 0 and date_val and date_val.lower() != 'nan':
                        combined_date = f"{date_val} {day_val}"
                        parsed_date = self._parse_ledger_date(combined_date)
                        if parsed_date:
                            ledger.append({
                                'date': parsed_date,
                                'description': item_val if item_val.lower() != 'nan' else '',
                                'account': account_code,
                                'debit': 0.0,
                                'credit': credit_val,
                            })
        
        if not ledger:
            return False
        
        # Group by (date, description) and save
        grouped = {}
        for row in ledger:
            key = (row["date"], row["description"])
            grouped.setdefault(key, []).append({
                "account": row["account"],
                "debit": row["debit"],
                "credit": row["credit"],
            })
        
        for (date_value, description_value), rows_data in grouped.items():
            balanced = balance_journal_rows(rows_data)
            entry = {"id": None, "date": date_value, "description": description_value, "lines": balanced}
            self.save_entry(entry_type, entry)
        
        self._load()
        return True

    def _parse_ledger_date(self, date_str):
        """Parse dates like '2023\nJuly  1.0' or '2023-07-01'."""
        if not date_str or date_str.lower() == 'nan':
            return None
        
        # Try standard formats first
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_str.strip(), fmt).date().isoformat()
            except ValueError:
                pass
        
        # Try "2023\nJuly  1.0" format - handle newlines and decimal days
        import re
        match = re.search(r'(\d{4})[^\w]*([A-Za-z]{3,})\s*(\d+)', date_str)
        if match:
            year, month_str, day = match.groups()
            month_map = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = month_map.get(month_str.lower()[:3])
            if month:
                try:
                    return date(int(year), month, int(day)).isoformat()
                except ValueError:
                    pass
        
        # Fallback: try to extract any date-like pattern
        match = re.search(r'(\d{4})[^\d]*(\d{1,2})[^\d]*(\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            try:
                return date(int(year), int(month), int(day)).isoformat()
            except ValueError:
                pass
        
        return None

    def export_template(self, file_path, template_type="entries"):
        """Export an Excel template for import."""
        if template_type == "entries":
            df = pd.DataFrame([
                {"Date": "2024-01-15", "Description": "Office Supplies", "Account": "120", "Debit": 500, "Credit": ""},
                {"Date": "2024-01-15", "Description": "Office Supplies", "Account": "510", "Debit": "", "Credit": 500},
                {"Date": "2024-01-16", "Description": "Cash Sales", "Account": "100", "Debit": 1000, "Credit": ""},
                {"Date": "2024-01-16", "Description": "Cash Sales", "Account": "400", "Debit": "", "Credit": 1000},
            ])
        elif template_type == "coa":
            df = pd.DataFrame([
                {"Code": "100", "Name": "Cash", "Type": "Asset", "Normal": "Debit"},
                {"Code": "120", "Name": "Office Supplies", "Type": "Asset", "Normal": "Debit"},
                {"Code": "200", "Name": "Accounts Payable", "Type": "Liability", "Normal": "Credit"},
                {"Code": "400", "Name": "Revenue", "Type": "Revenue", "Normal": "Credit"},
                {"Code": "500", "Name": "Expenses", "Type": "Expense", "Normal": "Debit"},
            ])
        else:
            raise ValueError("template_type must be 'entries' or 'coa'")
        
        df.to_excel(file_path, index=False)