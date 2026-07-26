# Community 593

> 26 nodes · cohesion 0.11

## Key Concepts

- **_get_unique_id()** (15 connections) — `phoenix/src/phoenix/server/ldap.py`
- **TestUniqueIdExtraction** (14 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_attribute_without_raw_values()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_binary_non_utf8_hex_encoded()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_binary_objectguid_conversion()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_bytearray_objectguid_conversion()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_empty_attribute_returns_none()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_empty_bytes_returns_none()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_missing_attribute_returns_none()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_string_uuid_as_bytes()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_uppercase_uuid_normalized_to_lowercase()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_whitespace_only_returns_none()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **.test_whitespace_stripped_from_uuid()** (3 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Extract unique identifier attribute, handling binary values.      Different LD** (1 connections) — `phoenix/src/phoenix/server/ldap.py`
- **Test non-UTF-8 binary format falls back to hex encoding.          If the value** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test attribute object without raw_values property returns None.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test unique identifier extraction from LDAP entries.      Tests the _get_uniqu** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test missing unique_id attribute returns None.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test empty raw_values returns None.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test OpenLDAP entryUUID (string format stored as bytes).          OpenLDAP sto** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test uppercase entryUUID is normalized to lowercase.          UUIDs are case-i** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test whitespace is stripped from string UUIDs.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test empty bytes returns None, not empty string.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test whitespace-only value returns None after stripping.** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- **Test AD objectGUID binary to UUID string conversion (MS-DTYP §2.3.4).** (1 connections) — `phoenix/tests/unit/server/test_ldap.py`
- *... and 1 more nodes in this community*

## Relationships

- [[Community 306]] (3 shared connections)
- [[Community 836]] (1 shared connections)
- [[Community 799]] (1 shared connections)

## Source Files

- `phoenix/src/phoenix/server/ldap.py`
- `phoenix/tests/unit/server/test_ldap.py`

## Audit Trail

- EXTRACTED: 52 (69%)
- INFERRED: 23 (31%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*