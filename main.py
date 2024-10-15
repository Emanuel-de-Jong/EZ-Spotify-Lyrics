import os
import re
import threading
import tkinter as tk
from tkinterdnd2 import DND_TEXT, TkinterDnD
import requests
from bs4 import BeautifulSoup
import syncedlyrics

LYRICS_PATH = "Lyrics"
SHOULD_SAVE_LYRICS = True
SHOULD_USE_SAVED_LYRICS = True
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
    def __init__(self, root):
        self.root = root
        self.root.title("EZ Spotify Lyrics")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        self.root.drop_target_register(DND_TEXT)
        self.root.dnd_bind('<<Drop>>', lambda e: self.handle_new_url(e.data))
        self.root.bind("<Control-v>", lambda e: self.handle_new_url(root.clipboard_get()))

        self.scrollbar = tk.Scrollbar(root)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_box = tk.Text(root, yscrollcommand=self.scrollbar.set, font=("Helvetica", FONT_SIZE))
        self.text_box.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.text_box.insert(tk.END, "Drag & drop or CTRL+V a Spotify link here to get the lyrics.")

        self.scrollbar.config(command=self.text_box.yview)

    def write(self, text="", should_clear=False):
        text += "\n"
        if should_clear:
            self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, text)

    def handle_new_url(self, url):
        # Start new thread so the UI doesn't freeze.
        threading.Thread(target=self.get_lyrics, args=(url,)).start()

    def get_lyrics(self, url):
        self.write("STARTING", True)

        url = url.strip()
        if not url:
            self.write("The given URL is empty.")
            return
        
        if "spotify.com/track" not in url:
            self.write(f"Invalid Spotify URL: {url}")
            self.write("It should look like: https://open.spotify.com/track/xyz")
            return

        # Remove any query parameters.
        url = url.split("?")[0]

        lyrics = None
        existing_lyrics_path = self.get_lyrics_dir_path(url)
        if SHOULD_USE_SAVED_LYRICS and os.path.exists(existing_lyrics_path):
            self.write("Using saved lyrics.")
            lyrics = self.get_existing_lyrics(existing_lyrics_path)
        
        if not lyrics:
            self.write("Getting lyrics from the internet.")
            artists, title = self.get_song_info(url)
            if not artists or not title:
                return
            
            lyrics = self.download_lyrics(artists, title, url)
            if not lyrics:
                return

        self.write()
        self.write(lyrics)

    def get_lyrics_dir_path(self, url):
        dir_name = url.split('/')[-1]
        return f"{LYRICS_PATH}{os.sep}{dir_name}{os.sep}"

    def get_existing_lyrics(self, dir_path):
        file_path = None
        for file_name in os.listdir(dir_path):
            if file_name.endswith('.lrc'):
                file_path = os.path.join(dir_path, file_name)
        if not file_path:
            self.write("Could not find saved lyrics.")
            return
        
        self.write(f"Saved lyrics found at: {file_path}")
        with open(file_path, 'r') as file:
            lyrics = file.read().strip()
            if not lyrics:
                self.write("Saved lyrics file is empty or corrupted.")
                return
            
            return lyrics

    def get_song_info(self, url):
        self.write(f"Getting song information from: {url}")
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            self.write(f"Failed to fetch song information. HTTP Status: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        page_title = soup.title.string if soup.title else None
        if not page_title:
            self.write("Could not retrieve page title. Invalid response from Spotify.")
            return
        self.write(f"Page title: {page_title}")

        split_str = " song by "
        if " and lyrics " in page_title:
            split_str = " song and lyrics by "
        title, artist_str = page_title.split(split_str)

        # Remove all non-alphanumeric characters.
        title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
        for word in TITLE_WORD_BLACKLIST:
            word_variations = [word, word.capitalize(), word.upper()]
            for word_variation in word_variations:
                title = title.replace(word_variation, '')
        # Combine multiple spaces into one.
        title = re.sub(r'\s+', ' ', title).strip()

        artists = artist_str.split(" | ")[0].split(", ")

        self.write(f"Title: {title}")
        self.write(f"Artists: {', '.join(artists)}")
        return artists, title

    def download_lyrics(self, artists, title, url):
        search_query = f"{title} {' '.join(artists)}"
        self.write(f"Searching for lyrics using syncedlyrics with query: {search_query}")
        
        save_path = None
        if SHOULD_SAVE_LYRICS:
            save_path = self.get_lyrics_dir_path(url)
            os.makedirs(save_path, exist_ok=True)
            save_path += f"{', '.join(artists)} - {title}.lrc"

        lyrics = syncedlyrics.search(search_query, save_path=save_path)
        if not lyrics:
            self.write("Syncedlyrics could not find lyrics for the song.")
            return
        
        self.write(f"Lyrics found and saved at: {save_path}")
        return lyrics


if __name__ == "__main__":
    print("Creating tkinter window.")
    root = TkinterDnD.Tk()
    app = EZSpotifyLyrics(root)

    print("Starting main loop.")
    root.mainloop()

    print("Exiting.")
