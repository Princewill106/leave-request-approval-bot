"""Leave Request Approval Bot."""
import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def parse_dates(text: str, year: int):
    t = text.lower()
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:([a-z]{3})[a-z]*)?\s*(?:to|-|until|till)\s*"
                  r"(\d{1,2})(?:st|nd|rd|th)?\s*([a-z]{3})[a-z]*", t)
    if not m:
        return None
    d1, m1, d2, m2 = m.groups()
    m1 = m1 if m1 in MONTHS else m2
    return date(year, MONTHS[m1], int(d1)), date(year, MONTHS[m2], int(d2))


def working_days(start, end, holidays):
    d, days = start, []
    while d <= end:
        if d.weekday() < 5 and d.isoformat() not in holidays:
            days.append(d)
        d += timedelta(days=1)
    return days


def decide(req, cfg, approved):
    span = parse_dates(req["text"], cfg["year"])
    if not span:
        return {"decision": "CLARIFY", "reason": "couldn't read the dates; please use e.g. '20 Oct to 24 Oct'"}
    days = working_days(*span, set(cfg["holidays"]))
    emp = cfg["staff"][req["employee"]]
    if len(days) > emp["balance"]:
        return {"decision": "DECLINE", "days": len(days),
                "reason": f"needs {len(days)} days but balance is {emp['balance']}"}
    for b in cfg["blackouts"]:
        b0, b1 = date.fromisoformat(b["from"]), date.fromisoformat(b["to"])
        if any(b0 <= d <= b1 for d in days) and emp["team"] in b["teams"]:
            return {"decision": "DECLINE", "days": len(days), "reason": f"overlaps blackout: {b['name']}"}
    team = [n for n, s in cfg["staff"].items() if s["team"] == emp["team"]]
    for d in days:
        away = sum(1 for n in team if n != req["employee"] and d.isoformat() in approved.get(n, []))
        if len(team) - away - 1 < cfg["min_on_duty"][emp["team"]]:
            return {"decision": "ROUTE TO MANAGER", "days": len(days),
                    "reason": f"{emp['team']} would be below minimum cover on {d:%a %d %b}"}
    return {"decision": "APPROVED", "days": len(days), "dates": [d.isoformat() for d in days],
            "reason": f"{len(days)} working days; balance after: {emp['balance'] - len(days)}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="sample_requests.json")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path("config.json").read_text())
    approved = {k: list(v) for k, v in cfg["already_approved"].items()}
    for r in json.loads(Path(a.input).read_text()):
        d = decide(r, cfg, approved)
        if d["decision"] == "APPROVED":
            approved.setdefault(r["employee"], []).extend(d["dates"])
            cfg["staff"][r["employee"]]["balance"] -= d["days"]
        print(f"{r['employee']:<8} \"{r['text']}\"\n         -> {d['decision']}: {d['reason']}\n")
    Path("output").mkdir(exist_ok=True)
    Path("output/leave_calendar.json").write_text(json.dumps(approved, indent=2))
    print("Balances:", {n: s["balance"] for n, s in cfg["staff"].items()})


if __name__ == "__main__":
    main()
