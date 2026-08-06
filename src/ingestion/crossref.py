from __future__ import annotations

from dataclasses import asdict, dataclass
import html
import json
from pathlib import Path
import re
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings

CROSSREF_API_URL = "https://api.crossref.org/works"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(text: str | None) -> str:
    if not text:
        return ""
    # Remove XML / HTML tags (e.g. <jats:p>, <b>, etc.)
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Unescape HTML entities
    cleaned = html.unescape(cleaned)
    # Collapse multiple whitespaces
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _parse_date(date_dict: dict[str, Any] | None) -> str:
    if not date_dict or not isinstance(date_dict, dict):
        return ""
    date_parts = date_dict.get("date-parts")
    if not date_parts or not isinstance(date_parts, list) or len(date_parts) == 0:
        return ""
    parts = date_parts[0]
    if not parts or not isinstance(parts, list):
        return ""

    try:
        year = parts[0]
        month = parts[1] if len(parts) > 1 else 1
        day = parts[2] if len(parts) > 2 else 1
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (ValueError, TypeError, IndexError):
        return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload response into a list of PaperRecord objects.

    Filters out any records that lack title or summary (abstract/description).
    """
    records: list[PaperRecord] = []
    items = payload.get("message", {}).get("items", [])

    for item in items:
        # Extract DOI / paper_id
        doi = item.get("DOI", "").strip()

        # Extract title
        titles = item.get("title", [])
        title_raw = titles[0] if isinstance(titles, list) and titles else str(titles or "")
        title = _clean_text(title_raw)

        # Extract abstract / summary / description
        summary_raw = item.get("abstract") or item.get("description") or ""
        summary = _clean_text(summary_raw)

        # Require both non-empty title and non-empty summary
        if not title or not summary:
            continue

        paper_id = doi or item.get("id", "") or f"crossref_{len(records)+1}"

        # Extract authors
        authors: list[str] = []
        raw_authors = item.get("author", [])
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    given = a.get("given", "").strip()
                    family = a.get("family", "").strip()
                    name = a.get("name", "").strip()
                    if given and family:
                        authors.append(f"{given} {family}")
                    elif family:
                        authors.append(family)
                    elif name:
                        authors.append(name)

        # Extract categories / subject
        categories: list[str] = []
        raw_subjects = item.get("subject", [])
        if isinstance(raw_subjects, list):
            categories = [str(s).strip() for s in raw_subjects if s]
        primary_category = categories[0] if categories else ""

        # Extract dates
        published = (
            _parse_date(item.get("published-print"))
            or _parse_date(item.get("published-online"))
            or _parse_date(item.get("issued"))
            or _parse_date(item.get("created"))
        )
        updated = (
            _parse_date(item.get("deposited"))
            or _parse_date(item.get("indexed"))
            or published
        )

        # Extract URLs
        abs_url = item.get("URL", "").strip()
        if not abs_url and doi:
            abs_url = f"https://doi.org/{doi}"

        pdf_url = ""
        links = item.get("link", [])
        if isinstance(links, list):
            for link in links:
                if isinstance(link, dict):
                    content_type = link.get("content-type", "")
                    if "pdf" in content_type.lower() or "pdf" in link.get("intended-application", "").lower():
                        pdf_url = link.get("URL", "").strip()
                        break

        # Comment / container-title
        container = item.get("container-title", [])
        comment = container[0] if isinstance(container, list) and container else str(container or "")

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Call external Crossref API with retry & backoff logic, save raw response and parsed records."""
    params: dict[str, str | int] = {
        "query": settings.source_query,
        "rows": settings.max_results,
    }
    if settings.source_filter:
        params["filter"] = settings.source_filter

    headers = {
        "User-Agent": "DataPipelineLab/1.0 (mailto:student@example.com)",
        "Accept": "application/json",
    }

    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))

    response = None
    max_manual_attempts = 3
    for attempt in range(max_manual_attempts):
        try:
            res = session.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)
            if res.status_code in {429, 503, 500, 502, 504}:
                time.sleep(2 ** attempt)
                continue
            res.raise_for_status()
            response = res
            break
        except requests.RequestException as exc:
            if attempt == max_manual_attempts - 1:
                raise RuntimeError(f"Failed to fetch Crossref data after retries: {exc}") from exc
            time.sleep(2 ** attempt)

    if response is None:
        raise RuntimeError("Failed to fetch Crossref response.")

    payload = response.json()

    # Form 1: Save raw HTTP response JSON
    raw_api_path = settings.paths.raw_api_response
    raw_api_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_api_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    # Parse records
    records = parse_crossref_payload(payload)

    # Form 2: Save parsed flat records JSON
    raw_records_path = settings.paths.raw_records_json
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    with open(raw_records_path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, indent=2, ensure_ascii=False)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map into list of PaperRecord dataclass objects."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(data)}")

    return [PaperRecord(**item) for item in data]
