import pytest
import httpx
import respx

from posthog_instantly_attribution.config import Config
from posthog_instantly_attribution.posthog import normalize_email, get_trial_emails, set_attributed_source

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


# ---------------------------------------------------------------------------
# normalize_email
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("User@Example.COM", "user@example.com"),
    ("  alice@example.com  ", "alice@example.com"),
    ("not-an-email", None),
    ("@nodomain", None),
    (None, None),
    (123, None),
    ("", None),
])
def test_normalize_email(value, expected):
    assert normalize_email(value) == expected


# ---------------------------------------------------------------------------
# get_trial_emails
# ---------------------------------------------------------------------------

@respx.mock
def test_get_trial_emails_returns_emails():
    url = "https://app.posthog.com/api/projects/12345/query"
    respx.post(url).mock(return_value=httpx.Response(
        200,
        json={"results": [["alice@example.com"], ["Bob@Example.com"]]},
    ))

    with httpx.Client() as client:
        emails = get_trial_emails(client, FAKE_CONFIG, "2026-01-01", include_already_attributed=False)

    assert emails == ["alice@example.com", "bob@example.com"]


@respx.mock
def test_get_trial_emails_deduplicates():
    url = "https://app.posthog.com/api/projects/12345/query"
    respx.post(url).mock(return_value=httpx.Response(
        200,
        json={"results": [["alice@example.com"], ["alice@example.com"]]},
    ))

    with httpx.Client() as client:
        emails = get_trial_emails(client, FAKE_CONFIG, "2026-01-01", include_already_attributed=False)

    assert emails == ["alice@example.com"]


@respx.mock
def test_get_trial_emails_skips_non_emails():
    url = "https://app.posthog.com/api/projects/12345/query"
    respx.post(url).mock(return_value=httpx.Response(
        200,
        json={"results": [["not-an-email"], ["alice@example.com"]]},
    ))

    with httpx.Client() as client:
        emails = get_trial_emails(client, FAKE_CONFIG, "2026-01-01", include_already_attributed=False)

    assert emails == ["alice@example.com"]


@respx.mock
def test_get_trial_emails_empty():
    url = "https://app.posthog.com/api/projects/12345/query"
    respx.post(url).mock(return_value=httpx.Response(200, json={"results": []}))

    with httpx.Client() as client:
        emails = get_trial_emails(client, FAKE_CONFIG, "2026-01-01", include_already_attributed=False)

    assert emails == []


# ---------------------------------------------------------------------------
# set_attributed_source
# ---------------------------------------------------------------------------

@respx.mock
def test_set_attributed_source_posts_identify():
    route = respx.post("https://app.posthog.com/capture/").mock(
        return_value=httpx.Response(200, json={"status": 1})
    )

    with httpx.Client() as client:
        set_attributed_source(client, FAKE_CONFIG, "alice@example.com")

    assert route.called
    payload = route.calls.last.request.read()
    import json
    body = json.loads(payload)
    assert body["event"] == "$identify"
    assert body["distinct_id"] == "alice@example.com"
    assert body["properties"]["$set"]["attributed_source"] == "Instantly"
