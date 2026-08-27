#!/usr/bin/env python3
"""Decide which QA method each changed file demands, and name the endpoints.

This is Step 3 of the quality-gates skill. The skill routes a change to one of
three methods, and this script is what makes that choice from the diff instead of
from a guess:

    curl      a live HTTP probe through the real server (Gate 7)
    handoff   a tool this skill cannot be: /qa for browser UI, /ios-qa for mobile
    coverage  a test-coverage review and nothing live (Gate 2 alone)

It exists as a script for the reason Gate 5's checker does. Told in prose to
"detect the shape of what changed", a model reads six file extensions, decides
the change is browser UI because a stylesheet moved, and hands a REST-only diff
to a browser tool. The routing then reads as a considered judgment, because the
report says HANDOFF either way. The stakeholder is whoever trusts that line.

THE FALSE-POSITIVE TRAP, which is the whole reason for the specificity model
below. Every surface has a cheap path signal and an expensive content signal.
`app/views/exports/index.json.jbuilder` sits under a template directory, so a
path-only rule calls it browser UI and hands a JSON API view to /qa. A Next.js
`app/api/exports/route.ts` ends in `.ts`, so an extension-only rule calls it a
library and probes nothing. Content beats path, and the specific path beats the
generic one, so the strongest evidence about a file decides its surface.

A CONTENT RULE STAYS INSIDE ITS OWN LANGUAGE, which is the same trap one level
down. This router held every pattern it searches for, so it classified ITSELF as
a REST API (a comment quoted `app.get('/x')`) and as a SwiftUI screen (a rule
quoted `import SwiftUI`). Both matches were text. Every content rule and every
endpoint extractor now names the suffixes that could mean it, so a Swift import
inside a Python file is what it actually is: a string.

AMBIGUITY IS REPORTED, NEVER RESOLVED BY COIN FLIP. When two surfaces tie at the
same specificity, the file lands in both and the tie is named. A Rails controller
that renders HTML and JSON really is two surfaces, and the skill grades each and
takes the worst. Inventing a single answer here would drop half a real change.

NO SURFACE MEANS `unknown`, WHICH ROUTES TO coverage AND SAYS SO. A file no rule
matched is not a file with nothing to check. Reporting it as `docs` to keep the
output tidy is how a whole shape leaves the gate in silence.

`--base` NARROWS THE ENDPOINTS, AND IS WORTH PASSING. Without it, a one-line
change to a controller lists every route that controller defines, and the probe
spec balloons to a dozen endpoints the diff never touched. With it, each endpoint
carries `changed: true` when its defining line is in the diff. The endpoints are
candidates either way: a framework's own route lister (`rails routes`,
`manage.py show_urls`) is authoritative, and this is the starting point.

STDOUT IS JSON AND NOTHING ELSE, so the caller can parse it. The counts, the
skipped files, and every warning go to stderr, following changed_set.py.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_OPERATOR_ERROR = 2

# A file bigger than this is a bundle, a fixture, or a vendored blob. Reading it
# costs more than the signal it carries, and its content is named on stderr as
# unread rather than dropped in silence.
MAX_CONTENT_BYTES = 512 * 1024

# Prose routes by PATH ONLY: no content rule and no endpoint extractor reads it.
# Documentation quotes code, and this repository's own files quote `app.get('/x')`
# and `from 'express'` in worked examples. Reading content here would classify
# every document that explains a REST route AS a REST route and send a probe after
# it. Gate 5's checker learned the same lesson the expensive way: it reported 194
# missing paths, every one of them a sample inside a fenced block.
PROSE_SUFFIXES = (".md", ".markdown", ".rst", ".txt", ".adoc")
PROSE_NAMES = ("LICENSE", "CHANGELOG", "NOTICE")

# What each surface demands, and who owns it when this skill cannot.
# The three methods are the skill's three QA routes; `none` means the change
# alters no behavior, which is Gate 2's SKIP.
SURFACE_ROUTES: dict[str, tuple[str, str | None]] = {
    "http-api": ("curl", None),
    "browser-ui": ("handoff", "/qa"),
    "mobile-ui": ("handoff", "/ios-qa"),
    "cli": ("coverage", None),
    "library": ("coverage", None),
    "prompt-assets": ("coverage", None),
    "infra": ("coverage", None),
    "docs": ("none", None),
    "unknown": ("coverage", None),
}

# Surfaces in the order a report should read them: the live methods first,
# because they are the rows a reader acts on.
SURFACE_ORDER = list(SURFACE_ROUTES)


@dataclass(frozen=True)
class Rule:
    """One piece of evidence that a file belongs to a surface.

    `specificity` is the whole design. 3 is a content signal, which is a
    statement about what the file does. 2 is a path that means one thing in its
    ecosystem (`config/routes.rb`, `**/*.vue`). 1 is a path or extension that
    only narrows the field (`**/*.py`, `**/*_controller.rb`). The highest
    specificity a file matches decides its surface, so a generic extension never
    outvotes what the file actually contains.

    `langs` is what keeps a content rule inside its own language, and it is not
    optional decoration. `import SwiftUI` inside a Python file is a string, not a
    Swift import. This router misclassified ITSELF as both a REST API and a
    SwiftUI screen before this field existed, because it holds every pattern it
    searches for. A rule with no `langs` applies to any suffix.
    """

    surface: str
    specificity: int
    pattern: str
    kind: str = "path"  # "path" or "content"
    langs: tuple[str, ...] = ()


# Path rules. Written against the repository-relative path with forward slashes.
# `**/` matches any run of leading directories including none, and `*` never
# crosses a slash, so `**/*.tsx` matches `Button.tsx` and `src/ui/Button.tsx`.
PATH_RULES: tuple[Rule, ...] = (
    # HTTP API. Every entry here names a file whose job is to define or render an
    # HTTP endpoint in its framework.
    Rule("http-api", 2, "config/routes.rb"),
    Rule("http-api", 2, "**/urls.py"),
    Rule("http-api", 2, "**/routers/**"),
    Rule("http-api", 2, "**/handlers/**"),
    Rule("http-api", 2, "app/controllers/api/**"),
    Rule("http-api", 2, "**/api/**/route.ts"),
    Rule("http-api", 2, "**/api/**/route.js"),
    Rule("http-api", 2, "pages/api/**"),
    Rule("http-api", 2, "src/pages/api/**"),
    Rule("http-api", 2, "**/openapi.yaml"),
    Rule("http-api", 2, "**/openapi.yml"),
    Rule("http-api", 2, "**/openapi.json"),
    Rule("http-api", 2, "**/swagger.yaml"),
    Rule("http-api", 2, "**/swagger.json"),
    # A jbuilder view renders JSON and lives under the same `app/views/` tree as
    # every HTML template, so it needs to outrank the browser-ui path rules. This
    # is the specific file the docstring's trap describes.
    Rule("http-api", 3, "**/*.jbuilder"),
    Rule("http-api", 1, "**/*_controller.rb"),
    Rule("http-api", 1, "**/views.py"),
    # Browser UI.
    Rule("browser-ui", 2, "**/*.tsx"),
    Rule("browser-ui", 2, "**/*.jsx"),
    Rule("browser-ui", 2, "**/*.vue"),
    Rule("browser-ui", 2, "**/*.svelte"),
    Rule("browser-ui", 2, "**/*.erb"),
    Rule("browser-ui", 2, "**/*.haml"),
    Rule("browser-ui", 2, "**/*.slim"),
    Rule("browser-ui", 2, "**/*.hbs"),
    Rule("browser-ui", 2, "**/*.html"),
    Rule("browser-ui", 2, "**/*.css"),
    Rule("browser-ui", 2, "**/*.scss"),
    Rule("browser-ui", 2, "**/*.sass"),
    Rule("browser-ui", 2, "**/*.less"),
    Rule("browser-ui", 2, "app/views/**"),
    Rule("browser-ui", 2, "**/templates/**"),
    Rule("browser-ui", 2, "**/components/**"),
    Rule("browser-ui", 2, "app/assets/**"),
    Rule("browser-ui", 2, "public/**"),
    # Mobile UI. A bare `.swift` or `.kt` file is a library until its content
    # says otherwise, which is what the content rules below decide.
    Rule("mobile-ui", 2, "**/*.storyboard"),
    Rule("mobile-ui", 2, "**/*.xib"),
    Rule("mobile-ui", 2, "**/*.xcassets/**"),
    Rule("mobile-ui", 2, "**/Assets.xcassets/**"),
    # CLI.
    Rule("cli", 2, "bin/**"),
    Rule("cli", 2, "cmd/**"),
    Rule("cli", 2, "**/cli.py"),
    Rule("cli", 2, "**/__main__.py"),
    Rule("cli", 2, "**/main.go"),
    Rule("cli", 2, "exe/**"),
    # Prompt assets: instructions an LLM reads at runtime. Specificity 2 so they
    # outrank the `**/*.md` docs rule below, which would otherwise call every
    # skill a document and route it to `none`.
    Rule("prompt-assets", 2, "skills/**/SKILL.md"),
    Rule("prompt-assets", 2, "agents/*.md"),
    Rule("prompt-assets", 2, "commands/*.md"),
    Rule("prompt-assets", 2, ".claude/**"),
    Rule("prompt-assets", 2, "**/prompts/**"),
    Rule("prompt-assets", 2, "hooks/**"),
    # Infrastructure. Its live check is the tool's own plan or validate step,
    # which Step 1 of the skill discovers; there is nothing to curl.
    Rule("infra", 2, "**/*.tf"),
    Rule("infra", 2, "**/*.tfvars"),
    Rule("infra", 2, "**/Dockerfile"),
    Rule("infra", 2, "**/docker-compose.yml"),
    Rule("infra", 2, "**/docker-compose.yaml"),
    Rule("infra", 2, ".github/workflows/**"),
    Rule("infra", 2, "**/*.k8s.yaml"),
    # Documentation. Specificity 1, so any rule above wins.
    Rule("docs", 1, "**/*.md"),
    Rule("docs", 1, "**/*.rst"),
    Rule("docs", 1, "**/*.txt"),
    Rule("docs", 1, "docs/**"),
    Rule("docs", 1, "LICENSE"),
    Rule("docs", 1, "CHANGELOG"),
    # Library: an importable source file with no entry point of its own. The
    # floor, at specificity 1.
    Rule("library", 1, "**/*.py"),
    Rule("library", 1, "**/*.rb"),
    Rule("library", 1, "**/*.ts"),
    Rule("library", 1, "**/*.js"),
    Rule("library", 1, "**/*.mjs"),
    Rule("library", 1, "**/*.go"),
    Rule("library", 1, "**/*.swift"),
    Rule("library", 1, "**/*.kt"),
    Rule("library", 1, "**/*.java"),
    Rule("library", 1, "**/*.rs"),
    Rule("library", 1, "**/*.ex"),
    Rule("library", 1, "**/*.exs"),
    Rule("library", 1, "**/*.php"),
    Rule("library", 1, "**/*.c"),
    Rule("library", 1, "**/*.cc"),
    Rule("library", 1, "**/*.h"),
)

# The suffixes each language owns, so a content rule stays inside it.
PY = (".py",)
RB = (".rb", ".rake", ".jbuilder")
JS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
GO = (".go",)
SWIFT = (".swift",)
JVM = (".java", ".kt", ".kts")
MARKUP = (".vue", ".svelte", ".html", ".erb", ".haml", ".slim", ".hbs")

# Content rules, all at specificity 3. Each says what the file does, which beats
# every guess its path supports, and each is confined to the language that could
# mean it. See Rule.langs.
CONTENT_RULES: tuple[Rule, ...] = (
    Rule("http-api", 3, r"ActionController::API", kind="content", langs=RB),
    Rule("http-api", 3, r"\brender\s+json:", kind="content", langs=RB),
    Rule("http-api", 3, r"\bjsonify\(", kind="content", langs=PY),
    Rule("http-api", 3, r"from\s+fastapi\b", kind="content", langs=PY),
    Rule("http-api", 3, r"@RestController\b", kind="content", langs=JVM),
    Rule("http-api", 3, r"require\(['\"]express['\"]\)", kind="content", langs=JS),
    Rule("http-api", 3, r"from\s+['\"]express['\"]", kind="content", langs=JS),
    Rule("browser-ui", 3, r"\bfrom\s+['\"]react['\"]", kind="content", langs=JS),
    Rule("browser-ui", 3, r"<template[\s>]", kind="content", langs=MARKUP),
    Rule("mobile-ui", 3, r"^\s*import\s+SwiftUI\b", kind="content", langs=SWIFT),
    Rule("mobile-ui", 3, r"^\s*import\s+UIKit\b", kind="content", langs=SWIFT),
    Rule("mobile-ui", 3, r"@Composable\b", kind="content", langs=JVM),
    Rule("mobile-ui", 3, r":\s*AppCompatActivity\b", kind="content", langs=JVM),
    Rule("cli", 3, r"\bimport\s+argparse\b", kind="content", langs=PY),
    Rule("cli", 3, r"\bimport\s+click\b", kind="content", langs=PY),
    Rule("cli", 3, r"\bimport\s+typer\b", kind="content", langs=PY),
    Rule("cli", 3, r"\bOptionParser\.new\b", kind="content", langs=RB),
    Rule("cli", 3, r"<\s*Thor\b", kind="content", langs=RB),
    Rule("cli", 3, r"cobra\.Command\b", kind="content", langs=GO),
    Rule("cli", 3, r"\bflag\.Parse\(\)", kind="content", langs=GO),
    Rule("cli", 3, r"require\(['\"]commander['\"]\)", kind="content", langs=JS),
)

# A test file is evidence, never a surface. Routing a diff that only touched
# specs to a live probe asks the probe to check the checker.
TEST_PATTERNS: tuple[str, ...] = (
    "**/test_*.py",
    "**/*_test.py",
    "**/*_test.go",
    "**/*_test.rb",
    "**/*_spec.rb",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/*.test.js",
    "**/*.spec.ts",
    "**/*.spec.tsx",
    "**/*.spec.js",
    "**/*Tests.swift",
    "**/*Test.java",
    "**/*Test.kt",
    "tests/**",
    "test/**",
    "spec/**",
    "**/__tests__/**",
)

# Neither a surface nor evidence: a lockfile or a manifest whose change is real
# but whose QA method is the project's own build. Named in the output so a reader
# can see they were considered.
IGNORED_PATTERNS: tuple[str, ...] = (
    "**/package-lock.json",
    "**/yarn.lock",
    "**/pnpm-lock.yaml",
    "**/Gemfile.lock",
    "**/poetry.lock",
    "**/uv.lock",
    "**/go.sum",
    "**/Cargo.lock",
    "**/*.snap",
    "**/*.svg",
    "**/*.png",
    "**/*.jpg",
    "**/*.gif",
    "**/*.ico",
    "**/*.woff",
    "**/*.woff2",
)

# `@@ -old,count +new,count @@`. Group 1 is the first line number in the new
# file, which is what an endpoint's `changed` flag is measured against. Same
# shape check_hygiene.py reads, kept local rather than imported: two scripts
# sharing 20 lines is cheaper than a helper module neither owns.
HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

DIFF_ARGS = ("diff", "--unified=0", "--no-color", "--no-ext-diff", "--no-textconv")

# All four prefix keys are pinned, not just quotePath. A caller with
# `diff.mnemonicPrefix` set writes `+++ w/app/api.js`, which does not start with
# `b/`, so every path key came out as `w/app/api.js` and every endpoint reported
# `changed: false`. The skill then builds a probe spec from the changed endpoints
# and finds none, so the gate checks nothing and says so in a voice that sounds
# fine. check_hygiene.py pins the same four for the same reason.
CONFIG_ARGS = (
    "-c", "core.quotePath=false",
    "-c", "diff.noprefix=false",
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.srcPrefix=a/",
    "-c", "diff.dstPrefix=b/",
)


class GitUnavailable(Exception):
    """git could not produce the diff, so no endpoint can be marked changed."""


@dataclass(frozen=True)
class Endpoint:
    """One candidate HTTP endpoint a changed file defines."""

    method: str | None
    path: str
    source: str
    extractor: str
    changed: bool | None = None

    def as_json(self) -> dict[str, object]:
        record: dict[str, object] = {
            "method": self.method,
            "path": self.path,
            "source": self.source,
            "extractor": self.extractor,
        }
        if self.changed is not None:
            record["changed"] = self.changed
        return record


@dataclass
class SurfaceFinding:
    """One surface the change touches, with the evidence that put it there."""

    surface: str
    paths: list[str] = field(default_factory=list)
    endpoints: list[Endpoint] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def glob_to_re(pattern: str) -> re.Pattern[str]:
    """Compile one path pattern, where `**/` spans directories and `*` does not.

    Written out rather than handed to `fnmatch`, which flattens `**` into `*` and
    would let `**/*.tsx` match a file whose name merely contains a slash-free
    lookalike. `Path.match` is no better: it cannot anchor a pattern like
    `app/controllers/api/**` to the repository root.
    """
    out = ["^"]
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:[^/]+/)*")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    out.append("$")
    return re.compile("".join(out))


PATH_MATCHERS = [(rule, glob_to_re(rule.pattern)) for rule in PATH_RULES]
CONTENT_MATCHERS = [
    (rule, re.compile(rule.pattern, re.MULTILINE)) for rule in CONTENT_RULES
]
TEST_MATCHERS = [glob_to_re(pattern) for pattern in TEST_PATTERNS]
IGNORED_MATCHERS = [glob_to_re(pattern) for pattern in IGNORED_PATTERNS]


def matches_any(path: str, matchers: list[re.Pattern[str]]) -> bool:
    return any(matcher.match(path) for matcher in matchers)


def is_prose(path: str) -> bool:
    """Whether this file's content must be ignored. See PROSE_SUFFIXES."""
    name = path.rsplit("/", 1)[-1]
    return path.endswith(PROSE_SUFFIXES) or name in PROSE_NAMES


def read_content(root: Path, path: str) -> str | None:
    """The file's text, or None when it cannot or should not be read.

    A deleted path returns None, which is correct and common: the changed set
    carries deletions, and a file that left the tree still routes by its path.
    """
    if is_prose(path):
        return None
    target = root / path
    try:
        if not target.is_file():
            return None
        if target.stat().st_size > MAX_CONTENT_BYTES:
            return None
        raw = target.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:8192]:  # binary, so no content rule can apply
        return None
    return raw.decode("utf-8", errors="replace")


# --- endpoint extraction ----------------------------------------------------
#
# Each extractor is conservative on purpose. It fires on an explicit method and
# an explicit literal path, and anything it cannot resolve goes to `unresolved`
# for a human or a route lister to settle. A guessed endpoint costs a probe
# against a URL that does not exist, which reads as a failing API.

# `api` is deliberately NOT a receiver here, and JSX files are excluded from this
# extractor entirely. `api.get('/api/v1/exports')` is the most common way an axios
# or fetch wrapper is called from a component, and reading it as a route
# definition scored the component http-api at specificity 3. That outranked its
# own `.tsx` rule, so a React-only change routed to curl and its `/qa` handoff
# disappeared: the exact misroute this router exists to prevent, pointing the
# other way.
EXPRESS_RE = re.compile(
    r"\b(?:app|router|server)\.(get|post|put|patch|delete|head|options)\("
    r"\s*['\"`](/[^'\"`]*)['\"`]"
)

# Server routes are not defined in JSX. A call that looks like one there is a
# client calling somebody else's endpoint.
JSX_SUFFIXES = (".jsx", ".tsx")
DECORATOR_RE = re.compile(
    r"@\w+\.(get|post|put|patch|delete|head|options)\(\s*['\"](/[^'\"]*)['\"]"
)
FLASK_RE = re.compile(r"@\w+\.route\(\s*['\"](/[^'\"]*)['\"]([^)]*)\)")
FLASK_METHODS_RE = re.compile(r"methods\s*=\s*[\[(]([^\])]*)[\])]")
RAILS_ROUTE_RE = re.compile(
    r"^\s*(get|post|put|patch|delete)\s+['\"]([^'\"]+)['\"]", re.MULTILINE
)
RAILS_RESOURCE_RE = re.compile(r"^\s*(resources?)\s+:(\w+)", re.MULTILINE)
DJANGO_PATH_RE = re.compile(r"\b(?:re_)?path\(\s*[r]?['\"]([^'\"]*)['\"]")
DJANGO_INCLUDE_RE = re.compile(r"\binclude\(\s*['\"]([^'\"]+)['\"]")
GO_CHI_RE = re.compile(
    r"\.(Get|Post|Put|Patch|Delete|Head|Options)\(\s*\"(/[^\"]*)\""
)
GO_HANDLEFUNC_RE = re.compile(r"HandleFunc\(\s*\"(/[^\"]*)\"")
SPRING_RE = re.compile(
    r"@(Get|Post|Put|Patch|Delete)Mapping\(\s*(?:value\s*=\s*)?\"([^\"]*)\""
)
NEXT_HANDLER_RE = re.compile(
    r"^\s*export\s+(?:async\s+)?(?:function|const)\s+"
    r"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    re.MULTILINE,
)


def line_of(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def next_route_path(path: str) -> str | None:
    """The URL a Next.js route handler file serves, derived from its own path.

    `app/api/exports/route.ts` serves `/api/exports`, and the file names no path
    of its own, so the path is the only place the URL exists.
    """
    parts = path.split("/")
    if parts and parts[0] == "src":
        parts = parts[1:]
    if len(parts) < 2 or not parts[-1].startswith("route."):
        return None
    if parts[0] == "app":
        parts = parts[1:]
    segments = [p for p in parts[:-1] if not (p.startswith("(") and p.endswith(")"))]
    return "/" + "/".join(segments) if segments else "/"


def extract_endpoints(path: str, content: str) -> tuple[list[Endpoint], list[str]]:
    """Every endpoint this file's text states outright, plus what it could not.

    Each extractor is confined to the language whose framework it reads, for the
    reason Rule.langs states: a comment in a Python file that quotes
    `app.get('/x')` describes an endpoint, and is not one.
    """
    found: list[Endpoint] = []
    unresolved: list[str] = []

    def add(method: str | None, url: str, offset: int, extractor: str) -> None:
        found.append(
            Endpoint(
                method=method.upper() if method else None,
                path=url,
                source=f"{path}:{line_of(content, offset)}",
                extractor=extractor,
            )
        )

    if path.endswith(JS) and not path.endswith(JSX_SUFFIXES):
        for match in EXPRESS_RE.finditer(content):
            add(match.group(1), match.group(2), match.start(), "express")
    if path.endswith(PY):
        for match in DECORATOR_RE.finditer(content):
            add(match.group(1), match.group(2), match.start(), "decorator")
        for match in FLASK_RE.finditer(content):
            methods = FLASK_METHODS_RE.search(match.group(2))
            names = (
                [m.strip().strip("'\"").upper() for m in methods.group(1).split(",")]
                if methods
                else ["GET"]
            )
            for name in [n for n in names if n]:
                add(name, match.group(1), match.start(), "flask")
    if path.endswith(JVM):
        for match in SPRING_RE.finditer(content):
            add(match.group(1), match.group(2) or "/", match.start(), "spring")
    if path.endswith(GO):
        for match in GO_CHI_RE.finditer(content):
            add(match.group(1), match.group(2), match.start(), "go-router")
        for match in GO_HANDLEFUNC_RE.finditer(content):
            add(None, match.group(1), match.start(), "go-handlefunc")

    if path.endswith("routes.rb"):
        for match in RAILS_ROUTE_RE.finditer(content):
            url = match.group(2).split("=>")[0].strip()
            add(match.group(1), url if url.startswith("/") else f"/{url}", match.start(), "rails")
        for match in RAILS_RESOURCE_RE.finditer(content):
            unresolved.append(
                f"{path}:{line_of(content, match.start())}: "
                f"`{match.group(1)} :{match.group(2)}` expands to several routes; "
                f"run `rails routes -g {match.group(2)}` to list them"
            )

    if path.endswith("urls.py"):
        for match in DJANGO_PATH_RE.finditer(content):
            url = match.group(1)
            add(None, url if url.startswith("/") else f"/{url}", match.start(), "django")
        for match in DJANGO_INCLUDE_RE.finditer(content):
            unresolved.append(
                f"{path}:{line_of(content, match.start())}: "
                f"`include('{match.group(1)}')` mounts another URL module; "
                f"run `manage.py show_urls` to resolve the full paths"
            )

    if re.search(r"/route\.[tj]sx?$", path):
        url = next_route_path(path)
        if url:
            for match in NEXT_HANDLER_RE.finditer(content):
                add(match.group(1), url, match.start(), "next-route-handler")

    return found, unresolved


# --- classification ---------------------------------------------------------


def surfaces_for(
    path: str, content: str | None, defines_endpoint: bool = False
) -> tuple[list[str], int]:
    """The surfaces this file belongs to, and the specificity that decided them.

    Ties are kept. A file whose strongest evidence points two ways points two
    ways, and the caller grades both.

    `defines_endpoint` scores at 3 alongside the content rules, rather than being
    added to the http-api surface afterward. A file that states a route IS an
    HTTP surface, so it must outrank its own `**/*.py` fallback; bolting it on
    later listed one Flask module as both an API and a library.
    """
    scored: list[tuple[int, str]] = []
    for rule, matcher in PATH_MATCHERS:
        if matcher.match(path):
            scored.append((rule.specificity, rule.surface))
    if content is not None:
        for rule, matcher in CONTENT_MATCHERS:
            if rule.langs and not path.endswith(rule.langs):
                continue  # a Swift import inside a Python file is a string
            if matcher.search(content):
                scored.append((rule.specificity, rule.surface))
    if defines_endpoint:
        scored.append((3, "http-api"))
    if not scored:
        return ["unknown"], 0
    best = max(score for score, _ in scored)
    winners = {surface for score, surface in scored if score == best}
    return sorted(winners), best


def route(
    root: Path, paths: list[str], added_lines: dict[str, set[int]] | None
) -> dict[str, object]:
    """Classify every changed path and build the routing decision."""
    findings: dict[str, SurfaceFinding] = {}
    tests: list[str] = []
    ignored: list[str] = []
    ambiguous: list[str] = []
    unread: list[str] = []

    def finding(surface: str) -> SurfaceFinding:
        return findings.setdefault(surface, SurfaceFinding(surface=surface))

    for path in paths:
        if matches_any(path, IGNORED_MATCHERS):
            ignored.append(path)
            continue
        if matches_any(path, TEST_MATCHERS):
            tests.append(path)
            continue

        content = read_content(root, path)
        # Prose is unread by design, so it is not a warning. A file that exists,
        # is not prose, and still yielded no text is binary or oversized, and the
        # reader needs to know it routed on its path alone.
        if content is None and not is_prose(path) and (root / path).is_file():
            unread.append(path)

        endpoints: list[Endpoint] = []
        unresolved: list[str] = []
        if content is not None:
            endpoints, unresolved = extract_endpoints(path, content)

        surfaces, _ = surfaces_for(path, content, defines_endpoint=bool(endpoints))
        if len(surfaces) > 1:
            ambiguous.append(f"{path}: {', '.join(surfaces)}")
        for surface in surfaces:
            finding(surface).paths.append(path)

        if not (endpoints or unresolved):
            continue
        api = finding("http-api")
        if path not in api.paths:
            # Reached when a file resolved something unresolvable and no endpoint:
            # `resources :exports` alone, in a file whose path said otherwise.
            api.paths.append(path)
        for endpoint in endpoints:
            changed = None
            if added_lines is not None:
                line = int(endpoint.source.rsplit(":", 1)[1])
                changed = line in added_lines.get(path, set())
            api.endpoints.append(
                Endpoint(
                    method=endpoint.method,
                    path=endpoint.path,
                    source=endpoint.source,
                    extractor=endpoint.extractor,
                    changed=changed,
                )
            )
        api.unresolved.extend(unresolved)

    ordered = [findings[s] for s in SURFACE_ORDER if s in findings]
    return {
        "version": 1,
        "surfaces": [
            {
                "surface": f.surface,
                "method": SURFACE_ROUTES[f.surface][0],
                "owner": SURFACE_ROUTES[f.surface][1],
                "paths": sorted(set(f.paths)),
                "endpoints": [e.as_json() for e in f.endpoints],
                "unresolved": f.unresolved,
            }
            for f in ordered
        ],
        "methods": sorted({SURFACE_ROUTES[f.surface][0] for f in ordered}),
        "tests": sorted(tests),
        "ignored": sorted(ignored),
        "ambiguous": sorted(ambiguous),
        "unread": sorted(unread),
    }


def added_lines_by_path(root: Path, base: str) -> dict[str, set[int]]:
    """The line numbers `base..working tree` adds, per file.

    `git diff <base>` with no `...HEAD`, matching changed_set.py: this skill runs
    before a commit more often than after one.
    """
    try:
        result = subprocess.run(
            ["git", *CONFIG_ARGS, "-C", str(root), *DIFF_ARGS, base, "--"],
            capture_output=True,
        )
    except OSError as exc:
        raise GitUnavailable(f"could not run git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitUnavailable(f"git diff against {base!r} failed: {detail}")

    added: dict[str, set[int]] = {}
    path = None
    line = 0
    in_hunk = False
    for raw in result.stdout.decode("utf-8", errors="replace").splitlines():
        hunk = HUNK_RE.match(raw)
        if hunk:
            line = int(hunk.group(1))
            in_hunk = True
        elif not in_hunk:
            if raw.startswith("+++ "):
                value = raw[4:]
                path = value[2:] if value.startswith("b/") else value
        elif raw.startswith("+"):
            if path:
                added.setdefault(path, set()).add(line)
            line += 1
        elif raw.startswith(" "):
            line += 1
        elif raw.startswith(("-", "\\")):
            pass
        else:
            in_hunk = False
    return added


def read_paths(args: argparse.Namespace) -> list[str]:
    """The changed set, from arguments or from a file, `-` meaning stdin."""
    if args.paths:
        raw = args.paths
    elif args.paths_from == "-":
        raw = sys.stdin.read().splitlines()
    elif args.paths_from:
        raw = Path(args.paths_from).read_text(encoding="utf-8").splitlines()
    else:
        raw = []
    return [p.strip() for p in raw if p.strip()]


def summarize(decision: dict[str, object]) -> str:
    surfaces = decision["surfaces"]
    assert isinstance(surfaces, list)
    if not surfaces:
        return "no surface: the changed set is empty or held only tests and lockfiles"
    parts = []
    for entry in surfaces:
        owner = f" -> {entry['owner']}" if entry["owner"] else ""
        parts.append(f"{entry['surface']}={entry['method']}{owner} ({len(entry['paths'])})")
    return "; ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--paths-from",
        metavar="FILE",
        help="Read the changed paths from FILE, or from stdin when FILE is -",
    )
    parser.add_argument(
        "--base",
        metavar="REV",
        help="Mark each endpoint changed or not by diffing the tree against REV",
    )
    parser.add_argument("paths", nargs="*", help="Changed paths, one per argument")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    if not root.is_dir():
        print(f"ERROR: --repo-root {root} is not a directory", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    try:
        paths = read_paths(args)
    except OSError as exc:
        print(f"ERROR: could not read the path list: {exc}", file=sys.stderr)
        return EXIT_OPERATOR_ERROR

    added_lines = None
    if args.base:
        if not args.base.strip():
            print("ERROR: --base must name a revision", file=sys.stderr)
            return EXIT_OPERATOR_ERROR
        try:
            added_lines = added_lines_by_path(root, args.base)
        except GitUnavailable as exc:
            # Exit 2, never a routing decision with every endpoint silently
            # unflagged: the caller asked for the narrowing and did not get it.
            print(f"ERROR: {exc}", file=sys.stderr)
            return EXIT_OPERATOR_ERROR

    decision = route(root, paths, added_lines)
    json.dump(decision, sys.stdout, indent=2)
    print()

    print(f"routed {len(paths)} paths: {summarize(decision)}", file=sys.stderr)
    if not args.base:
        print(
            "NOTE: no --base, so every endpoint is a candidate rather than a "
            "changed one; pass the base changed_set.py printed",
            file=sys.stderr,
        )
    for entry in decision["ambiguous"]:  # type: ignore[union-attr]
        print(f"AMBIGUOUS: {entry}", file=sys.stderr)
    for entry in decision["unread"]:  # type: ignore[union-attr]
        print(f"WARNING: routed by path only, content unread: {entry}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
