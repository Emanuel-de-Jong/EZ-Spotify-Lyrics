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

    def handle_drop(self, event):
        if self.is_lyrics_search_ongoing:
            return
        
        self.handle_new_url(event.data)

    def handle_paste(self):
        if self.is_lyrics_search_ongoing:
            return
        
        try:
            self.handle_new_url(self.root.clipboard_get())
        except tk.TclError:
            self.write("Your clipboard does not have a url in it.", True)

    def write(self, text="", should_clear=False):
        text += "\n"
        if should_clear:
            self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, text)

    def handle_new_url(self, url):
        threading.Thread(target=self.start_lyrics_search, args=(url,)).start()

    def start_lyrics_search(self, url):
        self.is_lyrics_search_ongoing = True
        self.get_lyrics(url)
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
        
        if "spotify.com/track" not in url:
            self.write("Invalid Spotify URL. It should look like: https://open.spotify.com/track/xyz")
            return

        lyrics = None
        existing_lyrics_path = self.get_lyrics_dir_path(url)
        if SHOULD_USE_SAVED_LYRICS and os.path.exists(existing_lyrics_path):
            lyrics = self.get_existing_lyrics(existing_lyrics_path)
        
        if not lyrics:
            artists, title = self.get_song_info(url)
            if not artists or not title:
                return

            lyrics = self.download_lyrics(artists, title, url)
            if not lyrics:
                return

        self.write(f"\n{lyrics}")

    def get_lyrics_dir_path(self, url):
        dir_name = url.split('/')[-1]
        return os.path.join(LYRICS_PATH, dir_name)

    def get_existing_lyrics(self, dir_path):
        self.write("Using saved lyrics.")

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
        self.write(f"Getting song information from the URL page...")
        try:
            response = requests.get(url, timeout=10)
            # Raise exception for non-2xx status codes
            response.raise_for_status()
        except requests.RequestException as e:
            self.write(f"Error: {str(e)}")
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
        if split_str not in page_title:
            self.write("Could not extract song information from the page title.")
            return

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
        lyrics = self.download_from_syncedlyrics(artists, title)
        if not lyrics:
            lyrics = self.download_from_scraper(artists, title)
        # if not lyrics:
        #     lyrics = self.download_from_xxx(artists, title)
        if not lyrics:
            return

        self.write(f"Lyrics found")

        if SHOULD_SAVE_LYRICS:
            save_dir_path = self.get_lyrics_dir_path(url)
            os.makedirs(save_dir_path, exist_ok=True)

            save_file_path = os.path.join(save_dir_path, f"{', '.join(artists)} - {title}.lrc")
            with open(save_file_path, 'w') as file:
                file.write(lyrics)

            self.write(f"Lyrics saved at: {save_file_path}")

        return lyrics
    
    def download_from_syncedlyrics(self, artists, title):
        package_name = "Syncedlyrics"

        self.write(f"Using {package_name} (Musixmatch, Lrclib, NetEase, Megalobiz, Genius).")
        search_query = f"{title} {' '.join(artists)}"
        self.write(f"Query: {search_query}")

        self.write("Searching...")
        lyrics = syncedlyrics.search(search_query, save_path=None)
        if not lyrics:
            self.write(package_name + self.LYRICS_PACKAGE_FAIL_MSG)
            return

        return lyrics

    def download_from_scraper(self, artists, title):
        package_name = "Scraper"

        self.write(f"Using {package_name} (AZLyrics).")
        artist = artists[0].lower().replace(" ", "")
        title = title.lower().replace(" ", "")
        url = f"https://www.azlyrics.com/lyrics/{artist}/{title}.html"
        self.write(f"URL: {url}")

        self.write("Searching...")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            self.write(f"Error: {str(e)}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        # Lyrics are stored in the first empty div.
        divs = soup.find_all("div", class_=None, id=None)
        if not divs or len(divs) < 1:
            self.write(package_name + self.LYRICS_PACKAGE_FAIL_MSG)
            return

        lyrics = divs[0].get_text(separator="\n").strip()
        if not lyrics:
            self.write(package_name + self.LYRICS_PACKAGE_FAIL_MSG)
            return
        
        return lyrics
    
    def download_from_xxx(self, artists, title):
        package_name = "Xxx"

        self.write(f"Using {package_name} (source1, source2).")

        self.write("Searching...")
        lyrics = None
        if not lyrics:
            self.write(package_name + self.LYRICS_PACKAGE_FAIL_MSG)
            return

        return lyrics


if __name__ == "__main__":
    print("Creating tkinter window.")
    root = TkinterDnD.Tk()
    app = EZSpotifyLyrics(root)

    print("Starting main loop.")
    root.mainloop()

    print("Exiting.")
