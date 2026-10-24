import generated.om_openapi_client.om_openapi_client as om_api_client  # type: ignore[import-untyped,unused-ignore]
from tests.integration.common_utils.constants import API_SERVER_URL

api_config = om_api_client.Configuration(host=API_SERVER_URL)
