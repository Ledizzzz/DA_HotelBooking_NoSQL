from fastapi import APIRouter, Request, Form, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from decimal import Decimal
from app.database.queries import (
    list_all_rooms,
    query_available_rooms,
    get_room,
    transact_book_room,
    query_customer_bookings
)
from app.services.auth_service import get_current_user
from app.services.websocket_manager import ws_manager

router = APIRouter(tags=["Customer Portal"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def homepage(
    request: Request,
    max_price: float | None = Query(None),
    min_guests: int | None = Query(None),
    room_type: str | None = Query(None),
    msg: str = "",
    error: str = ""
):
    """
    Trang chủ cổng khách hàng:
    - Nếu có tiêu chí lọc: Gọi [Truy vấn nâng cao 2 - Query + FilterExpression]
    - Nếu không lọc: Gọi [Truy vấn nâng cao 1 - Query begins_with] lấy toàn bộ danh mục phòng
    """
    current_user = get_current_user(request)

    if max_price or min_guests or (room_type and room_type != "All"):
        rooms = query_available_rooms(
            max_price=max_price,
            min_guests=min_guests,
            room_type=room_type
        )
    else:
        rooms = list_all_rooms()

    return templates.TemplateResponse(
        request=request,
        name="customer/index.html",
        context={
            "rooms": rooms,
            "user": current_user,
            "max_price": max_price,
            "min_guests": min_guests,
            "room_type": room_type,
            "msg": msg,
            "error": error
        }
    )


@router.get("/rooms/{room_id}", response_class=HTMLResponse)
async def room_detail_page(request: Request, room_id: str):
    """Trang chi tiết phòng nghỉ và tiện ích"""
    current_user = get_current_user(request)
    room = get_room(room_id)
    if not room:
        return RedirectResponse("/?error=Phong khong ton tai", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(
        request=request,
        name="customer/room_detail.html",
        context={
            "room": room,
            "user": current_user
        }
    )


@router.post("/book")
async def book_room_action(
    request: Request,
    room_id: str = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    note: str = Form("")
):
    """
    Xử lý đặt phòng trực tuyến:
    1. Kiểm tra đăng nhập (bắt buộc phải là tài khoản khách hàng hoặc admin/letan)
    2. Thực thi [Truy vấn nâng cao 5 - Giao dịch ACID TransactWriteItems]
    3. Phát sóng WebSocket Realtime thông báo đổi màu phòng và báo chuông Lễ tân
    """
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse(
            f"/login?msg=Vui long dang nhap de dat phong {room_id}",
            status_code=status.HTTP_302_FOUND
        )

    guest_name = current_user.get("name") or current_user.get("username")
    phone = current_user.get("phone") or "Chưa cập nhật"
    email = current_user.get("email") or "Chưa cập nhật"
    customer_username = current_user.get("username")

    # Gọi hàm TransactWriteItems chống Overbooking
    success, message, booking = transact_book_room(
        room_id=room_id,
        guest_name=guest_name,
        phone=phone,
        email=email,
        check_in=check_in,
        check_out=check_out,
        customer_username=customer_username,
        note=note
    )

    if not success:
        return RedirectResponse(
            f"/?error={message}",
            status_code=status.HTTP_302_FOUND
        )

    # Phát sóng Realtime qua WebSocket tới tất cả các máy đang mở
    await ws_manager.broadcast({
        "type": "room_updated",
        "room_id": room_id,
        "new_status": "Đã giữ"
    })
    if booking:
        await ws_manager.broadcast({
            "type": "new_booking",
            "booking": booking
        })

    return RedirectResponse(
        "/my-bookings?msg=Dat phong thanh cong! Le tan se som xac nhan don cua ban.",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/my-bookings", response_class=HTMLResponse)
async def my_bookings_page(request: Request, msg: str = ""):
    """
    Trang xem lịch sử đơn đặt phòng của chính khách hàng:
    Sử dụng [Truy vấn nâng cao 4 - Query trên Chỉ mục phụ GSI1]
    """
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login?msg=Vui long dang nhap de xem don dat", status_code=status.HTTP_302_FOUND)

    bookings = query_customer_bookings(current_user["username"])

    return templates.TemplateResponse(
        request=request,
        name="customer/my_bookings.html",
        context={
            "bookings": bookings,
            "user": current_user,
            "msg": msg
        }
    )


@router.post("/my-bookings/{booking_id}/cancel")
async def customer_cancel_booking(request: Request, booking_id: str):
    """Khách hàng tự hủy đơn đặt phòng khi đơn đang ở trạng thái 'Chờ xác nhận'"""
    current_user = get_current_user(request)
    if not current_user:
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

    from app.database.queries import update_booking_status, update_room_status, get_room
    from app.database.dynamo import hotel_table

    res = hotel_table.get_item(Key={"PK": "HOTEL#H01", "SK": f"BOOKING#{booking_id}"})
    booking = res.get("Item")
    if not booking or booking.get("NguoiDat") != current_user["username"]:
        return RedirectResponse("/my-bookings?error=Don dat phong khong hop le", status_code=status.HTTP_302_FOUND)

    if booking.get("TrangThai") != "Chờ xác nhận":
        return RedirectResponse("/my-bookings?error=Chi co the huy don khi dang Cho xac nhan", status_code=status.HTTP_302_FOUND)

    # Cập nhật đơn sang Đã hủy
    update_booking_status(booking_id, "Đã hủy")

    # Trả phòng về Trống
    room_id = booking.get("MaPhong")
    if room_id:
        update_room_status(room_id, "Trống")
        await ws_manager.broadcast({
            "type": "room_updated",
            "room_id": room_id,
            "new_status": "Trống"
        })

    await ws_manager.broadcast({
        "type": "booking_status_changed",
        "booking_id": booking_id,
        "new_status": "Đã hủy"
    })

    return RedirectResponse(
        "/my-bookings?msg=Da huy don dat phong thanh cong! Phong da duoc tra ve trang thai Trong.",
        status_code=status.HTTP_302_FOUND
    )
