import tkinter as tk
from tkinterdnd2 import DND_TEXT, TkinterDnD
import requests
from bs4 import BeautifulSoup
import re
import syncedlyrics

BLACKLISTED_TITLE_WORDS = [
    "remix", "mix", "live", "extended", "radio", "edit", "version", "feat", "ft", "featuring", "asot"
]

root = TkinterDnD.Tk()
root.title("EZ Spotify Lyrics")
root.geometry("600x600")

scrollbar = tk.Scrollbar(root)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

text_box = tk.Text(root, yscrollcommand=scrollbar.set)
text_box.drop_target_register(DND_TEXT)
text_box.dnd_bind('<<Drop>>', lambda e: get_lyrics(e.data))
text_box.pack(expand=True, fill=tk.BOTH)

scrollbar.config(command=text_box.yview)

def write(text):
    text_box.delete(1.0, tk.END)
    text_box.insert(tk.END, text)

def get_lyrics(url):
    artists, title = get_song_info(url)
    print(artists)
    print(title)

def get_song_info(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    page_title = soup.title.string
    print(page_title)

    split_str = " song by "
    if " and lyrics " in page_title:
        split_str = " song and lyrics by "
    title, artist_str = page_title.split(split_str)

    title = re.sub(r'[^a-zA-Z0-9 ]', '', title).lower()
    for word in BLACKLISTED_TITLE_WORDS:
        title = title.replace(word, '')
    title = re.sub(r'\s+', ' ', title).strip()

    artists = artist_str.split(" | ")[0].split(", ")

    return artists, title

if __name__ == "__main__":
    root.mainloop()