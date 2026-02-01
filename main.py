import discord
from discord.ext import commands
import os
import asyncio
import logging
import requests
import json
from utils.database import Database

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# インテント設定（全権限付与）
intents = discord.Intents.all()

class RumiaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or('/'),
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        self.db = Database()
        self.admin_ids = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id.isdigit()]

    async def setup_hook(self):
        # 1. リソースの準備 (フォントDL & Cookie生成)
        self.prepare_resources()
        
        # 2. データベース接続
        await self.db.connect()
        
        # 3. Cogのロード
        await self.load_extensions()
        
        # 4. コマンド同期
        # 本番環境では特定のギルドのみに即時同期するか、グローバル同期は時間を置く
        await self.tree.sync()
        logging.info("🌳 コマンドツリーを同期しました。")

    def prepare_resources(self):
        """フォントのダウンロードとCookieファイルの生成"""
        # フォント (Noto Sans JP)
        if not os.path.exists("fonts"):
            os.makedirs("fonts")
        font_path = "fonts/NotoSansJP-Bold.ttf"
        if not os.path.exists(font_path):
            logging.info("📥 フォントをダウンロード中...")
            url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf" # 代用URL
            # 実際には軽量なGoogle Fontsの直リンク推奨。ここでは例として処理のみ記述
            # 簡易的にNotoSansJPのURLを使用
            try:
                r = requests.get("https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Bold.ttf", allow_redirects=True)
                with open(font_path, "wb") as f:
                    f.write(r.content)
                logging.info("✅ フォントダウンロード完了")
            except Exception as e:
                logging.error(f"❌ フォントDL失敗: {e}")

        # YouTube Cookies (環境変数 -> ファイル)
        cookie_env = os.getenv("YOUTUBE_COOKIES")
        if cookie_env:
            logging.info("🍪 環境変数からcookies.txtを生成中...")
            with open("cookies.txt", "w") as f:
                f.write(cookie_env)

    async def load_extensions(self):
        """Cogsフォルダ内の拡張機能をロード"""
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logging.info(f"⚙️ Loaded Cog: {filename}")
                except Exception as e:
                    logging.error(f"❌ Failed to load {filename}: {e}")

    async def on_ready(self):
        logging.info(f"🚀 Logged in as {self.user} (ID: {self.user.id})")
        logging.info(f"📊 導入サーバー数: {len(self.guilds)}")
        await self.change_presence(activity=discord.Game(name="/help | Rumia Bot"))

    async def close(self):
        await self.db.close()
        await super().close()

# Botインスタンス作成と実行
bot = RumiaBot()

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """グローバルエラーハンドラー"""
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ クールダウン中です。あと {error.retry_after:.2f} 秒お待ちください。", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ 権限が不足しています。", ephemeral=True)
    else:
        logging.error(f"Command Error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ エラーが発生しました: {error}", ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("❌ DISCORD_TOKENが見つかりません。")
    else:
        bot.run(token)
