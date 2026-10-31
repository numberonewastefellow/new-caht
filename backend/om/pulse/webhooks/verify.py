"""Proving who is calling. One verifier per auth mode; a new sender format is one function
and one line in VERIFIERS.

Verifiers receive the raw body bytes and run before the JSON is parsed: a signature is
over the exact bytes sent, never over re-serialized JSON.
"""

import base64
import binascii
import hashlib
import hmac
from collections.abc import Callable
from collections.abc import Mapping
from dataclasses import dataclass

from om.configs.pulse_configs import PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS
from om.pulse.webhooks.tokens import SECRET_PREFIX

AUTH_STANDARD_WEBHOOKS = "standard_webhooks"
AUTH_HEADER_TOKEN = "header_token"
DEFAULT_SECRET_HEADER = "x-webhook-secret"

_MAX_SIGNATURES = 16
_MAX_ID_CHARS = 256


class VerificationError(Exception):
    """The caller didn't prove itself. The message is stored for the owner, so it says
    what was wrong and never includes a value from the request."""


@dataclass(frozen=True)
class SignedRequest:
    headers: Mapping[str, str]  # lower-case names
    body: bytes
    now_epoch: int


@dataclass(frozen=True)
class VerifierConfig:
    # Current first, then the previous one during a rotation
    secrets: tuple[str, ...]
    header_name: str | None = None


def _hmac_key(secret: str) -> bytes:
    encoded = secret[len(SECRET_PREFIX) :] if secret.startswith(SECRET_PREFIX) else secret
    return base64.b64decode(encoded)


def sign_standard_webhook(secret: str, message_id: str, timestamp: int, body: bytes) -> str:
    """The signature value for one secret, e.g. ``v1,K5oZ...``."""
    signed = f"{message_id}.{timestamp}.".encode() + body
    digest = hmac.new(_hmac_key(secret), signed, hashlib.sha256).digest()
    return f"v1,{base64.b64encode(digest).decode('ascii')}"


def verify_standard_webhook(request: SignedRequest, config: VerifierConfig) -> None:
    """Standard Webhooks: HMAC-SHA256 over ``id.timestamp.body``, with every ``v1,``
    signature checked against every active secret, so either side can rotate."""
    message_id = request.headers.get("webhook-id")
    raw_timestamp = request.headers.get("webhook-timestamp")
    raw_signatures = request.headers.get("webhook-signature")
    if not message_id or not raw_timestamp or not raw_signatures:
        raise VerificationError("Missing webhook-id, webhook-timestamp or webhook-signature")
    if len(message_id) > _MAX_ID_CHARS:
        raise VerificationError("webhook-id is too long")
    if not raw_timestamp.isascii() or not raw_timestamp.isdigit():
        raise VerificationError("webhook-timestamp is not a number of seconds")
    timestamp = int(raw_timestamp)
    if abs(request.now_epoch - timestamp) > PULSE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS:
        raise VerificationError("webhook-timestamp is outside the allowed window")

    presented = [s for s in raw_signatures.split(" ") if s.startswith("v1,")][:_MAX_SIGNATURES]
    if not presented:
        raise VerificationError("webhook-signature has no v1 signature")
    for secret in config.secrets:
        expected = sign_standard_webhook(secret, message_id, timestamp, request.body)
        for signature in presented:
            if hmac.compare_digest(expected.encode(), signature.encode()):
                return
    raise VerificationError("Signature does not match")


def verify_header_token(request: SignedRequest, config: VerifierConfig) -> None:
    """A shared secret in a fixed header, for senders that can't sign. Weaker: it doesn't
    cover the body and has no replay window."""
    name = (config.header_name or DEFAULT_SECRET_HEADER).lower()
    presented = request.headers.get(name)
    if not presented:
        raise VerificationError(f"Missing the {name} header")
    presented_digest = hashlib.sha256(presented.encode()).digest()
    for secret in config.secrets:
        if hmac.compare_digest(presented_digest, hashlib.sha256(secret.encode()).digest()):
            return
    raise VerificationError(f"The {name} header does not match")


Verifier = Callable[[SignedRequest, VerifierConfig], None]

VERIFIERS: dict[str, Verifier] = {
    AUTH_STANDARD_WEBHOOKS: verify_standard_webhook,
    AUTH_HEADER_TOKEN: verify_header_token,
}


def verify_request(auth_mode: str, request: SignedRequest, config: VerifierConfig) -> None:
    try:
        VERIFIERS[auth_mode](request, config)
    except (binascii.Error, ValueError) as e:
        # A stored secret that can't be decoded, or a header that can't be encoded.
        raise VerificationError("The request could not be verified") from e
