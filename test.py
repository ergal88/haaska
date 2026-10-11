import os
import json
import pytest
import requests

from haaska import HomeAssistant, Configuration, event_handler


@pytest.fixture
def configuration():
    return Configuration(opts_dict={
        "url": "http://localhost:8123",
        "bearer_token": "",
        "debug": False,
        "ssl_verify": True,
        "ssl_client": []
    })


@pytest.fixture
def home_assistant(configuration):
    return HomeAssistant(configuration)


def test_ha_build_url(home_assistant):
    url = home_assistant.build_url("test")
    assert url == "http://localhost:8123/api/test"


def test_get_user_agent(home_assistant):
    os.environ["AWS_DEFAULT_REGION"] = "test"
    user_agent = home_assistant.get_user_agent()
    assert user_agent.startswith(
        "Home Assistant Alexa Smart Home Skill - test - python-requests/")


def test_config_get(configuration):
    assert configuration.get(["debug"]) is False
    assert configuration.get(["test"]) is None
    assert configuration.get(["test"], default="default") == "default"


def test_config_get_url(configuration):
    test_urls = [
        "http://hass.example.com:8123",
        "http://hass.example.app"
    ]
    for expected_url in test_urls:
        assert configuration.get_url(expected_url + "/") == expected_url
        assert configuration.get_url(expected_url + "/api") == expected_url
        assert configuration.get_url(expected_url + "/api/") == expected_url


@pytest.mark.parametrize("client_cert, expected", [
    (None, None),
    ("", None),
    ([], None),
    ("combined.pem", "combined.pem"),
    (["cert.pem", "key.pem"], ("cert.pem", "key.pem")),
])
def test_client_certificate_https_pool(client_cert, expected):
    config = Configuration(opts_dict={
        "url": "https://example.invalid",
        "ssl_client": client_cert,
    })
    assert config.ssl_client == expected
    ha = HomeAssistant(config)
    request = requests.Request("POST", ha.build_url("alexa/smart_home"))
    prepared = ha.session.prepare_request(request)
    # Exercise the real Requests/urllib3 pool key without opening a socket.
    # Lists caused TypeError here, which the original tests never exercised.
    adapter = ha.session.get_adapter(prepared.url)
    pool = adapter.get_connection_with_tls_context(
        prepared, verify=ha.session.verify, cert=ha.session.cert)
    assert pool.host == "example.invalid"
    ha.session.close()


def test_missing_client_certificate():
    config = Configuration(opts_dict={"url": "https://example.invalid"})
    assert config.ssl_client is None


@pytest.mark.parametrize("client_cert", [["cert.pem"], ["a", "b", "c"]])
def test_invalid_client_certificate_pair(client_cert):
    with pytest.raises(ValueError, match="certificate and key"):
        Configuration(opts_dict={
            "url": "https://example.invalid", "ssl_client": client_cert})


def test_event_handler_forwarding(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.json").write_text(json.dumps({
        "url": "https://example.invalid/api",
        "bearer_token": "test-only-token",
        "ssl_client": [],
    }))
    event = {"directive": {"header": {
        "namespace": "Alexa.Discovery", "name": "Discover",
        "payloadVersion": "3", "messageId": "test-request"}}}
    response_event = {"event": {"header": {
        "namespace": "Alexa.Discovery", "name": "Discover.Response",
        "payloadVersion": "3", "messageId": "test-response"},
        "payload": {"endpoints": []}}}

    def send(session, request, **kwargs):
        assert request.url == "https://example.invalid/api/alexa/smart_home"
        assert request.headers["Authorization"] == "Bearer test-only-token"
        assert request.headers["content-type"] == "application/json"
        assert json.loads(request.body) == event
        assert kwargs["verify"] is True
        assert kwargs["cert"] is None
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps(response_event).encode("utf-8")
        return response

    monkeypatch.setattr(requests.Session, "send", send)
    assert event_handler(event, None) == response_event
