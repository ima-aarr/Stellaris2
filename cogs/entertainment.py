import discord
from discord import app_commands
from discord.ext import commands
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import asyncio
import aiohttp
from utils.constants import TOPICS, get_random_topic # パート1の定数を利用

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
        
        # フォント読み込み (fontsフォルダから。なければデフォルト)
        try:
            font_path = "fonts/NotoSansJP-Bold.ttf"
            font = ImageFont.truetype(font_path, 50)
            name_font = ImageFont.truetype(font_path, 40)
            logo_font = ImageFont.truetype(font_path, 20)
        except OSError:
            # フォールバック
            font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            logo_font = ImageFont.load_default()

        # アバター取得
        avatar_url = user.display_avatar.url
        try:
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
        except Exception as e:
            print(f"Image Error: {e}")
            return await interaction.followup.send("❌ 画像処理エラーが発生しました")

        # テキスト描画 (簡易折り返し)
        max_chars_per_line = 25
        wrapped_text = ""
        for i in range(0, len(text), max_chars_per_line):
            wrapped_text += text[i:i+max_chars_per_line] + "\n"
            
        # テキスト位置
        draw.text((380, 100), wrapped_text, font=font, fill=(255, 255, 255))
        draw.text((380, 50), f"- {user.display_name}", font=name_font, fill=(150, 150, 150))
        
        # ロゴ (右下)
        draw.text((WIDTH - 150, HEIGHT - 40), "Rumia Bot", font=logo_font, fill=(100, 100, 100))

        # 送信
        with io.BytesIO() as image_binary:
            img.save(image_binary, 'PNG')
            image_binary.seek(0)
            await interaction.followup.send(file=discord.File(fp=image_binary, filename='quote.png'))

    # --- なりすまし (Fake) ---
    @app_commands.command(name="fake", description="指定したユーザーになりすまして発言(Webhook)")
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def fake(self, interaction: discord.Interaction, target: discord.Member, message: str):
        # メンション無効化 (悪用防止)
        clean_content = discord.utils.remove_markdown(message)
        clean_content = clean_content.replace("@", "@\u200b") # Zero width space
        
        # Webhook取得または作成
        webhook = None
        try:
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
                allowed_mentions=discord.AllowedMentions.none()
            )
            await interaction.response.send_message("🥷", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ Webhookを作成する権限がありません。", ephemeral=True)

    # --- おみくじ (設定機能付き) ---
    omikuji_group = app_commands.Group(name="omikuji", description="おみくじ関連")

    @omikuji_group.command(name="play", description="運勢を占います")
    async def play_omikuji(self, interaction: discord.Interaction):
        # DBからカスタム設定を取得、なければデフォルト
        custom = await self.bot.db.fetch("SELECT * FROM omikuji_settings WHERE guild_id = $1", interaction.guild_id)
        
        if custom:
            # 確率に基づいて抽選 (重み付け抽選)
            choices = []
            weights = []
            for row in custom:
                choices.append(row)
                weights.append(row['probability'])
            
            if not choices:
                result = {"result_name": "吉", "description": "普通が一番"}
            else:
                result = random.choices(choices, weights=weights, k=1)[0]
                
            title = result['result_name']
            desc = result['description']
        else:
            results = [
                ("大吉", "最高の1日になるでしょう！"),
                ("中吉", "いいことあるかも。"),
                ("吉", "普通が一番。"),
                ("凶", "足元に気をつけて。"),
                ("大凶", "家にいよう。")
            ]
            title, desc = random.choice(results)
        
        # 「今日話しかけるべき人」
        member = random.choice(interaction.guild.members)
        
        embed = discord.Embed(title=f"⛩️ おみくじ結果: **{title}**", description=desc, color=0xE91E63)
        embed.add_field(name="ラッキーパーソン", value=f"{member.mention} に話しかけてみよう！")
        await interaction.response.send_message(embed=embed)

    @omikuji_group.command(name="add", description="おみくじの結果を追加")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_omikuji(self, interaction: discord.Interaction, name: str, description: str, probability: int):
        await self.bot.db.execute(
            "INSERT INTO omikuji_settings (guild_id, result_name, description, probability) VALUES ($1, $2, $3, $4)",
            interaction.guild.id, name, description, probability
        )
        await interaction.response.send_message(f"✅ 追加しました: {name} (重み: {probability})")

    # --- 話題提供 ---
    @app_commands.command(name="topic", description="話題を提供 (700種類以上)")
    async def topic(self, interaction: discord.Interaction):
        # utils/constants.py の関数を使用
        topic = get_random_topic()
        await interaction.response.send_message(f"💡 **話題**: {topic}")

async def setup(bot):
    await bot.add_cog(Entertainment(bot))
