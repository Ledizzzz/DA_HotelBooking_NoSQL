"""
=================================================================================
MÔ HÌNH TRUY VẤN CƠ SỞ DỮ LIỆU AMAZON DYNAMODB (BOTO3)
Đề tài: Hệ Thống Quản Lý & Đặt Phòng Khách Sạn (Single-Table Design)
Bảng: HotelBooking (ap-southeast-1)
Khóa chính: PK (Partition Key - String), SK (Sort Key - String)
Chỉ mục phụ: GSI1 (GSI1_PK, GSI1_SK)
=================================================================================
"""

import uuid
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from app.database.dynamo import dynamodb, dynamodb_client, hotel_table
from app.config import settings

HOTEL_DEFAULT_PK = "HOTEL#H01"


# ===============================================================================
# 1. CÁC TRUY VẤN CƠ BẢN (BASIC QUERIES - MỤC 5 & 7 TRONG THANG ĐIỂM)
# ===============================================================================

def get_room(room_id: str, hotel_pk: str = HOTEL_DEFAULT_PK) -> dict | None:
    """
    [Truy vấn cơ bản 1 - GetItem]
    Lấy thông tin chi tiết của 1 phòng dựa vào cặp khóa chính (PK, SK).
    """
    try:
        response = hotel_table.get_item(
            Key={
                "PK": hotel_pk,
                "SK": f"ROOM#{room_id}"
            }
        )
        return response.get("Item")
    except ClientError as e:
        print(f"Lỗi GetItem (Phòng): {e.response['Error']['Message']}")
        return None


def create_or_update_room(data: dict, hotel_pk: str = HOTEL_DEFAULT_PK) -> dict:
    """
    [Truy vấn cơ bản 2 - PutItem]
    Thêm mới hoặc cập nhật toàn bộ thông tin phòng vào bảng DynamoDB.
    """
    room_id = str(data["MaPhong"])
    item = {
        "PK": hotel_pk,
        "SK": f"ROOM#{room_id}",
        "LoaiThucThe": "Phong",
        "MaKhachSan": hotel_pk.replace("HOTEL#", ""),
        "MaPhong": room_id,
        "SoPhong": room_id,
        "TenLoaiPhong": data.get("TenLoaiPhong", "Phòng Tiêu Chuẩn"),
        "GiaMoiDem": Decimal(str(data.get("GiaMoiDem", 500000))),
        "Tang": int(data.get("Tang", 1)),
        "SoKhachToiDa": int(data.get("SoKhachToiDa", 2)),
        "TrangThai": data.get("TrangThai", "Trống"),
        "HinhAnh": data.get("HinhAnh", ""),
        "TienNghi": data.get("TienNghi", ["Wifi", "Điều hòa"]),
        "MoTa": data.get("MoTa", ""),
        "NgayCapNhat": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    hotel_table.put_item(Item=item)
    return item


def update_room_status(room_id: str, new_status: str, hotel_pk: str = HOTEL_DEFAULT_PK) -> bool:
    """
    [Truy vấn cơ bản 3 - UpdateItem]
    Cập nhật nhanh trạng thái của phòng (Trống, Đang ở, Cần dọn dẹp, Bảo trì).
    """
    try:
        hotel_table.update_item(
            Key={
                "PK": hotel_pk,
                "SK": f"ROOM#{room_id}"
            },
            UpdateExpression="SET TrangThai = :s, NgayCapNhat = :u",
            ExpressionAttributeValues={
                ":s": new_status,
                ":u": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )
        return True
    except ClientError as e:
        print(f"Lỗi UpdateItem (Phòng): {e.response['Error']['Message']}")
        return False


def delete_room(room_id: str, hotel_pk: str = HOTEL_DEFAULT_PK) -> bool:
    """
    [Truy vấn cơ bản 4 - DeleteItem]
    Xóa 1 phòng khỏi hệ thống dựa vào cặp khóa chính.
    """
    try:
        hotel_table.delete_item(
            Key={
                "PK": hotel_pk,
                "SK": f"ROOM#{room_id}"
            }
        )
        return True
    except ClientError as e:
        print(f"Lỗi DeleteItem (Phòng): {e.response['Error']['Message']}")
        return False


def get_user(username: str) -> dict | None:
    """
    [Truy vấn cơ bản 5 - GetItem Người dùng]
    Lấy thông tin tài khoản người dùng theo PK=USER#{username}, SK=PROFILE.
    """
    try:
        response = hotel_table.get_item(
            Key={
                "PK": f"USER#{username}",
                "SK": "PROFILE"
            }
        )
        return response.get("Item")
    except ClientError as e:
        print(f"Lỗi GetItem (User): {e.response['Error']['Message']}")
        return None


def create_user(data: dict) -> dict:
    """
    [Truy vấn cơ bản 6 - PutItem Người dùng]
    Tạo mới tài khoản người dùng (Khách hàng, Lễ tân, Quản trị viên).
    """
    username = data["username"].strip().lower()
    item = {
        "PK": f"USER#{username}",
        "SK": "PROFILE",
        "LoaiThucThe": "NguoiDung",
        "TenDangNhap": username,
        "MatKhauHash": data["password_hash"],
        "VaiTro": data.get("role", "customer"),
        "HoTen": data.get("name", username),
        "SoDienThoai": data.get("phone", ""),
        "Email": data.get("email", ""),
        "NgayTao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    hotel_table.put_item(Item=item)
    return item


# ===============================================================================
# 2. CÁC TRUY VẤN NÂNG CAO (ADVANCED QUERIES - MỤC 5 & 7 TRONG THANG ĐIỂM)
# ===============================================================================

def list_all_rooms(hotel_pk: str = HOTEL_DEFAULT_PK) -> list:
    """
    [Truy vấn nâng cao 1 - Query với begins_with]
    Lấy toàn bộ danh sách phòng thuộc một khách sạn cụ thể mà KHÔNG dùng Scan.
    Cú pháp: PK = HOTEL#H01 AND SK begins_with('ROOM#')
    """
    try:
        response = hotel_table.query(
            KeyConditionExpression=Key("PK").eq(hotel_pk) & Key("SK").begins_with("ROOM#")
        )
        rooms = response.get("Items", [])
        rooms.sort(key=lambda r: int(r.get("Tang", 1)) * 1000 + int(r.get("SoPhong", 0) if str(r.get("SoPhong", "")).isdigit() else 0))
        return rooms
    except ClientError as e:
        print(f"Lỗi Query list_all_rooms: {e.response['Error']['Message']}")
        return []


def query_available_rooms(
    hotel_pk: str = HOTEL_DEFAULT_PK,
    max_price: float | None = None,
    min_guests: int | None = None,
    room_type: str | None = None
) -> list:
    """
    [Truy vấn nâng cao 2 - Query kết hợp KeyCondition và FilterExpression]
    Tìm kiếm phòng trống với nhiều tiêu chí lọc đồng thời (giá tối đa, số khách, loại phòng).
    """
    try:
        key_condition = Key("PK").eq(hotel_pk) & Key("SK").begins_with("ROOM#")
        
        # Xây dựng FilterExpression động
        filters = Attr("TrangThai").eq("Trống")
        if max_price:
            filters = filters & Attr("GiaMoiDem").lte(Decimal(str(max_price)))
        if min_guests:
            filters = filters & Attr("SoKhachToiDa").gte(int(min_guests))
        if room_type and room_type != "All":
            filters = filters & Attr("TenLoaiPhong").eq(room_type)

        response = hotel_table.query(
            KeyConditionExpression=key_condition,
            FilterExpression=filters
        )
        return response.get("Items", [])
    except ClientError as e:
        print(f"Lỗi Query query_available_rooms: {e.response['Error']['Message']}")
        return []


def list_all_bookings(hotel_pk: str = HOTEL_DEFAULT_PK) -> list:
    """
    [Truy vấn nâng cao 3 - Query lấy toàn bộ đơn đặt phòng]
    Lấy danh sách tất cả các đơn đặt phòng thuộc khách sạn để Lễ tân quản lý.
    Cú pháp: PK = HOTEL#H01 AND SK begins_with('BOOKING#')
    """
    try:
        response = hotel_table.query(
            KeyConditionExpression=Key("PK").eq(hotel_pk) & Key("SK").begins_with("BOOKING#")
        )
        bookings = response.get("Items", [])
        bookings.sort(key=lambda b: b.get("NgayTao", ""), reverse=True)
        return bookings
    except ClientError as e:
        print(f"Lỗi Query list_all_bookings: {e.response['Error']['Message']}")
        return []


def query_customer_bookings(customer_username: str) -> list:
    """
    [Truy vấn nâng cao 4 - Query trên Global Secondary Index (GSI1)]
    Tìm nhanh toàn bộ lịch sử đơn đặt phòng của 1 khách hàng cụ thể thông qua GSI1.
    Cú pháp: GSI1_PK = CUSTOMER#{username} AND GSI1_SK begins_with('BOOKING#')
    """
    try:
        response = hotel_table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1_PK").eq(f"CUSTOMER#{customer_username.lower()}") & Key("GSI1_SK").begins_with("BOOKING#")
        )
        items = response.get("Items", [])
        items.sort(key=lambda b: b.get("NgayTao", ""), reverse=True)
        return items
    except ClientError as e:
        print(f"Lỗi Query GSI1: {e.response['Error']['Message']}")
        # Fallback qua scan nếu GSI1 chưa sẵn sàng
        return []


def transact_book_room(
    room_id: str,
    guest_name: str,
    phone: str,
    email: str,
    check_in: str,
    check_out: str,
    customer_username: str,
    note: str = "",
    hotel_pk: str = HOTEL_DEFAULT_PK
) -> tuple[bool, str, dict | None]:
    """
    [Truy vấn nâng cao 5 - Giao dịch đồng thời DynamoDB TransactWriteItems]
    Giao dịch ACID bảo đảm an toàn 100%:
    1. Tạo đơn đặt phòng mới.
    2. Cập nhật trạng thái phòng sang 'Đã giữ' (Chỉ khi phòng đang 'Trống').
    Nếu có người khác vừa đặt phòng đó trước nửa giây -> Giao dịch tự hủy để chống Overbooking.
    """
    room = get_room(room_id, hotel_pk)
    if not room:
        return False, "Phòng không tồn tại", None
    
    if room.get("TrangThai") != "Trống":
        return False, f"Phòng {room_id} hiện không còn trống (Trạng thái: {room.get('TrangThai')})", None

    booking_id = str(uuid.uuid4())[:8].upper()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Tính số đêm và tổng tiền
    try:
        d1 = datetime.strptime(check_in, "%Y-%m-%d")
        d2 = datetime.strptime(check_out, "%Y-%m-%d")
        nights = max(1, (d2 - d1).days)
    except Exception:
        nights = 1
    total_price = Decimal(str(room.get("GiaMoiDem", 500000))) * nights

    booking_item = {
        "PK": {"S": hotel_pk},
        "SK": {"S": f"BOOKING#{booking_id}"},
        "LoaiThucThe": {"S": "DatPhong"},
        "MaDatPhong": {"S": booking_id},
        "MaPhong": {"S": room_id},
        "SoPhong": {"S": str(room.get("SoPhong", room_id))},
        "TenLoaiPhong": {"S": room.get("TenLoaiPhong", "Standard")},
        "TenKhachHang": {"S": guest_name},
        "SoDienThoai": {"S": phone},
        "Email": {"S": email},
        "NgayNhan": {"S": check_in},
        "NgayTra": {"S": check_out},
        "SoDem": {"N": str(nights)},
        "TongTien": {"N": str(total_price)},
        "TrangThai": {"S": "Chờ xác nhận"},
        "NguoiDat": {"S": customer_username.lower()},
        "GhiChu": {"S": note},
        "NgayTao": {"S": now_str},
        "GSI1_PK": {"S": f"CUSTOMER#{customer_username.lower()}"},
        "GSI1_SK": {"S": f"BOOKING#{booking_id}"}
    }

    try:
        dynamodb_client.transact_write_items(
            TransactItems=[
                {
                    # 1. Thêm bản ghi Đặt phòng
                    "Put": {
                        "TableName": settings.DYNAMODB_TABLE,
                        "Item": booking_item
                    }
                },
                {
                    # 2. Cập nhật trạng thái phòng sang 'Đã giữ' kèm điều kiện phải đang 'Trống'
                    "Update": {
                        "TableName": settings.DYNAMODB_TABLE,
                        "Key": {
                            "PK": {"S": hotel_pk},
                            "SK": {"S": f"ROOM#{room_id}"}
                        },
                        "UpdateExpression": "SET TrangThai = :s, KhachHangHienTai = :k, NgayCapNhat = :u",
                        "ConditionExpression": "TrangThai = :expected_status",
                        "ExpressionAttributeValues": {
                            ":s": {"S": "Đã giữ"},
                            ":k": {"S": guest_name},
                            ":u": {"S": now_str},
                            ":expected_status": {"S": "Trống"}
                        }
                    }
                }
            ]
        )
        
        # Chuyển đổi item sang Python dict thông thường để trả về
        clean_item = {k: list(v.values())[0] for k, v in booking_item.items()}
        return True, "Đặt phòng thành công!", clean_item
        
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "TransactionCanceledException":
            return False, "Phòng này vừa được khách hàng khác đặt trước! Vui lòng chọn phòng khác.", None
        return False, f"Lỗi giao dịch DynamoDB: {e.response['Error']['Message']}", None


def update_booking_status(booking_id: str, new_status: str, hotel_pk: str = HOTEL_DEFAULT_PK) -> dict | None:
    """
    [Truy vấn cập nhật đơn đặt phòng & đồng bộ trạng thái phòng]
    - 'Đã xác nhận' -> Phòng giữ trạng thái 'Đã giữ'
    - 'Đang ở' (Check-in) -> Phòng chuyển sang 'Đang ở'
    - 'Đã trả phòng' (Check-out) -> Phòng chuyển sang 'Cần dọn dẹp'
    - 'Đã hủy' -> Phòng chuyển về 'Trống'
    """
    try:
        # 1. Lấy thông tin đơn
        res = hotel_table.get_item(Key={"PK": hotel_pk, "SK": f"BOOKING#{booking_id}"})
        booking = res.get("Item")
        if not booking:
            return None
        
        room_id = booking.get("MaPhong")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 2. Cập nhật đơn
        hotel_table.update_item(
            Key={"PK": hotel_pk, "SK": f"BOOKING#{booking_id}"},
            UpdateExpression="SET TrangThai = :s, NgayCapNhat = :u",
            ExpressionAttributeValues={":s": new_status, ":u": now_str}
        )
        booking["TrangThai"] = new_status

        # 3. Đồng bộ trạng thái phòng tương ứng
        if room_id:
            room_status_map = {
                "Đang ở": "Đang ở",
                "Đã trả phòng": "Cần dọn dẹp",
                "Đã hủy": "Trống",
                "Đã xác nhận": "Đã giữ"
            }
            if new_status in room_status_map:
                update_room_status(room_id, room_status_map[new_status], hotel_pk)

        return booking
    except ClientError as e:
        print(f"Lỗi update_booking_status: {e.response['Error']['Message']}")
        return None
