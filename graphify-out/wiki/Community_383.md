# Community 383

> 39 nodes · cohesion 0.08

## Key Concepts

- **FeatureFlagProvider** (11 connections) — `backend/om/feature_flags/interface.py`
- **PostHogFeatureFlagProvider** (10 connections) — `backend/om/feature_flags/posthog_provider.py`
- **NoOpFeatureFlagProvider** (9 connections) — `backend/om/feature_flags/interface.py`
- **TestFeatureFlagFactory** (7 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **get_default_feature_flag_provider()** (6 connections) — `backend/om/feature_flags/factory.py`
- **TestNoOpFeatureFlagProvider** (6 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **FeatureFlagProvider** (5 connections) — `backend/om/feature_flags/factory.py`
- **get_posthog_feature_flag_provider()** (5 connections) — `backend/om/feature_flags/factory.py`
- **interface.py** (5 connections) — `backend/om/feature_flags/interface.py`
- **.feature_enabled_for_user_tenant()** (5 connections) — `backend/om/feature_flags/interface.py`
- **UUID** (4 connections) — `backend/om/feature_flags/interface.py`
- **.feature_enabled()** (4 connections) — `backend/om/feature_flags/interface.py`
- **.feature_enabled()** (4 connections) — `backend/om/feature_flags/interface.py`
- **.feature_enabled()** (4 connections) — `backend/om/feature_flags/posthog_provider.py`
- **UUID** (3 connections) — `backend/om/feature_flags/posthog_provider.py`
- **factory.py** (3 connections) — `backend/om/feature_flags/factory.py`
- **test_feature_flag_provider_factory.py** (3 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **.test_factory_returns_provider()** (3 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **.test_posthog_provider()** (3 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **.test_always_returns_false()** (3 connections) — `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`
- **Any** (2 connections) — `backend/om/feature_flags/interface.py`
- **Any** (2 connections) — `backend/om/feature_flags/posthog_provider.py`
- **posthog_provider.py** (2 connections) — `backend/om/feature_flags/posthog_provider.py`
- **User** (1 connections) — `backend/om/feature_flags/interface.py`
- **Get the default feature flag provider implementation.      Returns the PostHog-b** (1 connections) — `backend/om/feature_flags/factory.py`
- *... and 14 more nodes in this community*

## Relationships

- [[Community 148]] (2 shared connections)
- [[Agent Tracing Processor]] (1 shared connections)

## Source Files

- `backend/om/feature_flags/factory.py`
- `backend/om/feature_flags/interface.py`
- `backend/om/feature_flags/posthog_provider.py`
- `backend/tests/external_dependency_unit/feature_flags/test_feature_flag_provider_factory.py`

## Audit Trail

- EXTRACTED: 91 (73%)
- INFERRED: 34 (27%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [[index]] to navigate.*