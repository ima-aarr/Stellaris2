import discord
from discord.ext import commands
import os
import asyncio
import logging
from dotenv import load_dotenv
from utils.db import Database
from utils.assets import check_and_download_assets

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LuminaMain")

load_dotenv()

class LuminaBot(commands.Bot):
    def __init__(self):
        # 全てのインテントを有効化
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or("/"),
            intents=intents,
            help_command=None, # カスタムヘルプを使うため無効化
            activity=discord.Activity(type=discord.ActivityType.playing, name="/help | 起動準備中...")
        )
        self.db = Database(os.getenv("DATABASE_URL"))
        
        # 管理者IDリストの読み込み (環境変数 ADMIN_IDS="123,456" 形式)
        admin_ids_str = os.getenv("ADMIN_IDS", "")
        self.admin_ids = [int(i) for i in admin_ids_str.split(",") if i.isdigit()]
        
        # 特別サーバーID (機能制限用)
        self.special_guild_id = int(os.getenv("SPECIAL_GUILD_ID", "0"))

    async def setup_hook(self):
        # 1. アセット確認 (フォント/クッキー)
        await check_and_download_assets()
        
        # 2. DB接続
        await self.db.connect()
        
        # 3. Cogロード
        extensions = [
            'cogs.general',
            'cogs.economy',
            'cogs.moderation',
            'cogs.entertainment',
            'cogs.rpg',
            'cogs.voice'
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                logger.info(f"✅ Loaded: {ext}")
            except Exception as e:
                logger.error(f"❌ Failed to load {ext}: {e}")

        # 4. コマンド同期 (グローバル)
        # 注意: グローバル同期は反映に時間がかかる場合がありますが、全サーバー適用のために実行
        try:
            await self.tree.sync()
            logger.info("✅ Command Tree Synced.")
        except Exception as e:
            logger.error(f"⚠️ Sync Error: {e}")

    async def on_ready(self):
        logger.info(f"🚀 {self.user} is Ready!")
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.custom,
            name="custom",
            state=f"/help | {len(self.guilds)} servers | 爆速応答モード"
        ))

    async def on_command_error(self, ctx, error):
        # 従来のPrefixコマンド用エラーハンドラ
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ クールダウン中: あと {error.retry_after:.2f}秒")
        else:
            logger.error(f"Command Error: {error}")

bot = LuminaBot()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.critical("❌ DISCORD_TOKEN が設定されていません！")
    else:
        bot.run(token)
