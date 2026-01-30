import asyncpg
import logging

class Database:
    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None
        self.logger = logging.getLogger("Database")

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(self.dsn)
            self.logger.info("✅ Database connected successfully.")
            await self.create_tables()
        except Exception as e:
            self.logger.critical(f"❌ Database connection failed: {e}")
            raise e

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            # ユーザーテーブル (経済・RPG用)
            # debt, job_id などを確実に追加
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    cash BIGINT DEFAULT 0,
                    bank BIGINT DEFAULT 0,
                    debt BIGINT DEFAULT 0,
                    xp BIGINT DEFAULT 0,
                    level INT DEFAULT 1,
                    job_id TEXT DEFAULT 'ニート',
                    last_daily TIMESTAMP,
                    last_work TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # ギルド設定 (AutoMod, Prefix, Log Channel)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id BIGINT PRIMARY KEY,
                    log_channel_id BIGINT,
                    welcome_channel_id BIGINT,
                    automod_enabled BOOLEAN DEFAULT FALSE,
                    timeout_duration INT DEFAULT 600,
                    verify_role_id BIGINT
                );
            """)

            # 警告管理
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS warns (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guild_id BIGINT,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 国家戦略用
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nations (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT,
                    population BIGINT DEFAULT 100,
                    resources BIGINT DEFAULT 1000,
                    army BIGINT DEFAULT 0,
                    tax_rate INT DEFAULT 10
                );
            """)

            # 自動応答設定
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_responses (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    trigger TEXT,
                    response TEXT
                );
            """)

            # 自動リアクション設定
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_reactions (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    trigger TEXT,
                    emoji TEXT
                );
            """)

            # おみくじ設定 (カスタム確率)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS omikuji_settings (
                    guild_id BIGINT,
                    result_name TEXT,
                    probability INT,
                    description TEXT,
                    PRIMARY KEY (guild_id, result_name)
                );
            """)

            # 管理者ホワイトリスト
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_whitelist (
                    user_id BIGINT PRIMARY KEY
                );
            """)

    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
