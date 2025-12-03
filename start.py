import discord
from dotenv import dotenv_values
from bot import MusicBot

CONFIG = dotenv_values()
BOT_TOKEN = CONFIG['BOT_TOKEN']
BOT_CHANNEL_ID = CONFIG['BOT_CHANNEL_ID']

bot = MusicBot(BOT_CHANNEL_ID)

@bot.slash_command(name="hello", description="Say hello to Acan!")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hey!")

@bot.slash_command(name="play", description="play a song")
async def play(ctx: discord.ApplicationContext, query: str):
    if not bot.verify_context(ctx):
        return
    msg = await ctx.respond(f"Searching for {query}")
    songdata = await bot.get_song(query)
    await msg.edit_original_response(content=f"Now playing {songdata['title']}")

bot.run(BOT_TOKEN)