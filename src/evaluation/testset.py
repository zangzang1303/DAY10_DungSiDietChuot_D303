from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def build_test_set(
    df: pd.DataFrame | list[dict[str, Any]],
    output_path: Path | str | None = None,
) -> list[dict[str, Any]]:
    """Build a frozen evaluation set from cleaned Crossref paper records.

    Generates realistic, factual QA pairs mapped directly to papers present in the clean dataset,
    adhering strictly to the required schema:
    {
        "id": "q1",
        "question_type": "factual",
        "question": "Question text",
        "ground_truth": "Ground truth answer",
        "ground_truth_doc_ids": ["paper_id"]
    }
    """
    if isinstance(df, pd.DataFrame):
        records = df.to_dict(orient="records")
    else:
        records = list(df)

    if not records:
        raise ValueError("Cannot build test set from an empty dataset.")

    # Create mapping by paper_id
    paper_map: dict[str, dict[str, Any]] = {str(r.get("paper_id", "")).strip(): r for r in records}

    # Curated factual question templates mapping to known paper IDs
    curated_questions = [
        {
            "id": "q1",
            "question_type": "factual",
            "paper_id": "10.1111/exsy.70341",
            "question": "Who are the authors of the paper titled 'Hi- RAG : A Hierarchical Retrieval-Augmented Generation Framework for Scalable and Generalisable Tool Selection in Large Language Model Agents'?",
            "ground_truth": "The authors are Wei Tian and Yuhao Zhou.",
        },
        {
            "id": "q2",
            "question_type": "factual",
            "paper_id": "10.2118/234689-pa",
            "question": "What is the application domain of the SafeRAG framework proposed by Qianwen Cao et al.?",
            "ground_truth": "SafeRAG is a multistage retrieval-augmented framework designed for oil and gas safety report generation.",
        },
        {
            "id": "q3",
            "question_type": "factual",
            "paper_id": "10.1007/s10278-026-02086-9",
            "question": "What diagnostic purpose does the JADE-Plus framework serve?",
            "ground_truth": "JADE-Plus is a multimodal agentic RAG framework for diagnostic support in jawbone lesions in oral and maxillofacial radiology.",
        },
        {
            "id": "q4",
            "question_type": "factual",
            "paper_id": "10.21203/rs.3.rs-10178277/v1",
            "question": "Who are the authors of the time-series forecasting study for cross-market equity analysis?",
            "ground_truth": "The authors are Novanto Yudistira and Yanuar Putra Kharisma Adhiyasa.",
        },
        {
            "id": "q5",
            "question_type": "factual",
            "paper_id": "10.3390/buildings16132637",
            "question": "What technologies are combined in the Agentic AI System for roof design compliance by Nawari O. Nawari and Oluwatoyin O. Lawal?",
            "ground_truth": "The system combines computer vision, retrieval-augmented generation (RAG), and large language models (LLMs).",
        },
        {
            "id": "q6",
            "question_type": "factual",
            "paper_id": "10.21079/11681/50309",
            "question": "Which hackathon event supported the R&D mission of the US Army Corps of Engineers (USACE) Civil Works?",
            "ground_truth": "The Microsoft Azure artificial intelligence / machine learning hackathon for development of retrieval-augmented generation large language model.",
        },
        {
            "id": "q7",
            "question_type": "factual",
            "paper_id": "10.63646/kpqm1958",
            "question": "Who authored the bibliometric review titled 'The Age of Autonomous Agents'?",
            "ground_truth": "The authors are Ben J. Weber, Clara M. Hofmann, and Amara N. Okoye.",
        },
        {
            "id": "q8",
            "question_type": "factual",
            "paper_id": "10.21203/rs.3.rs-10012178/v1",
            "question": "What governance prioritization architecture is proposed by Audrey Rah and Sven Hahues?",
            "ground_truth": "The paper proposes an integrated enterprise governance prioritization architecture for Generative AI (GenAI), Retrieval-Augmented Generation (RAG), and agentic AI.",
        },
    ]

    test_set: list[dict[str, Any]] = []

    # First, match curated questions against available papers in dataset
    for q_item in curated_questions:
        pid = q_item["paper_id"]
        if pid in paper_map:
            test_set.append(
                {
                    "id": q_item["id"],
                    "question_type": q_item["question_type"],
                    "question": q_item["question"],
                    "ground_truth": q_item["ground_truth"],
                    "ground_truth_doc_ids": [pid],
                }
            )

    # Dynamic fallback generator if fewer than 5 curated questions matched
    if len(test_set) < 5:
        for idx, rec in enumerate(records):
            pid = str(rec.get("paper_id", "")).strip()
            if any(pid in q["ground_truth_doc_ids"] for q in test_set):
                continue

            title = str(rec.get("title", "")).strip()
            authors = str(rec.get("authors_joined", "")).strip() or "the paper's authors"
            summary = str(rec.get("summary", "")).strip()

            if title and summary:
                qid = f"q{len(test_set) + 1}"
                test_set.append(
                    {
                        "id": qid,
                        "question_type": "factual",
                        "question": f"What is the main summary of the research paper titled '{title}'?",
                        "ground_truth": f"The paper by {authors} discusses: {summary[:200]}...",
                        "ground_truth_doc_ids": [pid],
                    }
                )
            if len(test_set) >= 8:
                break

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        write_json(out_p, test_set)

    return test_set

