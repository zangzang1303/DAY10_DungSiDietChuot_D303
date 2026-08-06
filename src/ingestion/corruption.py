from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd

from core.utils import write_json, normalize_whitespace


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    title = str(row.get("title", "") or "").strip()
    summary = str(row.get("summary", "") or "").strip()
    authors = str(row.get("authors_joined", "") or "").strip()
    categories = str(row.get("categories_joined", "") or "").strip()
    published = str(row.get("published", "") or "").strip()

    text = f"""
Title: {title}
Summary: {summary}
Authors: {authors}
Categories: {categories}
Published: {published}
""".strip()

    return normalize_whitespace(text)


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """
    Simulate controlled data corruption.

    Corruptions:
    1. Drop some latest records.
    2. Blank summary in some rows.
    3. Inject noise into text.
    4. Truncate title.
    5. Make published date stale.
    6. Add duplicate rows.
    7. Rebuild text_for_embedding.
    8. Write corruption log.
    """
    if df.empty:
        log = {
            "generated_at": datetime.now(UTC).isoformat(),
            "input_rows": 0,
            "output_rows": 0,
            "events": [],
            "warning": "Input dataframe was empty.",
        }
        write_json(output_log_path, log)
        return df.copy()

    corrupted = df.copy().reset_index(drop=True)
    input_rows = int(len(corrupted))
    events: list[dict[str, Any]] = []

    # Use fixed fractions to make the corruption repeatable.
    n_drop = max(1, int(input_rows * 0.10)) if input_rows >= 8 else 0
    n_blank = max(1, int(input_rows * 0.25))
    n_noise = max(1, int(input_rows * 0.20))
    n_truncate = max(1, int(input_rows * 0.15))
    n_stale = max(1, int(input_rows * 0.20))
    n_duplicate = max(1, int(input_rows * 0.10)) if input_rows >= 5 else 0

    # 1. Drop latest records based on age_days ascending.
    if n_drop > 0 and "age_days" in corrupted.columns:
        age_values = pd.to_numeric(corrupted["age_days"], errors="coerce")
        drop_indices = age_values.sort_values(na_position="last").head(n_drop).index.tolist()
        dropped_ids = corrupted.loc[drop_indices, "paper_id"].astype(str).tolist() if "paper_id" in corrupted.columns else []
        corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)
        events.append(
            {
                "type": "drop_latest_records",
                "affected_rows": len(drop_indices),
                "affected_paper_ids": dropped_ids,
                "description": "Dropped records with the smallest age_days to simulate missing recent papers.",
            }
        )

    # Recompute row count after drop.
    current_rows = int(len(corrupted))

    # 2. Blank summary.
    if "summary" in corrupted.columns and current_rows > 0:
        blank_indices = corrupted.index[: min(n_blank, current_rows)].tolist()
        affected_ids = corrupted.loc[blank_indices, "paper_id"].astype(str).tolist() if "paper_id" in corrupted.columns else []
        corrupted.loc[blank_indices, "summary"] = ""
        events.append(
            {
                "type": "blank_summary",
                "affected_rows": len(blank_indices),
                "affected_paper_ids": affected_ids,
                "description": "Blanked summary/abstract to reduce completeness and semantic content.",
            }
        )

    # 3. Inject noise into summary.
    if "summary" in corrupted.columns and current_rows > 0:
        noise_start = min(n_blank, current_rows)
        noise_end = min(noise_start + n_noise, current_rows)
        noise_indices = corrupted.index[noise_start:noise_end].tolist()
        affected_ids = corrupted.loc[noise_indices, "paper_id"].astype(str).tolist() if "paper_id" in corrupted.columns else []
        for idx in noise_indices:
            corrupted.at[idx, "summary"] = f"{corrupted.at[idx, 'summary']} NOISE_TOKEN NOISE_TOKEN unrelated corrupted text"
        events.append(
            {
                "type": "inject_noise",
                "affected_rows": len(noise_indices),
                "affected_paper_ids": affected_ids,
                "description": "Injected unrelated tokens into summary to weaken embedding quality.",
            }
        )

    # 4. Truncate title.
    if "title" in corrupted.columns and current_rows > 0:
        truncate_start = min(n_blank + n_noise, current_rows)
        truncate_end = min(truncate_start + n_truncate, current_rows)
        truncate_indices = corrupted.index[truncate_start:truncate_end].tolist()
        affected_ids = corrupted.loc[truncate_indices, "paper_id"].astype(str).tolist() if "paper_id" in corrupted.columns else []
        for idx in truncate_indices:
            title = str(corrupted.at[idx, "title"])
            corrupted.at[idx, "title"] = title[: max(8, min(20, len(title)))]
        events.append(
            {
                "type": "truncate_title",
                "affected_rows": len(truncate_indices),
                "affected_paper_ids": affected_ids,
                "description": "Truncated titles to simulate partial text corruption.",
            }
        )

    # 5. Make published date stale.
    if "published" in corrupted.columns and current_rows > 0:
        stale_start = min(n_blank + n_noise + n_truncate, current_rows)
        stale_end = min(stale_start + n_stale, current_rows)
        stale_indices = corrupted.index[stale_start:stale_end].tolist()
        affected_ids = corrupted.loc[stale_indices, "paper_id"].astype(str).tolist() if "paper_id" in corrupted.columns else []

        corrupted.loc[stale_indices, "published"] = "2000-01-01"
        if "age_days" in corrupted.columns:
            today = datetime.now(UTC).date()
            stale_age = (today - datetime(2000, 1, 1).date()).days
            corrupted.loc[stale_indices, "age_days"] = stale_age

        events.append(
            {
                "type": "make_published_stale",
                "affected_rows": len(stale_indices),
                "affected_paper_ids": affected_ids,
                "description": "Changed published date to an old date to simulate stale data.",
            }
        )

    # 6. Add duplicate rows.
    if n_duplicate > 0 and current_rows > 0:
        duplicate_rows = corrupted.head(min(n_duplicate, current_rows)).copy()
        corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
        affected_ids = duplicate_rows["paper_id"].astype(str).tolist() if "paper_id" in duplicate_rows.columns else []
        events.append(
            {
                "type": "add_duplicate_rows",
                "affected_rows": int(len(duplicate_rows)),
                "affected_paper_ids": affected_ids,
                "description": "Duplicated records to violate uniqueness.",
            }
        )

    # 7. Rebuild text_for_embedding.
    if "text_for_embedding" in corrupted.columns:
        corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)

    log = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_rows": input_rows,
        "output_rows": int(len(corrupted)),
        "events": events,
    }
    write_json(output_log_path, log)
    return corrupted