"""
DB 초기화 및 공용 접근 헬퍼.
SQLite (aiosqlite)를 사용. 봇 시작 시 init_db()를 한 번 호출한다.
"""

import json
import os
import aiosqlite

# Railway 볼륨을 쓸 경우 DB_PATH 환경변수로 볼륨 마운트 경로(예: /data/trpg.db)를 지정하세요.
# 지정하지 않으면 앱 폴더에 trpg.db로 저장되는데, Railway는 배포/재시작 시 파일시스템이
# 초기화될 수 있어 데이터가 날아갈 수 있습니다. 반드시 볼륨 사용을 권장합니다.
DB_PATH = os.getenv("DB_PATH", "trpg.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    system TEXT NOT NULL,
    stats_json TEXT NOT NULL,       -- 시스템 프로필에 정의된 능력치 값들
    hp_current INTEGER DEFAULT 0,
    hp_max INTEGER DEFAULT 0,
    extra_json TEXT DEFAULT '{}',   -- 인벤토리, 메모 등 자유 필드
    UNIQUE(guild_id, owner_id, name)
);

CREATE TABLE IF NOT EXISTS combat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL UNIQUE,
    round INTEGER DEFAULT 1,
    turn_index INTEGER DEFAULT 0,
    order_json TEXT DEFAULT '[]'    -- [{name, init, hp_current, hp_max, is_pc, char_id}]
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


# ---------- 캐릭터 ----------

async def create_character(guild_id: str, owner_id: str, name: str, system: str, stats: dict, hp_max: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO characters (guild_id, owner_id, name, system, stats_json, hp_current, hp_max)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (guild_id, owner_id, name, system, json.dumps(stats, ensure_ascii=False), hp_max, hp_max),
        )
        await db.commit()


async def get_character(guild_id: str, owner_id: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM characters WHERE guild_id=? AND owner_id=? AND name=?",
            (guild_id, owner_id, name),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def list_characters(guild_id: str, owner_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT name, system, hp_current, hp_max FROM characters WHERE guild_id=? AND owner_id=?",
            (guild_id, owner_id),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_stat(guild_id: str, owner_id: str, name: str, stat_key: str, value):
    char = await get_character(guild_id, owner_id, name)
    if not char:
        return None
    stats = json.loads(char["stats_json"])
    stats[stat_key] = value
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE characters SET stats_json=? WHERE guild_id=? AND owner_id=? AND name=?",
            (json.dumps(stats, ensure_ascii=False), guild_id, owner_id, name),
        )
        await db.commit()
    return stats


async def update_hp(guild_id: str, owner_id: str, name: str, delta: int):
    char = await get_character(guild_id, owner_id, name)
    if not char:
        return None
    new_hp = max(0, min(char["hp_max"], char["hp_current"] + delta))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE characters SET hp_current=? WHERE guild_id=? AND owner_id=? AND name=?",
            (new_hp, guild_id, owner_id, name),
        )
        await db.commit()
    return new_hp


async def delete_character(guild_id: str, owner_id: str, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM characters WHERE guild_id=? AND owner_id=? AND name=?",
            (guild_id, owner_id, name),
        )
        await db.commit()
        return cur.rowcount > 0


# ---------- 전투(이니셔티브) ----------

async def save_combat(channel_id: str, round_: int, turn_index: int, order: list):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO combat_sessions (channel_id, round, turn_index, order_json)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(channel_id) DO UPDATE SET
                 round=excluded.round, turn_index=excluded.turn_index, order_json=excluded.order_json""",
            (channel_id, round_, turn_index, json.dumps(order, ensure_ascii=False)),
        )
        await db.commit()


async def get_combat(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM combat_sessions WHERE channel_id=?", (channel_id,))
        row = await cur.fetchone()
        if not row:
            return None
        d = dict(row)
        d["order"] = json.loads(d["order_json"])
        return d


async def end_combat(channel_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM combat_sessions WHERE channel_id=?", (channel_id,))
        await db.commit()
