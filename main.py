import tkinter as tk
from tkinterdnd2 import DND_TEXT, TkinterDnD
import requests
from bs4 import BeautifulSoup
import re
import syncedlyrics


root = TkinterDnD.Tk()
root.title("EZ Spotify Lyrics")
root.geometry("600x800")

# main_frame = tk.Frame(root, width=600, height=1000)
# main_frame.pack()

scrollbar = tk.Scrollbar(root)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

text_box = tk.Text(root, yscrollcommand=scrollbar.set)
text_box.drop_target_register(DND_TEXT)
text_box.dnd_bind('<<Drop>>', lambda e: get_lyrics(e.data))
text_box.pack(expand=True, fill=tk.BOTH)

# text.insert(tk.END, "Hello")

scrollbar.config(command=text_box.yview)

def write(text):
    text_box.insert(tk.END, text)

def get_lyrics(url):
    title = get_title(url)
    print(title)

def get_title(url):
    response = requests.get(url)

    print(response.text)

    soup = BeautifulSoup(response.text, 'html.parser')

    title_tag = soup.find('h1', class_='encore-text-headline-large')
    if not title_tag:
        write(f"Can't find title in page")
        return

    title = title_tag.get_text()
    title = re.sub(r'[^a-zA-Z0-9 ]', '', title).strip().lower()
    return title

if __name__ == "__main__":
    root.mainloop()