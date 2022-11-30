import hashlib
import secrets


def get_token_and_hash():
    token = secrets.token_urlsafe(80)
    encoded_token = str.encode(token)
    hash_token = hashlib.sha256(encoded_token)
    token_hex_dig = hash_token.hexdigest()
    return token, token_hex_dig
