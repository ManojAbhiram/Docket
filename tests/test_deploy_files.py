"""The deployment files keep the promises the code relies on (NOTASK-17).

Regression: found by the production smoke test on 2026-10-11. The web image baked in
`VITE_API_URL=/api`, so the browser called `/api/api/auth/login`; nothing in the repository
exercised the images, so only a live run showed it.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_the_web_image_leaves_the_api_base_empty_since_paths_already_start_with_api() -> None:
    match = re.search(r"^ARG VITE_API_URL=(.*)$", _text("frontend/Dockerfile"), re.MULTILINE)

    assert match is not None
    assert match.group(1).strip() == ""


def test_nginx_proxies_api_without_changing_the_path_and_allows_the_upload_size() -> None:
    conf = _text("frontend/nginx.conf.template")

    assert "location /api/ {" in conf
    # No URI after the upstream, so the path reaches the API unchanged as /api/...
    assert re.search(r"proxy_pass \$\{API_UPSTREAM\};", conf)
    assert "client_max_body_size 9m;" in conf  # the upload cap is 8 MiB plus multipart overhead
    # Set, never appended, so a client cannot choose the address the sign-in limiter sees.
    assert "X-Forwarded-For $remote_addr;" in conf


def _service(name: str) -> str:
    """The text of one service in the compose file, up to the next service or the volumes."""
    stack = _text("docker-compose.prod.yml")
    match = re.search(rf"^  {name}:\n(.*?)(?=^  \w[\w-]*:\n|^\w)", stack, re.MULTILINE | re.DOTALL)
    assert match is not None, name
    return match.group(1)


def test_the_production_stack_publishes_only_the_web_container() -> None:
    assert "ports:" in _service("web")
    for name in ("api", "postgres", "migrate"):
        assert "ports:" not in _service(name), name


def test_the_production_api_runs_in_production_mode_with_secure_cookies_and_a_ceiling() -> None:
    api = _service("api")

    assert "ENV: production" in api
    assert 'SESSION_COOKIE_SECURE: "true"' in api
    assert 'WEB_CONCURRENCY: "1"' in api  # the document worker lives in this one process (ADR-0011)
    assert "mem_limit:" in api


def test_the_production_example_holds_placeholders_only() -> None:
    example = _text("deploy/production.env.example")

    assert "OPENROUTER_API_KEY=\n" in example
    assert "sk-or" not in example
