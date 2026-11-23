import json
import shutil
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from fastapi import APIRouter, Request, Form, UploadFile, File, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.database.queries import (
    list_all_rooms,
    create_or_update_room,
    delete_room,
    get_user,
    create_user,
    update_user_profile,
    delete_user_account
)
from app.database.dynamo import hotel_table, dynamodb_client
from app.services.auth_service import require_role
from app.services.security import hash_password
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/admin", tags=["Admin Console"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

BACKUPS_DIR = settings.UPLOAD_DIR.parent.parent.parent / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


# ===============================================================================
# 1. QUẢN LÝ PHÒNG (CRUD & UPLOAD ẢNH THẬT)
# ===============================================================================

@router.get("/rooms", response_class=HTMLResponse)
async def admin_rooms_page(request: Request, msg: str = "", error: str = ""):
    user = require_role(request, ["admin"])
    rooms = list_all_rooms()
    return templates.TemplateResponse(
        request=request,
        name="admin/rooms.html",
        context={
            "user": user,
            "rooms": rooms,
            "msg": msg,
            "error": error
        }
    )


@router.post("/rooms")
async def admin_create_or_edit_room(
    request: Request,
    room_number: str = Form(...),
    room_type: str = Form(...),
    price: float = Form(...),
    floor: int = Form(...),
    max_guests: int = Form(...),
    status_room: str = Form("Trống"),
    image_url: str = Form(""),
    amenities: str = Form(""),
    description: str = Form(""),
    photo_file: UploadFile = File(None)
):
    """
    Thêm mới hoặc sửa phòng:
    Hỗ trợ tải ảnh thật trực tiếp từ máy tính lên (lưu vào static/uploads) hoặc dán link ảnh online.
    """
    user = require_role(request, ["admin"])

    # 1. Ràng buộc số phòng: chỉ được nhập số
    clean_room_number = room_number.strip()
    if not clean_room_number.isdigit():
        return RedirectResponse(
            url="/admin/rooms?error=Số phòng chỉ được nhập chữ số (ví dụ: 101, 201), không được nhập chữ!",
            status_code=status.HTTP_302_FOUND
        )

    # 2. Ràng buộc giá tiền: không được âm và phải > 0
    if price <= 0:
        return RedirectResponse(
            url="/admin/rooms?error=Giá mỗi đêm không được âm và phải lớn hơn 0 VNĐ!",
            status_code=status.HTTP_302_FOUND
        )

    # 3. Ràng buộc số tầng: từ tầng 1 đến tầng 30
    if floor < 1 or floor > 30:
        return RedirectResponse(
            url="/admin/rooms?error=Số tầng không hợp lệ (chỉ được nhập từ tầng 1 đến tầng 30)!",
            status_code=status.HTTP_302_FOUND
        )

    # 4. Ràng buộc sức chứa: từ 1 đến 10 khách
    if max_guests < 1 or max_guests > 10:
        return RedirectResponse(
            url="/admin/rooms?error=Sức chứa tối đa của phòng chỉ từ 1 đến 10 người!",
            status_code=status.HTTP_302_FOUND
        )

    final_image_url = image_url.strip()

    # Xử lý tải ảnh từ máy tính lên nếu có
    if photo_file and photo_file.filename:
        ext = Path(photo_file.filename).suffix.lower()
        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            saved_name = f"room_{room_number}_{uuid.uuid4().hex[:6]}{ext}"
            file_path = settings.UPLOAD_DIR / saved_name
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(photo_file.file, buffer)
            final_image_url = f"/static/uploads/{saved_name}"

    if not final_image_url:
        final_image_url = "https://images.unsplash.com/photo-1618773928121-c32242e63f39?auto=format&fit=crop&w=1200&q=80"

    # Tách tiện ích thành danh sách
    amenities_list = [a.strip() for a in amenities.split(",") if a.strip()]
    if not amenities_list:
        amenities_list = ["Wifi 5G tốc độ cao", "Smart TV", "Điều hòa hai chiều"]

    room_data = {
        "MaPhong": room_number.strip(),
        "SoPhong": room_number.strip(),
        "TenLoaiPhong": room_type.strip(),
        "GiaMoiDem": price,
        "Tang": floor,
        "SoKhachToiDa": max_guests,
        "TrangThai": status_room,
        "HinhAnh": final_image_url,
        "TienNghi": amenities_list,
        "MoTa": description.strip()
    }

    create_or_update_room(room_data)

    # Phát sóng Realtime qua WebSocket
    await ws_manager.broadcast({
        "type": "room_updated",
        "room_id": room_number.strip(),
        "new_status": status_room
    })

    return RedirectResponse(
        url=f"/admin/rooms?msg=Da luu thong tin phong {room_number} thanh cong!",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/rooms/{room_id}/delete")
async def admin_delete_room(request: Request, room_id: str):
    """Xóa phòng khỏi hệ thống DynamoDB"""
    user = require_role(request, ["admin"])
    delete_room(room_id)

    await ws_manager.broadcast({
        "type": "room_updated",
        "room_id": room_id,
        "new_status": "Bảo trì"
    })

    return RedirectResponse(
        url=f"/admin/rooms?msg=Da xoa phong {room_id} thanh cong!",
        status_code=status.HTTP_302_FOUND
    )


# ===============================================================================
# 2. QUẢN LÝ TÀI KHOẢN (USER MANAGEMENT)
# ===============================================================================

@router.get("/users", response_class=HTMLResponse)
async def admin_users_page(request: Request, q: str = "", msg: str = "", error: str = ""):
    user = require_role(request, ["admin"])

    # Lấy danh sách tài khoản bằng Scan theo Loại thực thể NguoiDung
    try:
        res = hotel_table.scan(
            FilterExpression="LoaiThucThe = :u",
            ExpressionAttributeValues={":u": "NguoiDung"}
        )
        users = res.get("Items", [])
        # Sắp xếp tài khoản theo ngày tạo mới nhất
        users.sort(key=lambda u: u.get("NgayTao", ""), reverse=True)

        # Lọc tìm kiếm nếu có tham số q
        if q.strip():
            kw = q.strip().lower()
            users = [
                u for u in users
                if kw in u.get("TenDangNhap", "").lower()
                or kw in u.get("HoTen", "").lower()
                or kw in u.get("Email", "").lower()
                or kw in u.get("SoDienThoai", "").lower()
                or kw in u.get("VaiTro", "").lower()
            ]
    except Exception as e:
        users = []

    return templates.TemplateResponse(
        request=request,
        name="admin/users.html",
        context={
            "user": user,
            "users": users,
            "search_query": q,
            "msg": msg,
            "error": error
        }
    )


@router.post("/users")
async def admin_create_staff(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form(...),
    phone: str = Form(""),
    email: str = Form("")
):
    """Tạo tài khoản người dùng / nhân viên mới (Chỉ Admin)"""
    user = require_role(request, ["admin"])

    clean_user = username.strip().lower()
    if get_user(clean_user):
        return RedirectResponse(
            url=f"/admin/users?error=Tài khoản '{clean_user}' đã tồn tại trong hệ thống!",
            status_code=status.HTTP_302_FOUND
        )

    user_data = {
        "username": clean_user,
        "password_hash": hash_password(password),
        "role": role,
        "name": name.strip(),
        "phone": phone.strip(),
        "email": email.strip()
    }
    create_user(user_data)

    return RedirectResponse(
        url=f"/admin/users?msg=Đã tạo thành công tài khoản [{role.upper()}] '{clean_user}'!",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/users/{username}/edit")
async def admin_edit_user(
    request: Request,
    username: str,
    name: str = Form(...),
    role: str = Form(...),
    phone: str = Form(""),
    email: str = Form(""),
    new_password: str = Form("")
):
    """Admin chỉnh sửa thông tin tài khoản (Chỉ Admin)"""
    admin_user = require_role(request, ["admin"])
    clean_user = username.strip().lower()

    target_user = get_user(clean_user)
    if not target_user:
        return RedirectResponse(
            url="/admin/users?error=Không tìm thấy tài khoản cần chỉnh sửa!",
            status_code=status.HTTP_302_FOUND
        )

    # Không cho phép admin tự hạ quyền của chính mình
    if clean_user == admin_user.get("username") and role != "admin":
        return RedirectResponse(
            url="/admin/users?error=Bạn không thể tự hạ quyền Admin của chính tài khoản đang đăng nhập!",
            status_code=status.HTTP_302_FOUND
        )

    data = {
        "name": name.strip(),
        "role": role,
        "phone": phone.strip(),
        "email": email.strip()
    }
    if new_password.strip():
        data["password_hash"] = hash_password(new_password.strip())

    success = update_user_profile(clean_user, data)
    if success:
        return RedirectResponse(
            url=f"/admin/users?msg=Cập nhật tài khoản '{clean_user}' thành công!",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=f"/admin/users?error=Cập nhật tài khoản '{clean_user}' thất bại!",
            status_code=status.HTTP_302_FOUND
        )


@router.post("/users/{username}/delete")
async def admin_delete_user(
    request: Request,
    username: str
):
    """Admin xóa tài khoản người dùng khỏi hệ thống DynamoDB (Chỉ Admin)"""
    admin_user = require_role(request, ["admin"])
    clean_user = username.strip().lower()

    # Không cho phép admin tự xóa chính tài khoản đang đăng nhập
    if clean_user == admin_user.get("username"):
        return RedirectResponse(
            url="/admin/users?error=Bạn không thể xóa chính tài khoản Admin đang đăng nhập!",
            status_code=status.HTTP_302_FOUND
        )

    target_user = get_user(clean_user)
    if not target_user:
        return RedirectResponse(
            url="/admin/users?error=Tài khoản không tồn tại hoặc đã bị xóa trước đó!",
            status_code=status.HTTP_302_FOUND
        )

    success = delete_user_account(clean_user)
    if success:
        return RedirectResponse(
            url=f"/admin/users?msg=Đã xóa tài khoản '{clean_user}' khỏi hệ thống DynamoDB!",
            status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(
            url=f"/admin/users?error=Không thể xóa tài khoản '{clean_user}'!",
            status_code=status.HTTP_302_FOUND
        )


# ===============================================================================
# 3. SAO LƯU & XUẤT DỮ LIỆU DYNAMODB (BACKUP TO JSON)
# ===============================================================================

@router.get("/backup", response_class=HTMLResponse)
async def admin_backup_page(request: Request, msg: str = ""):
    user = require_role(request, ["admin"])

    # Lấy danh sách các tệp sao lưu đã tạo
    backup_files = []
    if BACKUPS_DIR.exists():
        for p in sorted(BACKUPS_DIR.glob("backup-*.json"), reverse=True):
            stat = p.stat()
            backup_files.append({
                "filename": p.name,
                "size_kb": round(stat.st_size / 1024, 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

    return templates.TemplateResponse(
        request=request,
        name="admin/backup.html",
        context={
            "user": user,
            "backups": backup_files,
            "table_name": settings.DYNAMODB_TABLE,
            "region": settings.AWS_REGION,
            "msg": msg
        }
    )


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super(DecimalEncoder, self).default(o)


@router.post("/backup/export")
async def admin_export_backup(request: Request):
    """
    Xuất toàn bộ bản ghi của bảng DynamoDB ra tệp tin JSON an toàn
    (Đáp ứng tiêu chí Backup/Restore của đồ án NoSQL)
    """
    user = require_role(request, ["admin"])

    items = []
    scan_kwargs = {}
    done = False
    start_key = None

    while not done:
        if start_key:
            scan_kwargs["ExclusiveStartKey"] = start_key
        response = hotel_table.scan(**scan_kwargs)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            done = True

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"backup-{timestamp}.json"
    file_path = BACKUPS_DIR / filename

    backup_payload = {
        "metadata": {
            "table_name": settings.DYNAMODB_TABLE,
            "region": settings.AWS_REGION,
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "exported_by": user.get("username"),
            "total_items": len(items)
        },
        "items": items
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)

    return RedirectResponse(
        url=f"/admin/backup?msg=Da xuat thanh cong {len(items)} ban ghi ra tap tin '{filename}'!",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/backup/download/{filename}")
async def admin_download_backup(request: Request, filename: str):
    """Tải tệp tin sao lưu JSON về máy tính cá nhân"""
    require_role(request, ["admin"])
    file_path = BACKUPS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Tệp tin sao lưu không tồn tại")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/json"
    )


@router.post("/backup/restore/{filename}")
async def admin_restore_backup(request: Request, filename: str):
    """
    Khôi phục dữ liệu từ tệp tin JSON vào DynamoDB (Restore)
    Sử dụng batch_writer để nạp nhanh hàng loạt bản ghi
    """
    require_role(request, ["admin"])
    file_path = BACKUPS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Tệp tin sao lưu không tồn tại")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f, parse_float=Decimal)

    items = data.get("items", [])
    restored_count = 0
    with hotel_table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
            restored_count += 1

    return RedirectResponse(
        url=f"/admin/backup?msg=Da khoi phuc thanh cong {restored_count} ban ghi tu tap tin '{filename}' vao DynamoDB!",
        status_code=status.HTTP_302_FOUND
    )
