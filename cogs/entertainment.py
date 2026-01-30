import discord
from discord import app_commands
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import asyncio
import aiohttp

class Entertainment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- Make it Quote (日本語対応版) ---
    @app_commands.command(name="makeitquote", description="名言風画像を生成します")
    async def makeitquote(self, interaction: discord.Interaction, user: discord.Member, text: str):
        await interaction.response.defer()

        # 設定
        WIDTH, HEIGHT = 1200, 400
        BG_COLOR = (20, 20, 20) # Discord Darker
        
        # 画像生成
        img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
        draw = ImageDraw.Draw(img)
        
        # フォント読み込み (assetsでDLしたパス)
        try:
            font_size = 50
            font = ImageFont.truetype("fonts/NotoSansJP-Bold.ttf", font_size)
            name_font = ImageFont.truetype("fonts/NotoSansJP-Bold.ttf", 40)
            small_font = ImageFont.truetype("fonts/NotoSansJP-Bold.ttf", 20)
        except:
            # フォールバック
            font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # アバター取得
        avatar_url = user.display_avatar.url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status != 200:
                    return await interaction.followup.send("❌ アバターの取得に失敗しました")
                data = await resp.read()
                
        avatar_img = Image.open(io.BytesIO(data)).convert("RGBA")
        avatar_img = avatar_img.resize((300, 300))
        
        # 丸く切り抜く
        mask = Image.new("L", (300, 300), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.ellipse((0, 0, 300, 300), fill=255)
        
        # 貼り付け
        img.paste(avatar_img, (50, 50), mask)

        # テキスト描画
        # 名前
        draw.text((380, 50), user.display_name, font=name_font, fill=(255, 255, 255))
        
        # 本文 (簡易折り返し)
        max_chars_per_line = 25
        wrapped_text = ""
        for i in range(0, len(text), max_chars_per_line):
            wrapped_text += text[i:i+max_chars_per_line] + "\n"
            
        draw.text((380, 120), wrapped_text, font=font, fill=(255, 255, 255))
        
        # ロゴ
        draw.text((WIDTH - 150, HEIGHT - 40), "Rumia Bot", font=small_font, fill=(150, 150, 150))

        # 送信
        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.followup.send(file=discord.File(fp=image_binary, filename='quote.png'))

    # --- なりすまし (Fake) ---
    @app_commands.command(name="fake", description="指定したユーザーになりすまして発言(Webhook)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def fake(self, interaction: discord.Interaction, target: discord.Member, message: str):
        # メンション無効化
        clean_content = discord.utils.remove_markdown(message)
        
        webhook = None
        webhooks = await interaction.channel.webhooks()
        for w in webhooks:
            if w.name == "RumiaFake":
                webhook = w
                break
        
        if not webhook:
            webhook = await interaction.channel.create_webhook(name="RumiaFake")
            
        await webhook.send(
            content=clean_content,
            username=target.display_name,
            avatar_url=target.display_avatar.url,
            allowed_mentions=discord.AllowedMentions.none() # メンション飛ばないように
        )
        
        await interaction.response.send_message("🥷", ephemeral=True)

    # --- おみくじ (設定機能付き) ---
    @app_commands.command(name="omikuji", description="運勢を占います")
    async def omikuji(self, interaction: discord.Interaction):
        # DBからカスタム設定を取得、なければデフォルト
        custom = await self.bot.db.fetch("SELECT * FROM omikuji_settings WHERE guild_id = $1", interaction.guild_id)
        
        if custom:
            # 確率に基づいて抽選 (簡易)
            choices = []
            for row in custom:
                choices.extend([row] * row['probability']) # 重み付け
            result = random.choice(choices)
            title = result['result_name']
            desc = result['description']
        else:
            results = [
                ("大吉", "最高の1日になるでしょう！"),
                ("中吉", "いいことあるかも。"),
                ("小吉", "普通が一番。"),
                ("凶", "足元に気をつけて。"),
                ("大凶", "家にいよう。")
            ]
            title, desc = random.choice(results)
            
        embed = discord.Embed(title=f"⛩️ おみくじ結果: **{title}**", description=desc, color=0xE91E63)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="topic", description="話題を提供 (700種類以上)")
    async def topic(self, interaction: discord.Interaction):
        # 本来はconstantsからインポート
        from utils.constants import TOPICS
        topic = random.choice(TOPICS)
        await interaction.response.send_message(f"💡 **話題**: {topic}")

async def setup(bot):
    await bot.add_cog(Entertainment(bot))
