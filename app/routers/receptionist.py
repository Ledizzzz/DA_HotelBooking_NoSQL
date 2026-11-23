from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import urllib.parse
from app.database.queries import (
    list_all_rooms,
    list_all_bookings,
    update_booking_status,
    update_room_status,
    get_room
)
from app.services.auth_service import require_role
from app.services.websocket_manager import ws_manager

router = APIRouter(prefix="/receptionist", tags=["Receptionist Portal"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def receptionist_dashboard(request: Request, msg: str = ""):
    """
    Bảng điều khiển Lễ Tân (Dashboard):
    - Hiển thị ma trận phòng trực quan theo tầng & trạng thái thời gian thực.
    - Danh sách đơn đặt phòng của khách hàng để xử lý Check-in / Check-out.
    - Thống kê tỷ lệ phòng trống / đang ở / cần dọn dẹp.
    """
    user = require_role(request, ["receptionist", "admin"])

    rooms = list_all_rooms()
    bookings = list_all_bookings()

    # Thống kê nhanh trạng thái phòng, tỷ lệ lấp đầy & tổng doanh thu
    total_rooms = len(rooms)
    occupied_count = sum(1 for r in rooms if r.get("TrangThai") == "Đang ở")
    reserved_count = sum(1 for r in rooms if r.get("TrangThai") == "Đã giữ")
    available_count = sum(1 for r in rooms if r.get("TrangThai") == "Trống")
    cleaning_count = sum(1 for r in rooms if r.get("TrangThai") == "Cần dọn dẹp")
    maintenance_count = sum(1 for r in rooms if r.get("TrangThai") == "Bảo trì")

    # Tỷ lệ lấp đầy phòng (%)
    occupancy_rate = round(((occupied_count + reserved_count) / total_rooms * 100), 1) if total_rooms > 0 else 0

    # Tổng doanh thu từ các đơn đặt phòng (không tính đơn Đã hủy)
    valid_statuses = ["Chờ xác nhận", "Đã xác nhận", "Đang ở", "Đã trả phòng"]
    total_revenue = sum(float(b.get("TongTien", 0)) for b in bookings if b.get("TrangThai") in valid_statuses)

    stats = {
        "total": total_rooms,
        "available": available_count,
        "reserved": reserved_count,
        "occupied": occupied_count,
        "cleaning": cleaning_count,
        "maintenance": maintenance_count,
        "occupancy_rate": occupancy_rate,
        "total_revenue": total_revenue
    }

    return templates.TemplateResponse(
        request=request,
        name="receptionist/dashboard.html",
        context={
            "user": user,
            "rooms": rooms,
            "bookings": bookings,
            "stats": stats,
            "msg": msg
        }
    )


@router.post("/bookings/{booking_id}/action")
async def handle_booking_action(
    request: Request,
    booking_id: str,
    action: str = Form(...)
):
    """
    Quy trình tiếp nhận & xử lý đơn đặt phòng của Lễ tân:
    - confirm: Lễ tân duyệt đơn đặt của khách
    - checkin: Khách đến làm thủ tục nhận phòng (Phòng tự động chuyển sang 'Đang ở')
    - checkout: Khách làm thủ tục trả phòng (Phòng tự động chuyển sang 'Cần dọn dẹp')
    - cancel: Hủy đơn đặt (Phòng trả về 'Trống')
    """
    user = require_role(request, ["receptionist", "admin"])

    action_map = {
        "confirm": "Đã xác nhận",
        "checkin": "Đang ở",
        "checkout": "Đã trả phòng",
        "cancel": "Đã hủy"
    }
    new_status = action_map.get(action)
    if not new_status:
        raise HTTPException(status_code=400, detail="Thao tác không hợp lệ")

    updated_booking = update_booking_status(booking_id, new_status)
    if not updated_booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn đặt phòng")

    room_id = updated_booking.get("MaPhong")
    room_item = get_room(room_id)
    room_status = room_item.get("TrangThai") if room_item else "Trống"

    # Phát sóng WebSocket đồng bộ tức thời sang mọi màn hình (Admin, Khách hàng, Lễ tân)
    await ws_manager.broadcast({
        "type": "booking_status_changed",
        "booking_id": booking_id,
        "new_status": new_status
    })
    if room_id:
        await ws_manager.broadcast({
            "type": "room_updated",
            "room_id": room_id,
            "new_status": room_status
        })

    msg_text = f"Đã cập nhật đơn #{booking_id} thành '{new_status}'!"
    encoded_msg = urllib.parse.quote(msg_text)
    return RedirectResponse(
        url=f"/receptionist?msg={encoded_msg}",
        status_code=status.HTTP_302_FOUND
    )


@router.post("/rooms/{room_id}/clean")
async def mark_room_cleaned(request: Request, room_id: str):
    """Buồng phòng dọn dẹp xong -> Lễ tân chuyển phòng sang 'Trống' để sẵn sàng đón khách tiếp theo"""
    user = require_role(request, ["receptionist", "admin"])

    update_room_status(room_id, "Trống")

    # Bắn tín hiệu WebSocket
    await ws_manager.broadcast({
        "type": "room_updated",
        "room_id": room_id,
        "new_status": "Trống"
    })

    msg_text = f"Phòng {room_id} đã dọn dẹp xong và sẵn sàng đón khách!"
    encoded_msg = urllib.parse.quote(msg_text)
    return RedirectResponse(
        url=f"/receptionist?msg={encoded_msg}",
        status_code=status.HTTP_302_FOUND
    )
