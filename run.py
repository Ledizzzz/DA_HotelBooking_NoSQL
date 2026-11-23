import sys
import uvicorn
from pathlib import Path

# Đảm bảo in tiếng Việt trên console Windows
if sys.platform.startswith("win"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Thêm thư mục gốc vào đường dẫn hệ thống
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings

if __name__ == "__main__":
    print(f"==================================================================")
    print(f"🏨 SAIGON GRAND LUXURY HOTEL - HỆ THỐNG ĐẶT PHÒNG THỜI GIAN THỰC")
    print(f"🔗 Mở trình duyệt truy cập: http://localhost:{settings.PORT}")
    print(f"📖 Tài liệu Swagger API:    http://localhost:{settings.PORT}/docs")
    print(f"==================================================================")
    
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=True
    )
