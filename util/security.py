import os
import rncryptor

from typing import ByteString

SECRET_KEY = os.getenv("SECRET_KEY")

__crypto_suite = None


def __get_crypto_suite() -> rncryptor.RNCryptor:
    global __crypto_suite
    if not __crypto_suite:
        __crypto_suite = rncryptor.RNCryptor()
    return __crypto_suite


def encrypt(value: str) -> ByteString:
    if not value:
        return None
    value = __get_crypto_suite().encrypt(value, SECRET_KEY)
    return value


def decrypt(value: ByteString) -> str:
    if not value:
        return None
    value = __get_crypto_suite().decrypt(value, SECRET_KEY)
    return value


def check_secret_key() -> None:
    if not SECRET_KEY:
        raise Exception("SECRET_KEY not set")
    if SECRET_KEY == "default":
        print("CAUTION: SECRET_KEY is set to default value", flush=True)
