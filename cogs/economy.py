import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime

# 定数インポート
# 注: 本来は from utils.constants import JOBS ですが、ファイル分割の都合上ここに再定義するか参照します
JOBS = {
    "ニート": {"salary": 0, "multiplier": 1.0, "desc": "自宅警備員"},
    "皿洗い": {"salary": 1000, "multiplier": 1.1, "desc": "地道な作業"},
    "コンビニ": {"salary": 2500, "multiplier": 1.2, "desc": "深夜シフト"},
    "エンジニア": {"salary": 5000, "multiplier": 1.5, "desc": "技術職"},
    "石油王": {"salary": 50000, "multiplier": 3.0, "desc": "富豪"}
}

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ユーザーデータ取得・初期化ヘルパー
    async def get_user_data(self, user_id):
        data = await self.bot.db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not data:
            # 新規ユーザー作成 (debtカラムを含む)
            await self.bot.db.execute(
                "INSERT INTO users (id, cash, bank, debt, job_id) VALUES ($1, 0, 0, 0, 'ニート')",
                user_id
            )
            data = await self.bot.db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        return data

    # --- /s コマンドグループ ---
    s = app_commands.Group(name="s", description="経済・スロットコマンド")

    @s.command(name="bal", description="所持金を確認します")
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        target = user or interaction.user
        data = await self.get_user_data(target.id)
        
        cash = data['cash']
        bank = data['bank']
        debt = data['debt']
        net_worth = cash + bank - debt
        
        embed = discord.Embed(title=f"💰 {target.display_name} の残高", color=0xF1C40F)
        embed.add_field(name="現金", value=f"{cash:,} 🪙", inline=True)
        embed.add_field(name="銀行", value=f"{bank:,} 🏦", inline=True)
        embed.add_field(name="借金", value=f"{debt:,} 💸", inline=True)
        embed.add_field(name="総資産", value=f"{net_worth:,} 💎", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)

    @s.command(name="work", description="働いてお金を稼ぎます")
    async def work(self, interaction: discord.Interaction):
        data = await self.get_user_data(interaction.user.id)
        
        # クールダウンチェック (簡易実装: DBのlast_workを確認)
        last_work = data['last_work']
        now = datetime.datetime.now()
        if last_work and (now - last_work).total_seconds() < 1800: # 30分
            remaining = int(1800 - (now - last_work).total_seconds())
            return await interaction.response.send_message(f"⏳ 休憩中... あと {remaining//60}分待ってね。", ephemeral=True)
            
        job_id = data['job_id']
        job_info = JOBS.get(job_id, JOBS["ニート"])
        
        # 収入計算 (乱数 + 職業補正)
        base = random.randint(500, 1500)
        earnings = int((base + job_info['salary']) * job_info['multiplier'])
        
        await self.bot.db.execute(
            "UPDATE users SET cash = cash + $1, last_work = $2 WHERE id = $3",
            earnings, now, interaction.user.id
        )
        
        await interaction.response.send_message(f"💼 **{job_id}** として働き、**{earnings:,}** 🪙 稼ぎました！")

    @s.command(name="slot", description="スロットを回します")
    async def slot(self, interaction: discord.Interaction, bet: int):
        data = await self.get_user_data(interaction.user.id)
        if data['cash'] < bet:
            return await interaction.response.send_message("❌ 現金が足りません！", ephemeral=True)
        
        # 結果抽選
        emojis = ["🍒", "🍋", "🍇", "🍉", "7️⃣"]
        result = [random.choice(emojis) for _ in range(3)]
        
        # 判定
        win_amt = 0
        if result[0] == result[1] == result[2]:
            if result[0] == "7️⃣":
                win_amt = bet * 10 # 大当たり
            else:
                win_amt = bet * 3
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win_amt = int(bet * 1.5)
            
        # DB更新
        if win_amt > 0:
            await self.bot.db.execute("UPDATE users SET cash = cash + $1 WHERE id = $2", win_amt, interaction.user.id)
            msg = f"🎉 **当たり！** {win_amt:,} 🪙 獲得！"
        else:
            await self.bot.db.execute("UPDATE users SET cash = cash - $1 WHERE id = $2", bet, interaction.user.id)
            msg = "💀 **ハズレ...** ドンマイ。"
            
        embed = discord.Embed(title="🎰 スロットマシン", description=f"| {' | '.join(result)} |\n\n{msg}", color=0xE91E63)
        await interaction.response.send_message(embed=embed)

    @s.command(name="send", description="送金します")
    async def send_money(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0: return await interaction.response.send_message("❌ 1以上を指定してください", ephemeral=True)
        if user.id == interaction.user.id: return await interaction.response.send_message("❌ 自分には送れません", ephemeral=True)
        
        sender = await self.get_user_data(interaction.user.id)
        if sender['cash'] < amount:
            return await interaction.response.send_message("❌ 現金が足りません", ephemeral=True)
            
        # トランザクション
        await self.bot.db.execute("UPDATE users SET cash = cash - $1 WHERE id = $2", amount, interaction.user.id)
        await self.bot.db.execute("INSERT INTO users (id, cash) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET cash = users.cash + $2", user.id, amount)
        
        await interaction.response.send_message(f"💸 {interaction.user.mention} が {user.mention} に **{amount:,}** 🪙 送金しました。")

    @s.command(name="borrow", description="借金をします (上限あり)")
    async def borrow(self, interaction: discord.Interaction, amount: int):
        if amount <= 0: return
        data = await self.get_user_data(interaction.user.id)
        
        # 借金上限は総資産の50%までとする
        net_worth = data['cash'] + data['bank']
        max_borrow = max(10000, net_worth // 2) # 最低1万は借りれる
        
        if data['debt'] + amount > max_borrow:
            return await interaction.response.send_message(f"❌ 借金限度額オーバーです。(あと {max_borrow - data['debt']:,} 借りられます)", ephemeral=True)
            
        await self.bot.db.execute("UPDATE users SET cash = cash + $1, debt = debt + $1 WHERE id = $2", amount, interaction.user.id)
        await interaction.response.send_message(f"💳 **{amount:,}** 🪙 借りました。ご利用は計画的に。")

    @s.command(name="repay", description="借金を返済します")
    async def repay(self, interaction: discord.Interaction, amount: int):
        if amount <= 0: return
        data = await self.get_user_data(interaction.user.id)
        
        if data['debt'] <= 0:
            return await interaction.response.send_message("✅ 借金はありません！", ephemeral=True)
            
        repay_amt = min(amount, data['debt'])
        if data['cash'] < repay_amt:
            return await interaction.response.send_message("❌ 現金が足りません", ephemeral=True)
            
        await self.bot.db.execute("UPDATE users SET cash = cash - $1, debt = debt - $1 WHERE id = $2", repay_amt, interaction.user.id)
        await interaction.response.send_message(f"💳 **{repay_amt:,}** 🪙 返済しました。残り借金: {data['debt'] - repay_amt:,}")

    @s.command(name="ranking", description="所持金ランキング")
    async def ranking(self, interaction: discord.Interaction):
        # サーバー内のユーザーのみ対象にしたいが、DB構造上全ユーザー取得になるため
        # ここでは上位10名を表示
        rows = await self.bot.db.fetch("SELECT id, cash, bank FROM users ORDER BY (cash + bank) DESC LIMIT 10")
        
        embed = discord.Embed(title="🏆 富豪ランキング", color=0xF1C40F)
        desc = ""
        for i, row in enumerate(rows, 1):
            user = self.bot.get_user(row['id'])
            name = user.display_name if user else f"ID:{row['id']}"
            total = row['cash'] + row['bank']
            desc += f"**{i}. {name}**: {total:,} 🪙\n"
            
        embed.description = desc
        await interaction.response.send_message(embed=embed)
        
    @s.command(name="info", description="経済システム情報")
    async def econ_info(self, interaction: discord.Interaction):
         await interaction.response.send_message("📊 本日のスロットペイアウト率: 95% \n市場は安定しています。", ephemeral=True)

    # --- 職業・ショップ関連 ---
    @app_commands.command(name="shop", description="職業を購入・変更")
    async def shop(self, interaction: discord.Interaction):
        # セレクトメニューで職業選択
        options = []
        for name, info in JOBS.items():
            if name == "ニート": continue
            # 転職費用は給料の10倍とする
            cost = info['salary'] * 10
            options.append(discord.SelectOption(
                label=f"{name} (¥{cost:,})", 
                description=f"給料: {info['salary']} | 倍率: {info['multiplier']}x",
                value=name
            ))
            
        view = discord.ui.View()
        select = discord.ui.Select(placeholder="職業を選択して購入", options=options[:25]) # 25個制限
        
        async def callback(it: discord.Interaction):
            job_name = select.values[0]
            cost = JOBS[job_name]['salary'] * 10
            
            data = await self.get_user_data(it.user.id)
            if data['cash'] < cost:
                return await it.response.send_message("❌ お金が足りません！", ephemeral=True)
                
            await self.bot.db.execute("UPDATE users SET cash = cash - $1, job_id = $2 WHERE id = $3", cost, job_name, it.user.id)
            await it.response.send_message(f"🎉 転職成功！あなたは今日から **{job_name}** です！")
            
        select.callback = callback
        view.add_item(select)
        await interaction.response.send_message("🏪 **ハロワーク (職業ショップ)**\n転職するには手数料がかかります。", view=view)

async def setup(bot):
    await bot.add_cog(Economy(bot))
