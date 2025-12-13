import discord
import logging
import asyncio
import lavalink
from lavalink import listener
from voice import LavalinkVoiceClient
import embeds

class MusicBot(discord.Bot):

    def __init__(self, **kwargs):
        '''
        Starts a new MusicBot instance.
        '''

        super().__init__(**kwargs)
        self.logger: logging.Logger = self._prepare_logger()
        self._text_channels: dict[int, int] = {}
        self.lava: lavalink.Client = None
        self._queue_display_limit = 10
        self._inactivity_minutes = 5
    
    async def play(self, query: str, ctx: discord.ApplicationContext):
        '''
        Resumes playback if a track is paused.
        If no track is paused, searches for the query and plays the first result.
        If a track is currently playing, the result is queued instead.
        '''

        if not self.verify_context(ctx):
            return

        # Connecting to voice if not already connected
        if ctx.guild.voice_client is None:
            await self.connect_to_voice(ctx)
        
        # Creating lavaplayer node
        player = self._get_player(ctx.guild_id)

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
        msg = await ctx.respond(f"Searching for '{query}'...")
        results = await player.node.get_tracks(f'ytsearch:{query.strip('<>')}')
        track = results.tracks[0]
        track.extra["requester"] = ctx.author.id

        # Playing track or queueing if already playing
        if not player.is_playing:
            self._currently_playing = track
            await player.play_track(track=track)
        else:
            player.queue.append(track)
            await msg.edit_original_response(embed=embeds.track("Queued:", track))

        # Feedback on track started
        # TODO: edit embed created above

    async def pause(self, ctx: discord.ApplicationContext):
        '''
        Pauses playback.
        '''

        if not self.verify_context(ctx):
            return

        if ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
            return
        
        player = self._get_player(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        await player.set_pause(True)
        await ctx.respond("Playback is paused.")

    async def skip(self, ctx: discord.ApplicationContext, queued_song: int | None):
        '''
        Skips the current track, or if a number is specified removes the queued track in that position.
        '''

        if not self.verify_context(ctx):
            return

        if ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
            return
        
        player = self._get_player(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        if queued_song is None:
            await player.skip()
            await ctx.respond("Skipped current song.")
        
        else:
            if len(player.queue) > queued_song or queued_song < 1:
                await ctx.respond(f"Invalid option: {queued_song}")
            else:
                song_title = player.queue[queued_song - 1].title
                player.queue.remove(player.queue[queued_song - 1])
                await ctx.respond(f"Removed from queue: {song_title}")

    async def show_queue(self, ctx: discord.ApplicationContext):
        '''
        Displays an embed that shows the next songs in queue.
        '''

        queued_tracks = self._get_player(ctx.guild_id).queue
        num_queued = len(queued_tracks)
        msg = f"Showing {min(num_queued, self._queue_display_limit)} out of {num_queued} queued tracks."
        num_queued > self._queue_display_limit
        queued_tracks = queued_tracks[:self._queue_display_limit]
        await ctx.respond(embed=embeds.multi_track(msg, queued_tracks))
    
    async def next(self, ctx: discord.ApplicationContext, queued_song: int):
        '''Moves the song at the provided queue position to the top of the queue.'''

        if not self.verify_context(ctx):
            return

        if ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
            return
        
        player = self._get_player(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        if len(player.queue) > queued_song or queued_song < 1:
            await ctx.respond(f"Invalid option: {queued_song}")
        else:
            song = player.queue[queued_song - 1]
            player.queue.remove(song)
            player.queue = [song] + player.queue
            await ctx.respond(f"Moved {song.title} to the top of the queue.")
    
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

    def verify_context(self, ctx: discord.ApplicationContext):
        '''
        Verifies that the context of the message is correct:
        - command was sent in the right channel
        - command was sent by a user in the voice channel
        '''

        channelid = ctx.channel_id
        guildid = ctx.guild_id

        if guildid not in self._text_channels:
            self._text_channels[guildid] = channelid

        if channelid != self._text_channels[guildid]:
            asyncio.ensure_future(
                ctx.respond(f"Invalid channel! Try asking in https://discord.com/channels/{guildid}/{self._text_channels[guildid]}.")
            )
            return False

        if ctx.author.voice is None:
            asyncio.ensure_future(
                ctx.respond("You must be connected to a voice channel to use music commands!")
            )
            return False

        return True
    
    @listener(lavalink.TrackStartEvent)
    async def update_song_display(self, event: lavalink.TrackStartEvent):
        '''
        Whenever a song starts playing, displays infomation on the
        song in the appropriate channel.
        '''

        guild_id = event.player.guild_id
        channel_id = self._text_channels[guild_id]
        channel = self.get_guild(guild_id).get_channel(channel_id)
        await channel.send(embed=embeds.track("Now Playing", event.track))
    
    def _get_player(self, guild_id) -> lavalink.player.DefaultPlayer:
        '''Gets the player corresponding to the given guild.'''

        return self.lava.player_manager.get(guild_id)
    
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

        app_id = self.application_id
        assert(isinstance(app_id, int))
        lava = lavalink.Client(app_id)
        lava.add_node(
                host=host,
                port=port,
                password=password,
                region=region,
                name='discordis-node')
        
        self.lava = lava
        self.lava.add_event_hooks(self)