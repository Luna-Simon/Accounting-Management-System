TYPES = ["Asset", "Liability", "Equity", "Revenue", "Cost of Sales", "Expense"]

DEFAULT_NORMAL = {
    "Asset": "Debit",
    "Liability": "Credit",
    "Equity": "Credit",
    "Revenue": "Credit",
    "Cost of Sales": "Debit",
    "Expense": "Debit",
}

INCOME_TYPES = ("Revenue", "Cost of Sales", "Expense")


def sums(*journals):
    totals = {}
    for journal in journals:
        for entry in journal:
            for line in entry["lines"]:
                debit, credit = totals.get(line["account"], (0, 0))
                totals[line["account"]] = (debit + line["debit"], credit + line["credit"])
    return totals


def side(net):
    return (net, 0) if net >= 0 else (0, -net)


def trial_balance(book, adjusted=False):
    journals = (book.entries, book.adjustments) if adjusted else (book.entries,)
    totals = sums(*journals)
    rows = []
    for account in book.accounts:
        if account["code"] in totals:
            debit, credit = totals[account["code"]]
            rows.append((account, *side(debit - credit)))
    return rows


def worksheet(book):
    posted = sums(book.entries)
    adjusting = sums(book.adjustments)
    rows = []
    for account in book.accounts:
        code = account["code"]
        if code not in posted and code not in adjusting:
            continue
        trial = side(posted.get(code, (0, 0))[0] - posted.get(code, (0, 0))[1])
        adjustment = adjusting.get(code, (0, 0))
        adjusted = side(trial[0] - trial[1] + adjustment[0] - adjustment[1])
        income = account["type"] in INCOME_TYPES
        statement = adjusted if income else (0, 0)
        position = (0, 0) if income else adjusted
        rows.append((account, *trial, *adjustment, *adjusted, *statement, *position))
    return rows


def worksheet_summary(rows):
    totals = [sum(row[i] for row in rows) for i in range(1, 11)]
    net = totals[7] - totals[6]
    final = list(totals)
    if net >= 0:
        final[6] += net
        final[9] += net
    else:
        final[7] -= net
        final[8] -= net
    return totals, net, final


def income_statement(book):
    adjusted = sums(book.entries, book.adjustments)
    groups = {"Revenue": [], "Cost of Sales": [], "Expense": []}
    for account in book.accounts:
        kind = account["type"]
        if kind in groups and account["code"] in adjusted:
            debit, credit = adjusted[account["code"]]
            amount = credit - debit if kind == "Revenue" else debit - credit
            groups[kind].append((account["name"], amount))
    revenue = sum(amount for _, amount in groups["Revenue"])
    cost = sum(amount for _, amount in groups["Cost of Sales"])
    expenses = sum(amount for _, amount in groups["Expense"])
    return {
        "revenue": groups["Revenue"],
        "cost": groups["Cost of Sales"],
        "expenses": groups["Expense"],
        "revenue_total": revenue,
        "cost_total": cost,
        "gross": revenue - cost,
        "expense_total": expenses,
        "net": revenue - cost - expenses,
    }
