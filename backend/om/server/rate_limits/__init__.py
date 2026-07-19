"""WS-F rate-limiting subsystem.

Clean-room, multi-tenant, observable token-rate-limiting for chat/search. Replaces the
former Onyx-EE ``token_rate_limit`` enforcement and the cloud ``tenant_usage`` control-plane
meter. See ``README.md`` in this package for the full design.
"""
