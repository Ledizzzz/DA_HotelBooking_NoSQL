"""
Dịch vụ Quản lý Phiên làm việc (Session & Authentication Service)
Hỗ trợ phân quyền chặt chẽ 3 vai trò: admin, receptionist, customer
"""

import hmac
import hashlib
import json
import base64
from fastapi import Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.config import settings

COOKIE_NAME = "hotel_session"

def _sign_data(payload_b64: str) -> str:
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"

def _verify_and_decode(cookie_value: str) -> dict | None:
    try:
        parts = cookie_value.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        json_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        return json.loads(json_bytes.decode("utf-8"))
    except Exception:
        return None

def set_user_cookie(response, user_dict: dict):
    payload_json = json.dumps({
        "username": user_dict.get("TenDangNhap") or user_dict.get("username"),
        "role": user_dict.get("VaiTro") or user_dict.get("role", "customer"),
        "name": user_dict.get("HoTen") or user_dict.get("name", ""),
        "email": user_dict.get("Email") or user_dict.get("email", ""),
        "phone": user_dict.get("SoDienThoai") or user_dict.get("phone", "")
    })
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
    signed_val = _sign_data(payload_b64)
    response.set_cookie(
        key=COOKIE_NAME,
        value=signed_val,
        httponly=True,
        max_age=86400 * 7, # 7 ngày
        samesite="lax"
    )

def clear_user_cookie(response):
    response.delete_cookie(key=COOKIE_NAME)

def get_current_user(request: Request) -> dict | None:
    cookie = request.cookies.get(COOKIE_NAME)
    if not cookie:
        return None
    return _verify_and_decode(cookie)

def require_role(request: Request, allowed_roles: list[str]) -> dict:
    user = get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/login?msg=Vui long dang nhap de tiep tuc"}
        )
    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập vào chức năng này"
        )
    return user
