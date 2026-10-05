"""Embed the chart notes and the reference corpora, inside Oracle AI Database.

Runs on the host as DA_OWNER after `db/seed.py`. The chart notes come out of
the relational tables through langchain-oracledb's
`OracleAutonomousDatabaseLoader`, so the vector store is derived from the
system of record rather than kept beside it. The text splitter
(`OracleTextSplitter`) and the embedding model (`OracleEmbeddings` with the
in-database ONNX model) both run in the database; no text leaves it to be
vectorised. Each table then gets an Oracle Text search index for keyword
search.

    uv run python db/embed.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb  # noqa: E402
from langchain_core.documents import Document  # noqa: E402
from langchain_oracledb.document_loaders import OracleAutonomousDatabaseLoader  # noqa: E402
from langchain_oracledb.document_loaders.oracleai import OracleTextSplitter  # noqa: E402
from langchain_oracledb.embeddings import OracleEmbeddings  # noqa: E402
from langchain_oracledb.retrievers.text_search import create_text_index  # noqa: E402
from langchain_oracledb.vectorstores import OracleVS  # noqa: E402
from langchain_oracledb.vectorstores.utils import DistanceStrategy  # noqa: E402

from common.config import EMBEDDING_MODEL, OWNER, VECTOR_TABLES, load_config, password  # noqa: E402
from data.patients import SYNTHETIC_BANNER  # noqa: E402
from data.reference import medquad_documents, pubmed_documents  # noqa: E402

CHUNKING = {"by": "words", "max": "180", "overlap": "20", "split": "sentence", "normalize": "all"}

NOTES_SQL = f"""
SELECT '{SYNTHETIC_BANNER}' || CHR(10) ||
       p.display_name || ' [' || p.patient_id || '] - ' || p.alias || CHR(10) ||
       n.kind || ', ' || TO_CHAR(n.note_date, 'YYYY-MM-DD') || ' (' || e.setting || '):' || CHR(10) ||
       n.body                                               AS text,
       p.patient_id                                         AS patient_id,
       p.patient_id || '-NOTE-' || LPAD(n.id, 4, '0')       AS doc_id,
       p.display_name || ' - ' || n.kind || ' (' || TO_CHAR(n.note_date, 'YYYY-MM-DD') || ')' AS title,
       'chart:' || p.patient_id || ':clinical_note:' || n.id AS source,
       TO_CHAR(n.note_date, 'YYYY-MM-DD')                   AS note_date
FROM clinical_note n
JOIN encounter e ON e.id = n.encounter_id
JOIN patient p   ON p.patient_id = n.patient_id
ORDER BY p.patient_id, n.note_date
"""


def chart_note_documents(dsn: str, pw: str) -> list[Document]:
    loader = OracleAutonomousDatabaseLoader(
        query=NOTES_SQL,
        user=OWNER,
        password=pw,
        dsn=dsn,
        metadata=["TEXT", "PATIENT_ID", "DOC_ID", "TITLE", "SOURCE", "NOTE_DATE"],
    )
    docs = []
    for row in loader.load():
        m = row.metadata
        docs.append(
            Document(
                page_content=m["TEXT"],
                metadata={
                    "id": m["DOC_ID"],
                    "patient_id": m["PATIENT_ID"],
                    "title": m["TITLE"],
                    "source": m["SOURCE"],
                    "note_date": m["NOTE_DATE"],
                },
            )
        )
    return docs


def as_documents(rows: list[dict]) -> list[Document]:
    return [
        Document(
            page_content=r["content"],
            metadata={"id": r["id"], "title": r["title"], "source": r["source"]},
        )
        for r in rows
    ]


def load(conn, embeddings, splitter, table: str, docs: list[Document]) -> int:
    conn.cursor().execute(f"DELETE FROM {table}")
    conn.commit()
    vs = OracleVS(
        client=conn,
        embedding_function=embeddings,
        table_name=table,
        distance_strategy=DistanceStrategy.COSINE,
        mutate_on_duplicate=True,
    )
    vs.add_documents(docs, text_splitter=splitter, ids=[d.metadata["id"] for d in docs])
    try:
        create_text_index(conn, f"{table}_TXT", vector_store=vs)
    except Exception as exc:  # noqa: BLE001
        if "already" not in str(exc).lower() and "955" not in str(exc):
            raise
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return cur.fetchone()[0]


def main() -> None:
    dsn = load_config()["dsn"]
    pw = password(OWNER)
    with oracledb.connect(user=OWNER, password=pw, dsn=dsn) as conn:
        embeddings = OracleEmbeddings(conn=conn, params={"provider": "database", "model": EMBEDDING_MODEL})
        splitter = OracleTextSplitter(conn=conn, params=CHUNKING)
        notes = chart_note_documents(dsn, pw)
        print(f"  loaded {len(notes)} chart notes from the relational tables")
        print("  fetching the public reference corpus")
        plan = {
            "PATIENT_NOTE_VEC": notes,
            "CLINICAL_REFERENCE": as_documents(medquad_documents()),
            "RESEARCH_EVIDENCE": as_documents(pubmed_documents()),
        }
        assert tuple(plan) == VECTOR_TABLES
        for table, docs in plan.items():
            t0 = time.time()
            chunks = load(conn, embeddings, splitter, table, docs)
            print(f"  {table:<20} {len(docs):>4} documents -> {chunks:>5} chunks in {time.time() - t0:6.1f} s")
    print("EMBED OK")


if __name__ == "__main__":
    main()
