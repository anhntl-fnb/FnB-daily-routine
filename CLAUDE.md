# FNB Daily Report — Claude Code Routine

## Mô tả
Chạy báo cáo hàng ngày lúc 8:00 sáng cho board Jira FNB.
Phân loại ticket theo 3 team và gửi kết quả vào Google Chat.

## Cách chạy

Thực hiện đúng thứ tự:

```bash
pip install -r requests --quiet
python daily_report.py
```

## Nếu script báo lỗi thiếu credentials

Kiểm tra các biến môi trường sau đã được cấu hình trong Routine:
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`

## Không cần làm gì khác

Script tự xử lý toàn bộ: query Jira → phân loại → gửi webhook.
Đọc log output để kiểm tra kết quả từng bước.
