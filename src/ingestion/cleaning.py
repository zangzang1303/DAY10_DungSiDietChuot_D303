from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
import html
from pathlib import Path
import re
from typing import Any

import pandas as pd

from ingestion.crossref import PaperRecord


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


def _format_date(date_str: str | None) -> str:
    if not date_str or not isinstance(date_str, str):
        return ""
    date_str = date_str.strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", date_str)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    return ""


def _calculate_age_days(published_str: str, run_date: datetime) -> int:
    formatted = _format_date(published_str)
    if not formatted:
        return 9999
    try:
        pub_dt = datetime.strptime(formatted, "%Y-%m-%d").date()
        target_dt = run_date.date() if isinstance(run_date, datetime) else run_date
        return max(0, (target_dt - pub_dt).days)
    except Exception:
        return 9999


def build_clean_dataframe(
    records: list[PaperRecord | dict[str, Any]], run_date: datetime | None = None
) -> pd.DataFrame:
    """Clean raw records into a standardized DataFrame ready for embedding and retrieval.

    Filters garbage records (missing title or summary < 100 chars), normalizes text fields,
    aggregates authors & categories into joined strings, computes freshness (age_days),
    and creates the semantic text_for_embedding field.
    """
    if run_date is None:
        run_date = datetime.now(UTC)

    cleaned_rows: list[dict[str, Any]] = []

    for rec in records:
        data = asdict(rec) if is_dataclass(rec) else dict(rec)  # type: ignore[arg-type]

        title = _clean_text(data.get("title", ""))
        summary = _clean_text(data.get("summary", ""))

        # Rule: Drop records without title or summary < 100 characters
        if not title or len(summary) < 100:
            continue

        paper_id = str(data.get("paper_id", "")).strip()

        # Handle authors
        raw_authors = data.get("authors", [])
        if isinstance(raw_authors, list):
            authors_list = [str(a).strip() for a in raw_authors if a]
        elif isinstance(raw_authors, str) and raw_authors:
            authors_list = [a.strip() for a in raw_authors.split(",") if a.strip()]
        else:
            authors_list = []
        authors_joined = ", ".join(authors_list) if authors_list else ""

        # Handle categories
        raw_categories = data.get("categories", [])
        if isinstance(raw_categories, list):
            categories_list = [str(c).strip() for c in raw_categories if c]
        elif isinstance(raw_categories, str) and raw_categories:
            categories_list = [c.strip() for c in raw_categories.split(",") if c.strip()]
        else:
            categories_list = []
        categories_joined = ", ".join(categories_list) if categories_list else ""

        primary_category = str(data.get("primary_category", "")).strip()
        if not primary_category and categories_list:
            primary_category = categories_list[0]

        published = _format_date(str(data.get("published", "")))
        updated = _format_date(str(data.get("updated", ""))) or published
        age_days = _calculate_age_days(published, run_date)
        summary_chars = len(summary)

        # Semantic representation column
        text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"

        cleaned_rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors_list,
                "categories": categories_list,
                "primary_category": primary_category,
                "published": published,
                "updated": updated,
                "abs_url": str(data.get("abs_url", "")).strip(),
                "pdf_url": str(data.get("pdf_url", "")).strip(),
                "comment": str(data.get("comment", "")).strip(),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": summary_chars,
                "age_days": age_days,
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(cleaned_rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "paper_id",
                "title",
                "summary",
                "authors",
                "categories",
                "primary_category",
                "published",
                "updated",
                "abs_url",
                "pdf_url",
                "comment",
                "authors_joined",
                "categories_joined",
                "summary_chars",
                "age_days",
                "text_for_embedding",
            ]
        )

    # Drop duplicate records based on paper_id or title
    df = df.drop_duplicates(subset=["paper_id"], keep="first")
    df = df.drop_duplicates(subset=["title"], keep="first")

    # Sort by published date descending
    df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)

    return df


def save_clean_data(df: pd.DataFrame, csv_path: Path, json_path: Path) -> None:
    """Save cleaned DataFrame to CSV and JSON artifacts."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)

