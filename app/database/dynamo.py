import boto3
from app.config import settings

def get_session():
    """Tạo AWS Boto3 Session từ biến môi trường trong file .env"""
    kwargs = {
        "region_name": settings.AWS_REGION
    }
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        
    return boto3.Session(**kwargs)

# Khởi tạo DynamoDB Resource và Client
session = get_session()
dynamodb = session.resource("dynamodb")
dynamodb_client = session.client("dynamodb")

# Tham chiếu trực tiếp đến bảng HotelBooking
hotel_table = dynamodb.Table(settings.DYNAMODB_TABLE)

def check_dynamo_connection() -> dict:
    """Kiểm tra kết nối và trạng thái của bảng trên AWS DynamoDB"""
    try:
        response = dynamodb_client.describe_table(TableName=settings.DYNAMODB_TABLE)
        table_meta = response["Table"]
        return {
            "success": True,
            "table_name": table_meta["TableName"],
            "status": table_meta["TableStatus"],
            "item_count": table_meta.get("ItemCount", 0),
            "key_schema": table_meta["KeySchema"],
            "region": settings.AWS_REGION
        }
    except Exception as e:
        return {
            "success": False,
            "error_type": type(e).__name__,
            "message": str(e)
        }
