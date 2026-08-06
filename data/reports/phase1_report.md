# Phase 1 Baseline Report

Generated at: `2026-08-06T03:36:00.943546+00:00`

## 1. Source Summary

| Field | Value |
|---|---|
| Source API | Crossref REST API |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Max results | 24 |
| Raw records | 24 |
| Clean records | 24 |

## 2. Baseline Evaluation Metrics

| Metric | Value |
|---|---:|
| `samples` | 8 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 0.2420 |
| `judge_accuracy` | 0.1250 |
| `mean_judge_score` | 1.2500 |

## 3. Data Quality Checks

Overall status: **PASS**

| Check | Dimension | Passed | Value | Threshold |
|---|---|---:|---|---|
| required_columns_present | schema_validity | PASS | `{'missing_columns': []}` | no missing required columns |
| row_count_positive | completeness | PASS | `24` | > 0 |
| paper_id_not_null | validity | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing paper_id |
| paper_id_unique | uniqueness | PASS | `{'duplicate_rows': 0, 'duplicate_rate': 0.0}` | 0 duplicate paper_id |
| title_not_null | completeness | PASS | `{'missing_rows': 0, 'missing_rate': 0.0}` | 0 missing title |
| summary_completeness | completeness | PASS | `{'missing_rows': 0, 'missing_rate': 0.0, 'short_summary_rows': 0, 'short_summary_rate': 0.0}` | missing summary rate <= 20% |
| text_for_embedding_ready | retrieval_readiness | PASS | `{'empty_rows': 0, 'empty_rate': 0.0, 'short_rows': 0, 'short_rate': 0.0}` | 0 empty text_for_embedding and short text rate <= 25% |
| freshness_age_days | freshness | PASS | `{'invalid_age_rows': 0, 'stale_rows': 0, 'stale_rate': 0.0}` | invalid age_days = 0 and stale rate <= 50%; threshold=180 days |

## 4. Freshness Report

| Field | Value |
|---|---|
| Latest published | 2026-08-01T00:00:00+00:00 |
| Oldest published | 2026-02-12T00:00:00+00:00 |
| Freshness threshold days | 180 |
| Stale rows | 0 |
| Stale rate | 0.0000 |
| Invalid age rows | 0 |
| Is fresh | True |

## 5. Interpretation

This baseline is the clean-data reference point for later comparison. 
The retrieval hit rate mainly reflects whether embedding and ChromaDB retrieval can find the ground-truth paper in top-k results. 
Token F1 measures lexical overlap between the generated answer and the ground truth, so it may be below 1.0 even when the retrieved document is correct.
