"""Find public implementations and research around the project's problem."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import httpx

from shared.bedrock_client import LITE_MODEL_ID, invoke_lite
from shared.github_client import get_file_content, search_repos
from shared.progress import record_lane
from shared.schemas import LandscapeResult
from shared.telemetry import start_span


def _queries(profile: dict) -> list[str]:
    seed = " ".join(profile.get("domain_keywords", [])) or profile["problem_signature"]["bottleneck_type"]
    try:
        result = json.loads(invoke_lite(
            "Turn this software idea into exactly 3 concise technical GitHub/arXiv search queries. "
            "Remove marketing adjectives. Return JSON array of strings.\n" + seed,
            max_tokens=300,
        ))
        queries = [q.strip() for q in result if isinstance(q, str) and q.strip()]
        if queries:
            return queries[:3]
    except (ValueError, TypeError):
        pass
    sig = profile["problem_signature"]
    return [sig[k].replace("_", " ") for k in ("state_space", "bottleneck_type", "failure_mode")]


def _arxiv(query: str) -> list[dict]:
    response = httpx.get(
        "https://export.arxiv.org/api/query",
        params={"search_query": f"all:{query}", "start": 0, "max_results": 3, "sortBy": "relevance"},
        timeout=5.0,
    )
    response.raise_for_status()
    root = ET.fromstring(response.text)
    ns = {"a": "http://www.w3.org/2005/Atom"}
    return [{"title": (e.findtext("a:title", default="", namespaces=ns)).strip(),
             "url": e.findtext("a:id", default="", namespaces=ns),
             "abstract_snippet": " ".join(e.findtext("a:summary", default="", namespaces=ns).split())[:400]}
            for e in root.findall("a:entry", ns)]


def lambda_handler(event: dict, context) -> dict:
    profile = event["project_profile"]
    trace = start_span("landscape_scout", LITE_MODEL_ID, profile)
    queries = _queries(profile)
    found: dict[str, dict] = {}
    for query in queries:
        try:
            for repo in search_repos(query, per_page=5):
                if repo.get("full_name"):
                    found[repo["full_name"].lower()] = repo
        except Exception:
            continue
    if len(found) < 2:
        broad = " ".join(profile.get("domain_keywords", [])[:2]) or profile["project_name"]
        try:
            for repo in search_repos(broad, per_page=5):
                if repo.get("full_name"):
                    found[repo["full_name"].lower()] = repo
        except Exception:
            pass

    candidates = sorted(found.values(), key=lambda r: r.get("stargazers_count", 0), reverse=True)[:5]
    competitors = []
    for repo in candidates:
        limitation = ""
        if len(competitors) < 3:
            try:
                readme = get_file_content(repo["owner"]["login"], repo["name"], "README.md")[:12000]
                match = re.search(r"(?ims)^#{1,3}\s*(?:limitations?|known issues|caveats?)\s*$\n(.*?)(?=^#{1,3}\s|\Z)", readme)
                limitation = " ".join(match.group(1).split())[:500] if match else "No limitations section found in README."
            except Exception:
                limitation = "README limitations could not be fetched."
        competitors.append({
            "name": repo.get("full_name", repo.get("name", "")),
            "url": repo.get("html_url", ""),
            "stars": repo.get("stargazers_count", 0),
            "description": repo.get("description") or "",
            "limitations": limitation,
        })

    try:
        papers = _arxiv(queries[0]) if queries else []
    except (httpx.HTTPError, ET.ParseError):
        papers = []
    gaps = []
    if not candidates:
        gaps.append("No matching public GitHub repositories were returned for the broadened queries.")
    if not papers:
        gaps.append("No matching arXiv papers were returned for the primary technical query.")
    result = LandscapeResult(direct_competitors=competitors, academic_papers=papers[:3], ecosystem_gaps=gaps)
    record_lane(profile.get("scan_id"), "landscape")
    payload = {"landscape": result.model_dump(), "search_queries": queries}
    payload["pipeline_trace"] = [trace.finish(payload)]
    return payload
