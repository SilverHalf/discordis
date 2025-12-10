import discord
from dotenv import dotenv_values
from bot import MusicBot

CONFIG = dotenv_values()
BOT_TOKEN = CONFIG['BOT_TOKEN']
BOT_CHANNEL_ID = CONFIG['BOT_CHANNEL_ID']

bot = MusicBot(BOT_CHANNEL_ID)

# todo autostart lavalink jar?

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is ready and online.")
    bot._prepare_lavalink(password=CONFIG['LAVALINK_PW'])

@bot.slash_command(name="play", description="Play a song or resume playback.")
async def play(ctx: discord.ApplicationContext, query: str | None = None):
    await bot.play(query, ctx)

@bot.slash_command(name="skip", description="Skip the currently playing song.")
async def skip(ctx: discord.ApplicationContext):
    await bot.skip(ctx)

@bot.slash_command(name="pause", description="Pauses the currently playing song.")
async def pause(ctx: discord.ApplicationContext):
    await bot.pause(ctx)

@bot.slash_command(name="disconnect", description="Stop all playback and disconnect from voice chat.")
async def disconnect(ctx: discord.ApplicationContext):
    await bot.disconnect_from_voice(ctx)

bot.run(BOT_TOKEN)