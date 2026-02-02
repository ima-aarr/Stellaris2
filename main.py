import discord
from discord.ext import commands
import os
import asyncio
import logging
import requests
import base64
from aiohttp import web
from utils.database import Database

# ログ設定 (詳細な情報を見やすく出力)
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
        # 環境変数 ADMIN_IDS から管理者IDリストを作成
        admin_env = os.getenv("ADMIN_IDS", "")
        self.admin_ids = [int(id) for id in admin_env.split(",") if id.isdigit()]

    async def setup_hook(self):
        """Bot起動時の初期化処理"""
        
        # 0. Health Check用Webサーバーの起動 (Koyebが落とさないようにする)
        await self.start_health_check_server()

        # 1. リソースの準備 (フォント・Cookie)
        self.prepare_resources()
        
        # 2. データベース接続
        await self.db.connect()
        
        # 3. Cog (機能拡張) のロード
        await self.load_extensions()
        
        # 4. コマンドツリーの同期
        await self.tree.sync()
        logging.info("🌳 コマンドツリーを同期しました。")

    async def start_health_check_server(self):
        """KoyebのHealth Check (Port 8000) をパスするためのダミーWebサーバー"""
        async def handle(request):
            return web.Response(text="OK", status=200)

        app = web.Application()
        app.router.add_get('/', handle)
        app.router.add_get('/health', handle)
        
        runner = web.AppRunner(app)
        await runner.setup()
        # 0.0.0.0 の Port 8000 で待機
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        logging.info("🌍 Health Check Server started on port 8000")

    def prepare_resources(self):
        """フォントのダウンロードとCookieファイルの復元"""
        # --- フォント準備 ---
        if not os.path.exists("fonts"):
            os.makedirs("fonts")
        font_path = "fonts/NotoSansJP-Bold.ttf"
        
        if not os.path.exists(font_path):
            logging.info("📥 フォントをダウンロード中...")
            try:
                url = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Bold.ttf"
                r = requests.get(url, allow_redirects=True)
                with open(font_path, "wb") as f:
                    f.write(r.content)
                logging.info("✅ フォントダウンロード完了")
            except Exception as e:
                logging.error(f"❌ フォントDL失敗: {e}")

        # --- Cookie準備 (Base64対応) ---
        cookie_env = os.getenv("YOUTUBE_COOKIES")
        if cookie_env:
            logging.info("🍪 環境変数からcookies.txtを生成中...")
            try:
                # Base64としてデコードを試みる (これが推奨)
                decoded_cookie = base64.b64decode(cookie_env).decode('utf-8')
                with open("cookies.txt", "w") as f:
                    f.write(decoded_cookie)
                logging.info("✅ Cookie (Base64) の復元に成功しました")
            except Exception:
                # Base64じゃない場合（そのまま書き込み・改行崩れのリスクあり）
                logging.warning("⚠️ Base64デコードに失敗。生テキストとして保存します。")
                with open("cookies.txt", "w") as f:
                    f.write(cookie_env)

    async def load_extensions(self):
        """cogsフォルダ内の拡張機能をロード"""
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

bot = RumiaBot()

# --- グローバルエラーハンドリング ---
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    if isinstance(error, discord.app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ クールダウン中です。あと {error.retry_after:.2f} 秒お待ちください。", ephemeral=True)
    elif isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message("❌ 権限が不足しています。", ephemeral=True)
    else:
        logging.error(f"Command Error: {error}")
        # インタラクションが既に終了しているか確認して送信
        if interaction.response.is_done():
            await interaction.followup.send(f"❌ エラーが発生しました: {error}", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ エラーが発生しました: {error}", ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logging.error("❌ DISCORD_TOKENが見つかりません。環境変数を確認してください。")
    else:
        bot.run(token)
