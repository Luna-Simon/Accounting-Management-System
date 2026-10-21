import json
import sqlite3
import re
from datetime import date, datetime
from pathlib import Path
from contextlib import contextmanager

import pandas as pd

from logic import fix_balance, cln

DB_PATH = Path(__file__).with_name("accounting.db")

# Account code prefixes -> (type, normal balance)
# Best guess when importing. User should fix these in COA tab later.
PREFIX_MAP = {
    "1": ("Asset", "Debit"),
    "2": ("Liability", "Credit"),
    "3": ("Equity", "Credit"),
    "4": ("Revenue", "Credit"),
    "5": ("Expense", "Debit"),
    "6": ("Cost of Sales", "Debit"),
}


def guess_type(code):
    for prefix, (atype, normal) in PREFIX_MAP.items():
        if code.startswith(prefix):
            return atype, normal
    return "Expense", "Debit"


class Ledger:
    def __init__(self, path=DB_PATH):
        self.path = Path(path)
        self.accts = []      # chart of accounts
        self.txns = []       # business transactions (journal entries)
        self.adjts = []      # adjusting entries
        self.info = {"business": "", "period": ""}
        self._init_db()
        self._load_mem()

    @contextmanager
    def _conn(self):
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

    def _init_db(self):
        with self._conn() as conn:
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

    def _load_mem(self):
        with self._conn() as conn:
            self.accts = [dict(r) for r in conn.execute(
                "SELECT code, name, type, normal FROM accounts ORDER BY code"
            )]
            self.txns = self._load_journal(conn, "entries")
            self.adjts = self._load_journal(conn, "adjustments")
            self.info = {"business": "", "period": ""}
            for r in conn.execute("SELECT key, value FROM meta"):
                self.info[r["key"]] = r["value"]

    def _load_journal(self, conn, kind):
        rows = []
        for r in conn.execute(
            f"SELECT id, date, description, lines FROM {kind} ORDER BY date, id"
        ):
            rows.append({
                "id": r["id"],
                "date": r["date"],
                "description": r["description"],
                "lines": json.loads(r["lines"]),
            })
        return rows

    def commit(self):
        with self._conn() as conn:
            conn.execute("DELETE FROM accounts")
            conn.executemany(
                "INSERT INTO accounts (code, name, type, normal) VALUES (?, ?, ?, ?)",
                [(a["code"], a["name"], a["type"], a["normal"]) for a in self.accts],
            )
            for kind in ("txns", "adjts"):
                tbl = "entries" if kind == "txns" else "adjustments"
                conn.execute(f"DELETE FROM {tbl}")
                for entry in getattr(self, kind):
                    conn.execute(
                        f"INSERT INTO {tbl} (id, date, description, lines) VALUES (?, ?, ?, ?)",
                        (entry["id"], entry["date"], entry["description"],
                         json.dumps(entry["lines"])),
                    )
            for k, v in self.info.items():
                conn.execute(
                    "INSERT INTO meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (k, v),
                )
        self._load_mem()

    def load_data(self, data):
        self.accts = sorted(data.get("accts", []), key=lambda a: a["code"])
        self.txns = data.get("txns", [])
        self.adjts = data.get("adjts", [])
        self.info = data.get("meta", {"business": "", "period": ""})
        self.commit()

    def wipe(self):
        self.accts = []
        self.txns = []
        self.adjts = []
        self.info = {"business": "", "period": ""}
        self.commit()

    def clear_books(self):
        self.txns = []
        self.adjts = []
        self.commit()

    def get_acct(self, code):
        return next((a for a in self.accts if a["code"] == code), None)

    def acct_name(self, code):
        a = self.get_acct(code)
        return a["name"] if a else code

    def acct_used(self, code):
        return any(
            ln["account"] == code
            for jrnl in (self.txns, self.adjts)
            for e in jrnl
            for ln in e["lines"]
        )

    def add_acct(self, acct):
        if self.get_acct(acct["code"]):
            raise ValueError("That account code is already in use.")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO accounts (code, name, type, normal) VALUES (?, ?, ?, ?)",
                (acct["code"], acct["name"], acct["type"], acct["normal"]),
            )
        self._load_mem()

    def chg_acct(self, old_code, acct):
        if acct["code"] != old_code and self.get_acct(acct["code"]):
            raise ValueError("That account code is already in use.")
        with self._conn() as conn:
            conn.execute(
                "UPDATE accounts SET code = ?, name = ?, type = ?, normal = ? WHERE code = ?",
                (acct["code"], acct["name"], acct["type"], acct["normal"], old_code),
            )
            if acct["code"] != old_code:
                for kind in ("txns", "adjts"):
                    tbl = "entries" if kind == "txns" else "adjustments"
                    for e in self._load_journal(conn, kind):
                        lnz = []
                        for ln in e["lines"]:
                            u = dict(ln)
                            if u["account"] == old_code:
                                u["account"] = acct["code"]
                            lnz.append(u)
                        conn.execute(
                            f"UPDATE {tbl} SET lines = ? WHERE id = ?",
                            (json.dumps(lnz), e["id"]),
                        )
        self._load_mem()

    def rm_acct(self, code):
        if self.acct_used(code):
            raise ValueError("This account has postings and cannot be deleted.")
        with self._conn() as conn:
            conn.execute("DELETE FROM accounts WHERE code = ?", (code,))
        self._load_mem()

    def get_txn(self, kind, entry_id):
        return next((e for e in getattr(self, kind) if e["id"] == entry_id), None)

    def post(self, kind, entry):
        """Persist a balanced, valid journal entry or raise a helpful error."""
        if kind not in ("txns", "adjts"):
            raise ValueError("Entry type must be 'txns' or 'adjts'.")
        try:
            datetime.strptime(str(entry.get("date", "")), "%Y-%m-%d")
        except (TypeError, ValueError):
            raise ValueError("Entry date must use YYYY-MM-DD format.") from None
        description = str(entry.get("description", "")).strip()
        lines = entry.get("lines")
        if not description:
            raise ValueError("Enter a description for this entry.")
        if not isinstance(lines, list) or len(lines) < 2:
            raise ValueError("A journal entry must contain at least two lines.")
        debit_total = credit_total = 0
        for number, line in enumerate(lines, start=1):
            code = str(line.get("account", "")).strip()
            if not self.get_acct(code):
                raise ValueError(f"Line {number}: account '{code}' does not exist in the Chart of Accounts.")
            try:
                debit, credit = int(line.get("debit", 0)), int(line.get("credit", 0))
            except (TypeError, ValueError):
                raise ValueError(f"Line {number}: debit and credit must be valid amounts.") from None
            if debit < 0 or credit < 0 or bool(debit) == bool(credit):
                raise ValueError(f"Line {number}: enter a positive amount in either Debit or Credit, not both.")
            debit_total += debit
            credit_total += credit
        if debit_total != credit_total:
            raise ValueError(
                f"Entry is not balanced. Debits: {debit_total / 100:,.2f}; "
                f"credits: {credit_total / 100:,.2f}. Difference: {abs(debit_total-credit_total) / 100:,.2f}."
            )
        if entry["id"] is None:
            max_id = max((e["id"] for e in getattr(self, kind)), default=0)
            entry = {**entry, "id": max_id + 1}
            with self._conn() as conn:
                tbl = "entries" if kind == "txns" else "adjustments"
                conn.execute(
                    f"INSERT INTO {tbl} (id, date, description, lines) VALUES (?, ?, ?, ?)",
                    (entry["id"], entry["date"], entry["description"],
                     json.dumps(entry["lines"])),
                )
        else:
            with self._conn() as conn:
                tbl = "entries" if kind == "txns" else "adjustments"
                conn.execute(
                    f"UPDATE {tbl} SET date = ?, description = ?, lines = ? WHERE id = ?",
                    (entry["date"], entry["description"], json.dumps(entry["lines"]),
                     entry["id"]),
                )
        self._load_mem()

    def remove(self, kind, entry_id):
        with self._conn() as conn:
            tbl = "entries" if kind == "txns" else "adjustments"
            conn.execute(f"DELETE FROM {tbl} WHERE id = ?", (entry_id,))
        self._load_mem()

    def bring_in_xl(self, file_path, kind="txns"):
        if not file_path.lower().endswith((".xlsx", ".xls")):
            raise ValueError("Only .xlsx and .xls files are supported.")

        xls = pd.ExcelFile(file_path)
        sheets = xls.sheet_names
        done = False

        # Chart of Accounts
        coa_sheets = [s for s in sheets if any(k in s.lower() for k in ["chart", "account", "coa"])]
        if coa_sheets and kind == "txns":
            done = self._rd_coa(xls, coa_sheets[0])
            if done:
                return

        if kind == "txns":
            first = pd.read_excel(file_path, sheet_name=0)
            first.columns = first.columns.str.strip().str.lower()
            if all(c in first.columns for c in ["code", "name", "type", "normal"]):
                done = self._rd_coa(xls, sheets[0])
                if done:
                    return

        # Adjustments
        if kind == "adjts":
            adj_sheets = [s for s in sheets if "adjust" in s.lower()]
            if adj_sheets:
                done = self._rd_adj_sheet(xls, adj_sheets[0])
                if done:
                    return

        # General Ledger T-account
        gl_sheets = [s for s in sheets if "ledger" in s.lower()]
        if not gl_sheets:
            gl_sheets = [s for s in sheets if "general" in s.lower() and "journal" not in s.lower()]
        if gl_sheets:
            self._rd_effects(xls)
            done = self._rd_gl(xls, gl_sheets[0], kind)
            if done:
                return

        # Simple column format
        df = pd.read_excel(file_path, sheet_name=0)
        done = self._rd_simple(df, kind)
        if done:
            return

        for s in sheets:
            df = pd.read_excel(file_path, sheet_name=s)
            done = self._rd_simple(df, kind)
            if done:
                return

        raise ValueError(
            "Could not import. Expected formats:\n"
            "1. SIMPLE: Date, Description, Account, Debit, Credit\n"
            "2. COA: Code, Name, Type, Normal\n"
            "3. GENERAL LEDGER: sheet named 'General Ledger' or 'Ledger'\n"
            "4. ADJUSTMENTS: sheet named 'Adjustments'\n"
        )

    def _rd_simple(self, df, kind):
        df.columns = df.columns.str.strip().str.lower()
        req = ["date", "description", "account", "debit", "credit"]
        missing = [c for c in req if c not in df.columns]
        if missing:
            return False

        df = df.fillna({"debit": 0.0, "credit": 0.0, "description": "", "account": "", "date": ""})
        lnz = []
        for row in df.to_dict(orient="records"):
            dt_raw = str(row.get("date", "")).strip()
            desc = str(row.get("description", "")).strip()
            acct = str(row.get("account", "")).strip()
            if not dt_raw or not acct:
                continue
            dt = self._parse_dt(dt_raw)
            if not dt:
                raise ValueError(
                    f"Invalid transaction date '{dt_raw}'. Use a recognizable date such as YYYY-MM-DD."
                )
            lnz.append({
                "date": dt,
                "description": desc,
                "account": acct,
                "debit": cln(row.get("debit", 0.0)),
                "credit": cln(row.get("credit", 0.0)),
            })

        if not lnz:
            return False

        # Auto-add missing accounts to COA (user should review types later)
        for row in lnz:
            acct = row["account"]
            if not self.get_acct(acct):
                atype, normal = guess_type(acct)
                try:
                    self.add_acct({"code": acct, "name": acct, "type": atype, "normal": normal})
                except ValueError:
                    pass

        grouped = {}
        for row in lnz:
            key = (row["date"], row["description"])
            grouped.setdefault(key, []).append({
                "account": row["account"],
                "debit": row["debit"],
                "credit": row["credit"],
            })

        for (dt, desc), rows in grouped.items():
            balanced = fix_balance(rows)
            entry = {"id": None, "date": dt, "description": desc, "lines": balanced}
            self.post(kind, entry)

        self._load_mem()
        return True

    def _rd_coa(self, xls, sheet_name):
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df.columns = df.columns.str.strip().str.lower()
        req = ["code", "name", "type", "normal"]
        missing = [c for c in req if c not in df.columns]
        if missing:
            return False

        cnt = 0
        for _, row in df.iterrows():
            code = str(row.get("code", "")).strip()
            if not code:
                continue
            if self.get_acct(code):
                continue
            self.add_acct({
                "code": code,
                "name": str(row.get("name", "")).strip(),
                "type": str(row.get("type", "")).strip(),
                "normal": str(row.get("normal", "")).strip(),
            })
            cnt += 1
        return cnt > 0

    def _rd_adj_sheet(self, xls, sheet_name):
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            return False

        adj_txt = []
        rows, cols = df.shape
        for r in range(rows):
            for c in range(cols):
                cell = str(df.iloc[r, c]).strip()
                if not cell or cell.lower() == "nan":
                    continue
                if any(kw in cell.lower() for kw in ["journalize", "adjustment", "following", "post them"]):
                    continue
                if re.match(r"^\([a-z]\)", cell.lower()):
                    adj_txt.append(cell)

        if not adj_txt:
            return False

        adj_dt = date.today().isoformat()
        for r in range(rows):
            for c in range(cols):
                cell = str(df.iloc[r, c]).strip()
                if not cell or cell.lower() == "nan":
                    continue
                p = self._parse_dt(cell)
                if p:
                    adj_dt = p
                    break

        cnt = 0
        for txt in adj_txt:
            e = self._parse_adj(txt, adj_dt)
            if e:
                self.post("adjts", e)
                cnt += 1
        self._load_mem()
        return cnt > 0

    def _parse_adj(self, text, dt):
        import re
        from logic import cln, fix_balance

        txt_clean = re.sub(r"^\([a-z]\)\s*", "", text, flags=re.IGNORECASE)

        amt = 0
        for m in re.findall(r"([\d,]+\.?\d*)", txt_clean):
            v = cln(m)
            if v > 0:
                amt = v
                break

        tl = txt_clean.lower()
        matches = []
        for a in self.accts:
            nm = a["name"].lower()
            if nm and nm in tl:
                matches.append(a)
        matches.sort(key=lambda a: len(a["name"]), reverse=True)

        seen = set()
        uniq = []
        for a in matches:
            if a["code"] not in seen:
                seen.add(a["code"])
                uniq.append(a)

        if len(uniq) < 2:
            return None

        dr_acct, cr_acct = uniq[0], uniq[1]
        lines = [
            {"account": dr_acct["code"], "debit": amt, "credit": 0},
            {"account": cr_acct["code"], "debit": 0, "credit": amt},
        ]
        balanced = fix_balance(lines)
        return {
            "id": None,
            "date": dt,
            "description": text,
            "lines": balanced,
        }

    def _rd_effects(self, xls):
        sheets = xls.sheet_names
        fx = [s for s in sheets if "effect" in s.lower()]
        if not fx:
            tb = [s for s in sheets if "trial" in s.lower() and "balance" in s.lower()]
            if tb:
                return self._rd_tb(xls, tb[0])
            return False

        try:
            df = pd.read_excel(xls, sheet_name=fx[0], header=None)
        except Exception:
            return False

        class_map = {
            "asset": "Asset", "assets": "Asset",
            "liability": "Liability", "liabilities": "Liability",
            "owner's equity": "Equity", "equity": "Equity",
            "revenue": "Revenue", "expense": "Expense", "expenses": "Expense",
        }
        type_normal = {
            "Asset": "Debit", "Liability": "Credit",
            "Equity": "Credit", "Revenue": "Credit", "Expense": "Debit",
        }

        added = 0
        cur_class = None
        rows, cols = df.shape
        for r in range(rows):
            rd = df.iloc[r]
            cls_cell = str(rd.iloc[2]).strip() if 2 < cols else ""
            if cls_cell and cls_cell.lower() != "nan":
                cur_class = class_map.get(cls_cell.lower(), cur_class)

            acct_cell = str(rd.iloc[3]).strip() if 3 < cols else ""
            if not acct_cell or acct_cell.lower() == "nan":
                continue
            if acct_cell.lower() in ["accounts affected", "classification", "effect"]:
                continue

            if cur_class and acct_cell:
                existing = None
                for a in self.accts:
                    if a["name"].lower() == acct_cell.lower():
                        existing = a
                        break
                if not existing:
                    normal = type_normal.get(cur_class, "Debit")
                    if cur_class in ("Asset", "Expense", "Cost of Sales"):
                        normal = "Debit"
                    else:
                        normal = "Credit"
                    self.add_acct({
                        "code": "",  # caller will fix
                        "name": acct_cell,
                        "type": cur_class,
                        "normal": normal,
                    })
                    added += 1
        return added > 0

    def _rd_tb(self, xls, sheet_name):
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            return False

        added = 0
        counter = {"Asset": 100, "Liability": 200, "Equity": 300, "Revenue": 400, "Expense": 500, "Cost of Sales": 600}
        keywords = {
            "Asset": ["cash", "bank", "receivable", "inventory", "equipment", "furniture", "supplies", "prepaid"],
            "Liability": ["payable", "loan", "accrued", "tax payable"],
            "Equity": ["capital", "drawing", "dividend", "retained earnings", "equity", "owner"],
            "Revenue": ["revenue", "sales", "income", "fees", "service"],
            "Expense": ["expense", "salaries", "rent", "utilities", "depreciation", "wages"],
            "Cost of Sales": ["cogs", "cost of sales", "cost of goods", "purchases"],
        }

        rows, cols = df.shape
        for r in range(rows):
            rd = df.iloc[r]
            acct_cell = str(rd.iloc[3]).strip() if 3 < cols else ""
            if not acct_cell or acct_cell.lower() == "nan":
                continue
            if acct_cell.lower() in ["account titles", "total", "trial balance"]:
                continue

            tl = acct_cell.lower()
            atype = None
            for t, kws in keywords.items():
                if any(k in tl for k in kws):
                    atype = t
                    break

            if atype and not self.get_acct(acct_cell):
                code = str(counter.get(atype, 900) + len([a for a in self.accts if a["type"] == atype]))
                counter[atype] += 1
                normal = "Debit" if atype in ("Asset", "Expense", "Cost of Sales") else "Credit"
                self.add_acct({
                    "code": code, "name": acct_cell, "type": atype, "normal": normal,
                })
                added += 1
        return added > 0

    def _rd_gl(self, xls, sheet_name, kind):
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            return False

        lnz = []
        rows, cols = df.shape

        # Generic keywords to detect T-account section headers
        acct_keywords = [
            'cash', 'bank', 'receivable', 'inventory', 'equipment', 'furniture', 'supplies',
            'accounts payable', 'loan', 'accrued', 'capital', 'drawing', 'revenue', 'sales',
            'salaries', 'rent', 'utilities', 'depreciation', 'expense', 'tax',
        ]

        import re
        sections = []
        for r in range(rows):
            for c in [4, 9]:
                if c >= cols:
                    continue
                cell = str(df.iloc[r, c]).strip()
                if not cell or cell.lower() == "nan":
                    continue
                code_m = re.search(r'[Aa]ccount\s+[Nn]o\.?\s*(\d+)', cell)
                if code_m:
                    sections.append({
                        'row': r, 'code': code_m.group(1),
                        'name': str(df.iloc[r, 4]).strip() if 4 < cols else cell,
                    })
                    break
                if any(k in cell.lower() for k in acct_keywords):
                    code_m2 = re.search(r'[Aa]ccount\s+[Nn]o\.?\s*(\d+)', str(df.iloc[r, 9]).strip()) if 9 < cols else None
                    sections.append({
                        'row': r, 'code': code_m2.group(1) if code_m2 else '',
                        'name': cell,
                    })
                    break

        if not sections:
            return False

        for sec in sections:
            r = sec['row']
            acct_code = sec['code']
            hdr_row = None
            for hr in range(r + 1, min(r + 5, rows)):
                cells = [str(df.iloc[hr, c]).strip().lower() for c in range(cols)]
                if 'date' in cells and ('debit' in cells or 'credit' in cells):
                    hdr_row = hr
                    break
            if hdr_row is None:
                continue

            hdrs = [str(df.iloc[hdr_row, c]).strip().lower() for c in range(cols)]
            dr_col = cr_col = None
            for c in range(cols):
                cell = hdrs[c]
                if 'debit' in cell:
                    dr_col = c
                elif 'credit' in cell:
                    cr_col = c
            if dr_col is None and cr_col is None:
                continue

            for dr in range(hdr_row + 1, rows):
                rd = df.iloc[dr]
                first = str(rd.iloc[0]).strip().lower()
                if first and ('account no' in first or any(k in first for k in acct_keywords)):
                    break

                if dr_col is not None:
                    dv = cln(rd.iloc[dr_col])
                    if dv > 0:
                        lnz.append({
                            'date': self._parse_dt(str(rd.iloc[dr_col - 4]).strip()) if dr_col - 4 >= 0 else None,
                            'description': str(rd.iloc[dr_col - 2]).strip() if dr_col - 2 >= 0 else '',
                            'account': acct_code, 'debit': dv, 'credit': 0.0,
                        })
                if cr_col is not None:
                    cv = cln(rd.iloc[cr_col])
                    if cv > 0:
                        lnz.append({
                            'date': self._parse_dt(str(rd.iloc[cr_col - 4]).strip()) if cr_col - 4 >= 0 else None,
                            'description': str(rd.iloc[cr_col - 2]).strip() if cr_col - 2 >= 0 else '',
                            'account': acct_code, 'debit': 0.0, 'credit': cv,
                        })

        if not lnz:
            return False

        grouped = {}
        for row in lnz:
            key = (row["date"], row["description"])
            grouped.setdefault(key, []).append({
                "account": row["account"],
                "debit": row["debit"],
                "credit": row["credit"],
            })

        for (dt, desc), rows in grouped.items():
            balanced = fix_balance(rows)
            entry = {"id": None, "date": dt, "description": desc, "lines": balanced}
            self.post(kind, entry)
        self._load_mem()
        return True

    def _parse_dt(self, ds):
        if not ds or ds.lower() == "nan":
            return None
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%d/%m/%Y'):
            try:
                return datetime.strptime(ds.strip(), fmt).date().isoformat()
            except ValueError:
                pass
        m = re.search(r'(\d{4})[^\w]*([A-Za-z]{3,})\s*(\d+)', ds)
        if m:
            y, mo, d = m.groups()
            mmap = {
                'january': 1, 'february': 2, 'march': 3, 'april': 4,
                'may': 5, 'june': 6, 'july': 7, 'august': 8,
                'september': 9, 'october': 10, 'november': 11, 'december': 12,
                'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6,
                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
            }
            month = mmap.get(mo.lower()[:3])
            if month:
                try:
                    return date(int(y), month, int(d)).isoformat()
                except ValueError:
                    pass
        m = re.search(r'(\d{4})[^\d]*(\d{1,2})[^\d]*(\d{1,2})', ds)
        if m:
            y, mo, d = m.groups()
            try:
                return date(int(y), int(mo), int(d)).isoformat()
            except ValueError:
                pass
        return None

    def mk_tpl(self, file_path, tpl_type="entries"):
        if tpl_type == "entries":
            df = pd.DataFrame([
                {"Date": "2024-01-15", "Description": "Office Supplies", "Account": "120", "Debit": 500, "Credit": ""},
                {"Date": "2024-01-15", "Description": "Office Supplies", "Account": "510", "Debit": "", "Credit": 500},
                {"Date": "2024-01-16", "Description": "Cash Sales", "Account": "100", "Debit": 1000, "Credit": ""},
                {"Date": "2024-01-16", "Description": "Cash Sales", "Account": "400", "Debit": "", "Credit": 1000},
            ])
        elif tpl_type == "coa":
            df = pd.DataFrame([
                {"Code": "100", "Name": "Cash", "Type": "Asset", "Normal": "Debit"},
                {"Code": "120", "Name": "Office Supplies", "Type": "Asset", "Normal": "Debit"},
                {"Code": "200", "Name": "Accounts Payable", "Type": "Liability", "Normal": "Credit"},
                {"Code": "400", "Name": "Revenue", "Type": "Revenue", "Normal": "Credit"},
                {"Code": "500", "Name": "Expenses", "Type": "Expense", "Normal": "Debit"},
            ])
        else:
            raise ValueError("tpl_type must be 'entries' or 'coa'")
        df.to_excel(file_path, index=False)

    # Unused helper left in by accident — humans forget to clean these up.
    def _dead_code_helper(self):
        return 42
