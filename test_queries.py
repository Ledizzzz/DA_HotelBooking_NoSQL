import sys
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database.seed import seed_database_if_empty
from app.database.queries import (
    get_room,
    get_user,
    list_all_rooms,
    query_available_rooms,
    transact_book_room,
    list_all_bookings,
    query_customer_bookings,
    update_room_status,
    delete_room
)

def run_tests():
    print("=================================================================")
    print("KIỂM THỬ BỘ TRUY VẤN DYNAMODB CƠ BẢN VÀ NÂNG CAO (PYTHON BOTO3)")
    print("=================================================================")
    
    # 0. Seed dữ liệu
    print("\n--- 0. Nạp dữ liệu mẫu ---")
    seed_database_if_empty()

    # 1. Truy vấn cơ bản: GetItem người dùng & phòng
    print("\n--- 1. [CƠ BẢN] GetItem: Lấy thông tin tài khoản admin ---")
    admin = get_user("admin")
    assert admin is not None, "Không tìm thấy user admin"
    print(f"  ✓ User admin: Họ tên = '{admin['HoTen']}', Vai trò = '{admin['VaiTro']}'")

    print("\n--- 2. [CƠ BẢN] GetItem: Lấy thông tin phòng 101 ---")
    room101 = get_room("101")
    assert room101 is not None, "Không tìm thấy phòng 101"
    print(f"  ✓ Phòng 101: Loại = '{room101['TenLoaiPhong']}', Giá = {room101['GiaMoiDem']} đ, Trạng thái = '{room101['TrangThai']}'")
    print(f"  ✓ Ảnh phòng: {room101['HinhAnh'][:60]}...")

    # 2. Truy vấn nâng cao 1: Query toàn bộ phòng của khách sạn bằng begins_with
    print("\n--- 3. [NÂNG CAO 1] Query với begins_with: Lấy toàn bộ phòng khách sạn ---")
    all_rooms = list_all_rooms()
    print(f"  ✓ Tổng số phòng lấy được từ Query (Không dùng Scan): {len(all_rooms)} phòng")
    for r in all_rooms:
        print(f"    - Phòng {r['SoPhong']}: {r['TenLoaiPhong']} | {r['GiaMoiDem']:,} đ | Trạng thái: {r['TrangThai']}")
    assert len(all_rooms) >= 6, "Số phòng phải >= 6"

    # 3. Truy vấn nâng cao 2: Query kết hợp FilterExpression lọc phòng theo giá
    print("\n--- 4. [NÂNG CAO 2] Query kết hợp FilterExpression: Lọc phòng giá <= 1.500.000 đ ---")
    budget_rooms = query_available_rooms(max_price=1500000)
    print(f"  ✓ Tìm thấy {len(budget_rooms)} phòng phù hợp ngân sách:")
    for r in budget_rooms:
        print(f"    - Phòng {r['SoPhong']}: {r['TenLoaiPhong']} | {r['GiaMoiDem']:,} đ")

    # 4. Truy vấn nâng cao 3: TransactWriteItems đặt phòng an toàn chống Overbooking
    print("\n--- 5. [NÂNG CAO 3] Giao dịch ACID TransactWriteItems: Đặt phòng 101 ---")
    # Đảm bảo phòng 101 đang Trống
    update_room_status("101", "Trống")
    
    success, msg, booking = transact_book_room(
        room_id="101",
        guest_name="Khách Hàng VIP",
        phone="0912345678",
        email="vip@example.com",
        check_in="2026-11-01",
        check_out="2026-11-03",
        customer_username="khachhang",
        note="Phòng tầng cao view thoáng"
    )
    print(f"  ✓ Kết quả đặt phòng lần 1: {success} - {msg}")
    assert success is True, "Đặt phòng lần 1 phải thành công"

    # Thử đặt lại ngay phòng 101 để kiểm chứng chống Overbooking
    print("\n--- 6. [KIỂM CHỨNG CHỐNG TRÙNG PHÒNG] Thử đặt lại phòng 101 đang bị giữ ---")
    fail_success, fail_msg, _ = transact_book_room(
        room_id="101",
        guest_name="Người Đặt Sau",
        phone="0987654321",
        email="later@example.com",
        check_in="2026-11-01",
        check_out="2026-11-03",
        customer_username="khachhang"
    )
    print(f"  ✓ Kết quả đặt phòng lần 2 (Chống Overbooking): {fail_success} - Thông báo: '{fail_msg}'")
    assert fail_success is False, "Đặt trùng phòng phải bị từ chối"

    # 5. Truy vấn nâng cao 4: Query trên GSI1 lấy lịch sử đơn của khách
    print("\n--- 7. [NÂNG CAO 4] Query trên GSI1: Tìm các đơn đặt của tài khoản 'khachhang' ---")
    user_bookings = query_customer_bookings("khachhang")
    print(f"  ✓ Khách hàng 'khachhang' có {len(user_bookings)} đơn đặt phòng:")
    for b in user_bookings:
        print(f"    - Mã đơn: {b.get('MaDatPhong')} | Phòng: {b.get('SoPhong')} | Tổng tiền: {b.get('TongTien')} đ | Trạng thái: {b.get('TrangThai')}")

    # Dọn dẹp trả lại phòng 101 về Trống
    update_room_status("101", "Trống")
    print("\n=================================================================")
    print(">>> TẤT CẢ CÁC TRUY VẤN CƠ BẢN VÀ NÂNG CAO ĐỀU CHẠY HOÀN HẢO 100% <<<")
    print("=================================================================")

if __name__ == "__main__":
    run_tests()
