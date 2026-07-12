from functools import lru_cache
from os import urandom
from typing import Any

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import modes

from om.configs.app_configs import ENCRYPTION_KEY_SECRET
from om.connectors.google_utils.shared_constants import (
    DB_CREDENTIALS_AUTHENTICATION_METHOD,
)
from om.utils.logger import setup_logger
from om.utils.variable_functionality import fetch_versioned_implementation

logger = setup_logger()


@lru_cache(maxsize=1)
def _get_trimmed_key(key: str) -> bytes:
    encoded_key = key.encode()
    key_length = len(encoded_key)
    if key_length < 16:
        raise RuntimeError("Invalid ENCRYPTION_KEY_SECRET - too short")
    elif key_length > 32:
        key = key[:32]
    elif key_length not in (16, 24, 32):
        valid_lengths = [16, 24, 32]
        key = key[: min(valid_lengths, key=lambda x: abs(x - key_length))]

    return encoded_key


# IMPORTANT DO NOT DELETE, THIS IS USED BY fetch_versioned_implementation
def _encrypt_string(input_str: str) -> bytes:
    if not ENCRYPTION_KEY_SECRET:
        return input_str.encode()

    key = _get_trimmed_key(ENCRYPTION_KEY_SECRET)
    iv = urandom(16)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(input_str.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()

    return iv + encrypted_data


# IMPORTANT DO NOT DELETE, THIS IS USED BY fetch_versioned_implementation
def _decrypt_bytes(input_bytes: bytes) -> str:
    if not ENCRYPTION_KEY_SECRET:
        return input_bytes.decode()

    key = _get_trimmed_key(ENCRYPTION_KEY_SECRET)
    iv = input_bytes[:16]
    encrypted_data = input_bytes[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()

    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()

    return decrypted_data.decode()


def mask_string(sensitive_str: str) -> str:
    """Masks a sensitive string, showing first and last few characters.
    If the string is too short to safely mask, returns a fully masked placeholder.
    """
    visible_start = 4
    visible_end = 4
    min_masked_chars = 6

    if len(sensitive_str) < visible_start + visible_end + min_masked_chars:
        return "••••••••••••"

    return f"{sensitive_str[:visible_start]}...{sensitive_str[-visible_end:]}"


MASK_CREDENTIALS_WHITELIST = {
    DB_CREDENTIALS_AUTHENTICATION_METHOD,
    "wiki_base",
    "cloud_name",
    "cloud_id",
}


def mask_credential_dict(credential_dict: dict[str, Any]) -> dict[str, Any]:
    masked_creds: dict[str, Any] = {}
    for key, val in credential_dict.items():
        if isinstance(val, str):
            # we want to pass the authentication_method field through so the frontend
            # can disambiguate credentials created by different methods
            if key in MASK_CREDENTIALS_WHITELIST:
                masked_creds[key] = val
            else:
                masked_creds[key] = mask_string(val)
        elif isinstance(val, dict):
            masked_creds[key] = mask_credential_dict(val)
        elif isinstance(val, list):
            masked_creds[key] = _mask_list(val)
        elif isinstance(val, (bool, type(None))):
            masked_creds[key] = val
        elif isinstance(val, (int, float)):
            masked_creds[key] = "*****"
        else:
            masked_creds[key] = "*****"

    return masked_creds


def _mask_list(items: list[Any]) -> list[Any]:
    masked: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            masked.append(mask_credential_dict(item))
        elif isinstance(item, str):
            masked.append(mask_string(item))
        elif isinstance(item, list):
            masked.append(_mask_list(item))
        elif isinstance(item, (bool, type(None))):
            masked.append(item)
        else:
            masked.append("*****")
    return masked


def encrypt_string_to_bytes(intput_str: str) -> bytes:
    versioned_encryption_fn = fetch_versioned_implementation(
        "om.utils.encryption", "_encrypt_string"
    )
    return versioned_encryption_fn(intput_str)


def decrypt_bytes_to_string(intput_bytes: bytes) -> str:
    versioned_decryption_fn = fetch_versioned_implementation(
        "om.utils.encryption", "_decrypt_bytes"
    )
    return versioned_decryption_fn(intput_bytes)


def test_encryption() -> None:
    test_string = "Onyx is the BEST!"
    encrypted_bytes = encrypt_string_to_bytes(test_string)
    decrypted_string = decrypt_bytes_to_string(encrypted_bytes)
    if test_string != decrypted_string:
        raise RuntimeError("Encryption decryption test failed")
