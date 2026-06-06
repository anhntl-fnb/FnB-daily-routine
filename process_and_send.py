#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FNB Daily Report — Processor & Sender (MCP version)

KHÔNG gọi Jira API. Claude query Jira qua Atlassian MCP rồi lưu kết quả
ra file JSON; script này đọc JSON đó → phân loại → gửi Google Chat.

Cách dùng:
    python process_and_send.py /tmp/jira_data.json

Format JSON đầu vào (Jira native):
{
  "new_issues":  [ {"key": "...", "fields": {...}}, ... ],
  "high_issues": [ {"key": "...", "fields": {...}}, ... ]
}
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

WEBHOOKS = {
    "team1": os.environ.get(
        "GCHAT_WEBHOOK_TEAM1",
        "https://chat.googleapis.com/v1/spaces/AAQAdLPTkFI/messages"
        "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        "&token=SNcVjMGe4OuysBvLvsmc6vhAg0yDn_irJynd-N2fNoA",
    ),
    "team2": os.environ.get(
        "GCHAT_WEBHOOK_TEAM2",
        "https://chat.googleapis.com/v1/spaces/AAQArf8Shaw/messages"
        "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        "&token=cywPmZTzBIis4TSFkhRDrZ3LczK_rLV2AsPjR1LJRgg",
    ),
    "team3": os.environ.get(
        "GCHAT_WEBHOOK_TEAM3",
        "https://chat.googleapis.com/v1/spaces/AAQAvpZ1kJ0/messages"
        "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        "&token=bWEx28vc9Qc6z9OAzbphsgMswJjY_MW04I-PX5-ZC50",
    ),
}

# ══════════════════════════════════════════════════════════════════════
#  TEAM / MODULE MAPPING
# ══════════════════════════════════════════════════════════════════════

TEAMS = {
    "team1": {
        "name": "Team 1 — Usability",
        "keywords": [
            "nhập hàng", "chuyển hàng", "xuất hủy", "kiểm kho",
            "trả hàng nhập", "trả nhập", "thiết lập", "tổng quan",
            "báo cáo", "mua hàng", "phiếu nhập", "phiếu xuất hủy",
            "phiếu chuyển", "nhap hang", "kiem kho", "bao cao",
            "setting", "report", "purchase", "inventory", "warehouse",
            "transfer stock", "xuat huy",
        ],
    },
    "team2": {
        "name": "Team 2 — Functionality",
        "keywords": [
            "hàng hóa", "hàng hoá", "foodapp", "food app",
            "grabfood", "grab food", "[gf", "gf -", "gf:", "trên gf",
            "shopeefood", "shopee food", "shopee", "grab",
            "khuyến mại", "khuyen mai", "emenu", "e-menu",
            "in bếp", "in kitchen", "đồng bộ", "dong bo",
            "kết nối", "ket noi", "sync", "baemin",
            "promotion", "kitchen", "appkn",
        ],
    },
    "team3": {
        "name": "Team 3 — Thuế và HĐDT",
        "keywords": [
            "thuế", "thue", "vat", "hddt", "hđdt",
            "hóa đơn điện tử", "hoá đơn điện tử",
            "hd dt", "einvoice", "e-invoice", "tax",
            "hóa đơn", "hoá đơn", "kê khai", "giảm thuế",
        ],
    },
}

# ══════════════════════════════════════════════════════════════════════
#  TICKET CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════

def classify(issue: dict) -> str:
    """Phân loại ticket vào team1 / team2 / team3 / other.

    Thứ tự ưu tiên: team3 (thuế/VAT đặc thù) → team1 → team2.
    """
    f = issue.get("fields", {})
    summary    = (f.get("summary") or "").lower()
    labels     = " ".join(f.get("labels", []) or []).lower()
    components = " ".join(
        (c or {}).get("name", "") for c in (f.get("components") or [])
    ).lower()
    haystack = f"{summary} {labels} {components}"

    for team_id in ("team3", "team1", "team2"):
        for kw in TEAMS[team_id]["keywords"]:
            if kw.lower() in haystack:
                return team_id
    return "other"

# ══════════════════════════════════════════════════════════════════════
#  MESSAGE FORMATTING
# ══════════════════════════════════════════════════════════════════════

PRIORITY_EMOJI = {
    "Highest": "🔴",
    "High":    "🟠",
    "Medium":  "🟡",
    "Low":     "🟢",
}
TICKET_BASE = "https://citigo.atlassian.net/browse"
DIVIDER = "━" * 36


def _safe_name(d) -> str:
    return (d or {}).get("name", "?") if isinstance(d, dict) else "?"


def _fmt_issue(issue: dict) -> str:
    f        = issue.get("fields", {})
    key      = issue.get("key", "?")
    summary  = f.get("summary") or "N/A"
    priority = _safe_name(f.get("priority"))
    status   = _safe_name(f.get("status"))
    p_em     = PRIORITY_EMOJI.get(priority, "⚪")
    key_link = f"<{TICKET_BASE}/{key}|{key}>"
    return f"{p_em} *{key_link}* [{status}]\n      _{summary}_"


def build_new_issue_msg(team_id: str, issues: list, date_str: str) -> str:
    tname = TEAMS.get(team_id, {}).get("name", "Khác")
    lines = [
        f"🆕  *NEW ISSUE — {date_str}*",
        DIVIDER,
        f"📋  {tname}  |  *{len(issues)} tickets*",
        "",
    ]
    if not issues:
        lines.append("✅  Không có ticket mới hôm qua.")
    else:
        lines.extend(_fmt_issue(i) for i in issues)
    return "\n".join(lines)


def build_high_issue_msg(team_id: str, issues: list) -> str:
    tname = TEAMS.get(team_id, {}).get("name", "Khác")
    lines = [
        f"⚠️  *HIGH ISSUES — Cần xử lý*",
        DIVIDER,
        f"📋  {tname}  |  *{len(issues)} tickets đang open*",
        "",
    ]
    if not issues:
        lines.append("✅  Không có ticket High/Highest đang mở.")
    else:
        lines.extend(_fmt_issue(i) for i in issues)
    return "\n".join(lines)


def build_other_msg(new_issues: list, high_issues: list) -> str:
    lines = [f"📦  *KHÁC — Chưa phân loại*", DIVIDER]
    if new_issues:
        lines.append(f"🆕  New ({len(new_issues)} tickets):")
        lines.extend(_fmt_issue(i) for i in new_issues)
    if high_issues:
        lines.append(f"\n⚠️  High ({len(high_issues)} tickets):")
        lines.extend(_fmt_issue(i) for i in high_issues)
    if not new_issues and not high_issues:
        lines.append("✅  Không có ticket nào.")
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════
#  GOOGLE CHAT SENDER
# ══════════════════════════════════════════════════════════════════════

def send_gchat(webhook_url: str, text: str, label: str = "") -> bool:
    if not webhook_url:
        print(f"      ⚠️  [{label}] Webhook chưa cấu hình — bỏ qua.")
        return False
    try:
        r = requests.post(webhook_url, json={"text": text}, timeout=15)
        if r.status_code == 200:
            print(f"      ✅  [{label}] Gửi thành công")
            return True
        print(f"      ❌  [{label}] HTTP {r.status_code}: {r.text[:120]}")
        return False
    except Exception as exc:
        print(f"      ❌  [{label}] Lỗi: {exc}")
        return False

# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    # ── Đọc file JSON ────────────────────────────────────────────────
    json_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/jira_data.json"

    print(f"\n{'═'*56}")
    print(f"  FNB Daily Report (MCP)  |  {datetime.now().strftime('%H:%M %d/%m/%Y')}")
    print(f"  Đọc dữ liệu: {json_path}")
    print(f"{'═'*56}\n")

    if not os.path.exists(json_path):
        print(f"❌  Không tìm thấy file {json_path}")
        print("    Claude cần query Jira qua MCP và lưu kết quả vào file này trước.")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as fp:
            data = json.load(fp)
    except Exception as exc:
        print(f"❌  Lỗi đọc JSON: {exc}")
        sys.exit(1)

    new_issues  = data.get("new_issues", [])
    high_issues = data.get("high_issues", [])
    date_str    = data.get("date") or (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")

    print(f"📥  Đọc được: {len(new_issues)} new  |  {len(high_issues)} high\n")

    # ── Phân loại ────────────────────────────────────────────────────
    new_by_team  = defaultdict(list)
    high_by_team = defaultdict(list)
    for i in new_issues:
        new_by_team[classify(i)].append(i)
    for i in high_issues:
        high_by_team[classify(i)].append(i)

    print("📊  Phân bổ:")
    for tid, tinfo in TEAMS.items():
        print(f"    {tinfo['name']}: {len(new_by_team[tid])} new  |  {len(high_by_team[tid])} high")
    print(f"    Khác: {len(new_by_team['other'])} new  |  {len(high_by_team['other'])} high\n")

    # ── Gửi từng team ────────────────────────────────────────────────
    for tid in ("team1", "team2", "team3"):
        wh = WEBHOOKS.get(tid, "")
        print(f"📤  {TEAMS[tid]['name']} ...")
        send_gchat(wh, build_new_issue_msg(tid, new_by_team[tid], date_str),
                   label=f"{tid}/new-issue")
        send_gchat(wh, build_high_issue_msg(tid, high_by_team[tid]),
                   label=f"{tid}/high-issue")

    # ── Nhóm "Khác" → webhook đầu tiên có sẵn (Team1) ───────────────
    other_new  = new_by_team.get("other", [])
    other_high = high_by_team.get("other", [])
    if other_new or other_high:
        print(f"\n📤  Nhóm Khác ({len(other_new)} new / {len(other_high)} high) ...")
        msg = build_other_msg(other_new, other_high)
        for tid in ("team1", "team2", "team3"):
            if WEBHOOKS.get(tid):
                send_gchat(WEBHOOKS[tid], msg, label="other")
                break

    print(f"\n{'═'*56}")
    print("  ✅  Hoàn thành!")
    print(f"{'═'*56}\n")


if __name__ == "__main__":
    main()
