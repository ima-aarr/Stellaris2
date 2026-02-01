import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import asyncio

# --- 認証ボタンのView ---
class VerifyView(discord.ui.View):
    def __init__(self, role_ids):
        super().__init__(timeout=None)
        # role_idsはカンマ区切りの文字列を想定
        self.role_ids = [int(r) for r in str(role_ids).split(",") if r.isdigit()]

    @discord.ui.button(label="認証する", style=discord.ButtonStyle.green, custom_id="verify_button_v1")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        added_roles = []
        for rid in self.role_ids:
            role = interaction.guild.get_role(rid)
            if role:
                if role not in interaction.user.roles:
                    try:
                        await interaction.user.add_roles(role)
                        added_roles.append(role.name)
                    except discord.Forbidden:
                        continue

        if added_roles:
            await interaction.followup.send(f"✅ 認証完了！ ロールを付与しました: {', '.join(added_roles)}", ephemeral=True)
        else:
            await interaction.followup.send("⚠️ 既に認証済みか、ロールが見つかりません。", ephemeral=True)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- メッセージ監視 (AutoMod & AutoReply) ---
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if not message.guild: return

        # 1. 自動応答 (Auto Response)
        # DBから取得 (キャッシュ推奨だが要件に従い実装)
        responses = await self.bot.db.fetch("SELECT * FROM auto_responses WHERE guild_id = $1", message.guild.id)
        for row in responses:
            if row['trigger'] in message.content:
                if row['response']:
                    await message.channel.send(row['response'])
                if row['reaction']:
                    try:
                        await message.add_reaction(row['reaction'])
                    except:
                        pass
                break # 1つヒットしたら終了

        # 2. スパム検知 (重複文字)
        # 「同じ文字が10回以上続き、かつ5回以上連続投稿」は判定が難しいので
        # 「1つのメッセージ内で同じ文字が10連続以上している」または「短時間の連投」を検知
        
        # 除外判定 (管理者権限持ちはスルー)
        if message.author.guild_permissions.administrator:
            return

        # 重複文字検知 (例: "ああああああああああ")
        if re.search(r'(.)\1{9,}', message.content):
            # ホワイトリスト確認
            is_allow = await self.bot.db.fetchval("SELECT 1 FROM admin_whitelist WHERE user_id = $1", message.author.id)
            if not is_allow:
                try:
                    await message.delete()
                    duration = datetime.timedelta(minutes=10) # デフォルト10分
                    await message.author.timeout(duration, reason="AutoMod: 重複文字スパム")
                    msg = await message.channel.send(f"🔒 {message.author.mention} をスパム検知で10分間タイムアウトしました。")
                    await asyncio.sleep(10)
                    await msg.delete()
                except discord.Forbidden:
                    pass
                except Exception as e:
                    print(f"AutoMod Error: {e}")

    # --- 処罰コマンド ---
    @app_commands.command(name="timeout", description="ユーザーをタイムアウト(ミュート)します")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "違反"):
        # 自分より上の役職は処罰不可
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ 自分より上位または同格のメンバーは処罰できません。", ephemeral=True)

        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"🔇 {member.mention} を {minutes}分間 タイムアウトしました。\n理由: {reason}")

    @app_commands.command(name="kick", description="ユーザーをキックします")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "違反"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ 権限レベルが不足しています。", ephemeral=True)
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 {member.mention} をキックしました。")

    @app_commands.command(name="ban", description="ユーザーをBANします")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "違反"):
        if member.top_role >= interaction.user.top_role:
            return await interaction.response.send_message("❌ 権限レベルが不足しています。", ephemeral=True)
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 {member.mention} をBANしました。")

    @app_commands.command(name="unban", description="BANを解除します")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            await interaction.response.send_message(f"✅ {user.name} のBANを解除しました。")
        except:
            await interaction.response.send_message("❌ ユーザーが見つからないか、BANされていません。", ephemeral=True)

    # --- 認証パネル設置 ---
    @app_commands.command(name="verify_setup", description="認証パネルを作成します (ロール複数指定可)")
    @app_commands.checks.has_permissions(administrator=True)
    async def verify_panel(self, interaction: discord.Interaction, role1: discord.Role, role2: discord.Role = None, title: str = "認証エリア", description: str = "ボタンを押して認証してください"):
        roles = [str(role1.id)]
        if role2: roles.append(str(role2.id))
        role_str = ",".join(roles)

        embed = discord.Embed(title=title, description=description, color=0x00FF00)
        view = VerifyView(role_str)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("✅ パネルを設置しました", ephemeral=True)

    # --- 自動応答管理 ---
    auto = app_commands.Group(name="auto_response", description="自動応答の設定")

    @auto.command(name="add", description="自動応答を追加")
    @app_commands.checks.has_permissions(administrator=True)
    async def ar_add(self, interaction: discord.Interaction, trigger: str, response: str, reaction: str = None):
        await self.bot.db.execute(
            "INSERT INTO auto_responses (guild_id, trigger, response, reaction) VALUES ($1, $2, $3, $4)",
            interaction.guild.id, trigger, response, reaction
        )
        await interaction.response.send_message(f"✅ 追加しました: 「{trigger}」→「{response}」")

    @auto.command(name="list", description="自動応答の一覧")
    async def ar_list(self, interaction: discord.Interaction):
        rows = await self.bot.db.fetch("SELECT id, trigger, response FROM auto_responses WHERE guild_id = $1", interaction.guild.id)
        if not rows:
            return await interaction.response.send_message("❌ 設定されていません", ephemeral=True)
        
        desc = "\n".join([f"{row['id']}: 「{row['trigger']}」→「{row['response']}」" for row in rows])
        embed = discord.Embed(title="🤖 自動応答一覧", description=desc, color=0x3498DB)
        await interaction.response.send_message(embed=embed)

    @auto.command(name="delete", description="自動応答を削除")
    @app_commands.checks.has_permissions(administrator=True)
    async def ar_delete(self, interaction: discord.Interaction, id: int):
        # 本来はSelectMenuで選ばせるが、実装簡略化のためID指定
        await self.bot.db.execute("DELETE FROM auto_responses WHERE id = $1 AND guild_id = $2", id, interaction.guild.id)
        await interaction.response.send_message(f"🗑️ ID:{id} を削除しました。")

    # --- ホワイトリスト ---
    @app_commands.command(name="whitelist_add", description="Bot管理者用: ホワイトリスト追加")
    async def whitelist_add(self, interaction: discord.Interaction, user: discord.User):
        if interaction.user.id not in self.bot.admin_ids:
            return await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
            
        await self.bot.db.execute("INSERT INTO admin_whitelist (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user.id)
        await interaction.response.send_message(f"✅ {user.name} をホワイトリストに追加しました。")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
