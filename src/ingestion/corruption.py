from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import normalize_whitespace, read_json, write_json


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value).strip()


def _rebuild_text_for_embedding(row: pd.Series) -> str:
    title = _clean(row.get("title", ""))
    summary = _clean(row.get("summary", ""))
    authors = _clean(row.get("authors_joined", ""))
    categories = _clean(row.get("categories_joined", ""))
    published = _clean(row.get("published", ""))

    return normalize_whitespace(
        f"""
        Title: {title}
        Summary: {summary}
        Authors: {authors}
        Categories: {categories}
        Published: {published}
        """
    )


def _load_test_doc_ids(output_log_path: Path) -> set[str]:
    """
    output_log_path usually is data/results/corruption_log.json.
    From that path, infer data/eval/test_set.json.
    """
    data_dir = output_log_path.parent.parent
    test_set_path = data_dir / "eval" / "test_set.json"

    if not test_set_path.exists():
        return set()

    test_set = read_json(test_set_path)
    ids: set[str] = set()

    for item in test_set:
        for doc_id in item.get("ground_truth_doc_ids", []):
            ids.add(str(doc_id))

    return ids


def _target_indices(df: pd.DataFrame, output_log_path: Path) -> list[int]:
    """
    Prefer rows whose paper_id appears in the frozen evaluation set.
    Fallback to first rows if test set is missing.
    """
    if "paper_id" not in df.columns:
        return list(df.index[: min(6, len(df))])

    test_doc_ids = _load_test_doc_ids(output_log_path)
    if test_doc_ids:
        mask = df["paper_id"].astype(str).isin(test_doc_ids)
        indices = df[mask].index.tolist()
        if indices:
            return indices

    return list(df.index[: min(6, len(df))])


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """
    Simulate controlled data corruption.

    Scenarios:
    1. Blank summary on evaluation-related documents.
    2. Make published date stale.
    3. Add duplicate rows with same paper_id.
    4. Inject unrelated noise into text_for_embedding.
    5. Rebuild text_for_embedding after changed fields.
    6. Write detailed corruption log.
    """
    output_log_path = Path(output_log_path)

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
    targets = _target_indices(corrupted, output_log_path)

    if not targets:
        targets = list(corrupted.index[: min(6, len(corrupted))])

    events: list[dict[str, Any]] = []

    def affected_ids(indices: list[int]) -> list[str]:
        if "paper_id" not in corrupted.columns:
            return []
        return corrupted.loc[indices, "paper_id"].astype(str).tolist()

    # Chia target docs cho nhiều kịch bản. Vì test_set của bạn có 8 samples,
    # thường targets sẽ là 2-6 paper đại diện.
    blank_indices = targets[: max(1, len(targets) // 2)]
    stale_indices = targets[max(1, len(targets) // 2):] or targets[-1:]
    noise_indices = targets
    duplicate_indices = targets[: max(1, min(3, len(targets)))]

    # 1. Blank Summary
    if "summary" in corrupted.columns:
        corrupted.loc[blank_indices, "summary"] = ""
        events.append(
            {
                "type": "blank_summary",
                "affected_rows": len(blank_indices),
                "affected_paper_ids": affected_ids(blank_indices),
                "description": "Blanked summary for documents that overlap with the frozen evaluation set.",
            }
        )

    # 2. Stale Date
    if "published" in corrupted.columns:
        corrupted.loc[stale_indices, "published"] = "2000-01-01"

        if "age_days" in corrupted.columns:
            today = datetime.now(UTC).date()
            stale_age = (today - datetime(2000, 1, 1).date()).days
            corrupted.loc[stale_indices, "age_days"] = stale_age

        events.append(
            {
                "type": "stale_date",
                "affected_rows": len(stale_indices),
                "affected_paper_ids": affected_ids(stale_indices),
                "description": "Changed published date to 2000-01-01 to simulate stale records.",
            }
        )

    # 3. Add Noise
    if "text_for_embedding" in corrupted.columns:
        for idx in noise_indices:
            old_text = _clean(corrupted.at[idx, "text_for_embedding"])
            corrupted.at[idx, "text_for_embedding"] = normalize_whitespace(
                old_text
                + " RANDOM_NOISE_TOKEN unrelated unrelated corrupted corrupted misleading content"
            )

        events.append(
            {
                "type": "add_noise",
                "affected_rows": len(noise_indices),
                "affected_paper_ids": affected_ids(noise_indices),
                "description": "Injected unrelated noise into text_for_embedding for evaluation-related papers.",
            }
        )

    # 4. Duplicates
    duplicate_rows = corrupted.loc[duplicate_indices].copy()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    events.append(
        {
            "type": "duplicate_rows",
            "affected_rows": int(len(duplicate_rows)),
            "affected_paper_ids": duplicate_rows["paper_id"].astype(str).tolist()
            if "paper_id" in duplicate_rows.columns
            else [],
            "description": "Duplicated records while keeping the same paper_id to violate uniqueness.",
        }
    )

    # 5. Rebuild text_for_embedding from corrupted fields, then keep noise appended.
    if "text_for_embedding" in corrupted.columns:
        corrupted["text_for_embedding"] = corrupted.apply(_rebuild_text_for_embedding, axis=1)

        # Add noise again after rebuild so retrieval content is actually noisy.
        for idx in noise_indices:
            if idx < len(corrupted):
                corrupted.at[idx, "text_for_embedding"] = normalize_whitespace(
                    _clean(corrupted.at[idx, "text_for_embedding"])
                    + " RANDOM_NOISE_TOKEN unrelated unrelated corrupted corrupted misleading content"
                )

    log = {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_rows": input_rows,
        "output_rows": int(len(corrupted)),
        "test_doc_ids_targeted": list(_load_test_doc_ids(output_log_path)),
        "target_indices": [int(i) for i in targets],
        "target_paper_ids": affected_ids(targets),
        "events": events,
    }

    write_json(output_log_path, log)
    return corrupted