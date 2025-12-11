from discord import Embed, Colour
from lavalink import AudioTrack
from datetime import timedelta

def track(name: str, track: AudioTrack) -> Embed:
    '''Creates an embed for the given track with the given message.'''

    embed = Embed(color=Colour.dark_green())
    embed.set_thumbnail(url=track.artwork_url)
    embed.add_field(name=name, value=track.title, inline=False)
    duration = timedelta(milliseconds=track.duration)
    embed.add_field(name='Duration', value=str(duration).removeprefix("00:"))
    embed.add_field(name="Requested by", value=f"<@{track.requester}>")

    return embed

def multi_track(name: str, tracks: list[AudioTrack]) -> Embed:
    '''Creates an embed for a list of tracks.'''

    embed = Embed(title=name, color=Colour.dark_green())
    for i, track in enumerate(tracks):
        embed.add_field(
            name=f"{i + 1}. {track.title}",
            value=f"Requested by <@{track.requester}>",
            inline=False)
    
    return embed