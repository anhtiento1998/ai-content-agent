"""`tiktok-auth`: local-redirect and paste-the-URL logins, with TikTok's endpoints faked."""

import hashlib
import json
import threading
import urllib.parse
import urllib.request

import pytest
from fakes import FakeText  # noqa: F401  (puts src/ on sys.path)

from ai_content_agent.config import Config
from ai_content_agent.publishers import tiktok_auth
from ai_content_agent.publishers.tiktok_auth import (
    TikTokAuthError, authorize, build_authorize_url, code_from_redirect, pkce_pair,
)
from ai_content_agent.publishers.tiktok_publisher import TikTokTokens

TOKENS = {"access_token": "act.1", "refresh_token": "rft.1", "expires_in": 86400, "refresh_expires_in": 31536000,
          "open_id": "user-1", "scope": "user.info.basic,video.publish", "token_type": "Bearer"}


class FakeTokenEndpoint:
    def __init__(self, reply=TOKENS):
        self.reply, self.sent = reply, None

    def post(self, url, headers, data, timeout):
        self.sent = {"url": url, **data}
        reply = self.reply
        return type("R", (), {"json": lambda self: reply})()


def _free_port():
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_pkce_and_authorize_url():
    verifier, challenge = pkce_pair("hex")
    assert challenge == hashlib.sha256(verifier.encode()).hexdigest()  # TikTok desktop: hex, not base64url
    assert "=" not in pkce_pair("base64url")[1] and pkce_pair("none") == (None, None)
    with pytest.raises(ValueError):
        pkce_pair("md5")

    url = build_authorize_url("key", "http://localhost:8721/callback/", "user.info.basic,video.publish", "st", "ch")
    query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
    assert url.startswith("https://www.tiktok.com/v2/auth/authorize/?")
    assert query == {"client_key": "key", "scope": "user.info.basic,video.publish", "response_type": "code",
                     "redirect_uri": "http://localhost:8721/callback/", "state": "st", "code_challenge": "ch",
                     "code_challenge_method": "S256"}


def test_code_from_redirect_checks_state_and_errors():
    assert code_from_redirect("https://site.example/cb?code=a%2Ab&state=st", "st") == "a*b"  # code is URL-decoded
    with pytest.raises(TikTokAuthError, match="state"):
        code_from_redirect("https://site.example/cb?code=abc&state=other", "st")
    with pytest.raises(TikTokAuthError, match="access_denied"):
        code_from_redirect("/callback/?error=access_denied&error_description=User+cancelled", "st")
    with pytest.raises(TikTokAuthError, match="no \\?code="):
        code_from_redirect("https://site.example/cb", "st")


def test_local_login_saves_tokens_the_publisher_can_use(tmp_path, monkeypatch):
    endpoint = FakeTokenEndpoint()
    monkeypatch.setattr(tiktok_auth, "requests", endpoint)
    port, token_file = _free_port(), tmp_path / "tiktok_token.json"
    opened, page_read = {}, threading.Event()

    def browser(url):  # plays the user approving in TikTok: follow the redirect with a code
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
        opened.update(query)
        callback = f"{query['redirect_uri']}?code=the-code&state={query['state']}"
        with urllib.request.urlopen(callback.replace("localhost", "127.0.0.1"), timeout=5) as response:
            opened["page"] = response.read().decode("utf-8")
        page_read.set()

    info = authorize("key", "secret", str(token_file), scope="user.info.basic,video.publish", port=port,
                     open_browser=browser, echo=lambda _text: None, timeout=10)

    # The "browser" runs in its own thread and may still be reading the page when authorize returns.
    assert page_read.wait(timeout=5)
    assert info["open_id"] == "user-1" and "Đăng nhập TikTok xong" in opened["page"]
    sent = endpoint.sent
    assert sent["url"].endswith("/v2/oauth/token/") and sent["grant_type"] == "authorization_code"
    assert (sent["code"], sent["client_secret"]) == ("the-code", "secret")
    assert sent["redirect_uri"] == f"http://localhost:{port}/callback/"
    assert hashlib.sha256(sent["code_verifier"].encode()).hexdigest() == opened["code_challenge"]

    saved = json.loads(token_file.read_text())
    assert saved["refresh_token"] == "rft.1" and saved["scope"] == TOKENS["scope"]
    tokens = TikTokTokens(client_key="key", client_secret="secret", token_file=str(token_file))
    assert tokens.access_token() == "act.1" and tokens.can_refresh  # no refresh token needed in .env any more
    config = Config(tiktok_client_key="key", tiktok_client_secret="secret", tiktok_token_file=str(token_file))
    assert config.status()["platforms"]["tiktok"]["ready"] is True


def test_web_app_login_takes_the_pasted_redirect(tmp_path, monkeypatch):
    endpoint = FakeTokenEndpoint()
    monkeypatch.setattr(tiktok_auth, "requests", endpoint)
    seen = {}

    def browser(url):
        seen.update(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)))

    authorize("key", "secret", str(tmp_path / "t.json"), scope="user.info.basic,video.upload",
              redirect_uri="https://kenh.example/tiktok/callback", open_browser=browser, echo=lambda _t: None,
              prompt=lambda _q: f"https://kenh.example/tiktok/callback?code=web-code&state={seen['state']}")

    assert "code_challenge" not in seen and "code_verifier" not in endpoint.sent  # web apps: no PKCE
    assert endpoint.sent["code"] == "web-code" and endpoint.sent["redirect_uri"] == "https://kenh.example/tiktok/callback"


def test_login_failures_are_explained(tmp_path, monkeypatch):
    with pytest.raises(TikTokAuthError, match="TIKTOK_CLIENT_KEY"):
        authorize(None, None, str(tmp_path / "t.json"), scope="x")

    monkeypatch.setattr(tiktok_auth, "requests", FakeTokenEndpoint({"error": "invalid_grant",
                                                                    "error_description": "code expired"}))
    seen = {}
    with pytest.raises(TikTokAuthError, match="invalid_grant.*code expired"):
        authorize("key", "secret", str(tmp_path / "t.json"), scope="x", redirect_uri="https://a.example/cb",
                  open_browser=lambda url: seen.update(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))),
                  echo=lambda _t: None, prompt=lambda _q: f"https://a.example/cb?code=c&state={seen['state']}")
    assert not (tmp_path / "t.json").exists()

    with pytest.raises(TikTokAuthError, match="No login arrived"):
        authorize("key", "secret", str(tmp_path / "t.json"), scope="x", port=_free_port(),
                  open_browser=lambda _url: None, echo=lambda _t: None, timeout=1)


def test_status_points_to_tiktok_auth_when_only_app_keys_are_set(tmp_path):
    config = Config(tiktok_client_key="key", tiktok_client_secret="secret",
                    tiktok_token_file=str(tmp_path / "missing.json"))
    tiktok = config.status()["platforms"]["tiktok"]
    assert tiktok["ready"] is False and "tiktok-auth" in tiktok["note"]
