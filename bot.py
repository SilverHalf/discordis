import discord
import logging
import lavalink
from lavalink import listener
from voice import LavalinkVoiceClient
import embeds
import spotify
from timer import DisconnectTimer

class MusicBot(discord.Bot):

    def __init__(self, **kwargs):
        '''
        Starts a new MusicBot instance.
        '''

        super().__init__(**kwargs)
        self.logger: logging.Logger = self._prepare_logger()
        self._text_channels: dict[int, int] = {}
        self.lava: lavalink.Client = None
        self._queue_display_limit = 5
        self._inactivity_seconds = 300
        self._search_results: dict[int, list[lavalink.AudioTrack | lavalink.DeferredAudioTrack]] = {}
        self._inactivity_timer: dict[int, DisconnectTimer] = {}

    async def play(self, query: str, ctx: discord.ApplicationContext):
        '''
        Resumes playback if a track is paused.
        If no track is paused, searches for the query and plays the first result.
        If a track is currently playing, the result is queued instead.
        '''

        self.reset_inactivity_timer(ctx)
        if not await self.verify_context(ctx):
            return

        # Connecting to voice
        await self.connect_to_voice(ctx)

        await ctx.respond('▶️')

        # If no query is passed, resuming playback
        if query is None:
            return await self.resume(ctx)
        
        # Managing searches
        if query.isdigit() and int(query) > 0 and int(query) <= self._queue_display_limit:
            if ctx.guild_id in self._search_results:
                track = self._search_results[ctx.guild_id][int(query) - 1]
                return await self._play_track(ctx, track)
        
        tracks = await self._search_yt(query, ctx)
        if not any(tracks):
            return
        await self._play_track(ctx, tracks[0])


    async def pause(self, ctx: discord.ApplicationContext):
        '''
        Pauses playback.
        '''

        self.reset_inactivity_timer(ctx)
        if not await self.verify_context(ctx, requires_voice = True):
            return
        
        player = self._get_player(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            self.logger.info("Could not pause: no playback active.")
            return
        
        await ctx.respond("⏸️")
        await player.set_pause(True)


    async def skip(self, ctx: discord.ApplicationContext, queued_song: int | None):
        '''
        Skips the current track, or if a number is specified removes the queued track in that position.
        '''

        self.reset_inactivity_timer(ctx)
        if not await self.verify_context(ctx, requires_voice = True):
            return
        
        player = self._get_player(ctx.guild_id)
        if not player.is_playing:
            await ctx.respond("I'm not playing anything right now!")
            return
        
        if queued_song is None or queued_song == 0:
            await player.skip()
            await ctx.respond("⏭️")
            return
        
        if queued_song > len(player.queue)  or queued_song < 1:
            await ctx.respond(f"Invalid option: {queued_song}. Please give an option between 0 and {len(player.queue)}.")
            return

        song_title = player.queue[queued_song - 1].title
        player.queue.remove(player.queue[queued_song - 1])
        await ctx.respond(f"Removed from queue: {song_title}")


    async def search(self, query: str, ctx: discord.ApplicationContext):
        '''
        Provides top search results for the provided query.
        Caches these results for later playback using the /play command.
        '''
        self.reset_inactivity_timer(ctx)
        if not await self.verify_context(ctx):
            return
        
        tracks = await self._search_yt(query, ctx)
        if not any(tracks):
            return
        tracks = tracks[:self._queue_display_limit]
        self._search_results[ctx.guild_id] = tracks
        await ctx.respond(embed=embeds.search_display(tracks))


    async def show_queue(self, ctx: discord.ApplicationContext):
        '''
        Displays an embed that shows the next songs in queue.
        '''

        self.reset_inactivity_timer(ctx)
        queued_tracks = self._get_player(ctx.guild_id).queue
        num_queued = len(queued_tracks)
        msg = f"Showing {min(num_queued, self._queue_display_limit)} out of {num_queued} queued tracks."
        num_queued > self._queue_display_limit
        queued_tracks = queued_tracks[:self._queue_display_limit]
        await ctx.respond(embed=embeds.queue_display(msg, queued_tracks))
        self.logger.info("Displayed queue.")


    async def next(self, ctx: discord.ApplicationContext, queued_song: int):
        '''Moves the song at the provided queue position to the top of the queue.'''

        self.reset_inactivity_timer(ctx)
        if not await self.verify_context(ctx):
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
            return

        song = player.queue[queued_song - 1]
        player.queue.remove(song)
        player.queue = [song] + player.queue
        await ctx.respond(f"Moved {song.title} to the top of the queue.")
        self.logger.info(f"Moved {song.title} to the top of the queue.")


    async def connect_to_voice(self, ctx: discord.ApplicationContext):
        '''
        Connects the bot to a voice channel.
        '''
        if not await self.verify_context(ctx):
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

        if not await self.verify_context(ctx, requires_voice = True):
            return
        self.get_guild()
        await ctx.guild.voice_client.disconnect(force = True)
        await ctx.respond("👋")


    async def resume(self, ctx: discord.ApplicationContext):
        '''Resumes playback if its's paused.'''

        player = self._get_player(ctx.guild_id)
        if not player.paused:
            await ctx.respond("Playback is not paused at the moment!")
            return
        await player.set_pause(False)
        

    async def verify_context(self, ctx: discord.ApplicationContext, requires_voice: bool = False):
        '''
        Verifies that the context of the message is correct:
        - command was sent in the right channel
        - command was sent by a user in the voice channel
        '''

        channelid = ctx.channel_id
        guildid = ctx.guild_id

        if guildid not in self._text_channels:
            self._text_channels[guildid] = channelid
        elif channelid != self._text_channels[guildid]:
            await ctx.respond(f"Invalid channel! Try asking in https://discord.com/channels/{guildid}/{self._text_channels[guildid]}.")
            return False

        if ctx.author.voice is None:
            await ctx.respond("You must be connected to a voice channel to use music commands!")
            return False
        
        if requires_voice and ctx.guild.voice_client is None:
            await ctx.respond("I'm not connected to any voice channels!")
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
        self.logger.info(f"Started playing: {event.track.title}")
    

    @listener(lavalink.QueueEndEvent)
    async def start_inactivity_timer(self, event: lavalink.QueueEndEvent):
        '''Starts an inactivity timer whenever music is no longer playing.'''
        
        self._inactivity_timer[event.player.guild_id] = DisconnectTimer(self._inactivity_seconds, self._disconnect, event.player.guild_id)

    def reset_inactivity_timer(self, ctx: discord.ApplicationContext):
        '''Resets an inactivity timer.'''

        if ctx.guild_id not in self._inactivity_timer:
            return
        
        self._inactivity_timer[ctx.guild_id].cancel()


    async def _play_track(self, ctx: discord.ApplicationContext, track: lavalink.AudioTrack):
        '''Plays a track or queues it if one is already playing.'''

        player = self._get_player(ctx.guild_id)
        track.extra["requester"] = ctx.author.id
        if not player.is_playing:
            await player.play_track(track=track)
        else:
            player.queue.append(track)
            await ctx.respond(embed=embeds.track("Queued in position {len(player.queue)}:", track))


    async def _search_yt(self, query: str, ctx: discord.ApplicationContext) -> list[lavalink.AudioTrack]:
        '''Searches youtube for the provided query and returns the result.'''

        player = self._get_player(ctx.guild_id)
        
        if 'open.spotify.com' in query:
            query = spotify.query_from_link(query)
            if query is None:
                await ctx.respond("You did not provide a valid spotify URL!")
                return []

        self.logger.info(f"Searching for '{query}'...")
        results = await player.node.get_tracks(f'ytsearch:{query.strip('<>')}')
        return results.tracks

    
    def _get_player(self, guild_id: int) -> lavalink.player.DefaultPlayer:
        '''
        Gets the player corresponding to the given guild, or creates
        one if necessary.
        '''

        player = self.lava.player_manager.get(guild_id)
        return player if player is not None else self.lava.player_manager.create(guild_id)

    async def _disconnect(self, guild_id: int):
        '''Alternative disconnect.'''

        guild = self.get_guild(guild_id)
        await guild.voice_client.disconnect(force = True)
    

    def _prepare_logger(self):
        '''Prepares a logger for the bot.'''

        logger = logging.getLogger('discord')
        logger.setLevel(logging.INFO)
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