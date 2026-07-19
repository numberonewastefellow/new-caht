"""Translate our typed config into python3-saml settings + request dicts.

Two responsibilities:
  * :func:`build_saml_settings` — the OneLogin settings dict, with strict mode and
    modern-crypto security defaults always on.
  * :func:`build_request_dict` — the request dict, whose host/path are derived from
    the *configured* ACS URL (not the raw proxied request) so python3-saml's
    ``Destination`` check validates correctly behind the web proxy.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from onelogin.saml2.constants import (  # type: ignore[import-untyped]
    OneLogin_Saml2_Constants as Saml2Constants,
)

from om.configs.app_configs import WEB_DOMAIN
from om.server.sso.config_store import SamlConfigData

# Modern signature/digest — reject SHA-1 (rejectDeprecatedAlgorithm) per OWASP.
_RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
_SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"


def build_saml_settings(config: SamlConfigData) -> dict[str, Any]:
    """Build the python3-saml settings dict from a config snapshot."""
    sp: dict[str, Any] = {
        "entityId": config.sp_entity_id,
        "assertionConsumerService": {
            "url": config.sp_acs_url,
            "binding": Saml2Constants.BINDING_HTTP_POST,
        },
        "NameIDFormat": Saml2Constants.NAMEID_UNSPECIFIED,
        "x509cert": config.sp_x509_cert or "",
        "privateKey": config.sp_private_key or "",
    }
    if config.sp_slo_url:
        sp["singleLogoutService"] = {
            "url": config.sp_slo_url,
            "binding": Saml2Constants.BINDING_HTTP_REDIRECT,
        }

    idp: dict[str, Any] = {
        "entityId": config.idp_entity_id,
        "singleSignOnService": {
            "url": config.idp_sso_url,
            "binding": Saml2Constants.BINDING_HTTP_REDIRECT,
        },
        "x509cert": config.idp_x509_cert,
    }
    if config.idp_slo_url:
        idp["singleLogoutService"] = {
            "url": config.idp_slo_url,
            "binding": Saml2Constants.BINDING_HTTP_REDIRECT,
        }

    security: dict[str, Any] = {
        # strict mode does the heavy lifting: signature, conditions, destination,
        # audience, and NotBefore/NotOnOrAfter validation.
        "authnRequestsSigned": config.authn_requests_signed,
        "logoutRequestSigned": config.authn_requests_signed,
        "logoutResponseSigned": config.authn_requests_signed,
        "wantMessagesSigned": config.want_messages_signed,
        "wantAssertionsSigned": config.want_assertions_signed,
        "wantNameId": True,
        "wantNameIdEncrypted": config.want_name_id_encrypted,
        "wantAttributeStatement": False,  # email may arrive via NameID only
        # Be permissive about AuthnContext — IdPs vary; we do not require a class.
        "requestedAuthnContext": False,
        "rejectDeprecatedAlgorithm": True,
        "signatureAlgorithm": _RSA_SHA256,
        "digestAlgorithm": _SHA256,
    }

    return {
        "strict": True,
        "debug": False,
        "sp": sp,
        "idp": idp,
        "security": security,
    }


def build_request_dict(
    config: SamlConfigData,
    *,
    get_data: dict[str, Any] | None = None,
    post_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the python3-saml request dict.

    Host + path come from the configured public ACS URL so ``get_self_url`` equals
    the assertion's ``Destination`` even though the backend actually receives the
    request on an internal proxied path.
    """
    parsed = urlsplit(config.sp_acs_url or f"{WEB_DOMAIN.rstrip('/')}/")
    http_host = parsed.netloc or urlsplit(WEB_DOMAIN).netloc
    return {
        "https": "on" if parsed.scheme == "https" else "off",
        "http_host": http_host,
        "script_name": parsed.path or "/",
        "get_data": get_data or {},
        "post_data": post_data or {},
    }
