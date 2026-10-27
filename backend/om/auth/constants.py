"""Authentication constants shared across auth modules."""

# API Key constants
API_KEY_PREFIX = "on_"
DEPRECATED_API_KEY_PREFIX = "dn_"
API_KEY_LENGTH = 192

# PAT constants. New tokens are issued with PAT_PREFIX; tokens already issued under the legacy
# upstream prefix keep working, so both are accepted on read (the legacy one is never issued).
PAT_PREFIX = "om_pat_"
LEGACY_PAT_PREFIXES = ("onyx_pat_",)
VALID_PAT_PREFIXES = [PAT_PREFIX, *LEGACY_PAT_PREFIXES]
PAT_LENGTH = 192

# Shared header constants
API_KEY_HEADER_NAME = "Authorization"
API_KEY_HEADER_ALTERNATIVE_NAME = "X-Onyx-Authorization"
BEARER_PREFIX = "Bearer "
