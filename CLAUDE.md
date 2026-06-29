# FNB Daily Report — Routine (MCP version)

Báo cáo board FNB hàng ngày. **Dùng Atlassian MCP connector** để query Jira
(KHÔNG dùng API token — đã bỏ vì lỗi 403).

---

## Bước 1: Query Jira qua Atlassian MCP

cloudId của citigo: `3fc829f0-cfb5-431f-bd71-598bd3816b2f`

Dùng tool `searchJiraIssuesUsingJql` chạy 2 query. Với mỗi query, lấy các
fields: `summary, status, priority, issuetype, created, labels, components, Subteam_FnB, Module FnB 2.0`.
Lấy tối đa 100 kết quả mỗi query (phân trang nếu cần).

**Query A — Bug mới tạo HÔM QUA:**
```
project = PST AND "Sản phẩm" = FnB AND issuetype != "New Feature" AND created >= startOfDay(-1) AND created < startOfDay() ORDER BY priority ASC, created DESC
```

**Query B — Bug đang open, ưu tiên cao:**
```
project = PST AND "Sản phẩm" = FnB AND status in (Open, Triaged, Transfer, "In Progress", Reopened, Testing) AND (priority in (High, Highest) OR "Impact scope" > 1) ORDER BY priority ASC, created ASC
```

> Lưu ý: `"Impact scope"` là custom field. Nếu JQL báo lỗi không nhận field này
> (vd "Field 'Impact scope' does not exist"), thử thay bằng tên đúng hoặc
> `cf[XXXXX]` (ID custom field). Nếu field là dạng dropdown chứ không phải số,
> điều kiện `> 1` có thể cần đổi (vd `in ("2","3",...)`).

---

## Bước 2: Lưu kết quả ra file JSON

Ghi file `/tmp/jira_data.json` theo ĐÚNG cấu trúc sau (giữ nguyên format Jira native,
vì script đọc theo `issue["fields"]["..."]`):

```json
{
  "date": "DD/MM/YYYY",
  "new_issues": [
    {
      "key": "PST-XXXX",
      "fields": {
        "summary": "tiêu đề ticket",
        "priority":  {"name": "Medium"},
        "issuetype": {"name": "Bug"},
        "status":    {"name": "Open"},
        "labels":    ["label1"],
        "components":[{"name": "..."}],
        "subteam_fnb": "giá trị field Subteam_FnB (chuỗi, rỗng nếu không có)",
        "module_fnb": "giá trị field Module FnB (chuỗi, rỗng nếu không có)"
      }
    }
  ],
  "high_issues": [ ... cùng cấu trúc ... ]
}
```

Quy tắc:
- Toàn bộ kết quả Query A → mảng `new_issues`
- Toàn bộ kết quả Query B → mảng `high_issues`
- `subteam_fnb`: giá trị (text) của field Subteam_FnB. Nếu là object có `.value`
  thì lấy `.value`; rỗng thì `""`.
- `module_fnb`: giá trị (text) của field **Module FnB 2.0** (vd "Hàng hóa",
  "Thuế & HĐDT", "Đơn hàng"...). Nếu là object có `.value` thì lấy `.value`;
  rỗng thì `""`. Script dùng field này để phân loại team (ưu tiên hơn keyword).
- `date` = ngày hôm qua (DD/MM/YYYY)
- Field nào thiếu/null → để `{"name": ""}` hoặc `[]`, KHÔNG bỏ trống key

---

## Bước 3: Chạy script gửi báo cáo

⚠️ **BẮT BUỘC:** Việc gửi tin nhắn Google Chat CHỈ được thực hiện bằng script
`process_and_send.py`. Script đã lo toàn bộ: sắp xếp theo priority
(Highest→High→Medium→Low), loại ticket trùng giữa NEW và HIGH, phân loại team,
format link ticket, và gọi webhook.

```bash
pip install requests
python process_and_send.py /tmp/jira_data.json
```

🚫 **TUYỆT ĐỐI KHÔNG:**
- KHÔNG tự gọi webhook Google Chat (curl/requests) bằng tay
- KHÔNG tự format/sắp xếp/lọc danh sách ticket rồi gửi
- KHÔNG tự soạn nội dung tin nhắn thay cho script

Nhiệm vụ của bạn chỉ gồm: query Jira (Bước 1) → ghi JSON (Bước 2) →
**CHẠY SCRIPT** (Bước 3). Mọi việc gửi tin là của script, không phải của bạn.

Nếu script báo lỗi, sửa file JSON cho đúng format rồi CHẠY LẠI SCRIPT —
không được gửi tin thủ công thay thế.

---

## Bước 4: Xác nhận

Đọc log của script, báo lại:
- Số ticket new / high đọc được (và số ticket trùng đã loại)
- Phân bổ theo Team1 / Team2 / Team3 / Khác
- Trạng thái gửi webhook (✅/❌) cho cả 3 team
