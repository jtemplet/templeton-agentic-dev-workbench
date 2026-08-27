#!/usr/bin/env python3
"""Regression suite for route_qa.py.

Stdlib only, no install, mirroring test_check_doc_paths.py. Run with:
    python3 skills/quality-gates/scripts/test_route_qa.py

The cases come from the router's contract, and the first group is the reason the
router is a script rather than three sentences of prose. Each case there is a file
whose path points one way and whose content points another, which is where a
path-only rule sends a REST change to a browser tool or probes nothing at all.

The prose-file group is the same lesson Gate 5 learned at scale: its checker
reported 194 missing paths, every one of them a sample inside a fenced block.
Documentation that explains a REST route must never be classified AS a REST route.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROUTER = Path(__file__).resolve().parent / "route_qa.py"

passed = 0
failed = 0


def check(name: str, fn) -> None:
    global passed, failed
    try:
        fn()
        print(f"  ok   - {name}")
        passed += 1
    except AssertionError as exc:
        print(f"  FAIL - {name}\n         {exc}")
        failed += 1


def build(files: dict[str, str]) -> Path:
    """A throwaway tree holding exactly the files a case needs."""
    root = Path(tempfile.mkdtemp())
    for path, body in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def run_full(
    root: Path, *paths: str, extra: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    """The whole result, for the cases that assert on stderr."""
    return subprocess.run(
        [sys.executable, str(ROUTER), "--repo-root", str(root), *extra, *paths],
        capture_output=True,
        text=True,
    )


def run(root: Path, *paths: str, extra: tuple[str, ...] = ()) -> dict:
    result = run_full(root, *paths, extra=extra)
    assert result.returncode == 0, f"router exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout)


def surfaces(decision: dict) -> dict[str, dict]:
    return {entry["surface"]: entry for entry in decision["surfaces"]}


def route_of(decision: dict, surface: str) -> str:
    entry = surfaces(decision).get(surface)
    assert entry, f"no {surface} surface in {sorted(surfaces(decision))}"
    return entry["method"]


def endpoints_of(decision: dict) -> list[tuple[str | None, str]]:
    """Every extracted endpoint as (method, path), in the order reported."""
    entry = surfaces(decision).get("http-api")
    assert entry, f"no http-api surface in {sorted(surfaces(decision))}"
    return [(e["method"], e["path"]) for e in entry["endpoints"]]


def extractors_of(decision: dict) -> set[str]:
    """Which extractors produced the endpoints.

    Asserted where two extractors could plausibly match the same text, so a case
    pins the one that is meant to fire rather than accepting any of them.
    """
    entry = surfaces(decision).get("http-api")
    assert entry, f"no http-api surface in {sorted(surfaces(decision))}"
    return {e["extractor"] for e in entry["endpoints"]}


print("\n  [content beats path: the misroutes a path-only rule produces]")


def case_jbuilder_is_api_not_browser() -> None:
    """A JSON view lives under the same app/views tree as every HTML template."""
    root = build({"app/views/exports/index.json.jbuilder": "json.id @export.id\n"})
    decision = run(root, "app/views/exports/index.json.jbuilder")
    assert "http-api" in surfaces(decision), (
        f"a jbuilder view renders JSON, so it routes to curl: {surfaces(decision)}"
    )
    assert "browser-ui" not in surfaces(decision), (
        f"app/views must not win over the jbuilder rule: {surfaces(decision)}"
    )


def case_next_route_handler_is_api() -> None:
    """`.ts` alone reads as a library, so nothing would be probed."""
    body = "export async function POST(req: Request) { return Response.json({}) }\n"
    root = build({"app/api/exports/route.ts": body})
    decision = run(root, "app/api/exports/route.ts")
    assert route_of(decision, "http-api") == "curl"
    endpoints = surfaces(decision)["http-api"]["endpoints"]
    assert endpoints == [
        {
            "method": "POST",
            "path": "/api/exports",
            "source": "app/api/exports/route.ts:1",
            "extractor": "next-route-handler",
        }
    ], f"the URL comes from the file path: {endpoints}"


def case_swiftui_screen_is_mobile_not_library() -> None:
    root = build({"Sources/App/HomeView.swift": "import SwiftUI\nstruct HomeView {}\n"})
    decision = run(root, "Sources/App/HomeView.swift")
    assert route_of(decision, "mobile-ui") == "handoff"
    assert surfaces(decision)["mobile-ui"]["owner"] == "/ios-qa"


def case_plain_swift_is_a_library() -> None:
    root = build({"Sources/Core/Money.swift": "struct Money { let cents: Int }\n"})
    decision = run(root, "Sources/Core/Money.swift")
    assert route_of(decision, "library") == "coverage"
    assert "mobile-ui" not in surfaces(decision), "no UI import means no handoff"


def case_argparse_module_is_cli() -> None:
    root = build({"src/tool/run.py": "import argparse\n\ndef main():\n    pass\n"})
    decision = run(root, "src/tool/run.py")
    assert route_of(decision, "cli") == "coverage"


for name, fn in [
    ("a .json.jbuilder view routes to curl, not /qa", case_jbuilder_is_api_not_browser),
    ("a Next.js route handler routes to curl", case_next_route_handler_is_api),
    ("a SwiftUI screen hands off to /ios-qa", case_swiftui_screen_is_mobile_not_library),
    ("a Swift file with no UI import is a library", case_plain_swift_is_a_library),
    ("a module importing argparse is a CLI", case_argparse_module_is_cli),
]:
    check(name, fn)


print("\n  [prose routes by path only: documentation is not the thing it documents]")


def case_markdown_quoting_express_is_not_an_api() -> None:
    body = "Register the route:\n\n```js\napp.post('/api/exports', handler)\n```\n"
    root = build({"docs/api.md": body})
    decision = run(root, "docs/api.md")
    assert "http-api" not in surfaces(decision), (
        f"a fenced sample is not an endpoint: {json.dumps(decision['surfaces'])}"
    )
    assert route_of(decision, "docs") == "none"


def case_skill_md_is_a_prompt_asset() -> None:
    root = build({"skills/thing/SKILL.md": "---\nname: thing\n---\n\nDo the thing.\n"})
    decision = run(root, "skills/thing/SKILL.md")
    assert route_of(decision, "prompt-assets") == "coverage", (
        "a skill is behavior an LLM reads, so it needs a coverage review, not `none`"
    )


def case_python_quoting_express_is_not_an_api() -> None:
    """The same trap one level down, and the one the router fell into on itself.

    A Python file that mentions `app.get('/x')` in a comment mentions an
    endpoint. It does not serve one, and probing `/x` would 404 against whatever
    server happened to be listening.
    """
    body = "# a router reads `app.get('/x')` out of Express sources\nimport re\n"
    root = build({"src/router.py": body})
    decision = run(root, "src/router.py")
    assert "http-api" not in surfaces(decision), (
        f"an Express pattern in Python is text: {json.dumps(decision['surfaces'])}"
    )


def case_swift_import_in_python_is_not_mobile() -> None:
    root = build({"src/rules.py": 'PATTERN = r"^\\s*import\\s+SwiftUI\\b"\n'})
    decision = run(root, "src/rules.py")
    assert "mobile-ui" not in surfaces(decision), (
        f"a Swift import inside Python is a string: {json.dumps(decision['surfaces'])}"
    )


def case_client_call_in_jsx_is_not_a_route() -> None:
    """The misroute that pointed the other way, found by a fresh-eyes pass.

    `api.get('/x')` is how an axios or fetch wrapper is CALLED from a component.
    Reading it as a route definition scored the component http-api at specificity
    3, which outranked its own `.tsx` rule, so a React-only change routed to curl
    and lost its `/qa` handoff entirely.
    """
    body = (
        "import { api } from './client'\n"
        "export const Panel = () => {\n"
        "  const load = () => api.get('/api/v1/exports')\n"
        "  return <div onClick={load} />\n"
        "}\n"
    )
    root = build({"src/Panel.tsx": body})
    decision = run(root, "src/Panel.tsx")
    assert route_of(decision, "browser-ui") == "handoff", (
        f"a component that calls an API is still browser UI: {json.dumps(decision['surfaces'])}"
    )
    assert "http-api" not in surfaces(decision), (
        f"calling an endpoint is not defining one: {json.dumps(decision['surfaces'])}"
    )


def case_express_route_in_plain_js_still_found() -> None:
    """The control for the case above: the real thing must still be detected."""
    root = build({"src/server.js": "app.get('/api/v1/exports', handler)\n"})
    decision = run(root, "src/server.js")
    endpoints = surfaces(decision)["http-api"]["endpoints"]
    assert [(e["method"], e["path"]) for e in endpoints] == [("GET", "/api/v1/exports")], endpoints


def case_the_router_does_not_misclassify_itself() -> None:
    """The shipped artifact, which is where this whole rule came from."""
    repo = Path(__file__).resolve().parents[3]
    decision = run(repo, "skills/quality-gates/scripts/route_qa.py")
    assert sorted(surfaces(decision)) == ["cli"], (
        f"route_qa.py is a CLI and nothing else: {sorted(surfaces(decision))}"
    )


for name, fn in [
    ("markdown quoting an Express route is not an API", case_markdown_quoting_express_is_not_an_api),
    ("a SKILL.md is a prompt asset, not a document", case_skill_md_is_a_prompt_asset),
    ("Python quoting an Express route is not an API", case_python_quoting_express_is_not_an_api),
    ("a Swift import inside Python is not mobile UI", case_swift_import_in_python_is_not_mobile),
    ("an api.get() call in .tsx stays browser UI", case_client_call_in_jsx_is_not_a_route),
    ("a real Express route in .js is still found", case_express_route_in_plain_js_still_found),
    ("the router does not classify itself as an API", case_the_router_does_not_misclassify_itself),
]:
    check(name, fn)


print("\n  [endpoint extractors: one case per framework]")

# Every extractor gets a case here, because both ways one can break are silent.
# An extractor that finds nothing empties the probe spec, so Gate 7 checks nothing
# and says so in a voice that sounds fine. An extractor that invents a path sends a
# probe at a URL that does not exist, which reads as a broken API. Six of these
# nine shipped with no case at all until the change-coverage gate said so.


def case_fastapi_router_decorator() -> None:
    body = (
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "\n"
        '@router.get("/api/v1/exports")\n'
        "def list_exports():\n"
        "    return []\n"
        "\n"
        '@router.delete("/api/v1/exports/{id}")\n'
        "def drop(id: str):\n"
        "    return None\n"
    )
    root = build({"app/routers/exports.py": body})
    decision = run(root, "app/routers/exports.py")
    assert route_of(decision, "http-api") == "curl"
    assert endpoints_of(decision) == [
        ("GET", "/api/v1/exports"),
        ("DELETE", "/api/v1/exports/{id}"),
    ], endpoints_of(decision)


def case_flask_route_defaults_to_get() -> None:
    """`@app.route` with no `methods=` is a GET, which is Flask's own default."""
    body = 'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/items")\ndef items():\n    return []\n'
    root = build({"app/views.py": body})
    decision = run(root, "app/views.py")
    assert endpoints_of(decision) == [("GET", "/items")], endpoints_of(decision)


def case_flask_explicit_methods_become_one_endpoint_each() -> None:
    """Two methods on one route are two cases to probe, not one."""
    body = (
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "\n"
        '@app.route("/items", methods=["POST", "PUT"])\n'
        "def write():\n"
        "    return {}, 201\n"
    )
    root = build({"app/views.py": body})
    decision = run(root, "app/views.py")
    assert endpoints_of(decision) == [("POST", "/items"), ("PUT", "/items")], endpoints_of(decision)


def case_django_urls_and_unresolved_include() -> None:
    """Django names no method at the URL, so the method is null rather than guessed."""
    body = (
        "from django.urls import path, include\n"
        "from . import views\n"
        "\n"
        "urlpatterns = [\n"
        '    path("items/", views.items),\n'
        '    path("api/", include("api.urls")),\n'
        "]\n"
    )
    root = build({"project/urls.py": body})
    decision = run(root, "project/urls.py")
    assert endpoints_of(decision) == [(None, "/items/"), (None, "/api/")], endpoints_of(decision)
    unresolved = surfaces(decision)["http-api"]["unresolved"]
    assert len(unresolved) == 1 and "show_urls" in unresolved[0], unresolved


def case_spring_mapping_annotations() -> None:
    """An empty `@PostMapping("")` is the class's own root path, not no path."""
    body = (
        "@RestController\n"
        'public class ExportController {\n'
        '  @GetMapping("/api/v1/exports")\n'
        "  public List<Export> list() { return null; }\n"
        '  @PostMapping("")\n'
        "  public Export create() { return null; }\n"
        "}\n"
    )
    root = build({"src/main/java/ExportController.java": body})
    decision = run(root, "src/main/java/ExportController.java")
    assert route_of(decision, "http-api") == "curl"
    assert endpoints_of(decision) == [("GET", "/api/v1/exports"), ("POST", "/")], endpoints_of(decision)


def case_go_chi_router() -> None:
    body = (
        "package api\n"
        "\n"
        "func Routes(r chi.Router) {\n"
        '\tr.Get("/api/v1/exports", listExports)\n'
        '\tr.Post("/api/v1/exports", createExport)\n'
        "}\n"
    )
    root = build({"internal/api/router.go": body})
    decision = run(root, "internal/api/router.go")
    assert endpoints_of(decision) == [
        ("GET", "/api/v1/exports"),
        ("POST", "/api/v1/exports"),
    ], endpoints_of(decision)
    assert extractors_of(decision) == {"go-router"}, extractors_of(decision)


def case_go_handlefunc_has_no_method() -> None:
    """`HandleFunc` registers every method, so the extractor claims none."""
    body = 'package api\n\nfunc Serve(mux *http.ServeMux) {\n\tmux.HandleFunc("/health", health)\n}\n'
    root = build({"internal/api/serve.go": body})
    decision = run(root, "internal/api/serve.go")
    assert endpoints_of(decision) == [(None, "/health")], endpoints_of(decision)
    assert extractors_of(decision) == {"go-handlefunc"}, extractors_of(decision)


for name, fn in [
    ("a FastAPI @router decorator yields its endpoints", case_fastapi_router_decorator),
    ("a Flask @app.route with no methods= is a GET", case_flask_route_defaults_to_get),
    ("a Flask route with two methods yields two endpoints", case_flask_explicit_methods_become_one_endpoint_each),
    ("Django path() yields a null method, include() is unresolved", case_django_urls_and_unresolved_include),
    ("Spring @Get/@PostMapping yield their endpoints", case_spring_mapping_annotations),
    ("a Go chi router yields its endpoints", case_go_chi_router),
    ("Go HandleFunc yields a null method", case_go_handlefunc_has_no_method),
]:
    check(name, fn)


print("\n  [the three routes, one per method]")


def case_rest_change_routes_to_curl() -> None:
    routes = 'Rails.application.routes.draw do\n  post "/api/v1/exports", to: "exports#create"\nend\n'
    root = build({"config/routes.rb": routes})
    decision = run(root, "config/routes.rb")
    assert decision["methods"] == ["curl"], f"one surface, one method: {decision['methods']}"
    endpoints = surfaces(decision)["http-api"]["endpoints"]
    assert [(e["method"], e["path"]) for e in endpoints] == [("POST", "/api/v1/exports")], endpoints


def case_browser_change_routes_to_qa() -> None:
    root = build({"app/javascript/ExportTable.tsx": "export const T = () => <div/>\n"})
    decision = run(root, "app/javascript/ExportTable.tsx")
    assert route_of(decision, "browser-ui") == "handoff"
    assert surfaces(decision)["browser-ui"]["owner"] == "/qa"


def case_library_change_routes_to_coverage() -> None:
    root = build({"src/money.py": "def cents(x):\n    return x * 100\n"})
    decision = run(root, "src/money.py")
    assert decision["methods"] == ["coverage"], decision["methods"]


def case_docs_only_change_routes_to_none() -> None:
    root = build({"README.md": "# Title\n"})
    decision = run(root, "README.md")
    assert decision["methods"] == ["none"], decision["methods"]


def case_two_surfaces_both_reported() -> None:
    """A full-stack change needs both a probe and a handoff, not a winner."""
    root = build(
        {
            "app/api/exports/route.ts": "export function GET() {}\n",
            "app/ui/Table.tsx": "export const T = () => <div/>\n",
        }
    )
    decision = run(root, "app/api/exports/route.ts", "app/ui/Table.tsx")
    assert sorted(decision["methods"]) == ["curl", "handoff"], decision["methods"]


for name, fn in [
    ("a REST route change routes to curl", case_rest_change_routes_to_curl),
    ("a React component change hands off to /qa", case_browser_change_routes_to_qa),
    ("a library change routes to a coverage review", case_library_change_routes_to_coverage),
    ("a docs-only change routes to none", case_docs_only_change_routes_to_none),
    ("a change touching two surfaces reports both", case_two_surfaces_both_reported),
]:
    check(name, fn)


print("\n  [evidence and noise are not surfaces]")


def case_test_files_are_evidence() -> None:
    root = build({"tests/test_export.py": "def test_x():\n    pass\n"})
    decision = run(root, "tests/test_export.py")
    assert decision["tests"] == ["tests/test_export.py"], decision
    assert not decision["surfaces"], (
        f"a spec-only diff has no surface to probe: {decision['surfaces']}"
    )


def case_lockfile_is_ignored() -> None:
    root = build({"package-lock.json": "{}\n"})
    decision = run(root, "package-lock.json")
    assert decision["ignored"] == ["package-lock.json"], decision
    assert not decision["surfaces"], decision["surfaces"]


def case_unknown_extension_is_named_not_dropped() -> None:
    root = build({"config/thing.xml": "<a/>\n"})
    decision = run(root, "config/thing.xml")
    assert route_of(decision, "unknown") == "coverage", (
        "a file no rule matched still needs checking, and the report must say so"
    )


for name, fn in [
    ("a test file is evidence, never a surface", case_test_files_are_evidence),
    ("a lockfile is ignored and named", case_lockfile_is_ignored),
    ("an unmatched file becomes `unknown`, not `docs`", case_unknown_extension_is_named_not_dropped),
]:
    check(name, fn)


print("\n  [--base narrows the endpoints to the ones the diff touched]")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True)


def case_base_flags_only_changed_endpoints() -> None:
    root = build({})
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    api = root / "app" / "api.js"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text("app.get('/old', h)\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "first")
    base = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    api.write_text("app.get('/old', h)\napp.post('/new', h)\n", encoding="utf-8")

    decision = run(root, "app/api.js", extra=("--base", base))
    endpoints = {e["path"]: e["changed"] for e in surfaces(decision)["http-api"]["endpoints"]}
    assert endpoints == {"/old": False, "/new": True}, (
        f"only the added line is a changed endpoint: {endpoints}"
    )


def case_no_base_leaves_changed_absent() -> None:
    root = build({"app/api.js": "app.get('/x', h)\n"})
    decision = run(root, "app/api.js")
    endpoint = surfaces(decision)["http-api"]["endpoints"][0]
    assert "changed" not in endpoint, (
        f"without --base, `changed` is unknown and must not be invented: {endpoint}"
    )


def case_bad_base_exits_2() -> None:
    root = build({"app/api.js": "app.get('/x', h)\n"})
    result = subprocess.run(
        [sys.executable, str(ROUTER), "--repo-root", str(root), "--base", "nope", "app/api.js"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (
        f"a base that will not resolve must exit 2, not route with every flag "
        f"silently unset, got {result.returncode}"
    )


def case_base_survives_a_mnemonic_prefix_config() -> None:
    """`diff.mnemonicPrefix` writes `+++ w/path`, not `+++ b/path`.

    Found by a fresh-eyes pass. With that key set and only `core.quotePath` pinned,
    every path key came out as `w/app/api.js`, so every endpoint reported
    `changed: false`, the probe spec came out empty, and the gate checked nothing.
    """
    root = build({})
    git(root, "init", "-q")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    git(root, "config", "diff.mnemonicPrefix", "true")
    api = root / "app" / "api.js"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text("app.get('/old', h)\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "first")
    base = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    api.write_text("app.get('/old', h)\napp.post('/new', h)\n", encoding="utf-8")

    decision = run(root, "app/api.js", extra=("--base", base))
    endpoints = {e["path"]: e["changed"] for e in surfaces(decision)["http-api"]["endpoints"]}
    assert endpoints == {"/old": False, "/new": True}, (
        f"the diff prefix must be pinned, not trusted: {endpoints}"
    )


def case_rails_resources_is_unresolved_not_guessed() -> None:
    root = build({"config/routes.rb": "Rails.application.routes.draw do\n  resources :exports\nend\n"})
    decision = run(root, "config/routes.rb")
    entry = surfaces(decision)["http-api"]
    assert not entry["endpoints"], f"the seven routes are not guessed: {entry['endpoints']}"
    assert len(entry["unresolved"]) == 1 and "rails routes" in entry["unresolved"][0], entry


for name, fn in [
    ("--base marks only the endpoints the diff added", case_base_flags_only_changed_endpoints),
    ("with no --base, `changed` is absent rather than guessed", case_no_base_leaves_changed_absent),
    ("a base that will not resolve exits 2", case_bad_base_exits_2),
    ("diff.mnemonicPrefix does not blank every flag", case_base_survives_a_mnemonic_prefix_config),
    ("`resources :x` is reported unresolved, not expanded", case_rails_resources_is_unresolved_not_guessed),
]:
    check(name, fn)


print("\n  [operator errors and input plumbing]")


def case_paths_from_a_file() -> None:
    """The form a caller uses when it already has the changed set on disk."""
    root = build({"src/a.py": "x = 1\n", "config/routes.rb": "get '/x', to: 'x#y'\n"})
    listing = root / "changed.txt"
    listing.write_text("src/a.py\nconfig/routes.rb\n", encoding="utf-8")
    decision = run(root, extra=("--paths-from", str(listing)))
    assert sorted(decision["methods"]) == ["coverage", "curl"], decision["methods"]
    assert surfaces(decision)["library"]["paths"] == ["src/a.py"], decision["surfaces"]


def case_unreadable_content_routes_by_path_and_warns() -> None:
    """A file routed on its path alone is named, never silently path-routed.

    Two classes reach this branch, and both are here: content git cannot decode,
    and content too large to be worth reading. Either way no content rule and no
    extractor saw the file, and the reader has to know that before trusting a
    surface that came from the extension alone.
    """
    root = build({})
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "blob.py").write_bytes(b"x = 1\n\x00\x01\x02binary payload\n")
    (root / "src" / "huge.py").write_text("# pad\n" * 100_000, encoding="utf-8")

    result = run_full(root, "src/blob.py", "src/huge.py")
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)
    assert decision["unread"] == ["src/blob.py", "src/huge.py"], (
        f"both an undecodable and an oversized file are unread: {decision['unread']}"
    )
    assert result.stderr.count("content unread") == 2, (
        f"each one must be named on stderr: {result.stderr}"
    )
    assert surfaces(decision)["library"]["paths"] == ["src/blob.py", "src/huge.py"], (
        "and each still routes by its path"
    )


def case_prose_is_unread_without_a_warning() -> None:
    """The control: prose is unread BY DESIGN, so it is not a warning."""
    result = run_full(build({"docs/guide.md": "# Guide\n"}), "docs/guide.md")
    decision = json.loads(result.stdout)
    assert decision["unread"] == [], f"prose is not a surprise: {decision['unread']}"
    assert "content unread" not in result.stderr, result.stderr


def case_paths_from_stdin() -> None:
    root = build({"src/a.py": "x = 1\n"})
    result = subprocess.run(
        [sys.executable, str(ROUTER), "--repo-root", str(root), "--paths-from", "-"],
        input="src/a.py\n\n",
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    decision = json.loads(result.stdout)
    assert surfaces(decision)["library"]["paths"] == ["src/a.py"], decision


def case_empty_changed_set_is_not_an_error() -> None:
    root = build({})
    decision = run(root)
    assert decision["surfaces"] == [] and decision["methods"] == [], decision


def case_bad_root_exits_2() -> None:
    result = subprocess.run(
        [sys.executable, str(ROUTER), "--repo-root", "/no/such/dir"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, f"a bad root must exit 2, got {result.returncode}"


def case_deleted_path_routes_by_path() -> None:
    """The changed set carries deletions, and a deleted route file still matters."""
    root = build({})
    decision = run(root, "config/routes.rb")
    assert route_of(decision, "http-api") == "curl"
    assert not decision["unread"], f"an absent file is not an unread file: {decision['unread']}"


for name, fn in [
    ("--paths-from - reads the changed set from stdin", case_paths_from_stdin),
    ("--paths-from FILE reads the changed set from a file", case_paths_from_a_file),
    ("an undecodable or oversized file is named unread", case_unreadable_content_routes_by_path_and_warns),
    ("prose is unread by design, with no warning", case_prose_is_unread_without_a_warning),
    ("an empty changed set routes to nothing, exit 0", case_empty_changed_set_is_not_an_error),
    ("a repo root that does not exist exits 2", case_bad_root_exits_2),
    ("a deleted file routes by its path", case_deleted_path_routes_by_path),
]:
    check(name, fn)


print(f"\nAll {passed} checks passed." if not failed else f"\n{failed} FAILED, {passed} passed.")
sys.exit(1 if failed else 0)
