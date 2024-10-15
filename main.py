import os
import re
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
FONT_SIZE = 16

BLACKLISTED_TITLE_WORDS = [
    "remix", "mix", "live", "extended", "radio", "edit", "version", "feat", "ft", "featuring", "asot"
]


def create_window():
    global root
    global text_box

    root = TkinterDnD.Tk()
    root.title("EZ Spotify Lyrics")
    root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

    scrollbar = tk.Scrollbar(root)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    text_box = tk.Text(root, yscrollcommand=scrollbar.set)
    text_box.drop_target_register(DND_TEXT)
    text_box.dnd_bind('<<Drop>>', lambda e: get_lyrics(e.data))
    text_box.pack(expand=True, fill=tk.BOTH)
    text_box.insert(tk.END, "Drag & drop a Spotify link here to get the lyrics.")

    scrollbar.config(command=text_box.yview)

def write(text="", should_clear=False):
    text += "\n"
    if should_clear:
        text_box.delete(1.0, tk.END)
    text_box.insert(tk.END, text)

def get_lyrics(url):
    write("STARTING", True)

    lyrics = None
    existing_lyrics_path = get_lyrics_dir_path(url)
    if SHOULD_USE_SAVED_LYRICS and os.path.exists(existing_lyrics_path):
        write("Using saved lyrics.")
        lyrics = get_existing_lyrics(existing_lyrics_path)
    
    if not lyrics:
        write("Getting lyrics from the internet.")
        artists, title = get_song_info(url)
        lyrics = download_lyrics(artists, title, url)
        if not lyrics:
            return

    write()
    write(lyrics)

def get_lyrics_dir_path(url):
    dir_name = url.split('/')[-1]
    return f"{LYRICS_PATH}{os.sep}{dir_name}{os.sep}"

def get_existing_lyrics(dir_path):
    file_path = None
    for file_name in os.listdir(dir_path):
        if file_name.endswith('.lrc'):
            file_path = os.path.join(dir_path, file_name)
    if not file_path:
        write("Could not find saved lyrics.")
        return
    
    write(f"Saved lyrics found at: {file_path}")
    
    with open(file_path, 'r') as file:
        return file.read()

def get_song_info(url):
    write(f"Getting song information from: {url}")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    page_title = soup.title.string
    write(f"Page title: {page_title}")

    split_str = " song by "
    if " and lyrics " in page_title:
        split_str = " song and lyrics by "
    title, artist_str = page_title.split(split_str)

    # Remove all non-alphanumeric characters.
    title = re.sub(r'[^a-zA-Z0-9 ]', '', title)
    for word in BLACKLISTED_TITLE_WORDS:
        word_variations = [word, word.capitalize(), word.upper()]
        for word_variation in word_variations:
            title = title.replace(word_variation, '')
    # Combine multiple spaces into one.
    title = re.sub(r'\s+', ' ', title).strip()

    artists = artist_str.split(" | ")[0].split(", ")

    write(f"Title: {title}")
    write(f"Aritsts: {', '.join(artists)}")
    return artists, title

def download_lyrics(artists, title, url):
    search_query = f"{title} {' '.join(artists)}"
    write(f"Searching for lyrics using syncedlyrics with query: {search_query}")
    
    save_path = None
    if SHOULD_SAVE_LYRICS:
        save_path = get_lyrics_dir_path(url)
        os.makedirs(save_path, exist_ok=True)
        save_path += f"{', '.join(artists)} - {title}.lrc"

    lyrics = syncedlyrics.search(search_query, save_path=save_path)
    if not lyrics:
        write("Syncedlyrics could not find lyrics for the song.")
        return
    
    write(f"Lyrics found and saved at: {save_path}")
    return lyrics


if __name__ == "__main__":
    print("Creating tkinter window.")
    create_window()

    print("Starting main loop.")
    root.mainloop()

    print("Exiting.")
