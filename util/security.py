
import os
import rncryptor

from typing import ByteString

SECRET_KEY = os.getenv("SECRET_KEY")

__crypto_suite = None


def encrypt(value: str) -> ByteString:
    if not value:
        return None
    global __crypto_suite
    value = __get_crypto_suite().encrypt(value, SECRET_KEY)
    return value

def decrypt(value: ByteString) -> str:
    if not value:
        return None
    global __crypto_suite
    value = __get_crypto_suite().decrypt(value, SECRET_KEY)
    return value

def __get_crypto_suite() -> rncryptor.RNCryptor:
    global __crypto_suite
    if not __crypto_suite:
        __crypto_suite = rncryptor.RNCryptor()
    return __crypto_suite
