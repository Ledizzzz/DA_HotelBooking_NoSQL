"""
=================================================================================
SCRIPT NẠP DỮ LIỆU MẪU BAN ĐẦU (SEED DATA) CHO BẢNG HOTELBOOKING
- 1 Khách sạn thông tin chuẩn
- 6 Phòng nghỉ hạng sang kèm ẢNH THẬT CHỤP THỰC TẾ độ phân giải cao
- 3 Tài khoản mẫu phân quyền: Admin, Lễ tân, Khách hàng
=================================================================================
"""

import sys
from decimal import Decimal
from app.services.security import hash_password
from app.database.dynamo import hotel_table, create_table_if_not_exists
from app.database.queries import (
    HOTEL_DEFAULT_PK,
    get_room,
    create_or_update_room,
    get_user,
    create_user
)

HOTEL_INFO = {
    "PK": HOTEL_DEFAULT_PK,
    "SK": "METADATA",
    "LoaiThucThe": "KhachSan",
    "MaKhachSan": "H01",
    "TenKhachSan": "Khách sạn Sài Gòn Grand Luxury",
    "DiaChi": "01 Đồng Khởi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
    "ThanhPho": "Hồ Chí Minh",
    "SoDienThoai": "02838295111",
    "Email": "lienhe@saigongrand.vn",
    "HangSao": 5
}

ROOMS_DATA = [
    {
        "MaPhong": "101",
        "TenLoaiPhong": "Phòng Tiêu Chuẩn (Standard Double)",
        "GiaMoiDem": 850000,
        "Tang": 1,
        "SoKhachToiDa": 2,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["Wifi 5G tốc độ cao", "Smart TV 55 inch", "Điều hòa Inverter", "Bình nóng lạnh", "Ấm đun siêu tốc", "Bàn làm việc"],
        "MoTa": "Không gian ấm cúng, thiết kế hiện đại tối giản với giường đôi cỡ Queen, cửa sổ lớn đón ánh sáng tự nhiên thích hợp cho cặp đôi hoặc chuyến công tác."
    },
    {
        "MaPhong": "102",
        "TenLoaiPhong": "Phòng Tiêu Chuẩn 2 Giường (Twin Standard)",
        "GiaMoiDem": 950000,
        "Tang": 1,
        "SoKhachToiDa": 2,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1595526114035-0d45ed16cfbf?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["Wifi 5G tốc độ cao", "2 Giường đơn êm ái", "Điều hòa hai chiều", "Minibar đồ uống", "Tủ quần áo lớn", "Trà & Cà phê miễn phí"],
        "MoTa": "Trang bị hai giường đơn riêng biệt với nệm cao su non êm ái, lý tưởng cho bạn bè hoặc đồng nghiệp đi công tác cùng nhau."
    },
    {
        "MaPhong": "201",
        "TenLoaiPhong": "Phòng Cao Cấp Ban Công (Deluxe City View)",
        "GiaMoiDem": 1450000,
        "Tang": 2,
        "SoKhachToiDa": 3,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1590490360182-c33d57733427?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["Ban công ngắm phố đi bộ", "Giường King cỡ lớn", "Bồn tắm nằm thảo dược", "Loa Bluetooth Marshall", "Máy pha cà phê Nespresso"],
        "MoTa": "Ban công riêng biệt hướng nhìn trực diện đại lộ Đồng Khởi lộng lẫy về đêm, bồn tắm nằm thư giãn sang trọng chuẩn 5 sao."
    },
    {
        "MaPhong": "202",
        "TenLoaiPhong": "Phòng Sang Trọng Hướng Vườn (Deluxe Garden Suite)",
        "GiaMoiDem": 1750000,
        "Tang": 2,
        "SoKhachToiDa": 3,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["View sân vườn xanh mát", "Khu tiếp khách riêng", "Ghế sofa cao cấp", "Tủ bảo mật an toàn", "Bồn tắm đứng massage"],
        "MoTa": "Góc nhìn tĩnh lặng hướng ra khu vườn treo nhiệt đới của khách sạn, mang lại cảm giác bình yên và thư thái tối đa."
    },
    {
        "MaPhong": "301",
        "TenLoaiPhong": "Phòng Suite Gia Đình Hạng Sang (Executive Family Suite)",
        "GiaMoiDem": 2600000,
        "Tang": 3,
        "SoKhachToiDa": 4,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1631049307264-da0ec9d70304?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["2 Phòng ngủ thông nhau", "Phòng khách độc lập", "Khu vực bếp mini", "Bàn ăn gia đình", "2 Phòng tắm riêng biệt"],
        "MoTa": "Căn hộ suite gia đình tiện nghi vượt trội với phòng ngủ cho bố mẹ và phòng ngủ riêng cho con, không gian sinh hoạt chung rộng rãi."
    },
    {
        "MaPhong": "302",
        "TenLoaiPhong": "Biệt Thự Tổng Thống Toàn Cảnh (Presidential Panoramic Penthouse)",
        "GiaMoiDem": 4800000,
        "Tang": 3,
        "SoKhachToiDa": 6,
        "TrangThai": "Trống",
        "HinhAnh": "https://images.unsplash.com/photo-1578683010236-d716f9a3f461?auto=format&fit=crop&w=1200&q=80",
        "TienNghi": ["Hồ sục Jacuzzi ngoài trời", "Quầy bar riêng", "Dịch vụ quản gia 24/7", "Bàn ăn 8 ghế hoàng gia", "Hệ thống âm thanh vòm"],
        "MoTa": "Đỉnh cao của sự xa hoa với view 360 độ toàn cảnh sông Sài Gòn, hồ sục Jacuzzi trên tầng thượng và dịch vụ chăm sóc thượng khách độc quyền."
    }
]

USERS_DATA = [
    {
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "role": "admin",
        "name": "Nguyễn Vương Lê - Quản Trị Viên",
        "phone": "0988888888",
        "email": "admin@saigongrand.vn"
    },
    {
        "username": "letan",
        "password_hash": hash_password("letan123"),
        "role": "receptionist",
        "name": "Trần Thị Lễ Tân",
        "phone": "0977777777",
        "email": "letan@saigongrand.vn"
    },
    {
        "username": "khachhang",
        "password_hash": hash_password("khach123"),
        "role": "customer",
        "name": "Hoàng Minh Khách Hàng",
        "phone": "0909123456",
        "email": "khachhang@gmail.com"
    }
]


def seed_database_if_empty():
    """Tự động kiểm tra và nạp dữ liệu mẫu ban đầu nếu bảng chưa có phòng hoặc tài khoản"""
    print("\n[SEED] Đang kiểm tra dữ liệu bảng HotelBooking...")
    create_table_if_not_exists()

    # 1. Nạp metadata khách sạn
    try:
        hotel_table.put_item(Item=HOTEL_INFO)
        print("  ✓ Đã cập nhật Metadata Khách sạn Sài Gòn Grand Luxury")
    except Exception as e:
        print(f"  ✗ Lỗi nạp metadata: {e}")

    # 2. Nạp tài khoản mẫu cho 3 vai trò
    for u in USERS_DATA:
        existing = get_user(u["username"])
        if not existing:
            create_user(u)
            print(f"  ✓ Đã tạo tài khoản [{u['role'].upper()}]: {u['username']} (Mật khẩu mặc định: {u['username']}123 hoặc khach123)")
        else:
            print(f"  - Tài khoản [{u['role']}]: {u['username']} đã tồn tại")

    # 3. Nạp danh mục 6 phòng sang trọng kèm ảnh thật
    for r in ROOMS_DATA:
        create_or_update_room(r, HOTEL_DEFAULT_PK)
        print(f"  ✓ Đã nạp phòng {r['MaPhong']} ({r['TenLoaiPhong']}) kèm ảnh thật")

    print("[SEED] Hoàn tất nạp dữ liệu mẫu cho DynamoDB!\n")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    seed_database_if_empty()
