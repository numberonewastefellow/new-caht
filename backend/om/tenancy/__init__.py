"""Multi-tenant data-isolation package (WS-M).

Clean-room reimplementation of the tenant schema-per-tenant isolation core with all
billing / control-plane / cloud-pool coupling removed. See ``README.md`` for the model.

The public, cross-workstream surface (Contract 3) lives in :mod:`om.tenancy.context`.
"""
