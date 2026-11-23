"""Inspect a bounded set of public repository files."""
from __future__ import annotations

import ast
import json
import re
import time
import tomllib
from pathlib import PurePosixPath

from shared.github_client import get_file_content, get_repo_tree
from shared.progress import record_lane
from shared.schemas import UniversalProjectProfile
from shared.telemetry import start_span

MANIFESTS = {"pyproject.toml", "package.json", "pom.xml", "go.mod", "Cargo.toml"}
ENTRY_POINTS = {"main.py", "app.py", "index.ts", "index.js"}
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}


def _priority(path: str) -> tuple[int, int, str]:
    name = PurePosixPath(path).name
    if name in MANIFESTS:
        rank = 0
    elif name in ENTRY_POINTS:
        rank = 1
    elif path.startswith("src/"):
        rank = 2
    else:
        rank = 3
    return rank, path.count("/"), path


def _python_symbols(source: str) -> tuple[set[str], set[str]]:
    imports: set[str] = set()
    symbols: set[str] = set()
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imports, symbols
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.add(node.name)
    return imports, symbols


def _js_symbols(source: str) -> tuple[set[str], set[str]]:
    imports = set(re.findall(r"\bfrom\s*['\"]([^'\"]+)", source))
    symbols = set(re.findall(r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:class|function)\s+(\w+)", source))
    return imports, symbols


def _manifest_dependencies(path: str, content: str) -> set[str]:
    try:
        if path == "package.json":
            data = json.loads(content)
            return set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
        if path == "pyproject.toml":
            data = tomllib.loads(content)
            deps = data.get("project", {}).get("dependencies", [])
            return {re.split(r"[<>=~!;\[]", d, maxsplit=1)[0].strip() for d in deps}
        if path == "Cargo.toml":
            data = tomllib.loads(content)
            return set(data.get("dependencies", {})) | set(data.get("dev-dependencies", {}))
        if path == "go.mod":
            return set(re.findall(r"(?m)^\s*([\w./-]+)\s+v[\w.+-]+", content))
        if path == "pom.xml":
            return set(re.findall(r"<artifactId>([^<]+)</artifactId>", content))
    except (ValueError, KeyError, TypeError):
        return set()
    return set()


def _shallow(profile: UniversalProjectProfile, scan_id: str | None, trace) -> dict:
    record_lane(scan_id, "repo_scan")
    updated = profile.model_copy(update={"input_type": "RFC_TEXT", "code_files_scanned": 0})
    result = {"repo_scan": updated.model_dump(), "repo_scan_status": "UNAVAILABLE"}
    result["pipeline_trace"] = [trace.finish(result)]
    return result


def lambda_handler(event: dict, context) -> dict:
    profile = UniversalProjectProfile.model_validate(event["project_profile"])
    scan_id = profile.scan_id
    trace = start_span("repo_scanner", "none", event)
    repo_url = event.get("repo_url")
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/#?]+)(?:\.git)?/?", repo_url or "", re.I)
    if not match:
        return _shallow(profile, scan_id, trace)
    owner, repo = match.groups()
    started = time.monotonic()
    try:
        tree = get_repo_tree(owner, repo, depth=2).get("tree", [])
    except Exception:
        return _shallow(profile, scan_id, trace)

    paths = [item["path"] for item in tree if item.get("type") == "blob"]
    readme_path = next((p for p in paths if p.lower() == "readme.md"), None)
    readme = get_file_content(owner, repo, readme_path)[:4000] if readme_path else ""
    manifests = sorted((p for p in paths if PurePosixPath(p).name in MANIFESTS), key=_priority)
    code_files = sorted((p for p in paths if PurePosixPath(p).suffix.lower() in CODE_SUFFIXES), key=_priority)
    selected = list(dict.fromkeys(manifests + code_files))[:40]
    dependencies: set[str] = set()
    modules: set[str] = set()
    tech: set[str] = set()
    has_tests = any("/tests/" in f"/{p.lower()}/" or PurePosixPath(p).name.startswith("test_") for p in paths)
    scanned = 0
    for path in selected:
        if time.monotonic() - started > 9:
            break
        content = get_file_content(owner, repo, path)[:4000]
        if PurePosixPath(path).name in MANIFESTS:
            dependencies.update(_manifest_dependencies(PurePosixPath(path).name, content))
            continue
        scanned += 1
        suffix = PurePosixPath(path).suffix.lower()
        tech.add({".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript", ".jsx": "JavaScript"}[suffix])
        imports, symbols = _python_symbols(content) if suffix == ".py" else _js_symbols(content)
        modules.update(imports)
        modules.update(f"{path}:{name}" for name in sorted(symbols))

    claims = [line.strip(" -*#") for line in readme.splitlines() if line.strip() and (line.startswith("#") or line.startswith("- "))][:12]
    enriched = profile.model_copy(update={
        "input_type": profile.input_type if scanned else "RFC_TEXT",
        "tech_stack": sorted(tech),
        "dependencies": sorted(d for d in dependencies if d),
        "core_modules": sorted(modules)[:60],
        "has_tests": has_tests,
        "readme_claims": claims,
        "dependency_count": len(dependencies),
        "code_files_scanned": scanned,
    })
    record_lane(scan_id, "repo_scan")
    result = {"repo_scan": enriched.model_dump(), "repo_scan_status": "OK" if scanned else "RFC_FALLBACK"}
    result["pipeline_trace"] = [trace.finish(result)]
    return result
