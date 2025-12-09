import discord
from dotenv import dotenv_values
from bot import MusicBot
import lavalink

CONFIG = dotenv_values()
BOT_TOKEN = CONFIG['BOT_TOKEN']
BOT_CHANNEL_ID = CONFIG['BOT_CHANNEL_ID']

bot = MusicBot(BOT_CHANNEL_ID)

# todo autostart lavalink jar?

@bot.event
async def on_ready():
    bot.logger.info(f"{bot.user} is ready and online.")
    bot._prepare_lavalink(password=CONFIG['LAVALINK_PW'])

@bot.slash_command(name="hello", description="Say hello to Acan!")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("Hey!")

@bot.slash_command(name="play", description="Have Acan play a song.")
async def play(ctx: discord.ApplicationContext, query: str):
    if not bot.verify_context(ctx):
        return
    
    await bot.connect_to_voice(ctx)
    msg = await ctx.respond(f"Searching for {query}")
    # songdata = await bot.search_song(query)
    
    player: lavalink.player.BasePlayer = bot.lava.player_manager.get(ctx.guild_id)
    query = query.strip('<>')
    query = f'ytsearch:{query}'
    results = await player.node.get_tracks(query)
    track = results.tracks[0]
    track.extra["requester"] = ctx.author.id
    await player.play_track(track=track)
    await msg.edit_original_response(content=f"Now playing {track.title}")


@bot.slash_command(name="disconnect", description="Disconnect Acan from voice chat.")
async def disconnect(ctx: discord.ApplicationContext):
    if not bot.verify_context(ctx):
        return
    
    await bot.disconnect_from_voice(ctx)

bot.run(BOT_TOKEN)