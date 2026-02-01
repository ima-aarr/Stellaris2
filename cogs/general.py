import discord
from discord import app_commands
from discord.ext import commands
import datetime
import time
import platform
import psutil

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    # --- 情報系コマンド ---
    @app_commands.command(name="ping", description="Botの応答速度・稼働状況を確認")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! {latency}ms")

    @app_commands.command(name="info", description="Rumia Botの詳細情報を表示")
    async def info(self, interaction: discord.Interaction):
        uptime_seconds = int(time.time() - self.start_time)
        uptime = str(datetime.timedelta(seconds=uptime_seconds))
        
        server_count = len(self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds)
        command_count = len(list(self.bot.tree.walk_commands()))

        # メモリ使用率など
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024 # MB

        embed = discord.Embed(title="💜 Rumia Bot について", color=0x9B59B6)
        embed.description = (
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "｜Discordサーバーの運営を安定かつ安全に\n"
            "｜行うことを目的として開発された多機能Botです。\n"
            "｜初心者から管理者まで安心して使えるBotを目指しています。\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        embed.add_field(name="｜主な機能", value="｜モデレーション｜経済｜RPG｜音楽｜便利機能", inline=False)
        embed.add_field(name="｜Bot統計", value=f"｜サーバー数: {server_count}｜ユーザー数: {user_count}｜コマンド数: {command_count}", inline=False)
        embed.add_field(name="｜稼働情報", value=f"｜稼働時間: {uptime}｜Mem: {memory_usage:.1f}MB\n｜Python: {platform.python_version()}｜discord.py: {discord.__version__}", inline=False)
        embed.add_field(name="｜技術仕様", value="｜Discord公式API準拠｜全コマンド安全応答処理実装｜安定動作を最優先設計", inline=False)
        
        embed.add_field(name="｜リンク", value="不具合報告: `/bot_report` | ヘルプ: `/help`", inline=False)
        
        embed.set_footer(text=f"Bot ID: {self.bot.user.id} | リクエスト時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bot_report", description="開発者への要望・不具合報告")
    async def report(self, interaction: discord.Interaction, content: str):
        # 簡易的にログに出力（本来はWebhookで開発者サーバーに飛ばすのがベスト）
        print(f"REPORT from {interaction.user}: {content}")
        await interaction.response.send_message("✅ 報告を受け付けました。ありがとうございます！", ephemeral=True)

    @app_commands.command(name="admin_server_list", description="【運営用】参加サーバーTop30")
    async def server_list(self, interaction: discord.Interaction):
        # 環境変数のADMIN_IDSに含まれる人のみ実行可能
        if interaction.user.id not in self.bot.admin_ids:
            return await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        # 人数順にソート
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)[:30]
        
        desc = ""
        for i, g in enumerate(guilds, 1):
            invite_url = "権限不足"
            # 招待リンク作成を試みる
            try:
                # 招待権限のあるチャンネルを探す
                for channel in g.text_channels:
                    if channel.permissions_for(g.me).create_instant_invite:
                        invite = await channel.create_invite(max_age=300, max_uses=1)
                        invite_url = f"[招待]({invite.url})"
                        break
            except:
                pass
            
            desc += f"**{i}. {g.name}** ({g.member_count}人) - {invite_url}\nID: {g.id}\n"
            
        embed = discord.Embed(title="🏢 参加サーバー Top 30", description=desc, color=0x9B59B6)
        await interaction.followup.send(embed=embed)

    # --- 便利機能 ---
    @app_commands.command(name="avatar", description="ユーザーのアイコンを表示")
    async def avatar(self, interaction: discord.Interaction, user: discord.User = None):
        target = user or interaction.user
        embed = discord.Embed(title=f"{target.display_name} のアイコン", color=0x9B59B6)
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="check", description="サーバー過疎度チェック (詳細版)")
    async def check(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        limit_date = datetime.datetime.now() - datetime.timedelta(days=2)
        total_msg = 0
        channel_stats = {}
        active_channels = 0
        
        # 過去2日間のメッセージを集計
        for ch in interaction.guild.text_channels:
            # Botが読めるチャンネルのみ
            if not ch.permissions_for(interaction.guild.me).read_message_history:
                continue
                
            try:
                count = 0
                async for _ in ch.history(after=limit_date, limit=None): # limit=Noneだと重いので適宜制限推奨だが、要望通り正確に
                    count += 1
                
                if count > 0:
                    total_msg += count
                    channel_stats[ch.name] = count
                    active_channels += 1
            except discord.Forbidden:
                continue
            except Exception:
                continue
            
        # レベル判定
        if total_msg > 500:
            level, emoji, status = 5, "🟩", "超活発！"
        elif total_msg > 200:
            level, emoji, status = 4, "🟩", "活発なサーバー！"
        elif total_msg > 50:
            level, emoji, status = 3, "🟨", "普通"
        elif total_msg > 10:
            level, emoji, status = 2, "🟥", "静かかも..."
        else:
            level, emoji, status = 1, "⬛", "過疎状態..."

        embed = discord.Embed(title=f"📊 {status} (レベル{level})", color=0x9B59B6)
        
        # 統計情報
        desc = (
            f"**統計情報**\n"
            f"過疎りレベル: {emoji} レベル {level}\n"
            f"合計メッセージ: {total_msg} 件\n"
            f"調査チャンネル: {len(interaction.guild.text_channels)} チャンネル\n"
            f"調査期間: 過去2日間\n\n"
            f"**上位チャンネル**\n"
        )
        
        # 上位チャンネル表示
        sorted_chs = sorted(channel_stats.items(), key=lambda x: x[1], reverse=True)
        top_chs = sorted_chs[:5]
        for name, count in top_chs:
            desc += f"• {name}: {count}件\n"
            
        desc += "\n**調査チャンネル一覧**\n"
        for name, count in sorted_chs[:15]: # 長くなりすぎないようにTop15まで
            desc += f"• {name} - {count}件\n"
            
        embed.description = desc
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="embed", description="埋め込みメッセージ作成 (色は紫固定)")
    async def make_embed(self, interaction: discord.Interaction, title: str, description: str):
        embed = discord.Embed(title=title, description=description, color=0x9B59B6)
        embed.set_footer(text=f"Created by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="color_code", description="ロールの色コードを表示")
    async def color_code(self, interaction: discord.Interaction, role: discord.Role):
        color = str(role.color).upper()
        await interaction.response.send_message(f"🎨 {role.name} のカラーコード: `{color}`")

async def setup(bot):
    await bot.add_cog(General(bot))
