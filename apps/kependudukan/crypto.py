import os
import hmac
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings

def get_blind_index_key() -> bytes:
    """Retrieves or derives the 256-bit key for HMAC blind indexing."""
    custom_key = getattr(settings, 'SECRET_KEY_BLIND', None)
    if custom_key:
        return custom_key.encode('utf-8')[:32].ljust(32, b'0')
    # Fallback: derive deterministically from Django SECRET_KEY via SHA256
    return hashlib.sha256(settings.SECRET_KEY.encode('utf-8') + b'::blind_index').digest()

def get_aes_key() -> bytes:
    """Retrieves or derives the 256-bit key for AES-256-GCM PII encryption."""
    custom_key = getattr(settings, 'SECRET_KEY_DATA', None)
    if custom_key:
        return custom_key.encode('utf-8')[:32].ljust(32, b'0')
    # Fallback: derive deterministically from Django SECRET_KEY via SHA256
    return hashlib.sha256(settings.SECRET_KEY.encode('utf-8') + b'::data_encryption').digest()

def clean_identity_number(val: str) -> str:
    """Strips formatting and ensures clean numeric string."""
    if not val:
        return ""
    return "".join(c for c in str(val) if c.isdigit())

def hmac_blind_index(raw_val: str) -> str:
    """
    Computes deterministic HMAC-SHA256 blind index for exact search
    without exposing plaintext PII.
    """
    clean_val = clean_identity_number(raw_val)
    key = get_blind_index_key()
    return hmac.new(key, clean_val.encode('utf-8'), hashlib.sha256).hexdigest()

def encrypt_pii(plaintext: str) -> bytes:
    """
    Encrypts sensitive string using AES-256-GCM.
    Returns: 12-byte IV + Ciphertext + 16-byte Tag
    """
    if not plaintext:
        return b""
    key = get_aes_key()
    aesgcm = AESGCM(key)
    iv = os.urandom(12)  # Standard 96-bit nonce for AES-GCM
    data = plaintext.encode('utf-8')
    # AESGCM.encrypt appends 16-byte tag to the ciphertext automatically
    encrypted = aesgcm.encrypt(iv, data, None)
    return iv + encrypted

def decrypt_pii(payload: bytes) -> str:
    """
    Decrypts AES-256-GCM payload.
    Payload expected format: IV (12 bytes) + Ciphertext + Tag (16 bytes)
    """
    if not payload or len(payload) < 28:
        return ""
    key = get_aes_key()
    aesgcm = AESGCM(key)
    iv = payload[:12]
    ciphertext_and_tag = payload[12:]
    decrypted = aesgcm.decrypt(iv, ciphertext_and_tag, None)
    return decrypted.decode('utf-8')

def mask_nik(nik: str) -> str:
    """Formats 16-digit NIK to 327301******0001."""
    clean = clean_identity_number(nik)
    if len(clean) == 16:
        return f"{clean[:6]}******{clean[-4:]}"
    elif len(clean) > 8:
        return f"{clean[:4]}{'*' * (len(clean) - 8)}{clean[-4:]}"
    return "****************"

def mask_kk(kk: str) -> str:
    """Formats 16-digit KK to 327301******0005."""
    clean = clean_identity_number(kk)
    if len(clean) == 16:
        return f"{clean[:6]}******{clean[-4:]}"
    elif len(clean) > 8:
        return f"{clean[:4]}{'*' * (len(clean) - 8)}{clean[-4:]}"
    return "****************"

def mask_phone(phone: str) -> str:
    """Formats phone number e.g. 0812****7890."""
    clean = clean_identity_number(phone)
    if len(clean) >= 10:
        return f"{clean[:4]}****{clean[-4:]}"
    return clean
