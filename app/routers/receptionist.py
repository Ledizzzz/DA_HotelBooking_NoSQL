from fastapi import APIRouter, Request, Form, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
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

    # Thống kê nhanh trạng thái phòng
    stats = {
        "total": len(rooms),
        "available": sum(1 for r in rooms if r.get("TrangThai") == "Trống"),
        "reserved": sum(1 for r in rooms if r.get("TrangThai") == "Đã giữ"),
        "occupied": sum(1 for r in rooms if r.get("TrangThai") == "Đang ở"),
        "cleaning": sum(1 for r in rooms if r.get("TrangThai") == "Cần dọn dẹp"),
        "maintenance": sum(1 for r in rooms if r.get("TrangThai") == "Bảo trì")
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

    return RedirectResponse(
        url=f"/receptionist?msg=Da cap nhat don #{booking_id} thanh '{new_status}'!",
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

    return RedirectResponse(
        url=f"/receptionist?msg=Phong {room_id} da don dep xong va san sang don khach!",
        status_code=status.HTTP_302_FOUND
    )
