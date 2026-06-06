# FNB Daily Report — Routine (MCP version)

Báo cáo board FNB hàng ngày 8h sáng. Query Jira qua **Atlassian MCP connector**
(không dùng API token → hết lỗi 403), phân loại theo team, gửi Google Chat.

## Cấu trúc

```
fnb-daily-routine/
├── CLAUDE.md            ← Hướng dẫn Claude (query MCP → lưu JSON → chạy script)
├── process_and_send.py  ← Đọc JSON, phân loại, gửi 3 webhook
├── requirements.txt
└── README.md
```

## Luồng hoạt động

```
Routine 8h
   ↓
Claude query Jira qua Atlassian MCP (2 JQL)
   ↓
Claude lưu /tmp/jira_data.json (format Jira native)
   ↓
python process_and_send.py /tmp/jira_data.json
   ↓
Phân loại Team1/2/3/Khác → gửi Google Chat
```

## Setup Routine

| Mục | Giá trị |
|---|---|
| Repository | `anhntl-fnb/fnb-daily-routine` |
| Schedule | Daily 08:00 (GMT+7) |
| **Connectors** | **BẬT Atlassian** (bắt buộc — dùng để query Jira) |
| Environment setup script | `pip install requests` |
| Env vars | KHÔNG cần token nữa |

## Khác biệt so với bản cũ

- ❌ Bỏ `daily_report.py` (gọi REST API + token → 403)
- ✅ Dùng `process_and_send.py` (chỉ xử lý + gửi, Claude lo phần query qua MCP)
- ✅ KHÔNG cần `JIRA_EMAIL` / `JIRA_API_TOKEN`
- ⚠️ BẮT BUỘC bật connector **Atlassian** trong routine

## Phân loại module

| Team | Modules |
|---|---|
| Team 1 | Nhập hàng, Chuyển hàng, Xuất hủy, Kiểm kho, Trả hàng nhập, Thiết lập, Tổng quan, Báo cáo |
| Team 2 | Hàng hóa, FoodApp, GrabFood, ShopeeFood, Khuyến mại, Emenu, In bếp, Đồng bộ |
| Team 3 | Thuế, VAT, HĐDT |
| Khác | Không khớp keyword → gửi vào webhook Team1 |

Thứ tự ưu tiên phân loại: Team3 → Team1 → Team2 (tránh nhầm VAT vào Team2).
