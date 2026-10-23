import sys
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def verify_all_endpoints():
    print("==================================================================")
    print("KIỂM THỬ TẤT CẢ CÁC ĐƯỜNG DẪN ENDPOINT ỨNG DỤNG WEB PYTHON FASTAPI")
    print("==================================================================")

    # 1. Trang chủ
    res = client.get("/")
    print(f"1. GET / (Trang chủ khách hàng): Status {res.status_code}")
    assert res.status_code == 200, "Trang chủ phải trả về 200"

    # 2. Trang đăng nhập
    res = client.get("/login")
    print(f"2. GET /login: Status {res.status_code}")
    assert res.status_code == 200, "Trang đăng nhập phải trả về 200"

    # 3. Trang đăng ký
    res = client.get("/register")
    print(f"3. GET /register: Status {res.status_code}")
    assert res.status_code == 200, "Trang đăng ký phải trả về 200"

    # 4. Trang chi tiết phòng 101
    res = client.get("/rooms/101")
    print(f"4. GET /rooms/101: Status {res.status_code}")
    assert res.status_code == 200, "Trang chi tiết phòng phải trả về 200"

    # 5. Đăng nhập Admin
    login_res = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    print(f"5. POST /login (Admin): Status {login_res.status_code}")
    assert login_res.status_code in [302, 303], "Đăng nhập admin phải chuyển hướng 302"
    cookie = login_res.cookies.get("hotel_session")
    assert cookie is not None, "Phải có session cookie sau khi đăng nhập"

    # 6. Truy cập phân hệ Admin với cookie
    res = client.get("/admin/rooms", cookies={"hotel_session": cookie})
    print(f"6. GET /admin/rooms (Đã đăng nhập Admin): Status {res.status_code}")
    assert res.status_code == 200, "Trang quản trị phòng phải trả về 200"

    res = client.get("/admin/users", cookies={"hotel_session": cookie})
    print(f"7. GET /admin/users: Status {res.status_code}")
    assert res.status_code == 200, "Trang quản trị người dùng phải trả về 200"

    res = client.get("/admin/backup", cookies={"hotel_session": cookie})
    print(f"8. GET /admin/backup: Status {res.status_code}")
    assert res.status_code == 200, "Trang sao lưu phải trả về 200"

    # 7. Truy cập phân hệ Lễ tân với cookie
    res = client.get("/receptionist", cookies={"hotel_session": cookie})
    print(f"9. GET /receptionist (Bảng Lễ Tân): Status {res.status_code}")
    assert res.status_code == 200, "Trang lễ tân phải trả về 200"

    # 8. Kiểm thử xuất sao lưu JSON
    res = client.post("/admin/backup/export", cookies={"hotel_session": cookie}, follow_redirects=False)
    print(f"10. POST /admin/backup/export: Status {res.status_code}")
    assert res.status_code == 302, "Xuất sao lưu phải hoàn tất và chuyển hướng 302"

    print("\n==================================================================")
    print(">>> TẤT CẢ 10/10 BÀI KIỂM THỬ HỆ THỐNG ĐÃ VƯỢT QUA XUẤT SẮC 100%! <<<")
    print("==================================================================")

if __name__ == "__main__":
    verify_all_endpoints()
