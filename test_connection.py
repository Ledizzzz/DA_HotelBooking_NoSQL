import sys
import os
from pathlib import Path

# Đảm bảo in Tiếng Việt trên Windows console không bị lỗi UTF-8
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Thêm thư mục gốc vào đường dẫn import
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database.dynamo import check_dynamo_connection

if __name__ == "__main__":
    print("--- KIỂM TRA KẾT NỐI AMAZON DYNAMODB (SINGAPORE) ---")
    res = check_dynamo_connection()
    if res.get("success"):
        print(f"\n>>> THÀNH CÔNG: Đã kết nối bảng '{res['table_name']}' trên AWS (Trạng thái: {res['status']})")
        print(f">>> Cặp khóa chính: {res['key_schema']}")
        print(f">>> Số lượng item hiện tại: {res['item_count']}")
    else:
        print(f"\n>>> THẤT BÀI: {res.get('error_type')} - {res.get('message')}")
        sys.exit(1)
