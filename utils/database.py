import asyncpg
import os
import logging

class Database:
    def __init__(self):
        self.pool = None
        self.db_url = os.getenv("DATABASE_URL")

    async def connect(self):
        if not self.db_url:
            logging.warning("⚠️ DATABASE_URLが設定されていません。DB機能は動作しません。")
            return

        try:
            self.pool = await asyncpg.create_pool(self.db_url)
            logging.info("🗄️ データベースに接続しました。")
            await self.initialize_tables()
        except Exception as e:
            logging.error(f"❌ DB接続エラー: {e}")

    async def initialize_tables(self):
        """テーブルとカラムの初期化・修復"""
        async with self.pool.acquire() as conn:
            # ユーザーテーブル (経済機能用)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    cash BIGINT DEFAULT 0,
                    bank BIGINT DEFAULT 0,
                    debt BIGINT DEFAULT 0,
                    job_id TEXT DEFAULT 'ニート',
                    last_daily TIMESTAMP,
                    last_work TIMESTAMP,
                    xp BIGINT DEFAULT 0,
                    level INT DEFAULT 1,
                    bio TEXT DEFAULT 'プロフィールは未設定です。'
                )
            """)
            
            # カラム追加チェック (既存DBへのパッチ適用)
            # debtカラムがない場合に備えて追加を試みる
            try:
                await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS debt BIGINT DEFAULT 0")
                await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS xp BIGINT DEFAULT 0")
                await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS level INT DEFAULT 1")
            except Exception as e:
                logging.warning(f"Column update warning: {e}")

            # サーバー設定テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS guilds (
                    id BIGINT PRIMARY KEY,
                    prefix TEXT DEFAULT '/',
                    log_channel BIGINT,
                    welcome_channel BIGINT,
                    automod_enabled BOOLEAN DEFAULT FALSE,
                    automod_level INT DEFAULT 1,
                    verify_role_id BIGINT
                )
            """)

            # 自動応答テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS auto_responses (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    trigger TEXT,
                    response TEXT,
                    reaction TEXT
                )
            """)

            # 警告管理テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS warnings (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    user_id BIGINT,
                    reason TEXT,
                    moderator_id BIGINT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 国家戦略テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS nations (
                    user_id BIGINT PRIMARY KEY,
                    name TEXT,
                    population BIGINT DEFAULT 100,
                    resources BIGINT DEFAULT 1000,
                    army BIGINT DEFAULT 0,
                    tax_rate INT DEFAULT 10
                )
            """)
            
            # おみくじ設定テーブル
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS omikuji_settings (
                    id SERIAL PRIMARY KEY,
                    guild_id BIGINT,
                    result_name TEXT,
                    description TEXT,
                    probability INT
                )
            """)
            
            # 管理者ホワイトリスト
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS admin_whitelist (
                    user_id BIGINT PRIMARY KEY
                )
            """)

            logging.info("✅ データベーステーブルの初期化完了")

    async def execute(self, query, *args):
        if not self.pool: return
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query, *args):
        if not self.pool: return []
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query, *args):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
            
    async def fetchval(self, query, *args):
        if not self.pool: return None
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def close(self):
        if self.pool:
            await self.pool.close()
