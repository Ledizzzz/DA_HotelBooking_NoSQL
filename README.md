# 🏨 Saigon Grand Luxury Hotel - Realtime Booking System
> **Đồ án môn học: Cơ Sở Dữ Liệu NoSQL (Amazon DynamoDB)**  
> **Kiến trúc:** Single-Table Design · Fast API (Python 3.11) · WebSockets · Boto3

---

## 🌟 Tính Năng Nổi Bật

1. **Phân quyền 3 vai trò (RBAC)**:
   - **Khách hàng (Customer)**: Xem danh sách phòng kèm ảnh chụp thực tế 5 sao, bộ lọc tìm kiếm theo giá/số khách, đặt phòng trực tuyến, theo dõi lịch sử đơn đặt.
   - **Lễ tân (Receptionist)**: Ma trận phòng thời gian thực (đổi màu tự động qua WebSocket), tiếp nhận đơn khách đặt, quy trình Check-in ➔ Check-out ➔ Dọn phòng.
   - **Quản trị viên (Admin)**: Toàn quyền quản lý phòng (thêm/sửa/xóa, tải ảnh thật trực tiếp từ máy lên), quản lý nhân viên, xuất dữ liệu Sao lưu (Backup) DynamoDB ra JSON.

2. **Cơ sở dữ liệu Amazon DynamoDB Chuẩn**:
   - Kiến trúc **Single-Table Design** với cặp khóa chính `PK` (Partition Key) và `SK` (Sort Key).
   - Tối ưu hóa đọc dữ liệu bằng **`Query` + `begins_with`** (không dùng `Scan`, tiết kiệm chi phí RCU).
   - Truy vấn nâng cao trên **Global Secondary Index (GSI1)** để lấy lịch sử đơn theo từng khách hàng.
   - Giao dịch đồng thời **`TransactWriteItems` (ACID)** chống Overbooking (đặt trùng phòng) khi có nhiều người đặt cùng thời điểm.

3. **Công nghệ Sử Dụng**:
   - **Backend**: Python 3.11, FastAPI, Uvicorn, Boto3, WebSockets, Bcrypt.
   - **Frontend**: Jinja2 Templates, Luxury Dark & Gold Design, Vanilla JavaScript ES6.
   - **Tài liệu API tự động**: Swagger UI (`/docs`).

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy

### 1. Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường:
Tạo file `.env` từ file mẫu `.env.example` và điền thông tin AWS:
```env
PORT=8000
SECRET_KEY=hotel-booking-secret-2026
AWS_REGION=ap-southeast-1
DYNAMODB_TABLE=HotelBooking
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Khởi chạy máy chủ:
```bash
python run.py
```

* Mở trình duyệt web: **http://localhost:8000**
* Tài liệu Swagger API: **http://localhost:8000/docs**

---

## 🔑 Tài Khoản Mẫu (Đã tích hợp nút Điền Nhanh 1-click):
- **Admin**: `admin` / `admin123`
- **Lễ tân**: `letan` / `letan123`
- **Khách hàng**: `khachhang` / `khach123`
