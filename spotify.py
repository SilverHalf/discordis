'''Module for building youtube queries from spotify links.'''

import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

def query_from_link(url: str) -> str | None:
    '''
    Given a spotify url, returns an appopriate search query containing
    the track's name and author. If the url is invalid, returns none.
    '''

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id = os.getenv("SPOTIFY_ID"),
        client_secret = os.getenv("SPOTIFY_SECRET"),
        redirect_uri = os.getenv("SPOTIFY_REDIRECT"),
        scope="user-library-read")
    )
    try:
        track: dict = sp.track(url)
    except spotipy.SpotifyException:
        return None
    return f'{track['name']} {' '.join(artist['name'] for artist in track['artists'])}'


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    query_from_link('https://open.spotify.com/track/0GqGrPWhmiRX9BU93')