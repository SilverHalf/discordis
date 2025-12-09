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
    
    async def connect_to_voice(self, ctx: discord.ApplicationContext):
        channel = ctx.author.voice.channel
        await channel.connect(cls=LavalinkVoiceClient)
        self.logger.info(f"Connected to voice channel {ctx.author.voice.channel.name} (ID {ctx.author.voice.channel.id})")

    async def disconnect_from_voice(self, ctx: discord.ApplicationContext):
        '''
        Disconnects the bot from a voice channel if it is connected.
        '''

        guild = ctx.guild
        if isinstance(guild, discord.Guild):
            await guild.voice_client.disconnect(force = True)
            self.logger.info("Disconnected from voice channel.")
            await ctx.respond("I'm off for now!")
        else:
            raise TypeError(f"Guild is of wrong type: {type(guild)}")
    

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
        