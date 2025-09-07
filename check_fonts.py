import tkinter as tk
from tkinter import font

root = tk.Tk()
print([f for f in font.families() if "vt" in f.lower() or "press" in f.lower()])
root.destroy()
