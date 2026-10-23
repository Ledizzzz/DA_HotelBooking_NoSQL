from fastapi import APIRouter, Request, Form, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.database.queries import get_user, create_user
from app.services.security import verify_password, hash_password
from app.services.auth_service import set_user_cookie, clear_user_cookie, get_current_user

router = APIRouter(tags=["Authentication"])
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", msg: str = ""):
    current_user = get_current_user(request)
    if current_user:
        if current_user["role"] == "admin":
            return RedirectResponse("/admin/rooms", status_code=status.HTTP_302_FOUND)
        elif current_user["role"] == "receptionist":
            return RedirectResponse("/receptionist", status_code=status.HTTP_302_FOUND)
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"error": error, "msg": msg, "user": None}
    )


@router.post("/login")
async def handle_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    clean_username = username.strip().lower()
    user_item = get_user(clean_username)

    if not user_item:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Tên đăng nhập không tồn tại trên hệ thống!", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    pw_hash = user_item.get("MatKhauHash", "")
    if not verify_password(password, pw_hash):
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Mật khẩu không chính xác!", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Chuyển hướng theo đúng vai trò
    role = user_item.get("VaiTro", "customer")
    if role == "admin":
        dest_url = "/admin/rooms"
    elif role == "receptionist":
        dest_url = "/receptionist"
    else:
        dest_url = "/"

    response = RedirectResponse(url=dest_url, status_code=status.HTTP_302_FOUND)
    set_user_cookie(response, user_item)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, error: str = ""):
    current_user = get_current_user(request)
    if current_user:
        return RedirectResponse("/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        request=request,
        name="auth/register.html",
        context={"error": error, "user": None}
    )


@router.post("/register")
async def handle_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    phone: str = Form(""),
    email: str = Form("")
):
    clean_username = username.strip().lower()
    if len(clean_username) < 3:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Tên đăng nhập phải có ít nhất 3 ký tự!", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST
        )
    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Mật khẩu phải từ 6 ký tự trở lên!", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    existing = get_user(clean_username)
    if existing:
        return templates.TemplateResponse(
            request=request,
            name="auth/register.html",
            context={"error": "Tên đăng nhập này đã được sử dụng! Vui lòng chọn tên khác.", "user": None},
            status_code=status.HTTP_400_BAD_REQUEST
        )

    new_user_data = {
        "username": clean_username,
        "password_hash": hash_password(password),
        "role": "customer",
        "name": name.strip(),
        "phone": phone.strip(),
        "email": email.strip()
    }
    created_item = create_user(new_user_data)

    response = RedirectResponse(url="/?msg=Dang ky thanh cong!", status_code=status.HTTP_302_FOUND)
    set_user_cookie(response, created_item)
    return response


@router.get("/logout")
async def handle_logout():
    response = RedirectResponse(url="/login?msg=Ban da dang xuat thanh cong", status_code=status.HTTP_302_FOUND)
    clear_user_cookie(response)
    return response
