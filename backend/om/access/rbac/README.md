# RBAC — enterprise access control around Teams

Clean-room, best-in-class role-based access control for Om, built around
**Teams**. This module is the authorization brain; the document-ACL layer
(`om/access/README.md`) is its search-facing consumer.

## The model (and why)

The design is a **hybrid of RBAC and relationship-based access control (ReBAC)**,
which the research consistently recommends over either alone: coarse role tiers
for instance-wide capabilities, plus team-scoped, resource-instance grants for
the fine-grained middle. ReBAC (Google Zanzibar) is "a superset of RBAC" that
shines exactly where flat RBAC suffers *role explosion* — nested resources,
sharing, multi-tenancy.

Three layers:

1. **Coarse roles** (`om.auth.schemas.UserRole`, unchanged): `admin`,
   `global_curator`, `curator`, `basic`, `limited`, plus the non-web
   `slack_user` / `ext_perm_user`. Strict **least-privilege, deny-by-default**:
   a role holds only what `ROLE_PERMISSION_MATRIX` lists; everything else is
   denied. **Separation of duties** is enforced — content curation is split from
   instance administration, and only `admin`/`global_curator` may mint curators
   (a plain curator cannot manufacture peers and escalate laterally).
2. **Teams** group users and own **resource-scoped grants** — a team is granted
   connectors, document-sets, credentials, agents and LLM providers via the
   association tables (Contract 1). The *team* is the grant principal, so a
   membership change propagates to every resource at once instead of N per-user
   rows.
3. **Team-scoped role**: `user__team.is_curator` marks a per-team curator
   (`TeamRole.CURATOR` vs `MEMBER`).

All decisions flow through **one Policy Decision Point** — `PermissionService`.
Routes are thin Policy Enforcement Points that call a `decide_*` method and
enforce the returned `AccessDecision`; they never re-derive policy. Centralizing
authorization "once and reusing it" is OWASP's top prescription against Broken
Access Control (the #1 web risk); it also makes the policy uniformly
unit-testable and auditable (see `tests/unit/om/access/test_rbac.py`).

## Files

| File | Role |
|------|------|
| `permissions.py` | Pure data: `Permission`/`ResourceType`/`Action`/`TeamRole` enums + the least-privilege `ROLE_PERMISSION_MATRIX`. No DB/request deps. |
| `repository.py` | `TeamRepository` — team/membership/curator/resource-grant queries. Takes a caller-supplied tenant-bound `Session` (multi-tenant-safe by construction). |
| `service.py` | `PermissionService` — the PDP. Combines the matrix with team scoping (admin→all, global_curator→member-of, curator→curator-of). Raises `PermissionDenied` (mapped to HTTP 403 by the PEP). |
| `audit.py` | `audit_event` / `emit_event` — structured OpenSearch logs (Standard 9) for every team mutation; never raises into the business path. |
| `models.py` | `AccessDecision`, `PermissionDenied` (framework-free). |

## Multi-tenant readiness

The PDP and repository never open their own session and never read the tenant
from anywhere global — they operate solely on the caller-supplied session from
`om.tenancy.context`, which is bound to the current tenant's Postgres schema.
Whatever schema the session is bound to is the only data any decision can touch,
so cross-tenant leakage is impossible by construction (Contract 3 / Standard 4).

## Structured log events (Standard 9)

Emitted by `om/db/team.py` via `audit_event`, with fields `event`, `entity`,
`entity_id`, `tenant_id`, `actor_user_id`, `action`, `status`, `duration_ms`,
`error`:
`team.created | team.updated | team.deleted | team.member_added |
team.grant_changed`.

## How to add a new resource-scoped permission

1. Add the resource to `ResourceType` and a `Permission` value (`"{resource}:{action}"`).
2. Add it to `_CURATOR_SCOPED_PERMISSIONS` (curators may exercise it) or leave it
   out (admin-only) in `permissions.py`.
3. Map `ResourceType → Permission` in `service.py::_RESOURCE_CURATE_PERMISSION`
   if it is a "curate a team-scoped resource" check.
4. Add a `decide_*` method (or reuse `decide_curate_resource`) and enforce it in
   the route with `permission_service.require(...)`.
5. Add a unit test asserting least-privilege still holds.

## Research that informed the design

- **RBAC vs ReBAC / Zanzibar** — https://authzed.com/zanzibar ·
  https://www.usenix.org/conference/atc19/presentation/pang ·
  https://openfga.dev/docs/authorization-concepts · https://www.permit.io/blog/rbac-vs-rebac
- **Least-privilege role hierarchies / SoD** — https://csrc.nist.gov/projects/role-based-access-control/faqs ·
  https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html ·
  https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams
- **Resource-scoped grants** — https://cloud.google.com/iam/docs/configuring-resource-based-access ·
  https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_boundaries.html ·
  https://www.osohq.com/learn/what-is-fine-grained-authorization
- **Centralized PDP/PEP** — https://owasp.org/Top10/2021/A01_2021-Broken_Access_Control/ ·
  https://csrc.nist.gov/pubs/sp/800/162/upd2/final · https://www.openpolicyagent.org/docs
