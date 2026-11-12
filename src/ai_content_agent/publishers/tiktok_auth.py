"""One-time TikTok login (`ai-content-agent tiktok-auth`): get the first refresh token.

OAuth v2 authorization-code flow against the user's own TikTok developer app:

1. A browser opens TikTok's consent page (/v2/auth/authorize/).
2. TikTok redirects to the redirect URI registered in the app's Login Kit
   settings, carrying a one-time code.
3. The code is exchanged at /v2/oauth/token/ and the tokens are written to
   TIKTOK_TOKEN_FILE in the format TikTokTokens refreshes from then on.

Desktop apps (default): the redirect goes to a small listener on this
machine — register exactly the URI the command prints, e.g.
http://localhost:8721/callback/ — and PKCE is used. TikTok's desktop PKCE
is non-standard: the challenge is the *hex* SHA-256 of the verifier, not
base64url (`--pkce base64url` or `none` exist in case that changes).

Web apps: TikTok only redirects to the app's registered https URL. Pass it
with --redirect-uri; after consent, copy the address the browser lands on
(it contains ?code=...) and paste it into the terminal.

Written from TikTok's documented flow; not yet run against a live app.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import secrets
import threading
import time
import urllib.parse
import webbrowser
from typing import Callable

import requests

from .tiktok_publisher import _API_BASE, TikTokTokens

AUTHORIZE_URL = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES_BY_MODE = {"direct": "user.info.basic,video.publish", "inbox": "user.info.basic,video.upload"}
PKCE_METHODS = ("hex", "base64url", "none")
_DONE_PAGE = (
    "<!doctype html><meta charset='utf-8'><title>ai-content-agent</title>"
    "<body style='font-family:sans-serif;padding:3em'><h2>{title}</h2><p>{body}</p></body>"
)


class TikTokAuthError(RuntimeError):
    pass


def pkce_pair(method: str = "hex") -> tuple[str | None, str | None]:
    """(code_verifier, code_challenge) — both None for method "none"."""

    if method not in PKCE_METHODS:
        raise ValueError(f"--pkce must be one of {', '.join(PKCE_METHODS)}, got {method!r}")
    if method == "none":
        return None, None
    verifier = secrets.token_urlsafe(64)[:64]
    digest = hashlib.sha256(verifier.encode("ascii"))
    challenge = digest.hexdigest() if method == "hex" else base64.urlsafe_b64encode(digest.digest()).rstrip(b"=").decode()
    return verifier, challenge


def build_authorize_url(client_key: str, redirect_uri: str, scope: str, state: str,
                        code_challenge: str | None = None) -> str:
    params = {"client_key": client_key, "scope": scope, "response_type": "code",
              "redirect_uri": redirect_uri, "state": state}
    if code_challenge:
        params.update(code_challenge=code_challenge, code_challenge_method="S256")
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def code_from_redirect(url_or_query: str, state: str) -> str:
    """The authorization code in a redirect URL (or bare query string), after checking `state`."""

    query = urllib.parse.urlsplit(url_or_query).query or url_or_query.lstrip("?")
    params = {key: values[0] for key, values in urllib.parse.parse_qs(query).items()}
    if params.get("error"):
        raise TikTokAuthError(f"TikTok refused the login ({params['error']}): "
                              f"{params.get('error_description', 'no description')}")
    if not params.get("code"):
        raise TikTokAuthError("The redirect carried no ?code= — copy the full address the browser landed on")
    if params.get("state") != state:
        raise TikTokAuthError("The redirect's state does not match this login attempt — start tiktok-auth again")
    return params["code"]


def wait_for_callback(port: int, state: str, *, timeout: float = 300.0,
                      on_ready: Callable[[], None] | None = None) -> str:
    """Listen on 127.0.0.1:`port` for TikTok's redirect and return the code."""

    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (http.server API)
            if "code=" not in self.path and "error=" not in self.path:
                self.send_response(404)  # favicon and other stray requests
                self.end_headers()
                return
            try:
                result["code"] = code_from_redirect(self.path, state)
                page = _DONE_PAGE.format(title="Đăng nhập TikTok xong", body="Bạn có thể đóng tab này và quay lại terminal.")
            except TikTokAuthError as exc:
                result["error"] = exc
                page = _DONE_PAGE.format(title="Đăng nhập TikTok thất bại", body="Xem thông báo trong terminal.")
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):  # keep the code out of the terminal log
            return

    try:
        server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        raise TikTokAuthError(f"Cannot listen on port {port} ({exc}) — choose another with --port and register "
                              "that redirect URI in the TikTok app") from exc
    server.timeout = 0.5
    deadline = time.monotonic() + timeout
    try:
        if on_ready:
            threading.Thread(target=on_ready, daemon=True).start()
        while not result and time.monotonic() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if "error" in result:
        raise result["error"]
    if "code" not in result:
        raise TikTokAuthError(f"No login arrived within {timeout:.0f}s — is the redirect URI registered in the TikTok app?")
    return result["code"]


def exchange_code(client_key: str, client_secret: str, code: str, redirect_uri: str,
                  code_verifier: str | None = None) -> dict:
    data = {"client_key": client_key, "client_secret": client_secret, "code": code,
            "grant_type": "authorization_code", "redirect_uri": redirect_uri}
    if code_verifier:
        data["code_verifier"] = code_verifier
    resp = requests.post(f"{_API_BASE}/oauth/token/", headers={"Content-Type": "application/x-www-form-urlencoded"},
                         data=data, timeout=30).json()
    if "access_token" not in resp or "refresh_token" not in resp:
        raise TikTokAuthError(f"TikTok did not issue tokens ({resp.get('error', 'unknown')}): "
                              f"{resp.get('error_description', resp)}")
    return resp


def authorize(
    client_key: str | None,
    client_secret: str | None,
    token_file: str,
    *,
    scope: str,
    port: int = 8721,
    redirect_uri: str | None = None,
    pkce: str = "hex",
    open_browser: Callable[[str], object] = webbrowser.open,
    prompt: Callable[[str], str] = input,
    echo: Callable[[str], None] = print,
    timeout: float = 300.0,
) -> dict:
    """Run the login and save the tokens. Returns {"open_id", "scope", "expires_in", "refresh_expires_in"}."""

    if not client_key or not client_secret:
        raise TikTokAuthError("Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env first (TikTok for Developers > "
                              "your app > App details)")
    local = redirect_uri is None
    redirect_uri = redirect_uri or f"http://localhost:{port}/callback/"
    state = secrets.token_urlsafe(24)
    verifier, challenge = pkce_pair(pkce if local else "none")
    url = build_authorize_url(client_key, redirect_uri, scope, state, challenge)

    if local:
        echo(f"Redirect URI to register in the TikTok app (Login Kit): {redirect_uri}")
        echo(f"Opening TikTok in your browser. If nothing opens, visit:\n{url}")
        code = wait_for_callback(port, state, timeout=timeout, on_ready=lambda: open_browser(url))
    else:
        echo(f"Open this address, approve, then copy the address the browser lands on:\n{url}")
        open_browser(url)
        code = code_from_redirect(prompt("Paste the redirected address here: ").strip(), state)

    tokens = exchange_code(client_key, client_secret, code, redirect_uri, verifier)
    TikTokTokens(client_key=client_key, client_secret=client_secret, token_file=token_file).store(tokens)
    return {key: tokens.get(key) for key in ("open_id", "scope", "expires_in", "refresh_expires_in")}
