from pathlib import Path

import pandas as pd

from store import Book


def test_book_uses_sqlite_and_keeps_account_api(tmp_path):
    db_path = tmp_path / "accounting.db"
    book = Book(db_path)

    book.add_account({"code": "100", "name": "Cash", "type": "Asset", "normal": "Debit"})
    book.save_entry("entries", {
        "id": None,
        "date": "2026-01-02",
        "description": "Opening entry",
        "lines": [
            {"account": "100", "debit": 100, "credit": 0},
            {"account": "200", "debit": 0, "credit": 100},
        ],
    })

    assert db_path.exists()
    assert book.find("100")["name"] == "Cash"
    assert len(book.entries) == 1
    assert book.entries[0]["lines"][0]["account"] == "100"


def test_import_from_excel_inserts_entries(tmp_path):
    db_path = tmp_path / "import.db"
    spreadsheet = tmp_path / "journal.xlsx"
    pd.DataFrame([
        {
            "Date": "2026-01-03",
            "Description": "Invoice",
            "Account": "100",
            "Debit": 125.5,
            "Credit": 0,
        },
        {
            "Date": "2026-01-03",
            "Description": "Invoice",
            "Account": "200",
            "Debit": 0,
            "Credit": 125.5,
        },
    ]).to_excel(spreadsheet, index=False)

    book = Book(db_path)
    book.import_from_excel(str(spreadsheet), "entries")

    assert len(book.entries) == 1
    assert sum(line["debit"] for line in book.entries[0]["lines"]) == 125.5 * 100
    assert sum(line["credit"] for line in book.entries[0]["lines"]) == 125.5 * 100
