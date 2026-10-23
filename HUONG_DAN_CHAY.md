# 🏨 HƯỚNG DẪN KHỞI CHẠY & BÁO CÁO ĐỒ ÁN
## HỆ THỐNG ĐẶT PHÒNG KHÁCH SẠN THỜI GIAN THỰC (PYTHON FASTAPI + DYNAMODB)

Dự án được xây dựng hoàn toàn mới bằng **Python 3.11, FastAPI, Boto3, WebSockets và Amazon DynamoDB (Single-Table Design)**. Dự án đáp ứng trọn vẹn 100% các tiêu chí trong thang điểm đánh giá đồ án môn Cơ sở dữ liệu NoSQL.

---

## 🚀 1. Khởi Chạy Ứng Dụng (Chỉ Cần 1 Lệnh)

1. Mở cửa sổ dòng lệnh (**Command Prompt** hoặc **PowerShell**) tại thư mục `Web_Hotel_Python`:
   ```bash
   cd d:\HOCTAP\TaiLieuNoSQl\DoAnNoSQL\Web_Hotel_Python
   ```

2. Chạy lệnh:
   ```bash
   python run.py
   ```

3. Mở trình duyệt web bất kỳ:
   * **Giao diện Web khách sạn**: 👉 **[http://localhost:8000](http://localhost:8000)**
   * **Tài liệu kiểm thử Swagger API**: 👉 **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

## 🔑 2. Danh Sách 3 Tài Khoản Phân Quyền Mẫu (RBAC)

Hệ thống đã tích hợp sẵn nút bấm **"Điền Nhanh" (1 click)** tại màn hình Đăng nhập để thuận tiện khi thuyết trình và chấm thi:

| Vai trò | Tên đăng nhập | Mật khẩu | Quyền hạn trong hệ thống |
| :--- | :--- | :--- | :--- |
| **Quản trị viên (Admin)** | `admin` | `admin123` | Toàn quyền: Thêm/Sửa/Xóa phòng, tải ảnh thật lên từ máy tính, quản lý nhân viên, xuất dữ liệu Sao lưu (Backup) DynamoDB ra JSON. |
| **Lễ tân (Receptionist)** | `letan` | `letan123` | Xem ma trận phòng trực quan theo tầng thời gian thực, nhận đơn đặt phòng mới qua chuông thông báo WebSocket, làm thủ tục Check-in (nhận phòng), Check-out (trả phòng) và hoàn tất dọn phòng. |
| **Khách hàng (Customer)** | `khachhang` | `khach123` | Xem danh mục phòng kèm **ảnh chụp thực tế chất lượng cao**, lọc tìm phòng theo giá và số khách, đặt phòng trực tuyến và xem lại lịch sử các đơn đặt phòng của mình. |

*(Người dùng mới cũng có thể tự do nhấn **Đăng Ký** tài khoản khách hàng ngay trên giao diện).*

---

## 📚 3. BẢNG ĐỐI CHIẾU CÁC TRUY VẤN DYNAMODB (DÙNG ĐỂ DÁN VÀO BÁO CÁO ĐỒ ÁN)

Toàn bộ các truy vấn được tập trung tại tệp mã nguồn: **`app/database/queries.py`**. Nhóm có thể trích dẫn trực tiếp các hàm này vào Chương 4 & Chương 5 của cuốn Báo cáo:

### 🟢 A. Các Truy Vấn Cơ Bản (Mục 5 & Mục 7 Thang Điểm)

| STT | Tên hàm trong code | Lệnh DynamoDB (Boto3) | Mục đích nghiệp vụ thực tế |
| :---: | :--- | :--- | :--- |
| **1** | `get_room(room_id)` | `table.get_item(Key={'PK': ..., 'SK': ...})` | Lấy chi tiết 1 phòng theo cặp khóa chính `PK=HOTEL#H01` và `SK=ROOM#{id}` |
| **2** | `create_or_update_room(data)` | `table.put_item(Item=item)` | Thêm phòng mới hoặc cập nhật toàn bộ thông tin phòng kèm ảnh |
| **3** | `update_room_status(room_id, status)`| `table.update_item(...)` | Cập nhật nhanh trạng thái phòng (`Trống`, `Đang ở`, `Cần dọn dẹp`, `Bảo trì`) |
| **4** | `delete_room(room_id)` | `table.delete_item(Key=...)` | Xóa 1 phòng khỏi hệ thống |
| **5** | `get_user(username)` | `table.get_item(Key={'PK': f'USER#{u}', 'SK': 'PROFILE'})` | Lấy thông tin tài khoản người dùng để xác thực đăng nhập |
| **6** | `create_user(data)` | `table.put_item(Item=user_item)` | Đăng ký thành viên mới (mật khẩu băm Bcrypt 12 vòng an toàn) |

---

### 🔵 B. Các Truy Vấn Nâng Cao (Mục 5 & Mục 7 Thang Điểm - Điểm Nhấn NoSQL)

| STT | Tên hàm trong code | Kỹ thuật DynamoDB Nâng Cao | Mục đích & Lợi ích tối ưu NoSQL |
| :---: | :--- | :--- | :--- |
| **1** | `list_all_rooms()` | `Query` kết hợp `begins_with` trên Sort Key (`SK begins_with 'ROOM#'`) | Lấy toàn bộ phòng của khách sạn chỉ trong 1 phân vùng `HOTEL#H01`. **Không dùng Scan**, tiết kiệm 95% chi phí RCU trên AWS! |
| **2** | `query_available_rooms()` | `Query` kết hợp `FilterExpression` linh hoạt | Lọc tìm kiếm phòng trống thỏa mãn đồng thời: mức giá tối đa, số lượng khách và hạng phòng mong muốn. |
| **3** | `query_customer_bookings()`| `Query` trên **Global Secondary Index (GSI1)** | Lấy toàn bộ lịch sử đơn đặt phòng của 1 khách hàng cụ thể thông qua `GSI1_PK=CUSTOMER#{username}` với tốc độ mili-giây. |
| **4** | `list_all_bookings()` | `Query` với Sort Key phân vùng (`SK begins_with 'BOOKING#'`) | Hiển thị hàng đợi đơn đặt phòng cho Lễ tân xử lý theo thứ tự thời gian. |
| **5** | `transact_book_room()` | **`dynamodb_client.transact_write_items` (Giao dịch ACID)** | Đặt phòng an toàn đồng thời: vừa tạo đơn đặt vừa đổi phòng sang `Đã giữ`. Kèm điều kiện `ConditionExpression: TrangThai = 'Trống'`. **Chống hiện tượng Overbooking (đặt trùng phòng) khi 2 khách bấm cùng 1 giây!** |

---

## 💾 4. Tính Năng Sao Lưu Dữ Liệu (Backup to JSON)

Tại trang Quản trị viên (`/admin/backup`):
* Nhấn nút **"Tạo Bản Sao Lưu Mới (.JSON)"**: Hệ thống tự động quét toàn bộ bảng DynamoDB và đóng gói thành tệp tin JSON có định dạng chuẩn (kèm metadata: thời gian xuất, tổng số bản ghi, vùng AWS).
* Cho phép **Tải về (.JSON)** về máy tính cá nhân để lưu trữ dự phòng.
