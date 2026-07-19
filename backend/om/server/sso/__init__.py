"""Clean-room SAML SSO service package (WS-C).

Public surface:
- ``api.sso_router``          — public SP endpoints under ``/sso/saml/*``.
- ``api.admin_sso_router``    — admin config CRUD under ``/admin/sso/saml/*``.
- ``provisioning.provision_sso_user`` — JIT user provisioning entrypoint.

See ``README.md`` for the flow, config table/UI, attribute mapping, and the
structured-log events this package emits.
"""
