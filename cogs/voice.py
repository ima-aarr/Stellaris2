import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import os

# YouTube DL設定
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    # クッキーファイル指定 (main.pyで生成されたファイルを使用)
    'cookiefile': 'cookies.txt' 
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.volume = 0.5 # デフォルト音量 50%

    def check_voice(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return "❌ 先にボイスチャンネルに参加してください。"
        return None

    @app_commands.command(name="join", description="VCに参加")
    async def join(self, interaction: discord.Interaction):
        err = self.check_voice(interaction)
        if err: return await interaction.response.send_message(err, ephemeral=True)
        
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()
        await interaction.response.send_message(f"🔊 {channel.name} に接続しました。")

    @app_commands.command(name="leave", description="VCから退出")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 退出しました。")
        else:
            await interaction.response.send_message("❌ VCに参加していません。", ephemeral=True)

    @app_commands.command(name="music_play", description="音楽を再生 (YouTube対応・CookieFix済み)")
    async def play(self, interaction: discord.Interaction, query: str):
        err = self.check_voice(interaction)
        if err: return await interaction.response.send_message(err, ephemeral=True)
        
        await interaction.response.defer()
        
        # VC接続確認
        if not interaction.guild.voice_client:
            try:
                await interaction.user.voice.channel.connect()
            except Exception as e:
                return await interaction.followup.send(f"❌ 接続エラー: {e}")
            
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.stop() # 割り込み再生

        try:
            # yt-dlpでURL抽出
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)
                # 検索結果の場合の処理
                if 'entries' in info:
                    info = info['entries'][0]
                    
                url2 = info['url']
                title = info.get('title', 'Unknown')
                
                # 音源ソース作成
                source = await discord.FFmpegOpusAudio.from_probe(
                    url2,
                    **FFMPEG_OPTIONS
                )
                
                # 音量調整用トランスフォーマー
                vc.play(discord.PCMVolumeTransformer(source, volume=self.volume))
                
                await interaction.followup.send(f"🎵 再生中: **{title}**")
                
        except Exception as e:
            # エラーの詳細を表示
            await interaction.followup.send(f"❌ 再生エラー: {e}\n(Cookie設定を確認してください)")

    @app_commands.command(name="music_volume", description="音量を変更 (0-100)")
    async def volume(self, interaction: discord.Interaction, level: int):
        if not 0 <= level <= 100:
            return await interaction.response.send_message("❌ 0から100の間で指定してください", ephemeral=True)
            
        self.volume = level / 100
        if interaction.guild.voice_client and interaction.guild.voice_client.source:
            interaction.guild.voice_client.source.volume = self.volume
            
        await interaction.response.send_message(f"🔊 音量を {level}% に設定しました。")

    @app_commands.command(name="music_stop", description="音楽を停止")
    async def stop(self, interaction: discord.Interaction):
        if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏹️ 停止しました。")
        else:
            await interaction.response.send_message("❌ 再生していません。", ephemeral=True)
            
    # --- 自動切断機能 ---
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Botがいるチャンネルで、Botひとりぼっちになったら抜ける
        if not member.guild.voice_client: return
        vc = member.guild.voice_client
        if vc.channel and len(vc.channel.members) == 1: # Botだけ
            await asyncio.sleep(60) # 1分待つ
            if len(vc.channel.members) == 1:
                await vc.disconnect()

async def setup(bot):
    await bot.add_cog(Voice(bot))
