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


def test_nginx_does_not_compress_the_api_so_its_etag_stays_strong() -> None:
    conf = _text("frontend/nginx.conf.template")
    api_block = conf.split("location /api/ {", 1)[1].split("}", 1)[0]

    assert "gzip off;" in api_block


DEPLOY_TARGETS = (
    "deploy",
    "deploy-first",
    "deploy-bootstrap",
    "deploy-clone",
    "deploy-caddy",
    "deploy-build",
    "deploy-push",
    "deploy-release",
    "deploy-verify",
    "deploy-apply",
    "deploy-env",
    "deploy-status",
    "deploy-logs",
    "deploy-ssh",
    "deploy-seed-accounts",
    "deploy-backup",
    "deploy-restore",
    "deploy-rollback",
    "deploy-prune",
)


def _deploy_section() -> str:
    return _text("Makefile").split("# Deployment", 1)[1]


def _recipe(target: str) -> str:
    """The text of one Makefile target: its line and the tab-indented lines after it."""
    match = re.search(rf"^{target}:.*\n((?:\t.*\n|\n(?=\t))*)", _deploy_section(), re.MULTILINE)
    assert match is not None, target
    return match.group(0)


def test_every_deploy_target_is_documented_for_make_help() -> None:
    for target in DEPLOY_TARGETS:
        assert re.search(rf"^{target}:.*?## \S", _deploy_section(), re.MULTILINE), target


def test_every_target_that_talks_to_the_server_checks_for_a_host_and_a_key_first() -> None:
    macro = _deploy_section().split("define need_deploy", 1)[1].split("endef", 1)[0]
    assert "DEPLOY_HOST" in macro
    assert "DEPLOY_KEY" in macro
    assert "exit 1" in macro

    for target in DEPLOY_TARGETS:
        recipe = _recipe(target)
        if "$(SSH" in recipe:
            assert "$(call need_deploy" in recipe, target


def test_deploy_builds_then_sends_then_releases_then_verifies() -> None:
    recipe = _recipe("deploy")

    assert "$(MAKE) deploy-build deploy-push deploy-release deploy-verify" in recipe
    # Never from a branch, a dirty tree or a main that differs from the remote.
    assert "= main" in recipe
    assert "git diff --quiet" in recipe
    assert "origin/main" in recipe


def test_the_first_deploy_prepares_the_server_before_it_ships_and_sets_up_https_last() -> None:
    chain = "$(MAKE) deploy-bootstrap deploy-clone deploy-build deploy-push"
    tail = "deploy-release deploy-caddy deploy-verify"

    assert f"{chain} {tail}" in _recipe("deploy-first")


def test_the_release_pulls_main_fast_forward_only_and_pins_the_image_version() -> None:
    recipe = _recipe("deploy-release")

    assert "--ff-only" in recipe
    assert "DOCKET_VERSION=" in recipe
    assert "up -d" in recipe
    assert "--build" not in recipe  # the server never builds: the images are sent to it


def test_the_server_firewall_rules_go_above_the_reject_rule() -> None:
    script = _deploy_section().split("define DEPLOY_BOOTSTRAP_SCRIPT", 1)[1].split("endef", 1)[0]

    assert "awk '/REJECT/" in script
    assert "iptables -I INPUT" in script
    assert "iptables -A INPUT" not in script  # appending lands below Oracle's REJECT rule


def test_no_deploy_target_can_delete_the_database_volume_or_print_secrets() -> None:
    section = _deploy_section()

    for forbidden in ("down -v", "--volumes", "volume rm", "volume prune", "docker system prune"):
        assert forbidden not in section, forbidden
    assert "cat deploy/production.env" not in section
    assert "echo $$POSTGRES_PASSWORD" not in section


def test_the_per_machine_deploy_settings_file_is_not_committed() -> None:
    assert "deploy/deploy.local.mk" in _text(".gitignore").splitlines()
