# FNB Daily Report — Setup Guide

## Cấu trúc repo

```
fnb-daily-routine/
├── CLAUDE.md          ← Routine prompt (Claude đọc file này)
├── daily_report.py    ← Script chính
├── requirements.txt
├── .env.example       ← Mẫu biến môi trường
└── README.md
```

---

## Luồng hoạt động

```
Routine chạy 8h
    ↓
Claude đọc CLAUDE.md
    ↓
pip install + python daily_report.py
    ↓
Query Jira: tickets hôm qua + High/Highest open
    ↓
Phân loại → Team1 / Team2 / Team3 / Khác
    ↓
POST Google Chat webhook × 3 teams
```

---

## Setup Routine trên claude.ai/code

### Bước 1: Push repo lên GitHub

```bash
git init
git add .
git commit -m "feat: FNB daily report routine"
git remote add origin https://github.com/<your-org>/fnb-daily-routine.git
git push -u origin main
```

### Bước 2: Lấy Jira API Token

1. Vào https://id.atlassian.com/manage-profile/security/api-tokens
2. Nhấn **Create API token**
3. Đặt tên: `claude-routine-fnb`
4. Copy token (chỉ hiển thị 1 lần)

### Bước 3: Tạo Routine tại claude.ai/code/routines

| Field | Giá trị |
|---|---|
| **Name** | FNB Daily Board Report |
| **Repository** | `<your-org>/fnb-daily-routine` |
| **Schedule** | Daily, 8:00 AM (ICT = UTC+7 → 01:00 UTC) |
| **Prompt** | *(để trống — Claude sẽ đọc CLAUDE.md)* |

### Bước 4: Thêm Environment Variables trong Routine

```
JIRA_EMAIL          = your-email@citigo.vn
JIRA_API_TOKEN      = <token từ bước 2>
GCHAT_WEBHOOK_TEAM2 = https://chat.googleapis.com/v1/spaces/AAQArf8Shaw/...
```
*(GCHAT_WEBHOOK_TEAM1 và TEAM3 thêm sau khi có webhook)*

---

## Output mẫu trong Google Chat

### 🆕 NEW ISSUE — 03/06/2026
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Team 2 — Hàng hóa & F&B App | 12 tickets

🐛✅ FNB-94821 [Temporary]
   App kết nối ver 26.6.7 không mở lên
🔧📌 FNB-94807 [In Progress]
   In bếp đơn 15-61 thiếu món
...
```

### ⚠️ HIGH ISSUES — Cần xử lý
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Team 2 — Hàng hóa & F&B App | 5 tickets

🟠📞 FNB-94817 [New]
   Chuyển về giao diện cũ FNB v...
🟠🔧 FNB-94782 [New]
   Thiếu logic filter theo Tài khoản ngân hàng
...
```

---

## Thêm webhook Team1 / Team3

Khi đã tạo webhook cho Team1 và Team3:

1. Vào **claude.ai/code/routines** → edit routine
2. Thêm env var:
   ```
   GCHAT_WEBHOOK_TEAM1 = https://chat.googleapis.com/...
   GCHAT_WEBHOOK_TEAM3 = https://chat.googleapis.com/...
   ```

---

## Phân loại module

| Team | Modules |
|---|---|
| **Team 1** | Nhập hàng, Chuyển hàng, Xuất hủy, Kiểm kho, Trả hàng nhập, Thiết lập, Tổng quan, Báo cáo |
| **Team 2** | Hàng hóa, FoodApp, GrabFood, ShopeeFood, Khuyến mại, Emenu, In bếp, Đồng bộ |
| **Team 3** | Thuế, VAT, HĐDT |
| **Khác** | Không khớp keyword → gửi vào webhook đầu tiên có sẵn |

Để thêm keyword mới, chỉnh mảng `keywords` trong `TEAMS` ở `daily_report.py`.
