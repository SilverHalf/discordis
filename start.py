import discord
from dotenv import load_dotenv
from bot import MusicBot
from os import getenv

load_dotenv()

# todo autostart lavalink jar?

bot = MusicBot()

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is ready and online.")
    bot._prepare_lavalink(password=getenv('LAVALINK_PW'))

@bot.slash_command(name="play", description="Play a song or resume playback.")
async def play(ctx: discord.ApplicationContext, query: str | None = None):
    await bot.play(query, ctx)

@bot.slash_command(name="skip", description="Skip the currently playing song, or the queued track in a given position.")
async def skip(ctx: discord.ApplicationContext, queue_postion: int | None = None):
    await bot.skip(ctx, queue_postion)

@bot.slash_command(name="pause", description="Pauses the currently playing song.")
async def pause(ctx: discord.ApplicationContext):
    await bot.pause(ctx)

@bot.slash_command(name="disconnect", description="Stop all playback and disconnect from voice chat.")
async def disconnect(ctx: discord.ApplicationContext):
    await bot.disconnect_from_voice(ctx)

@bot.slash_command(name="queue", description="Shows all songs currently in queue.")
async def queue(ctx: discord.ApplicationContext):
    await bot.show_queue(ctx)

@bot.slash_command(name="next", description="Moves the song in the given position to the top of the queue.")
async def next(ctx: discord.ApplicationContext, queue_postion: int):
    await bot.next(ctx, queue_postion)

@bot.slash_command(name="search", description="Look for a song and play the result.")
async def search(ctx: discord.ApplicationContext, query: str):
    await bot.search(query, ctx)

bot.run(getenv('BOT_TOKEN'))
