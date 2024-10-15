import os
import re
import csv
import time
import threading
import tkinter as tk
from tkinterdnd2 import DND_TEXT, TkinterDnD
import requests
from bs4 import BeautifulSoup
import syncedlyrics
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

LYRICS_PATH = "Lyrics"
CSV_FILE = "lyrics_data.csv"
SHOULD_SAVE_LYRICS = True
SHOULD_USE_SAVED_LYRICS = True
SHOULD_CUT_TITLE_AT_DASH = True
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 800
FONT_SIZE = 20

TITLE_WORD_BLACKLIST = [
    "mix", "mixed", "remix", "edit",
    "extended", "radio",
    "feat", "ft", "featuring",
    "original", "version", "live", "edition", "anthem",
    "asot"
]

class EZSpotifyLyrics:
    LYRICS_PACKAGE_FAIL_MSG = " could not find lyrics."

    is_lyrics_search_ongoing = False

    def __init__(self, root):
        self.root = root
        self.root.title("EZ Spotify Lyrics")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.root.drop_target_register(DND_TEXT)
        self.root.dnd_bind('<<Drop>>', self.handle_drop)
        self.root.bind("<Control-v>", self.handle_paste)

        self.scrollbar = tk.Scrollbar(root)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_box = tk.Text(root, yscrollcommand=self.scrollbar.set, font=("Helvetica", FONT_SIZE))
        self.text_box.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.text_box.insert(tk.END, "Drag & drop or CTRL+V a Spotify link here to get the lyrics.")

        self.scrollbar.config(command=self.text_box.yview)

        self.lyrics_data = self.load_lyrics_data()

        # Check for Spotify API credentials
        self.spotipy_available = False
        try:
            self.spotipy = spotipy
            client_id = os.getenv("SPOTIPY_CLIENT_ID")
            client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
            if client_id and client_secret:
                self.sp = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())
                self.spotipy_available = True
            else:
                self.sp = None
        except ImportError:
            self.spotipy = None
            self.sp = None

    def save_lyrics_data(self):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for track_id, file_name in self.lyrics_data.items():
                writer.writerow([track_id, file_name])

    def load_lyrics_data(self):
        if not os.path.exists(CSV_FILE):
            return {}
        
        with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            return {row[0]: row[1] for row in reader}

    def handle_drop(self, event):
        if self.is_lyrics_search_ongoing:
            return
        
        self.handle_new_url(event.data)

    def handle_paste(self, event=None):
        if self.is_lyrics_search_ongoing:
            return
        
        try:
            self.handle_new_url(self.root.clipboard_get())
        except tk.TclError:
            self.write("Your clipboard does not have a URL in it.", True)

    def write(self, text="", should_clear=False):
        text += "\n"
        if should_clear:
            self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, text)
        self.text_box.see(tk.END)  # Auto-scroll to the end

    def handle_new_url(self, url):
        threading.Thread(target=self.start_lyrics_search, args=(url,)).start()

    def start_lyrics_search(self, url):
        self.is_lyrics_search_ongoing = True
        self.get_lyrics(url)
        self.save_lyrics_data()
        self.is_lyrics_search_ongoing = False

        self.write("\nDrag & drop or CTRL+V a new Spotify link here to get the next lyrics.")

    def get_lyrics(self, url):
        self.write("URL received. Starting lyrics search.", True)

        # Remove any query parameters.
        url = url.split("?")[0].strip()

        self.write(url)

        if not url:
            self.write("The given URL is empty.")
            return

        if "spotify.com/track" in url:
            self.write("Detected a track URL.")
            track_id = url.split("track/")[1]
            # Get track info from Spotify web page
            track = self.get_track_info_web(track_id)
            if not track:
                self.write("Could not retrieve track information.")
                return
            title = track['title']
            artists = track['artists']
            song_info_str = f"{', '.join(artists)} - {title}"
            self.write(f"Processing track: {song_info_str}")
            self.process_track(track_id, artists, title)
        elif "spotify.com/playlist" in url:
            self.write("Detected a playlist URL.")
            playlist_id = url.split("playlist/")[1].split("?")[0]
            tracks = []
            if self.spotipy_available:
                self.write("Playlist support is enabled using Spotify API.")
                # Get tracks using spotipy
                try:
                    results = self.sp.playlist_items(playlist_id)
                    tracks = results['items']
                    # Handle pagination
                    while results['next']:
                        results = self.sp.next(results)
                        tracks.extend(results['items'])
                except Exception as e:
                    self.write(f"Error accessing playlist: {str(e)}")
                    return

                self.write(f"Found {len(tracks)} tracks in the playlist.")
                for idx, item in enumerate(tracks):
                    track = item.get('track')
                    if track and 'id' in track:
                        track_id = track['id']
                        title = track.get('name', 'Unknown Title')
                        artists = [artist['name'] for artist in track.get('artists', [])]
                        song_info_str = f"{', '.join(artists)} - {title}"
                        self.write(f"\nProcessing track {idx+1}/{len(tracks)}: {song_info_str}")
                        self.process_track(track_id, artists, title)

                        self.save_lyrics_data()

                        # 5 second delay every 10 tracks to avoid rate limiting.
                        if (idx + 1) % 10 == 0:
                            self.write(f"\nPausing for 5 seconds to avoid rate limiting...")
                            time.sleep(5)
                    else:
                        self.write(f"Skipping invalid track entry at position {idx+1}")
            else:
                self.write("Playlist support is disabled (missing Spotify API credentials).")
                self.write("Attempting to retrieve playlist tracks without API (may not be reliable).")
                # Attempt to scrape playlist page
                tracks = self.get_playlist_tracks_web(playlist_id)
                if not tracks:
                    self.write("Could not retrieve playlist tracks without API.")
                    return

                self.write(f"Found {len(tracks)} tracks in the playlist.")
                for idx, track in enumerate(tracks):
                    track_id = track['id']
                    title = track['title']
                    artists = track['artists']
                    song_info_str = f"{', '.join(artists)} - {title}"
                    self.write(f"\nProcessing track {idx+1}/{len(tracks)}: {song_info_str}")
                    self.process_track(track_id, artists, title)
        else:
            self.write("Invalid Spotify URL. It should be a track or playlist URL.")
            return

    def get_track_info_web(self, track_id):
        # Attempt to get track info by scraping the track page
        url = f"https://open.spotify.com/track/{track_id}"
        self.write(f"Fetching track info from {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.write(f"Error fetching track page: {str(e)}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        # Extract track title and artist from the page metadata
        title_tag = soup.find('meta', property='og:title')
        artist_tag = soup.find('meta', property='og:description')
        if title_tag and artist_tag:
            title = title_tag['content']
            artists = artist_tag['content'].replace(' · Song · ', '').split(', ')
            return {'id': track_id, 'title': title, 'artists': artists}
        else:
            return None

    def get_playlist_tracks_web(self, playlist_id):
        # Attempt to get playlist tracks by scraping the playlist page
        url = f"https://open.spotify.com/playlist/{playlist_id}"
        self.write(f"Fetching playlist info from {url}")
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.write(f"Error fetching playlist page: {str(e)}")
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        # Parse initial state from page scripts
        scripts = soup.find_all('script')
        for script in scripts:
            if 'Spotify.Entity' in script.text:
                json_text = script.text.strip().split('Spotify.Entity = ')[1].rsplit(';', 1)[0]
                import json
                try:
                    data = json.loads(json_text)
                    tracks = []
                    for item in data['tracks']['items']:
                        track_info = item['track']
                        track_id = track_info['uri'].split(':')[-1]
                        title = track_info['name']
                        artists = [artist['name'] for artist in track_info['artists']]
                        tracks.append({'id': track_id, 'title': title, 'artists': artists})
                    return tracks
                except Exception as e:
                    self.write(f"Error parsing playlist data: {str(e)}")
                    return None
        self.write("Could not find playlist data in page scripts.")
        return None

    def process_track(self, track_id, artists, title):
        lyrics = None
        song_info_str = f"{', '.join(artists)} - {title}"
        key = track_id
        if SHOULD_USE_SAVED_LYRICS and key in self.lyrics_data:
            file_name = self.lyrics_data[key]
            if not file_name:
                self.write(f"Lyrics search was previously unsuccessful for {song_info_str}.")
                return

            lyrics = self.load_lyrics(file_name)
            song_info_str = file_name.replace(".lrc", "")

        if not lyrics:
            self.lyrics_data[key] = ""

            lyrics = self.download_lyrics(artists, title)
            if not lyrics:
                self.write(f"Could not find lyrics for {song_info_str}.")
                return

            file_name = f"{self.safe_filename(song_info_str)}.lrc"
            self.save_lyrics(lyrics, file_name)
            self.lyrics_data[key] = file_name

        self.write(song_info_str)
        self.write(f"\n{lyrics}")

    def safe_filename(self, filename):
        # Replace invalid characters for filenames
        return "".join(c if c.isalnum() or c in " -_." else "_" for c in filename)

    def save_lyrics(self, lyrics, file_name):
        if not SHOULD_SAVE_LYRICS:
            return

        # Replace invalid filename characters
        file_name = self.safe_filename(file_name)

        file_path = os.path.join(LYRICS_PATH, file_name)
        os.makedirs(LYRICS_PATH, exist_ok=True)

        self.write(f"Saving lyrics to file: {file_path}")
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(lyrics)

        self.write(f"Lyrics saved at: {file_path}")

    def load_lyrics(self, file_name):
        file_name = self.safe_filename(file_name)  # Ensure filename safety

        file_path = os.path.join(LYRICS_PATH, file_name)
        self.write(f"Looking for saved lyrics at: {file_path}")

        if not os.path.exists(file_path):
            self.write("Saved lyrics file is missing.")
            return None

        self.write(f"Saved lyrics found at: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
            lyrics = file.read().strip()
            if not lyrics:
                self.write("Saved lyrics file is empty or corrupted.")
                return None

        return lyrics

    def download_lyrics(self, artists, title):
        lyrics = self.download_from_syncedlyrics(artists, title)
        # You can add additional methods to download lyrics from other sources if needed
        if not lyrics:
            return

        self.write(f"Lyrics found")
        return lyrics

    def download_from_syncedlyrics(self, artists, title):
        package_name = "Syncedlyrics"

        self.write(f"Using {package_name} (Musixmatch, Genius, Lrclib, NetEase, Megalobiz).")

        # search_query = f"{title} {' '.join(artists)}"
        search_query = title

        # Check if the artist is already in the title. Often happens with remixes.
        is_artist_in_title = True
        for word in artists[0].split(" "):
            if word.lower() not in search_query.lower():
                is_artist_in_title = False
                break
        if not is_artist_in_title:
            search_query = f"{search_query} {artists[0]}"

        self.write(f"Query: {search_query}")

        self.write("Searching...")
        lyrics = syncedlyrics.search(
            search_query,
            # All providers but custom search order.
            providers=["Musixmatch", "Genius", "Lrclib", "NetEase", "Megalobiz"],
            save_path=None)
        if not lyrics:
            self.write(package_name + self.LYRICS_PACKAGE_FAIL_MSG)
            return

        return lyrics


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = EZSpotifyLyrics(root)
    root.mainloop()
