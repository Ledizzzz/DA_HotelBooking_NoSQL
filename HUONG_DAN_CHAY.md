# 🏨 HƯỚNG DẪN KHỞI CHẠY & BÁO CÁO ĐỒ ÁN
## HỆ THỐNG ĐẶT PHÒNG KHÁCH SẠN THỜI GIAN THỰC (PYTHON FASTAPI + DYNAMODB)

> **Môn học:** Cơ Sở Dữ Liệu NoSQL (Trường Đại học Công Thương TP.HCM - HUIT)  
> **Kiến trúc:** Amazon DynamoDB (Single-Table Design) · Python 3.11 (FastAPI + Boto3) · Realtime WebSockets

---

## 🚀 1. Hướng Dẫn Cài Đặt Môi Trường & Khởi Chạy

Dự án sử dụng cơ sở dữ liệu **Serverless trên đám mây AWS DynamoDB** nên trên máy tính **hoàn toàn không cần cài đặt phần mềm Database cục bộ**. Chỉ cần máy tính có cài sẵn Python:

### Bước 1: Cài đặt các thư viện cần thiết
Mở terminal (**Command Prompt** hoặc **PowerShell**) tại thư mục của đồ án và chạy lệnh:
```bash
pip install -r requirements.txt
```
*(Lệnh này tự động cài đặt: `fastapi`, `uvicorn`, `boto3`, `jinja2`, `bcrypt`, `passlib`, `websockets`, `python-dotenv`,...)*

### Bước 2: Kiểm tra cấu hình kết nối đám mây (`.env`)
Đảm bảo tệp `.env` ở thư mục gốc đã có các thông số kết nối AWS IAM:
```env
PORT=8000
AWS_REGION=ap-southeast-1
DYNAMODB_TABLE=HotelBooking
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
# (Bổ sung AWS_SESSION_TOKEN nếu dùng tài khoản học tập AWS Academy Learner Lab)
```

### Bước 3: Khởi chạy máy chủ (Chỉ cần 1 lệnh)
```bash
python run.py
```

### Bước 4: Truy cập ứng dụng trên trình duyệt
* 🌐 **Giao diện Web khách sạn:** 👉 **[http://localhost:8000](http://localhost:8000)** *(hoặc http://127.0.0.1:8000)*
* 📖 **Tài liệu kiểm thử Swagger API:** 👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🔑 2. Danh Sách Tài Khoản Phân Quyền (Đã Tích Hợp Nút "Điền Nhanh" 1-Click)

Tại màn hình đăng nhập, hệ thống tích hợp sẵn 3 nút bấm **Điền Nhanh Demo** để chấm thi và thuyết trình thuận tiện:

| Vai trò | Tên đăng nhập | Mật khẩu | Quyền hạn & Chức năng trong hệ thống |
| :--- | :--- | :--- | :--- |
| **Quản trị viên (Admin)** | `admin` | `admin123` | **Toàn quyền:** Thêm/Sửa/Xóa phòng nghỉ (ràng buộc số phòng, giá > 0, tầng 1–30, khách 1–10, chọn hạng phòng tiếng Việt, tải ảnh thật từ máy tính); Quản lý tài khoản (Tìm kiếm Live Search, Sửa phân quyền, Đổi mật khẩu, Xóa tài khoản có khóa bảo vệ); Sao lưu & Khôi phục (Restore) dữ liệu JSON bằng `batch_writer`. |
| **Lễ tân (Receptionist)** | `letan` | `letan123` | Giám sát ma trận phòng phân tầng tự động đổi màu thời gian thực; Dashboard thống kê lưới 3x2 (Tỷ lệ lấp đầy & Doanh thu); Thanh tìm kiếm đơn đặt phòng tức thì + Nút lọc nhanh trạng thái để thực hiện: Duyệt đơn ➔ Check-in ➔ Check-out ➔ Đã dọn xong. |
| **Khách hàng (Customer)** | `khachhang` | `khach123` | Khám phá phòng kèm ảnh chụp 5 sao, bộ lọc tìm kiếm phòng đa tiêu chí (giá, khách, hạng phòng), đặt phòng chống Overbooking, xem lịch sử đơn đặt và tự Hủy đơn chờ duyệt. |

*(Người dùng mới cũng có thể tự do nhấn **Đăng Ký** tài khoản cá nhân, mật khẩu được băm bảo mật bằng thuật toán Bcrypt 12 vòng).*

---

## 📚 3. Bảng Đối Chiếu Các Truy Vấn DynamoDB (Dùng Cho Báo Cáo & Vấn Đáp)

Toàn bộ các truy vấn được tập trung tại tệp mã nguồn: **`app/database/queries.py`** đáp ứng 100% thang điểm đánh giá:

### 🟢 A. Các Truy Vấn Cơ Bản (Độ phức tạp O(1) theo Khóa chính)

| STT | Tên hàm trong code | Thao tác Boto3 DynamoDB | Mục đích nghiệp vụ thực tế |
| :---: | :--- | :--- | :--- |
| **1** | `get_room(room_id)` | `table.get_item(Key={'PK': ..., 'SK': ...})` | Lấy chi tiết 1 phòng theo cặp khóa chính `PK=HOTEL#H01` và `SK=ROOM#{id}` |
| **2** | `create_or_update_room(data)` | `table.put_item(Item=item)` | Thêm phòng mới hoặc cập nhật toàn bộ thông tin phòng kèm ảnh thật |
| **3** | `update_room_status(room_id, status)`| `table.update_item(...)` | Cập nhật nhanh trạng thái buồng phòng (`Trống`, `Đang ở`, `Cần dọn dẹp`, `Bảo trì`) |
| **4** | `delete_room(room_id)` | `table.delete_item(Key=...)` | Xóa 1 phòng khỏi hệ thống DynamoDB |
| **5** | `get_user(username)` | `table.get_item(Key={'PK': f'USER#{u}', 'SK': 'PROFILE'})` | Lấy thông tin tài khoản người dùng để xác thực đăng nhập |
| **6** | `create_user(data)` | `table.put_item(Item=user_item)` | Đăng ký thành viên mới (mật khẩu băm Bcrypt 12 vòng an toàn) |
| **7** | `update_user_profile(user, data)` | `table.update_item(...)` | Cập nhật họ tên, vai trò, SĐT, email và đổi mật khẩu mới cho tài khoản |
| **8** | `delete_user_account(username)` | `table.delete_item(Key={'PK': ..., 'SK': 'PROFILE'})` | Xóa tài khoản người dùng khỏi hệ thống |

---

### 🔵 B. Các Truy Vấn Nâng Cao (Điểm Nhấn Tối Ưu NoSQL)

| STT | Tên hàm trong code | Kỹ thuật DynamoDB Nâng Cao | Mục đích & Lợi ích tối ưu NoSQL |
| :---: | :--- | :--- | :--- |
| **1** | `list_all_rooms()` | `Query` kết hợp `begins_with` trên Sort Key (`SK begins_with 'ROOM#'`) | Lấy toàn bộ danh sách phòng chỉ trong 1 phân vùng `HOTEL#H01`. **Không dùng Scan**, tiết kiệm 95% chi phí RCU trên AWS! |
| **2** | `query_available_rooms()` | `Query` kết hợp `FilterExpression` linh hoạt | Lọc tìm kiếm phòng trống thỏa mãn đồng thời: mức giá tối đa, số lượng khách và hạng phòng mong muốn. |
| **3** | `query_customer_bookings()`| `Query` trên **Global Secondary Index (GSI1)** | Lấy toàn bộ lịch sử đơn đặt của 1 khách hàng thông qua `GSI1_PK=CUSTOMER#{username}` với tốc độ mili-giây mà không cần Scan bảng. |
| **4** | `list_all_bookings()` | `Query` với Sort Key phân vùng (`SK begins_with 'BOOKING#'`) | Hiển thị hàng đợi đơn đặt phòng cho Lễ tân xử lý theo thứ tự thời gian. |
| **5** | `transact_book_room()` | **`dynamodb_client.transact_write_items` (Giao dịch ACID)** | Đặt phòng an toàn đồng thời: vừa tạo đơn đặt vừa đổi phòng sang `Đã giữ` kèm điều kiện `ConditionExpression: TrangThai = 'Trống'`. **Chống triệt để hiện tượng Overbooking (đặt trùng phòng) khi 2 khách cùng bấm tại một thời điểm!** |

---

## 💾 4. Tính Năng Sao Lưu & Khôi Phục Dữ Liệu (Backup & Restore)

Tại trang Quản trị viên (**`/admin/backup`**):
* **Sao lưu dữ liệu (Backup):** Nhấn nút **"Tạo Bản Sao Lưu Mới (.JSON)"** ➔ Hệ thống tự động quét toàn bộ bảng DynamoDB và đóng gói thành tệp JSON chuẩn (kèm metadata: thời gian xuất, tổng số bản ghi, vùng AWS), hỗ trợ tải về máy tính.
* **Khôi phục dữ liệu (Restore):** Nhấn nút **"Khôi Phục"** tại bất kỳ bản sao lưu nào ➔ Hệ thống sử dụng lệnh `batch_writer` để nạp ngược toàn bộ các bản ghi từ file JSON lên lại bảng DynamoDB một cách nhanh chóng.
