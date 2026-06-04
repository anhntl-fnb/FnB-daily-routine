#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FNB Daily Board Report
Chạy mỗi ngày 8:00 sáng qua Claude Code Routine.
Query Jira FNB → Phân loại theo team → Gửi Google Chat.
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from collections import defaultdict
from base64 import b64encode

# ══════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════════════

JIRA_BASE  = os.environ.get("JIRA_BASE_URL", "https://citigo.atlassian.net")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "")
JIRA_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
PROJECT    = "FNB"
BOARD_URL  = "https://citigo.atlassian.net/jira/software/c/projects/FNB/boards/7078"

# Thêm webhook Team1 / Team3 vào env var khi có
WEBHOOKS = {
    "team1": os.environ.get("GCHAT_WEBHOOK_TEAM1", ""),
    "team2": os.environ.get(
        "GCHAT_WEBHOOK_TEAM2",
        "https://chat.googleapis.com/v1/spaces/AAQArf8Shaw/messages"
        "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
        "&token=cywPmZTzBIis4TSFkhRDrZ3LczK_rLV2AsPjR1LJRgg",
    ),
    "team3": os.environ.get("GCHAT_WEBHOOK_TEAM3", ""),
}

# ══════════════════════════════════════════════════════════════════════
#  TEAM / MODULE MAPPING
# ══════════════════════════════════════════════════════════════════════

TEAMS = {
    "team1": {
        "name": "Team 1 — Kho & Báo cáo",
        "modules": [
            "Nhập hàng", "Chuyển hàng", "Xuất hủy", "Kiểm kho",
            "Trả hàng nhập", "Thiết lập", "Tổng quan", "Báo cáo",
        ],
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
        "name": "Team 2 — Hàng hóa & F&B App",
        "modules": [
            "Hàng hóa", "FoodApp", "GrabFood", "ShopeeFood",
            "Khuyến mại", "Emenu", "In bếp", "Đồng bộ",
        ],
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
        "name": "Team 3 — Thuế & HĐDT",
        "modules": ["Thuế", "VAT", "HĐDT"],
        "keywords": [
            "thuế", "thue", "vat", "hddt", "hđdt",
            "hóa đơn điện tử", "hoá đơn điện tử",
            "hd dt", "einvoice", "e-invoice", "tax",
            "hóa đơn", "hoá đơn", "kê khai", "giảm thuế",
        ],
    },
}

# ══════════════════════════════════════════════════════════════════════
#  JIRA API HELPERS
# ══════════════════════════════════════════════════════════════════════

def _auth_headers() -> dict:
    token = b64encode(f"{JIRA_EMAIL}:{JIRA_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def jira_search(jql: str, fields: list, max_results: int = 300) -> list:
    """Paginate qua Jira search API và trả về toàn bộ issues."""
    url = f"{JIRA_BASE}/rest/api/3/search"
    issues, start = [], 0

    while True:
        payload = {
            "jql": jql,
            "fields": fields,
            "maxResults": min(100, max_results - len(issues)),
            "startAt": start,
        }
        r = requests.post(url, headers=_auth_headers(), json=payload, timeout=30)
        r.raise_for_status()
        data   = r.json()
        batch  = data.get("issues", [])
        issues.extend(batch)
        total  = data.get("total", 0)

        if not batch or len(issues) >= total or len(issues) >= max_results:
            break
        start += len(batch)

    return issues

# ══════════════════════════════════════════════════════════════════════
#  TICKET CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════

def classify(issue: dict) -> str:
    """Phân loại ticket vào team1 / team2 / team3 / other.

    Thứ tự ưu tiên: team3 (thuế/VAT rất đặc thù) → team1 → team2.
    Tránh nhầm ticket VAT vào team2 do keyword 'hàng hóa'.
    """
    f = issue.get("fields", {})
    summary    = f.get("summary", "").lower()
    labels     = " ".join(f.get("labels", [])).lower()
    components = " ".join(c.get("name", "") for c in f.get("components", [])).lower()
    haystack   = f"{summary} {labels} {components}"

    for team_id in ("team3", "team1", "team2"):
        team = TEAMS[team_id]
        for kw in team["keywords"]:
            if kw.lower() in haystack:
                return team_id
    return "other"

# ══════════════════════════════════════════════════════════════════════
#  MESSAGE FORMATTING
# ══════════════════════════════════════════════════════════════════════

PRIORITY_EMOJI = {
    "Highest": "🔴", "Critical": "🔴",
    "High":    "🟠", "Medium":   "🟡", "Low": "⚪",
}
TYPE_EMOJI = {
    "Production Bug":    "🐛",
    "Bug-In-Development":"🔧",
    "Support":           "📞",
    "Task":              "✅",
    "Sub-task":          "🔗",
}
DIVIDER = "━" * 36


def _fmt_issue(issue: dict) -> str:
    f        = issue["fields"]
    key      = issue["key"]
    summary  = (f.get("summary") or "N/A")[:75]
    priority = (f.get("priority") or {}).get("name", "?")
    itype    = (f.get("issuetype") or {}).get("name", "?")
    status   = (f.get("status") or {}).get("name", "?")
    p_em     = PRIORITY_EMOJI.get(priority, "⚪")
    t_em     = TYPE_EMOJI.get(itype, "📌")
    return f"{p_em}{t_em} *{key}* [{status}]\n      _{summary}_"


def build_new_issue_msg(team_id: str, issues: list, date_str: str) -> str:
    tname = TEAMS.get(team_id, {}).get("name", "Khác")
    count = len(issues)
    lines = [
        f"🆕  *NEW ISSUE — {date_str}*",
        DIVIDER,
        f"📋  {tname}  |  *{count} tickets*",
        "",
    ]
    if not issues:
        lines.append("✅  Không có ticket mới hôm qua.")
    else:
        lines.extend(_fmt_issue(i) for i in issues)
    lines += ["", f"🔗  {BOARD_URL}"]
    return "\n".join(lines)


def build_high_issue_msg(team_id: str, issues: list) -> str:
    tname = TEAMS.get(team_id, {}).get("name", "Khác")
    count = len(issues)
    lines = [
        f"⚠️  *HIGH ISSUES — Cần xử lý*",
        DIVIDER,
        f"📋  {tname}  |  *{count} tickets đang open*",
        "",
    ]
    if not issues:
        lines.append("✅  Không có ticket High/Highest đang mở.")
    else:
        lines.extend(_fmt_issue(i) for i in issues)
    lines += ["", f"🔗  {BOARD_URL}"]
    return "\n".join(lines)


def build_other_msg(new_issues: list, high_issues: list, date_str: str) -> str:
    lines = [
        f"📦  *KHÁC — Chưa phân loại*",
        DIVIDER,
    ]
    if new_issues:
        lines.append(f"🆕  New ({len(new_issues)} tickets):")
        lines.extend(_fmt_issue(i) for i in new_issues)
    if high_issues:
        lines.append(f"\n⚠️  High ({len(high_issues)} tickets):")
        lines.extend(_fmt_issue(i) for i in high_issues)
    if not new_issues and not high_issues:
        lines.append("✅  Không có ticket nào.")
    lines += ["", f"🔗  {BOARD_URL}"]
    return "\n".join(lines)

# ══════════════════════════════════════════════════════════════════════
#  GOOGLE CHAT SENDER
# ══════════════════════════════════════════════════════════════════════

def send_gchat(webhook_url: str, text: str, label: str = "") -> bool:
    if not webhook_url:
        print(f"      ⚠️  [{label}] Webhook chưa được cấu hình — bỏ qua.")
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
    now       = datetime.now()
    yesterday = now - timedelta(days=1)
    date_str  = yesterday.strftime("%d/%m/%Y")
    ymd_y     = yesterday.strftime("%Y-%m-%d")
    ymd_t     = now.strftime("%Y-%m-%d")

    print(f"\n{'═'*56}")
    print(f"  FNB Daily Report  |  {now.strftime('%H:%M  %d/%m/%Y')}")
    print(f"  Báo cáo ngày: {date_str}")
    print(f"{'═'*56}\n")

    # ── Validate credentials ─────────────────────────────────────────
    if not JIRA_EMAIL or not JIRA_TOKEN:
        print("❌  Thiếu JIRA_EMAIL hoặc JIRA_API_TOKEN.")
        print("    Cấu hình trong credential vault của Routine rồi chạy lại.")
        sys.exit(1)

    FIELDS = [
        "summary", "status", "priority", "issuetype",
        "created", "labels", "components", "assignee",
    ]

    # ── Query 1: Tickets tạo hôm qua ────────────────────────────────
    print(f"📥  Query 1 — Tickets mới ngày {date_str} ...")
    jql_new = (
        f'project = {PROJECT} '
        f'AND created >= "{ymd_y}" '
        f'AND created < "{ymd_t}" '
        f'ORDER BY priority ASC, created DESC'
    )
    new_issues = jira_search(jql_new, FIELDS)
    print(f"    → Tìm thấy {len(new_issues)} tickets\n")

    # ── Query 2: High/Highest đang open ─────────────────────────────
    print("📥  Query 2 — High/Highest priority đang open ...")
    jql_high = (
        f'project = {PROJECT} '
        f'AND priority in (High, Highest) '
        f'AND status in (New, "In Progress", Considering, "Ready for staging") '
        f'ORDER BY priority ASC, created ASC'
    )
    high_issues = jira_search(jql_high, FIELDS)
    print(f"    → Tìm thấy {len(high_issues)} tickets\n")

    # ── Classify ─────────────────────────────────────────────────────
    new_by_team  = defaultdict(list)
    high_by_team = defaultdict(list)
    for i in new_issues:
        new_by_team[classify(i)].append(i)
    for i in high_issues:
        high_by_team[classify(i)].append(i)

    # In phân bổ
    print("📊  Phân bổ tickets:")
    for tid, tinfo in TEAMS.items():
        n = len(new_by_team[tid])
        h = len(high_by_team[tid])
        print(f"    {tinfo['name']}: {n} new  |  {h} high")
    print(f"    Khác: {len(new_by_team['other'])} new  |  {len(high_by_team['other'])} high\n")

    # ── Gửi từng team ────────────────────────────────────────────────
    for tid in ("team1", "team2", "team3"):
        wh    = WEBHOOKS.get(tid, "")
        tname = TEAMS[tid]["name"]
        print(f"📤  {tname} ...")

        new_msg  = build_new_issue_msg(tid, new_by_team[tid],  date_str)
        high_msg = build_high_issue_msg(tid, high_by_team[tid])

        send_gchat(wh, new_msg,  label=f"{tid}/new-issue")
        send_gchat(wh, high_msg, label=f"{tid}/high-issue")

    # ── Gửi nhóm "Khác" → webhook đầu tiên có sẵn ───────────────────
    other_new  = new_by_team.get("other", [])
    other_high = high_by_team.get("other", [])

    if other_new or other_high:
        print(f"\n📤  Nhóm Khác ({len(other_new)} new / {len(other_high)} high) ...")
        other_msg = build_other_msg(other_new, other_high, date_str)
        for tid in ("team1", "team2", "team3"):
            wh = WEBHOOKS.get(tid, "")
            if wh:
                send_gchat(wh, other_msg, label="other")
                break

    print(f"\n{'═'*56}")
    print("  ✅  Hoàn thành!")
    print(f"{'═'*56}\n")


if __name__ == "__main__":
    main()
