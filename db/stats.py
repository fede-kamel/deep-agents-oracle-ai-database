"""Print the chunk count of each vector store, as the schema owner. Read-only."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import oracledb  # noqa: E402

from common.config import OWNER, VECTOR_TABLES, load_config, password  # noqa: E402


def main() -> int:
    with oracledb.connect(user=OWNER, password=password(OWNER), dsn=load_config()["dsn"]) as conn:
        cur = conn.cursor()
        counts = {}
        for table in VECTOR_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = cur.fetchone()[0]
    print(" ".join(f"{t}={n}" for t, n in counts.items()))
    return 0 if all(counts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
