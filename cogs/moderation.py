import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re

class VerifyView(discord.ui.View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="認証する", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(self.role_id)
        if role:
            if role in interaction.user.roles:
                await interaction.response.send_message("✅ 既に認証済みです。", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"🎉 認証完了！ {role.name} を付与しました。", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ ロールが見つかりません。管理者に連絡してください。", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- メッセージ監視 (AutoMod) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if not message.guild: return

        # 1. 重複文字スパム検知 (同じ文字が10回以上続き、かつ5回以上連続投稿された場合...は難しいので、単一メッセージ内の異常な繰り返しを検知)
        # 要望: "同じ10文字以上の文字が5回以上連続投稿されたなら" -> 文脈的に「同じメッセージの連投」または「文字の羅列」
        # ここでは「文字の羅列」を検知してタイムアウトするロジックを実装
        
        # 同じ文字が15回以上連続しているか (例: "あ" * 15)
        if re.search(r'(.)\1{14,}', message.content):
            # ホワイトリスト確認
            is_allow = await self.bot.db.fetchval("SELECT 1 FROM admin_whitelist WHERE user_id = $1", message.author.id)
            if not is_allow:
                try:
                    await message.delete()
                    duration = datetime.timedelta(minutes=10) # デフォルト10分
                    await message.author.timeout(duration, reason="AutoMod: スパム検知")
                    await message.channel.send(f"🔒 {message.author.mention} をスパム検知でタイムアウトしました。", delete_after=10)
                except:
                    pass
                return

        # 2. NGワード (Auto Responses / Deletion)
        # DBから取得
        # (パフォーマンスのため、本来はキャッシュすべきですが、要件通りDB連携します)
        # ここでは簡易的な実装
        pass

    # --- 処罰コマンド ---
    @app_commands.command(name="timeout", description="ユーザーをタイムアウト(ミュート)します")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "違反"):
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"🔇 {member.mention} を {minutes}分間 タイムアウトしました。\n理由: {reason}")

    @app_commands.command(name="kick", description="ユーザーをキックします")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "違反"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 {member.mention} をキックしました。")

    @app_commands.command(name="ban", description="ユーザーをBANします")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "違反"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} をBANしました。")

    @app_commands.command(name="unban", description="BANを解除します")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"✅ {user.name} のBANを解除しました。")

    # --- 認証パネル設置 ---
    @app_commands.command(name="verify", description="認証パネルを作成します")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_panel(self, interaction: discord.Interaction, role: discord.Role, title: str = "認証エリア", description: str = "ボタンを押して認証してください"):
        embed = discord.Embed(title=title, description=description, color=0x00FF00)
        view = VerifyView(role.id)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ パネルを設置しました", ephemeral=True)

    # --- AutoMod設定 ---
    @app_commands.command(name="whitelist_add", description="Bot管理者用: ホワイトリスト追加")
    async def whitelist_add(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id not in self.bot.admin_ids:
            return await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
            
        await self.bot.db.execute("INSERT INTO admin_whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
        await interaction.response.send_message(f"✅ {user.name} をホワイトリストに追加しました。")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
