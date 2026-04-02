import os
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

TARGET_PLAYLIST_ID = "0YqCQ1jfJ37VmIXWgPM90V"
CHAT_ID = -1001592882608


def extract_spotify_links(text):
    if not text:
        return []
    return re.findall(r"https?://open\.spotify\.com/track/[a-zA-Z0-9]+", text)


def get_existing_track_ids(sp, playlist_id):
    existing_tracks = set()
    results = sp.playlist_items(playlist_id)
    while results:
        for item in results["items"]:
            track = item.get("track")
            if track and track.get("id"):
                existing_tracks.add(track["id"])
        if results["next"]:
            results = sp.next(results)
        else:
            break
    return existing_tracks


def sync_spotify_tracks():
    print("Step 1: Initializing Spotify...")
    auth_manager = SpotifyOAuth(
        client_id=os.environ["SPOTIPY_CLIENT_ID"],
        client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
        redirect_uri="http://127.0.0.1:8000",
        scope="playlist-modify-public",
    )
    token_info = auth_manager.refresh_access_token(os.environ["SPOTIFY_REFRESH_TOKEN"])
    sp = spotipy.Spotify(auth=token_info["access_token"])
    print("Step 1: Spotify OK")

    print("Step 2: Connecting to Telegram...")
    client = TelegramClient(
        StringSession(os.environ["TELEGRAM_STRING_SESSION"]),
        int(os.environ["TELEGRAM_API_ID"]),
        os.environ["TELEGRAM_API_HASH"],
    )

    with client:
        print("Step 2: Connected to Telegram.")
        chat = client.get_entity(CHAT_ID)

        spotify_links = []
        for message in client.iter_messages(chat, limit=300):
            links = extract_spotify_links(message.text)
            spotify_links.extend(links)

        print(f"Found {len(spotify_links)} Spotify links.")

        track_ids = [link.split("/")[-1].split("?")[0] for link in spotify_links]
        unique_track_ids = list(dict.fromkeys(track_ids))
        existing_track_ids = get_existing_track_ids(sp, playlist_id=TARGET_PLAYLIST_ID)
        new_track_ids = [t for t in unique_track_ids if t not in existing_track_ids]

        if new_track_ids:
            print(f"Adding {len(new_track_ids)} new tracks...")
            sp.playlist_add_items(TARGET_PLAYLIST_ID, new_track_ids)
            print("Tracks added successfully!")
        else:
            print("No new tracks to add.")


if __name__ == "__main__":
    sync_spotify_tracks()
