import httpx
import respx

from posthog_instantly_attribution.config import Config
from posthog_instantly_attribution.instantly import exists_in_instantly

FAKE_CONFIG = Config(
    posthog_personal_api_key="phx_test",
    posthog_project_api_key="phc_test",
    posthog_project_id="12345",
    instantly_api_key="inst_test",
    posthog_host="https://app.posthog.com",
    instantly_host="https://api.instantly.ai",
    request_timeout_seconds=10.0,
    sleep_seconds=0.0,
)

URL = "https://api.instantly.ai/api/v2/leads/list"


@respx.mock
def test_exists_in_instantly_true():
    respx.post(URL).mock(return_value=httpx.Response(
        200, json={"items": [{"email": "alice@example.com"}]}
    ))
    with httpx.Client() as client:
        assert exists_in_instantly(client, FAKE_CONFIG, "alice@example.com") is True


@respx.mock
def test_exists_in_instantly_false():
    respx.post(URL).mock(return_value=httpx.Response(200, json={"items": []}))
    with httpx.Client() as client:
        assert exists_in_instantly(client, FAKE_CONFIG, "ghost@example.com") is False


@respx.mock
def test_exists_in_instantly_raises_on_http_error():
    respx.post(URL).mock(return_value=httpx.Response(401, json={"error": "unauthorized"}))
    with httpx.Client() as client:
        try:
            exists_in_instantly(client, FAKE_CONFIG, "alice@example.com")
            assert False, "Should have raised"
        except httpx.HTTPStatusError as exc:
            assert exc.response.status_code == 401
