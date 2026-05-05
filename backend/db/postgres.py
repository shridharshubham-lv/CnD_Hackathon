import json
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host="localhost",
        port=5432,
        user="hackuser",
        password="hackpass",
        dbname="hackdb",
    )


def init_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaigns (
            id SERIAL PRIMARY KEY,
            name TEXT,
            raw_brief TEXT,
            enriched_brief JSONB,
            execution_plan JSONB,
            qa_report JSONB,
            answers JSONB,
            status TEXT DEFAULT 'in_progress',
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS campaign_patterns (
            id SERIAL PRIMARY KEY,
            campaign_id INTEGER REFERENCES campaigns(id),
            pattern JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    # Add answers column if it doesn't exist (migration for existing DBs)
    cur.execute("""
        DO $$ BEGIN
            ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS answers JSONB;
        EXCEPTION WHEN undefined_table THEN NULL;
        END $$;
    """)
    # Add channel_assets column if it doesn't exist (migration for existing DBs)
    cur.execute("""
        DO $$ BEGIN
            ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS channel_assets JSONB;
        EXCEPTION WHEN undefined_table THEN NULL;
        END $$;
    """)
    conn.commit()
    cur.close()
    conn.close()


def save_campaign(name: str, raw_brief: str, enriched_brief: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO campaigns (name, raw_brief, enriched_brief)
        VALUES (%s, %s, %s)
        RETURNING id
        """,
        (name, raw_brief, json.dumps(enriched_brief)),
    )
    campaign_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return campaign_id


def update_campaign(campaign_id: int, **kwargs):
    conn = get_connection()
    cur = conn.cursor()
    set_clauses = []
    values = []
    for key, value in kwargs.items():
        if key in ("enriched_brief", "execution_plan", "qa_report", "answers", "channel_assets"):
            set_clauses.append(f"{key} = %s")
            values.append(json.dumps(value))
        else:
            set_clauses.append(f"{key} = %s")
            values.append(value)
    values.append(campaign_id)
    query = f"UPDATE campaigns SET {', '.join(set_clauses)} WHERE id = %s"
    cur.execute(query, values)
    conn.commit()
    cur.close()
    conn.close()


def get_campaign(campaign_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return None
    result = dict(row)
    result["created_at"] = str(result["created_at"])
    return result


def get_all_campaigns() -> list[dict]:
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM campaigns ORDER BY created_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    results = []
    for row in rows:
        r = dict(row)
        r["created_at"] = str(r["created_at"])
        results.append(r)
    return results


def save_patterns(campaign_id: int, patterns: list[dict]):
    conn = get_connection()
    cur = conn.cursor()
    for p in patterns:
        cur.execute(
            "INSERT INTO campaign_patterns (campaign_id, pattern) VALUES (%s, %s)",
            (campaign_id, json.dumps(p)),
        )
    conn.commit()
    cur.close()
    conn.close()


def delete_campaign(campaign_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM campaign_patterns WHERE campaign_id = %s", (campaign_id,))
    cur.execute("DELETE FROM campaigns WHERE id = %s", (campaign_id,))
    conn.commit()
    cur.close()
    conn.close()
