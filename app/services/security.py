import bcrypt

def hash_password(password: str) -> str:
    """Băm mật khẩu bằng thuật toán Bcrypt an toàn chuẩn công nghiệp"""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác thực mật khẩu người dùng nhập với chuỗi băm trong CSDL DynamoDB"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False
