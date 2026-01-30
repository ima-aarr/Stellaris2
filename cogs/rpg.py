import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

class RPG(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- ゲームコマンド群 ---
    game = app_commands.Group(name="game", description="ミニゲーム集")

    @game.command(name="emerald", description="エメラルドを使ったハイ＆ロー")
    async def emerald(self, interaction: discord.Interaction, bet: int):
        # 簡易的な賭けゲーム
        if bet <= 0: return
        # ユーザー資産チェックはEconomy Cogのメソッドを使うか、ここでDB直叩き
        # 簡略化のためDB直叩き
        current = await self.bot.db.fetchval("SELECT cash FROM users WHERE id = $1", interaction.user.id) or 0
        if current < bet:
            return await interaction.response.send_message("❌ 資金不足です。", ephemeral=True)
            
        # 勝率50%
        win = random.choice([True, False])
        if win:
            await self.bot.db.execute("UPDATE users SET cash = cash + $1 WHERE id = $2", bet, interaction.user.id)
            await interaction.response.send_message(f"💎 **勝利！** エメラルドが輝き、{bet} 獲得！")
        else:
            await self.bot.db.execute("UPDATE users SET cash = cash - $1 WHERE id = $2", bet, interaction.user.id)
            await interaction.response.send_message(f"💔 **敗北...** エメラルドは砕け散った... (-{bet})")

    @game.command(name="8ball", description="魔法の水晶で占う")
    async def eightball(self, interaction: discord.Interaction, question: str):
        answers = ["はい", "いいえ", "たぶん", "絶対にそうです", "やめたほうがいい", "見通しは明るい", "今は分からない"]
        await interaction.response.send_message(f"🔮 質問: {question}\n💬 答え: **{random.choice(answers)}**")

    @game.command(name="roll", description="ダイスを振る")
    async def roll(self, interaction: discord.Interaction, max: int = 100):
        await interaction.response.send_message(f"🎲 コロコロ... **{random.randint(1, max)}** (1-{max})")

    @game.command(name="lovecalc", description="恋愛度計算機")
    async def lovecalc(self, interaction: discord.Interaction, target: discord.Member):
        score = random.randint(0, 100)
        msg = f"💘 {interaction.user.name} と {target.name} の相性は... **{score}%** です！"
        if score > 90: msg += "\n結婚しちゃえよ！💍"
        elif score < 20: msg += "\n...諦めよう。"
        await interaction.response.send_message(msg)

    @game.command(name="shiritori", description="Botとしりとり")
    async def shiritori(self, interaction: discord.Interaction):
        # 簡易しりとりロジック
        await interaction.response.send_message("🍎 しりとり開始！「りんご」！ (次の言葉を入力してね)")
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
            
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            content = msg.content
            if content.startswith("ご"):
                await interaction.followup.send("🦍 ゴリラ！...あ、また「ら」だ！\n私の負けです...降参！")
            else:
                await interaction.followup.send(f"🤔 {content}...? うーん、難しい言葉知ってるね！今回は引き分け！")
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ 時間切れ！私の勝ち！")

    @game.command(name="bot-quest", description="Botからのクエスト")
    async def quest(self, interaction: discord.Interaction):
        quests = [
            "サーバー内で「こんにちは」と3人に挨拶する",
            "ボイスチャンネルに10分間滞在する",
            "おみくじで大吉を出す",
            "スロットで777を出す",
            "管理者に感謝の言葉を伝える"
        ]
        q = random.choice(quests)
        embed = discord.Embed(title="📜 本日のクエスト", description=f"**{q}**\n\n達成したら心の中でガッツポーズしてください。", color=0x3498DB)
        await interaction.response.send_message(embed=embed)

    # --- 国家戦略 (Nation) ---
    nation = app_commands.Group(name="nation", description="国家運営シミュレーション")

    @nation.command(name="create", description="国家を建国する")
    async def create_nation(self, interaction: discord.Interaction, name: str):
        exists = await self.bot.db.fetchval("SELECT 1 FROM nations WHERE user_id = $1", interaction.user.id)
        if exists:
            return await interaction.response.send_message("❌ すでに国家を持っています。", ephemeral=True)
            
        await self.bot.db.execute(
            "INSERT INTO nations (user_id, name) VALUES ($1, $2)",
            interaction.user.id, name
        )
        await interaction.response.send_message(f"🚩 **{name}** 建国！\n人口: 100人 | 資源: 1000 | 軍備: 0")

    @nation.command(name="status", description="国家のステータス")
    async def nation_status(self, interaction: discord.Interaction):
        data = await self.bot.db.fetchrow("SELECT * FROM nations WHERE user_id = $1", interaction.user.id)
        if not data:
            return await interaction.response.send_message("❌ 国家を持っていません。`/nation create` で建国してください。", ephemeral=True)
            
        embed = discord.Embed(title=f"🚩 {data['name']} の状況", color=0xE74C3C)
        embed.add_field(name="👥 人口", value=f"{data['population']:,} 人", inline=True)
        embed.add_field(name="🪵 資源", value=f"{data['resources']:,}", inline=True)
        embed.add_field(name="⚔️ 軍備", value=f"{data['army']:,}", inline=True)
        embed.add_field(name="💰 税率", value=f"{data['tax_rate']}%", inline=True)
        
        await interaction.response.send_message(embed=embed)

    @nation.command(name="collect", description="税金と資源を徴収 (1日1回)")
    async def collect(self, interaction: discord.Interaction):
        data = await self.bot.db.fetchrow("SELECT * FROM nations WHERE user_id = $1", interaction.user.id)
        if not data: return await interaction.response.send_message("❌ 建国してください", ephemeral=True)
        
        # 簡易計算
        money_gain = data['population'] * (data['tax_rate'] / 100) * 10
        resource_gain = data['population'] * 2
        
        # Userテーブルにお金追加、Nationテーブルに資源追加
        await self.bot.db.execute("UPDATE users SET cash = cash + $1 WHERE id = $2", int(money_gain), interaction.user.id)
        await self.bot.db.execute("UPDATE nations SET resources = resources + $1 WHERE user_id = $2", int(resource_gain), interaction.user.id)
        
        await interaction.response.send_message(f"📦 徴収完了！\n資金: +{int(money_gain)} | 資源: +{int(resource_gain)}")

async def setup(bot):
    await bot.add_cog(RPG(bot))
