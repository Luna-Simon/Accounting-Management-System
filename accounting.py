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

CONTRA_ASSET_ACCOUNTS = {"accumulated depreciation"}


def calc_dep(cost, residual, life_years, months=1):
    from decimal import Decimal, ROUND_HALF_UP
    cost = Decimal(str(cost))
    residual = Decimal(str(residual))
    life = Decimal(str(life_years))
    annual = (cost - residual) / life
    monthly = annual / Decimal(12)
    amt = monthly * Decimal(months)
    return int((amt * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def make_dep(dep_code, acc_code, amt_cents, desc="Depreciation expense"):
    return {
        "id": None,
        "date": "",
        "description": desc,
        "lines": [
            {"account": dep_code, "debit": amt_cents, "credit": 0},
            {"account": acc_code, "debit": 0, "credit": amt_cents},
        ],
    }


def agg(*jrnls):
    totals = {}
    for j in jrnls:
        for e in j:
            for ln in e["lines"]:
                dr, cr = totals.get(ln["account"], (0, 0))
                totals[ln["account"]] = (dr + ln["debit"], cr + ln["credit"])
    return totals


def which_side(net):
    return (net, 0) if net >= 0 else (0, -net)


def tb(bk, adjusted=False):
    j = (bk.txns, bk.adjts) if adjusted else (bk.txns,)
    totals = agg(*j)
    rows = []
    amap = {a["code"]: a for a in bk.accts}
    all_codes = set(totals.keys()) | set(amap.keys())
    for code in sorted(all_codes):
        a = amap.get(code, {"code": code, "name": code, "type": "", "normal": ""})
        dr, cr = totals.get(code, (0, 0)) if code in totals else (0, 0)
        rows.append((a, *which_side(dr - cr)))
    return rows


def ws(bk):
    posted = agg(bk.txns)
    adjusting = agg(bk.adjts)
    rows = []
    for a in bk.accts:
        code = a["code"]
        if code not in posted and code not in adjusting:
            continue
        p = posted.get(code, (0, 0))
        adj = adjusting.get(code, (0, 0))
        tr = which_side(p[0] - p[1])
        adjd = which_side(tr[0] - tr[1] + adj[0] - adj[1])
        income = a["type"] in INCOME_TYPES
        st = adjd if income else (0, 0)
        pos = (0, 0) if income else adjd
        rows.append((a, *tr, *adj, *adjd, *st, *pos))
    return rows


def ws_detail(bk):
    posted = agg(bk.txns)
    adjusting = agg(bk.adjts)
    amap = {a["code"]: a for a in bk.accts}
    all_codes = set(posted.keys()) | set(adjusting.keys()) | set(amap.keys())
    rows = []
    for code in sorted(all_codes):
        a = amap.get(code, {"code": code, "name": code, "type": "", "normal": ""})
        p = posted.get(code, (0, 0))
        adj = adjusting.get(code, (0, 0))
        tr = which_side(p[0] - p[1])
        adjd = which_side(tr[0] - tr[1] + adj[0] - adj[1])
        income = a["type"] in INCOME_TYPES
        st = adjd if income else (0, 0)
        pos = (0, 0) if income else adjd
        rows.append({
            "account": a,
            "tb_dr": tr[0], "tb_cr": tr[1],
            "adj_dr": adj[0], "adj_cr": adj[1],
            "adj_tb_dr": adjd[0], "adj_tb_cr": adjd[1],
            "is_dr": st[0], "is_cr": st[1],
            "bs_dr": pos[0], "bs_cr": pos[1],
        })
    return rows


def ws_totals(rows):
    keys = ["tb_dr", "tb_cr", "adj_dr", "adj_cr", "adj_tb_dr", "adj_tb_cr",
            "is_dr", "is_cr", "bs_dr", "bs_cr"]
    tots = [sum(r[k] for r in rows) for k in keys]
    net = tots[7] - tots[6]
    fin = list(tots)
    if net >= 0:
        fin[6] += net
        fin[9] += net
    else:
        fin[7] -= net
        fin[8] -= net
    return tots, net, fin


def pl(bk):
    adjusted = agg(bk.txns, bk.adjts)
    groups = {"Revenue": [], "Cost of Sales": [], "Expense": []}
    for a in bk.accts:
        k = a["type"]
        if k in groups and a["code"] in adjusted:
            dr, cr = adjusted[a["code"]]
            amt = cr - dr if k == "Revenue" else dr - cr
            groups[k].append((a["name"], amt))
    rev = sum(amt for _, amt in groups["Revenue"])
    cogs = sum(amt for _, amt in groups["Cost of Sales"])
    exps = sum(amt for _, amt in groups["Expense"])
    return {
        "revenue": groups["Revenue"],
        "cost": groups["Cost of Sales"],
        "expenses": groups["Expense"],
        "revenue_total": rev,
        "cost_total": cogs,
        "gross": rev - cogs,
        "expense_total": exps,
        "net": rev - cogs - exps,
    }


def bs(bk):
    adjusted = agg(bk.txns, bk.adjts)
    is_data = pl(bk)
    net_income = is_data["net"]

    assets = []
    liabs = []
    equity = []

    for a in bk.accts:
        k = a["type"]
        code = a["code"]
        if code not in adjusted:
            continue
        dr, cr = adjusted[code]
        if k == "Asset":
            amt = dr - cr
            if amt != 0:
                assets.append((a["name"], amt))
        elif k == "Liability":
            amt = cr - dr
            if amt != 0:
                liabs.append((a["name"], amt))
        elif k == "Equity":
            amt = cr - dr
            if amt != 0:
                equity.append((a["name"], amt))

    asset_total = sum(amt for _, amt in assets)
    liability_total = sum(amt for _, amt in liabs)
    equity_total = sum(amt for _, amt in equity) + net_income

    return {
        "assets": assets,
        "liabilities": liabs,
        "equity": equity,
        "asset_total": asset_total,
        "liability_total": liability_total,
        "equity_total": equity_total,
        "net_income": net_income,
        "total_assets": asset_total,
        "total_liabilities_equity": liability_total + equity_total,
    }
