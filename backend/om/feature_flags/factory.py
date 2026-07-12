from om.configs.app_configs import DEV_MODE
from om.feature_flags.interface import FeatureFlagProvider
from om.feature_flags.interface import NoOpFeatureFlagProvider
from om.feature_flags.posthog_provider import PostHogFeatureFlagProvider
from shared_configs.configs import MULTI_TENANT


def get_posthog_feature_flag_provider() -> FeatureFlagProvider:
    """
    Get the PostHog feature flag provider instance.

    This is the EE implementation that gets loaded by the versioned
    implementation loader.

    Returns:
        PostHogFeatureFlagProvider: The PostHog-based feature flag provider
    """
    return PostHogFeatureFlagProvider()


def get_default_feature_flag_provider() -> FeatureFlagProvider:
    """
    Get the default feature flag provider implementation.

    Returns the PostHog-based provider in Enterprise Edition when available,
    otherwise returns a no-op provider that always returns False.

    This function is designed for dependency injection - callers should
    use this factory rather than directly instantiating providers.

    Returns:
        FeatureFlagProvider: The configured feature flag provider instance
    """
    if MULTI_TENANT or DEV_MODE:
        return get_posthog_feature_flag_provider()
    return NoOpFeatureFlagProvider()
