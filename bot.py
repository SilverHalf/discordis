import discord
import logging
from queue import Queue
import asyncio
from py_yt import VideosSearch
import lavalink
from voice import LavalinkVoiceClient

class MusicBot(discord.Bot):

    def __init__(self, channel: int | str, **kwargs):
        '''
        Starts a new MusicBot instance.
        '''

        super().__init__(**kwargs)
        self.logger: logging.Logger = self._prepare_logger()

        self._text_channel = int(channel)

        self._currently_playing = None
        self._queue: Queue = None
        self.lava: lavalink.Client = None

    def verify_context(self, ctx: discord.ApplicationContext):
        '''
        Verifies that the context of the message is correct:
        - command was sent in the right channel
        - command was sent by a user in the voice channel
        '''
        channelid = ctx.channel_id
        guildid = ctx.guild_id
        if channelid != self._text_channel:
            asyncio.ensure_future(
                ctx.respond(f"Invalid channel! Try asking in https://discord.com/channels/{guildid}/{self._text_channel}.")
            )
            return False

        if ctx.author.voice is None:
            asyncio.ensure_future(
                ctx.respond("You must be connected to a voice channel to use music commands!")
            )
            return False

        return True
    
    async def play(self, query: str, ctx: discord.ApplicationContext):
        if not self.verify_context(ctx):
            return

        # Connecting to voice if not already connected
        if ctx.guild.voice_client is None:
            await self.connect_to_voice(ctx)
        
        # Creating lavaplayer node
        player: lavalink.player.DefaultPlayer = self.lava.player_manager.get(ctx.guild_id)

        # If no query is passed, resuming playback if possible
        if query is None:
            if not player.paused:
                await ctx.respond("Playback is not paused at the moment!")
                return
            await player.set_pause(False)
            await ctx.respond("Playback resumed.")
            return

        # Isearching youtube for query
        # TODO: replace with embed
        msg = await ctx.respond(f"Searching for {query}")
        results = await player.node.get_tracks(f'ytsearch:{query.strip('<>')}')
        track = results.tracks[0]
        track.extra["requester"] = ctx.author.id

        # Playing track or queueing if already playing
        if not player.is_playing:
            self._currently_playing = track
            await player.play_track(track=track)
            await msg.edit_original_response(content=f"Now playing: {track.title}")
        else:
            player.queue.append(track)
            await msg.edit_original_response(content=f"Queued: {track.title}")

        # Feedback on track started
        # TODO: edit embed created above

    async def pause(self, ctx: discord.ApplicationContext):

        if not self.verify_context(ctx):
            return

        if ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
            return
        
        player: lavalink.player.DefaultPlayer = self.lava.player_manager.get(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        await player.set_pause(True)
        await ctx.respond("Playback is paused.")

    async def skip(self, ctx: discord.ApplicationContext):

        if not self.verify_context(ctx):
            return

        if ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
            return
        
        player: lavalink.player.DefaultPlayer = self.lava.player_manager.get(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        await player.skip()
        await ctx.respond("Skipped current song.")
    
    async def connect_to_voice(self, ctx: discord.ApplicationContext):
        '''
        Connects the bot to a voice channel.
        '''
        if not self.verify_context(ctx):
            return
        if ctx.guild.voice_client is not None:
            return
        channel = ctx.author.voice.channel
        await channel.connect(cls=LavalinkVoiceClient)
        self.logger.info(f"Connected to voice channel {ctx.author.voice.channel.name} (ID {ctx.author.voice.channel.id})")

    async def disconnect_from_voice(self, ctx: discord.ApplicationContext):
        '''
        Disconnects the bot from a voice channel if it is connected.
        '''

        if not self.verify_context(ctx):
            return

        guild = ctx.guild
        assert isinstance(guild, discord.Guild)
        if guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice clients!")
        else:
            await guild.voice_client.disconnect(force = True)
            self.logger.info(f"Disconnected from voice channel {ctx.author.voice.channel.name} (ID {ctx.author.voice.channel.id})")
            await ctx.respond("I'm off for now!")
    
    async def search_song(self, query: str):
        '''
        Searches for a query on youtube and returns information on the song.
        '''

        result = await VideosSearch(query, limit=1, language='en', region='US').next()

        return result['result'][0]
    
    def _prepare_logger(self):
        '''Prepares a logger for the bot.'''

        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        logger.addHandler(handler)

        return logger
    
    def _prepare_lavalink(self,
            password: str,
            host: str = 'localhost',
            port: int = 2333,
            region: str = 'eu'):

        lava = lavalink.Client(self.application_id)
        lava.add_node(
                host=host,
                port=port,
                password=password,
                region=region,
                name='discordis-node')
        
        self.lava = lava

if __name__ == '__main__':
    bot = MusicBot('1096111829815672832')
        