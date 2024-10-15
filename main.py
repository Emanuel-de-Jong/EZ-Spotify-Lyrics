import os
import re
import csv
import threading
import tkinter as tk
from tkinterdnd2 import DND_TEXT, TkinterDnD
import requests
from bs4 import BeautifulSoup
import syncedlyrics

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

    def save_lyrics_data(self):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for url, file_name in self.lyrics_data.items():
                writer.writerow([url, file_name])

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

    def handle_paste(self):
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
        
        if "spotify.com/track" not in url:
            self.write("Invalid Spotify URL. It should look like: https://open.spotify.com/track/xyz")
            return

        lyrics = None
        song_info_str = None
        if SHOULD_USE_SAVED_LYRICS and url in self.lyrics_data:
            file_name = self.lyrics_data[url]
            if not file_name:
                self.write("Lyrics search was previously unsuccessful for this URL.")
                return
            
            lyrics = self.get_existing_lyrics(file_name)
            song_info_str = file_name.replace(".lrc", "")

        self.lyrics_data[url] = ""

        if not lyrics:
            artists, title = self.get_song_info(url)
            if not artists or not title:
                return
            
            song_info_str = self.song_info_to_string(artists, title)

            lyrics = self.download_lyrics(artists, title, url)
            if not lyrics:
                return

            self.lyrics_data[url] = f"{song_info_str}.lrc"

        self.write(song_info_str, True)
        self.write(f"\n{lyrics}")

    def get_existing_lyrics(self, file_name):
        self.write("Using saved lyrics.")

        file_path = os.path.join(LYRICS_PATH, file_name)
        if not os.path.exists(file_path):
            self.write("Saved lyrics file is missing.")
            return

        self.write(f"Saved lyrics found at: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as file:
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
        if SHOULD_CUT_TITLE_AT_DASH:
            title = title.split(" - ")[0]
        title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
        blacklist_str = "|".join(TITLE_WORD_BLACKLIST)
        title = re.sub(r'\b(?:' + blacklist_str + r')\b', '', title, flags=re.IGNORECASE)
        # Combine multiple spaces into one.
        title = re.sub(r'\s+', ' ', title).strip()

        artist_str = artist_str.split(" | ")[0]
        # artist_str = re.sub(r'[^a-zA-Z0-9, ]', '', artist_str)
        artist_str = re.sub(r'\s+', ' ', artist_str).strip()
        artists = artist_str.split(", ")

        self.write(f"Title: {title}")
        self.write(f"Artists: {', '.join(artists)}")
        return artists, title

    def download_lyrics(self, artists, title, url):
        lyrics = self.download_from_syncedlyrics(artists, title)
        # if not lyrics:
        #     lyrics = self.download_from_scraper(artists, title)
        # if not lyrics:
        #     lyrics = self.download_from_xxx(artists, title)
        if not lyrics:
            return

        self.write(f"Lyrics found")

        if SHOULD_SAVE_LYRICS:
            save_file_name = f"{self.song_info_to_string(artists, title)}.lrc"
            save_file_path = os.path.join(LYRICS_PATH, save_file_name)
            os.makedirs(LYRICS_PATH, exist_ok=True)
            with open(save_file_path, 'w', encoding='utf-8') as file:
                file.write(lyrics)

            self.write(f"Lyrics saved at: {save_file_path}")

        return lyrics

    def song_info_to_string(self, artists, title):
        return f"{', '.join(artists)} - {title}"
    
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
    root = TkinterDnD.Tk()
    app = EZSpotifyLyrics(root)
    root.mainloop()
