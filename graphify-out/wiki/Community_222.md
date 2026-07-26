# Community 222

> 59 nodes · cohesion 0.05

## Key Concepts

- **EncryptionService** (20 connections) — `phoenix/src/phoenix/server/encryption.py`
- **is_encrypted()** (12 connections) — `phoenix/src/phoenix/server/encryption.py`
- **TestEncryptionService** (12 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **TestIsEncrypted** (10 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **validate_provider_config()** (4 connections) — `phoenix/src/phoenix/db/models.py`
- **validate_secret_config()** (4 connections) — `phoenix/src/phoenix/db/models.py`
- **._derive_encryption_key()** (4 connections) — `phoenix/src/phoenix/server/encryption.py`
- **.__init__()** (4 connections) — `phoenix/src/phoenix/server/encryption.py`
- **.test_handles_very_long_fernet_tokens()** (4 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_returns_true_for_valid_fernet_token()** (4 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **encryption.py** (3 connections) — `phoenix/src/phoenix/server/encryption.py`
- **test_encryption.py** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_decrypt_corrupted_data_raises()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_decrypt_empty_bytes_raises()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_decrypt_with_wrong_secret_raises()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypt_decrypt_roundtrip()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypt_empty_bytes_raises()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypt_long_data()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypt_unicode_characters()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypt_very_short_data()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_encrypting_same_data_twice_produces_different_ciphertexts()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_key_derivation_is_deterministic()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_returns_false_for_empty_bytes()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_returns_false_for_exactly_56_bytes()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- **.test_returns_false_for_non_base64()** (3 connections) — `phoenix/tests/unit/server/test_encryption.py`
- *... and 34 more nodes in this community*

## Relationships

- [[Phoenix Annotation Config & Evaluators]] (4 shared connections)
- [[Community 66]] (1 shared connections)
- [[Community 150]] (1 shared connections)
- [[Community 247]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/db/models.py`
- `phoenix/src/phoenix/server/encryption.py`
- `phoenix/tests/unit/server/test_encryption.py`

## Audit Trail

- EXTRACTED: 119 (72%)
- INFERRED: 46 (28%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*