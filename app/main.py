"""
ỨNG DỤNG QUẢN LÝ VÀ ĐẶT PHÒNG KHÁCH SẠN THỜI GIAN THỰC (REAL-TIME HOTEL BOOKING)
Nền tảng: Python FastAPI + Jinja2 + Amazon DynamoDB (Single-Table Design) + WebSocket
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.seed import seed_database_if_empty
from app.services.websocket_manager import ws_manager
from app.routers import auth, customer, receptionist, admin

# Đảm bảo thư mục lưu trữ ảnh tải lên tồn tại
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Sự kiện vòng đời ứng dụng: Tự động kiểm tra và nạp dữ liệu mẫu ban đầu"""
    print("\n[SERVER] Đang khởi động hệ thống khách sạn...")
    try:
        seed_database_if_empty()
    except Exception as e:
        print(f"[SERVER] Lưu ý: Seed dữ liệu gặp thông báo: {e}")
    print(f"[SERVER] Máy chủ đã sẵn sàng hoạt động tại: http://localhost:{settings.PORT}")
    print(f"[SERVER] Tài liệu kiểm thử Swagger API: http://localhost:{settings.PORT}/docs\n")
    yield
    print("[SERVER] Máy chủ đang dừng...")


app = FastAPI(
    title="Saigon Grand Luxury Hotel - DynamoDB Real-time API",
    description="Hệ thống quản lý và đặt phòng khách sạn trực tuyến thời gian thực với Amazon DynamoDB (Single-Table Design), phân quyền 3 vai trò (Admin, Lễ tân, Khách hàng).",
    version="2.0.0",
    lifespan=lifespan
)

# Gắn thư mục tĩnh (CSS, JS, Hình ảnh tải lên)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Cổng WebSocket thời gian thực
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Lắng nghe thông điệp giữ kết nối từ client
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# Đăng ký các Router phân hệ
app.include_router(auth.router)
app.include_router(customer.router)
app.include_router(receptionist.router)
app.include_router(admin.router)
