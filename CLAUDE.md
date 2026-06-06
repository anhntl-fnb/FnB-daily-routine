# FNB Daily Report — Routine (MCP version)

Báo cáo board FNB hàng ngày. **Dùng Atlassian MCP connector** để query Jira
(KHÔNG dùng API token — đã bỏ vì lỗi 403).

---

## Bước 1: Query Jira qua Atlassian MCP

cloudId của citigo: `3fc829f0-cfb5-431f-bd71-598bd3816b2f`

Dùng tool `searchJiraIssuesUsingJql` chạy 2 query. Với mỗi query, lấy các
fields: `summary, status, priority, issuetype, created, labels, components`.
Lấy tối đa 100 kết quả mỗi query (phân trang nếu cần).

**Query A — Tickets mới tạo HÔM QUA:**
```
project = FNB AND created >= startOfDay(-1) AND created < startOfDay() ORDER BY priority ASC, created DESC
```

**Query B — High/Highest đang open:**
```
project = FNB AND priority in (High, Highest) AND status in (New, "In Progress", Considering, "Ready for staging") ORDER BY priority ASC, created ASC
```

---

## Bước 2: Lưu kết quả ra file JSON

Ghi file `/tmp/jira_data.json` theo ĐÚNG cấu trúc sau (giữ nguyên format Jira native,
vì script đọc theo `issue["fields"]["..."]`):

```json
{
  "date": "DD/MM/YYYY",
  "new_issues": [
    {
      "key": "FNB-XXXX",
      "fields": {
        "summary": "tiêu đề ticket",
        "priority":  {"name": "Medium"},
        "issuetype": {"name": "Production Bug"},
        "status":    {"name": "New"},
        "labels":    ["label1"],
        "components":[{"name": "..."}]
      }
    }
  ],
  "high_issues": [ ... cùng cấu trúc ... ]
}
```

Quy tắc:
- Toàn bộ kết quả Query A → mảng `new_issues`
- Toàn bộ kết quả Query B → mảng `high_issues`
- `date` = ngày hôm qua (DD/MM/YYYY)
- Field nào thiếu/null → để `{"name": ""}` hoặc `[]`, KHÔNG bỏ trống key

---

## Bước 3: Chạy script gửi báo cáo

```bash
pip install requests
python process_and_send.py /tmp/jira_data.json
```

---

## Bước 4: Xác nhận

Đọc log, báo lại:
- Số ticket new / high đọc được
- Phân bổ theo Team1 / Team2 / Team3 / Khác
- Trạng thái gửi webhook (✅/❌) cho cả 3 team
