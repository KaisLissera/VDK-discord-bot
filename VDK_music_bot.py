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
from datetime import timedelta

import Secret

#Get path to working directory
path_wd = os.getcwd()
# Path to save audio
path_audio = os.path.join(path_wd,"audio")

intents = discord.Intents.default()
intents.message_content = True
# Use ! as command prefix
bot = commands.Bot(command_prefix='!', intents = intents)

def yt_download_audio(url:str)->dict:
    output = {}
    id = ""
    ext = ""
    max_abr = 0
    try:
        # Extract audio formats
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url,download = False)
            output['title'] = info.get('title')
            id = info.get('id')
            for f in info.get("formats"):
                if(f.get("acodec") != "none" and f.get("vcodec") == "none"):
                    if(f.get("abr") > max_abr):
                        ext = f.get("audio_ext")
                        max_abr = f.get("abr")
        output['path'] = os.path.join(path_audio,f"{id}.{ext}")
        
        # Download audio
        options = {
            'quiet': True,
            'format': f"bestaudio/{format}",
            'outtmpl':output.get('path')
        }
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
    except:
        return {}
    return output

# Get first search results from youtube
def yt_search(query:str, max_results:int=5)->list[dict]:
    options = {
        "quiet": True,
        "extract_flat": True,
        "force_generic_extractor": False
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        try:
            search_query = f"ytsearch{max_results}:{query}"
            info:dict = ydl.extract_info(search_query, download=False)
            videos = []
            for entry in info["entries"]:
                entry:dict
                videos.append({
                        "title": entry.get("title"),
                        "channel": entry.get("channel"),
                        "url": entry.get("url"),
                        "duration": entry.get("duration", 0)
                    })
            return videos
        except:
            return []
        
# Format search results to printable format
def format_search_results(results:list[dict])->str:
    i = 1
    output = ""
    for item in results:
        str_duration = str(timedelta(seconds=item["duration"]))
        output += f"{i}. {item['channel']} {item['title']} {str_duration}\n"
        output += f"{item['url']}\n"
        output += "\n"
        i+=1
    return output

# Wait list
wait_list:list[dict] = []
def clean_queue(vc:discord.VoiceClient):
    """
    Delete audio files in wait list for voice client
    """
    for item in wait_list:
        ctx:commands.Context = item.get("ctx")
        if ctx.message.guild.voice_client == vc:
            try:
                os.remove(item.get("file"))
            except:
                pass

@bot.event
async def on_voice_state_update(member, before, after):
    """
    Disconnect from voice if alone
    """
    for vc in bot.voice_clients:
        vc:discord.VoiceClient
        if (vc.is_connected() and (len(vc.channel.members) == 1)):
            await vc.loop.run_in_executor(None,lambda:clean_queue(vc))
            await vc.disconnect()

@bot.command(name = 'leave')
async def leave(ctx:commands.Context):
    """
    Disconnect from voice channel, clear songs in queue
    """
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    if vc.is_connected():
        await vc.loop.run_in_executor(None,lambda:clean_queue(vc))
        await ctx.send(f"Disconnected from {vc.channel.name}")
        await vc.disconnect()
    else:
        await ctx.send("Not connected to voice channel")

def play_final(old_file:str,voice_client:discord.VoiceClient):
    """
    Callback for play coroutine, delete old audio, start playing next song or disconnect from voice if wait list is empty
    """
    # Disconnect from voice channel async
    async def disconnect(voice_client:discord.VoiceClient):
        await voice_client.disconnect()
    
    # Play audio in voice channel async
    async def play(ctx:commands.Context,voice_client:discord.VoiceClient,file:str,title:str):
        await ctx.send(f"Now playing {title} in {voice_client.channel.name}")
        voice_client.play(discord.FFmpegOpusAudio(source = file, executable = "ffmpeg"),after=lambda e:play_final(file,voice_client))
    
    #Delete old file
    try:
        os.remove(old_file)
    except:
        pass
    # Start playing next audio
    list_is_empty = True
    for item in wait_list:
        ctx:commands.Context = item.get("ctx")
        title:str = item.get("title")
        file:str = item.get("file")
        if ctx.message.guild.voice_client == voice_client:
            wait_list.remove(item)
            list_is_empty = False
            asyncio.run_coroutine_threadsafe(
                play(ctx,voice_client,file,title),
                voice_client.loop
            )
            break
    # Disconnect is queue is empty
    if list_is_empty:
        asyncio.run_coroutine_threadsafe(
            disconnect(voice_client),
            voice_client.loop
        )

@bot.command(name = 'play')
async def play(ctx:commands.Context,query:str):
    """
    Play audio from youtube video, command author must be in voice channel
    """
    # Check author is not connected to voice
    if ctx.author.voice == None:
        await ctx.send(f"Use !play command while in voice channel")
        return
    # Check if already connected to any voice channel in server
    add_audio_to_queue = False
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    if vc == None:
        vc = await ctx.author.voice.channel.connect()
    elif vc.channel ==  ctx.author.voice.channel:
        add_audio_to_queue = True
    else:
        await ctx.send(f"Currently playnd in another voice channel")
        return
    
    # Check if need make search first
    if query.find("/watch?") == -1:
        search_results = await vc.loop.run_in_executor(None,lambda:yt_search(query,1))
        url:str = search_results[0].get("url")
        if url.find("/watch?") == -1:
            await ctx.send(f"Can't find audio")
            return
    else:
        url = query

    # Download audio with url
    metadata = await vc.loop.run_in_executor(None,lambda:yt_download_audio(url))
    if metadata.get("title") == None:
        await ctx.send(f"Can't download audio")
        return

    #Add audio to queue
    if add_audio_to_queue:
        await ctx.send(f"{metadata.get('title')} added to queue")
        wait_list.append({"ctx":ctx,"title":metadata.get("title"),"file":metadata.get("path")})
        return
    #Start playing in vc
    await ctx.send(f"Now playing {metadata.get('title')} in {vc.channel.name}")
    vc.play(
        discord.FFmpegOpusAudio(source = metadata.get("path"), executable = "ffmpeg"),
        after=lambda e:play_final(metadata.get("path"),vc)
    )

@bot.command(name = "search")
async def search(ctx:commands.Context,query:str):
    """
    Search audio on youtube
    """
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    if vc == None:
        loop = asyncio.get_event_loop()
    else:
        loop = vc.loop
    search_results = await loop.run_in_executor(None,lambda:yt_search(query,5))
    url:str = search_results[0].get("url")
    if url.find("/watch?") == -1:
            await ctx.send(f"Can't find anything")
            return
    await ctx.send(format_search_results(search_results), suppress_embeds=True)

@bot.command(name = 'skip')
async def skip(ctx:commands.Context):
    """
    Skip audio playing in voice channel, author must be in same voice channel
    """
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    #Check if connected to any voice channel
    if vc == None:
        await ctx.send(f"Not connected to voice channel")
        return
    # Check if author in same voice channel
    if ctx.author.voice.channel == ctx.message.guild.voice_client.channel:
        await ctx.send(f"Skipped current audio in {vc.channel.name}")
        vc.stop()
        #vc.source = discord.FFmpegOpusAudio(source = os.path.join(path_wd,"silence.mp4"), executable = "ffmpeg")
    else:
        await ctx.send(f"You must be in same voice channel to use this command")

# Pause audio in voice channel
@bot.command(name = 'pause')
async def pause(ctx:commands.Context):
    """
    Pause audio playing in voice channel, author must be in same voice channel
    """
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    #Check if connected to any voice channel
    if vc == None:
        await ctx.send(f"Not connected to voice channel")
        return
    # Check if author in same voice channel
    if ctx.author.voice.channel == ctx.message.guild.voice_client.channel:
        await ctx.send(f"Paused playing in {vc.channel.name}")
        vc.pause()
    else:
        await ctx.send(f"You must be in same voice channel to use this command")

# Resume audio in voice channel
@bot.command(name = 'resume')
async def resume(ctx:commands.Context):
    """
    Resume audio playing in voice channel, author must be in same voice channel
    """
    vc:discord.VoiceClient = ctx.message.guild.voice_client
    #Check if connected to any voice channel
    if vc == None:
        await ctx.send(f"Not connected to voice channel")
        return
    # Check if author in same voice channel
    if ctx.author.voice.channel == ctx.message.guild.voice_client.channel:
        await ctx.send(f"Resumed playing in {vc.channel.name}")
        vc.resume()
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