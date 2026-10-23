import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc dự án: Web_Hotel_Python
BASE_DIR = Path(__file__).resolve().parent.parent

# Tải cấu hình từ file .env
load_dotenv(BASE_DIR / ".env")

class Settings:
    PORT: int = int(os.getenv("PORT", 8000))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "hotel-booking-secret-2026")
    
    # Cấu hình AWS DynamoDB Singapore
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1")
    DYNAMODB_TABLE: str = os.getenv("DYNAMODB_TABLE", "HotelBooking")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # Thư mục lưu trữ ảnh tải lên
    UPLOAD_DIR: Path = BASE_DIR / "app" / "static" / "uploads"

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
