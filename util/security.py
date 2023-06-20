
import os
import base64
from typing import ByteString
from cryptography.fernet import Fernet


SECRET_KEY = os.getenv("FERNET_SECRET_KEY")
__fernet = None

def set_secret_key() -> None:
    secret_key = Fernet.generate_key()
    os.environ["FERNET_SECRET_KEY"] = base64.decodebytes(secret_key)

def ecrypt(value: str) -> ByteString:
    global __fernet
    return __get_fernet().encrypt(value.encode())

def decrypt(token: ByteString) -> ByteString:
    global __fernet
    return __get_fernet().decrypt(token)

def __get_fernet() -> Fernet:
    if not os.getenv("FERNET_SECRET_KEY"):
        set_secret_key()

    global __fernet
    if not __fernet:
        __fernet = Fernet(base64.encode(SECRET_KEY))
    return __fernet