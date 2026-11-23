"""Check project names against GitHub, PyPI, and npm."""
from __future__ import annotations

import asyncio
import re
from urllib.parse import quote

import httpx

from shared.github_client import _headers
from shared.progress import record_lane
from shared.schemas import NameCollisionResult
from shared.telemetry import start_span


def _normalize(name: str) -> str:
    value = re.sub(r"[-_ ]+(ai|js|py|labs|hq)$", "", name.lower()).strip("-_ ")
    return re.sub(r"[^a-z0-9]", "", value)


def _jaro_winkler(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    window = max(len(left), len(right)) // 2 - 1
    window = max(0, window)
    left_hits = [False] * len(left)
    right_hits = [False] * len(right)
    matches = 0
    for i, char in enumerate(left):
        for j in range(max(0, i - window), min(i + window + 1, len(right))):
            if not right_hits[j] and char == right[j]:
                left_hits[i] = right_hits[j] = True
                matches += 1
                break
    if not matches:
        return 0.0
    left_order = [left[i] for i, hit in enumerate(left_hits) if hit]
    right_order = [right[i] for i, hit in enumerate(right_hits) if hit]
    transpositions = sum(a != b for a, b in zip(left_order, right_order)) / 2
    jaro = (matches / len(left) + matches / len(right) + (matches - transpositions) / matches) / 3
    prefix = 0
    for a, b in zip(left, right):
        if a != b or prefix == 4:
            break
        prefix += 1
    return jaro + prefix * 0.1 * (1 - jaro)


def _double_metaphone(name: str) -> set[str]:
    from metaphone import doublemetaphone

    return {key for key in doublemetaphone(name) if key}


async def _lookup(name: str) -> tuple[list[dict], bool]:
    normalized = _normalize(name)
    pypi_name = name.replace("_", "-")
    npm_name = quote(name, safe="@/")
    urls = [
        f"https://api.github.com/search/repositories?q={quote(name + ' in:name')}&per_page=10",
        f"https://pypi.org/pypi/{quote(pypi_name, safe='')}/json",
        f"https://registry.npmjs.org/{npm_name}",
    ]
    headers = {**_headers(), "Accept": "application/vnd.github+json"}
    async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
        responses = await asyncio.gather(*(client.get(url, headers=headers) for url in urls), return_exceptions=True)
    rows: list[dict] = []
    partial = False
    for source, response in zip(("github", "pypi", "npm"), responses):
        if isinstance(response, Exception):
            partial = True
            continue
        if response.status_code in (403, 429) or response.status_code >= 500:
            partial = True
        if response.status_code >= 400:
            continue
        try:
            data = response.json()
        except ValueError:
            continue
        if source == "github":
            rows.extend({"name": item.get("name", ""), "url": item.get("html_url", ""), "source": source}
                        for item in data.get("items", []))
        elif source == "pypi":
            info = data.get("info", {})
            rows.append({"name": info.get("name", pypi_name), "url": info.get("project_url", ""), "source": source})
        else:
            rows.append({"name": data.get("name", name), "url": data.get("homepage", "") or f"https://www.npmjs.com/package/{npm_name}", "source": source})
    return [r for r in rows if r["name"] and normalized], partial


def _alternatives(name: str) -> list[str]:
    stem = re.sub(r"[^A-Za-z0-9]", "", name.title()) or "Project"
    options = [f"{stem}Atlas", f"{stem}Foundry", f"{stem}Lens"]
    return list(dict.fromkeys(options))[:3]


def lambda_handler(event: dict, context) -> dict:
    profile = event["project_profile"]
    name = str(profile.get("project_name") or "")
    trace = start_span("name_collision", "none", name)
    rows, partial = asyncio.run(_lookup(name))
    normalized = _normalize(name)
    exact = [r["url"] or r["name"] for r in rows if _normalize(r["name"]) == normalized]
    scored = [(r, _jaro_winkler(normalized, _normalize(r["name"]))) for r in rows]
    fuzzy = [r["url"] or r["name"] for r, score in scored if 0.78 <= score < 1.0]
    target_keys = _double_metaphone(name)
    phonetic = []
    for row, score in scored:
        if score < 0.78 and target_keys and (target_keys & _double_metaphone(row["name"])):
            phonetic.append(row["url"] or row["name"])
    best = max((score for _, score in scored), default=0.0)
    # Fixed advisory bands: RED >= 0.88, YELLOW >= 0.78, otherwise GREEN.
    # This is per-scan thresholding; no prior collision state is persisted.
    traffic = "RED" if exact or best >= 0.88 else "YELLOW" if best >= 0.78 or phonetic else "GREEN"
    status = "PARTIAL_TIMEOUT" if partial else "OK"
    if partial:
        traffic = "YELLOW"
    result = NameCollisionResult(
        traffic_light=traffic,
        exact_matches=list(dict.fromkeys(exact)),
        fuzzy_matches=list(dict.fromkeys(fuzzy)),
        phonetic_matches=list(dict.fromkeys(phonetic)),
        safe_alternatives=_alternatives(name),
        status=status,
        registries_checked=["github", "pypi", "npm"],
    )
    record_lane(profile.get("scan_id"), "name_collision")
    payload = {"name_collision": result.model_dump()}
    payload["pipeline_trace"] = [trace.finish(payload)]
    return payload
