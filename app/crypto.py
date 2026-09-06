from cryptography.fernet import Fernet, InvalidToken

from .config import GARMIN_TOKEN_ENC_KEY

_fernet = Fernet(GARMIN_TOKEN_ENC_KEY.encode() if isinstance(GARMIN_TOKEN_ENC_KEY, str) else GARMIN_TOKEN_ENC_KEY)


def encrypt_text(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_text(ciphertext: str) -> str:
    try:
        return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt stored Garmin token; it may be corrupt.") from exc
