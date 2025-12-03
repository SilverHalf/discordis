import discord
import logging
from queue import Queue
import asyncio
from py_yt import VideosSearch

class MusicBot(discord.Bot):

    def __init__(self, channel: int | str, **kwargs):
        '''
        Starts a new MusicBot instance.
        '''

        super().__init__(**kwargs)
        self._logger: logging.Logger = self._prepare_logger()

        self._channel = int(channel)
        self_currently_playing = None
        self._queue: Queue = None

    def verify_context(self, ctx: discord.ApplicationContext):
        '''
        Verifies that the context of the message is correct:
        - command was sent in the right channel
        - command was sent by a user in the voice channel
        '''
        channelid = ctx.channel_id
        guildid = ctx.guild_id
        if channelid != self._channel:
            asyncio.ensure_future(
                ctx.respond(f"Invalid channel! Try asking in https://discord.com/channels/{guildid}/{self._channel}.")
            )
            return False

        if ctx.author.voice is None:
            asyncio.ensure_future(
                ctx.respond("You must be connected to a voice channel to use music commands!")
            )
            return False

        return True

    async def get_song(self, query: str):

        result = await VideosSearch(query, limit=1, language='en', region='US').next()

        return result['result'][0]
    
    def _prepare_logger(self):
        '''Prepares a logger for the bot.'''

        logger = logging.getLogger('discord')
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
        handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
        logger.addHandler(handler)

if __name__ == '__main__':
    bot = MusicBot('1096111829815672832')
    asyncio.run(bot.get_song('sultans of swing'))
        