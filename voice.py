import discord
import lavalink
from lavalink.errors import ClientError

class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.VoiceChannel,):
        super().__init__(client, channel)
        if not hasattr(self.client, 'lava'):
            raise RuntimeError("Client does not hava an instantiated Lavalink connection.")
        self.lavalink: lavalink.Client = client.lava
        self._destroyed = False
    
    async def on_voice_server_update(self, data):
        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_SERVER_UPDATE',
            'd': data
        }
        await self.lavalink.voice_update_handler(lavalink_data)
    
    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']

        if not channel_id:
            await self._destroy()
            return

        self.channel = self.client.get_channel(int(channel_id))

        # the data needs to be transformed before being handed down to
        # voice_update_handler
        lavalink_data = {
            't': 'VOICE_STATE_UPDATE',
            'd': data
        }

        await self.lavalink.voice_update_handler(lavalink_data)
    
    async def connect(self, *, timeout: float, reconnect: bool):
        # Called when connecting to a voice channel
         
        if self.lavalink.player_manager.get(self.channel.guild.id) is None:
            self.lavalink.player_manager.create(self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel = self.channel)

    async def disconnect(self, *, force = False):
        guild_id = self.channel.guild.id
        player = self.lavalink.player_manager.get(guild_id)
        if not force and not player.is_connected:
            return
          # None means disconnect
        await self.channel.guild.change_voice_state(channel=None)

        # update the channel_id of the player to None
        # this must be done because the on_voice_state_update that would set channel_id
        # to None doesn't get dispatched after the disconnect
        player.channel_id = None
        await self._destroy(guild_id)
    
    async def _destroy(self, guild_id):
        self.cleanup()

        if self._destroyed:
            # Idempotency handling, if `disconnect()` is called, the changed voice state
            # could cause this to run a second time.
            return

        self._destroyed = True

        try:
            await self.lavalink.player_manager.destroy(guild_id)
        except ClientError:
            pass