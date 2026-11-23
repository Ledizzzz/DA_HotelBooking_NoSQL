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
        if settings.AWS_SESSION_TOKEN:
            kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN
        
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

def create_table_if_not_exists() -> bool:
    """Tự động tạo bảng DynamoDB theo chuẩn Single-Table Design nếu chưa tồn tại"""
    try:
        dynamodb_client.describe_table(TableName=settings.DYNAMODB_TABLE)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        print(f"[DynamoDB] Bảng '{settings.DYNAMODB_TABLE}' chưa có trên AWS. Đang khởi tạo bảng...")
        table = dynamodb.create_table(
            TableName=settings.DYNAMODB_TABLE,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1_PK", "AttributeType": "S"},
                {"AttributeName": "GSI1_SK", "AttributeType": "S"}
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1_PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1_SK", "KeyType": "RANGE"}
                    ],
                    "Projection": {
                        "ProjectionType": "ALL"
                    }
                }
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        table.wait_until_exists()
        print(f"[DynamoDB] Tạo bảng '{settings.DYNAMODB_TABLE}' thành công!")
        return True
    except Exception as e:
        print(f"[DynamoDB] Không thể tạo bảng: {e}")
        return False
