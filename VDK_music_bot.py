"""
Copyright 2026 Konstantin Krasninskiy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os

import Secret

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents = intents)

# Disconnect if alone in voice channel
@bot.event
async def on_voice_state_update(member, before, after):
    for vc in bot.voice_clients:
        vc:discord.VoiceClient
        if (vc.is_connected() and (len(vc.channel.members) == 1)):
            #await vc.disconnect()
            pass

#Disconnect from voice channel in server
@bot.command(name = 'leave')
async def leave(ctx:commands.Context):
    """
    Leave voice channel
    """
    voice_client:discord.VoiceClient = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await ctx.send(f"Disconnected from {voice_client.channel.name}")
        await voice_client.disconnect()
    else:
        await ctx.send("Not connected to voice channel")

# Wait list
url_list = []

# Play callback
def play_final(delete_file:str,voice_client:discord.VoiceClient):
    os.remove(delete_file)
    async def disconnect(voice_client:discord.VoiceClient):
        await voice_client.disconnect()
    asyncio.run_coroutine_threadsafe(
        disconnect(voice_client),
        voice_client.loop
    )

# Download and start playing audio in voice channel
@bot.command(name = 'play')
async def play(ctx:commands.Context,url:str):
    """
    [url] play audio from youtube video, command author must be in voice channel
    """
    # If author is not connected to voice
    if ctx.author.voice == None:
        await ctx.send(f"Use !play command while in voice channel")
        return
    #Check if connected to any voice channel
    add2wait = False
    voice_client:discord.VoiceClient = ctx.message.guild.voice_client
    if voice_client == None:
        voice_client = await ctx.author.voice.channel.connect()
    elif voice_client.channel ==  ctx.author.voice.channel():
        add2wait = True
    else:
        await ctx.send(f"Currently playnd in another voice channel")
        return

    # Extract audio format data
    format = ""
    title = ""
    id = ""
    max_abr = 0
    try:
        with yt_dlp.YoutubeDL() as ydl:
            loop = asyncio.get_event_loop()
            video_info = await loop.run_in_executor(
                None,
                lambda: ydl.extract_info(url,download = False)
            )
            title = video_info.get('title')
            id = video_info.get("id")
            for f in video_info.get("formats"):
                if(f.get("acodec") != "none" and f.get("vcodec") == "none"):
                    if(f.get("abr") > max_abr):
                        format = f.get("audio_ext")
                        max_abr = f.get("abr")
    except:
        await ctx.send(f"Bad link format")
        return

    #Download audio
    with yt_dlp.YoutubeDL({'format': f"bestaudio/{format}",'outtmpl':f"audio/{id}.{format}"}) as ydl:
        await loop.run_in_executor(
            None,
            lambda:ydl.download([url])
        )

    #Start playing
    await ctx.send(f"Now playing {title} in {voice_client.channel.name}")
    voice_client.play(
        discord.FFmpegOpusAudio(source = f"audio/{id}.{format}", executable = "ffmpeg"),
        after=lambda e:play_final(f"audio/{id}.{format}",voice_client)
    )

# Pause audio in voice channel
@bot.command(name = 'pause')
async def pause(ctx:commands.Context):
    """
    Pause audio playing in voice channel, author must be in same voice channel
    """
    voice_client:discord.VoiceClient = ctx.message.guild.voice_client
    #Check if connected to any voice channel
    if voice_client == None:
        await ctx.send(f"Not connected to voice channel")
        return
    # Check if author in same voice channel
    if ctx.author.voice.channel == ctx.message.guild.voice_client.channel:
        await ctx.send(f"Paused playing in {voice_client.channel.name}")
        voice_client.pause()
    else:
        await ctx.send(f"You must be in same voice channel to use this command")

# Resume audio in voice channel
@bot.command(name = 'resume')
async def resume(ctx:commands.Context):
    """
    Resume audio playing in voice channel, author must be in same voice channel
    """
    voice_client:discord.VoiceClient = ctx.message.guild.voice_client
    #Check if connected to any voice channel
    if voice_client == None:
        await ctx.send(f"Not connected to voice channel")
        return
    # Check if author in same voice channel
    if ctx.author.voice.channel == ctx.message.guild.voice_client.channel:
        await ctx.send(f"Resumed playing in {voice_client.channel.name}")
        voice_client.resume()
    else:
        await ctx.send(f"You must be in same voice channel to use this command")

# Check are bot still alive
@bot.command(name = 'ping')
async def ping(ctx:commands.Context):
    """
    Show bot latency in seconds
    """
    await ctx.send(f"Ping {bot.latency:.3} s")

bot.run(Secret.DISCORD_API_KEY)