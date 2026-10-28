"""Schlüsseldatei (Platzhalter -> Original) passwortverschlüsselt speichern/laden."""
import base64
import json
import os

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 600_000


def _key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS)
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_mapping(mapping: dict, password: str) -> bytes:
    salt = os.urandom(16)
    token = Fernet(_key(password, salt)).encrypt(json.dumps(mapping, ensure_ascii=False).encode())
    return json.dumps({"v": 1, "salt": base64.b64encode(salt).decode(), "data": token.decode()}).encode()


def decrypt_mapping(blob: bytes, password: str) -> dict:
    obj = json.loads(blob)
    try:
        raw = Fernet(_key(password, base64.b64decode(obj["salt"]))).decrypt(obj["data"].encode())
    except InvalidToken:
        raise ValueError("Passwort falsch oder Datei beschädigt.")
    return json.loads(raw)
