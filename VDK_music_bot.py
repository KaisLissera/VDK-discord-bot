import discord
from discord.ext import commands
import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents = intents)

global CurrentVoice

@bot.event
async def on_ready():
    print("VDKMusicBot is connected")

@bot.event
async def on_voice_state_update(member, before, after):
    voice = discord.utils.get(bot.voice_clients, guild=member.guild)
    if voice and voice.is_connected():
        if len(voice.channel.members) == 1:
            await voice.disconnect()

@bot.command(name = 'join')
async def join(ctx):
    voice = ctx.author.voice
    if not voice:
        await ctx.send("You must be in voice channel to use this command")
    else:
        global CurrentVoice
        CurrentVoice = voice
        await voice.channel.connect()
        await ctx.send("Joined voice channel")

@bot.command(name = 'leave')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("Bot is not connected to a voice channel.")

@bot.command(name = 'play')
async def play(ctx, url):
    voice = ctx.author.voice
    vc = await voice.channel.connect()

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        video_info = ydl.extract_info(url, download = False)
        title = video_info.get("title", "YouTube video")
        file_path = ydl.prepare_filename(video_info)
    file_path = file_path.replace(".webm", ".mp3")
    print(file_path)

    await ctx.send("Now playing " + title)

    vc.play(discord.FFmpegPCMAudio(executable = "ffmpeg.exe", source = file_path))

@bot.command(name = 'ping')
async def ping(ctx):
    await ctx.send(bot.latency)

bot.run('token')