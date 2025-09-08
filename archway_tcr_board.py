import os
import threading
import requests
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta

# ---- Config ----
STATION_ID = "940GZZLUACY"  # Archway (Northern)
LINE_ID = "northern"
REFRESH_SEC = 15

APP_ID = os.getenv("TFL_APP_ID")
APP_KEY = os.getenv("TFL_APP_KEY")

# ---- Pixel / dot-matrix font selection ----
def pick_pixel_font(root):
    """
    Prefer VT323 → Press Start 2P → Pixel Operator Mono → Menlo → DejaVu Sans Mono.
    Returns (family, size_large, size_medium, size_small).
    """
    preferred = ["VT323", "Press Start 2P", "Pixel Operator Mono", "Menlo", "DejaVu Sans Mono"]
    families = {f.lower(): f for f in tkfont.families(root)}  # map for exact casing

    chosen = None
    for fam in preferred:
        if fam.lower() in families:
            chosen = families[fam.lower()]
            break
    if chosen is None:
        chosen = "DejaVu Sans Mono"

    # Sizes tuned for Retina; tweak up/down if needed
    if chosen.lower() == "vt323":
        return chosen, 28, 16, 12   # large, medium, small
    if chosen.lower() == "press start 2p":
        return chosen, 18, 12, 10
    if chosen.lower() == "pixel operator mono":
        return chosen, 24, 14, 12
    return chosen, 24, 14, 12

# ---- Branch filter: trains that will call at Tottenham Court Road (via Charing Cross)
def is_via_charing_cross(pred):
    text = " ".join([
        str(pred.get("platformName") or ""),
        str(pred.get("towards") or ""),
        str(pred.get("destinationName") or "")
    ]).lower()
    southbound = "southbound" in text or pred.get("direction", "").lower() == "inbound"
    via_cx = ("via charing cross" in text) or ("battersea power station" in text and "via bank" not in text)
    return southbound and via_cx

def fetch_predictions():
    base = f"https://api.tfl.gov.uk/StopPoint/{STATION_ID}/Arrivals"
    params = {"line": LINE_ID}
    if APP_ID and APP_KEY:
        params["app_id"] = APP_ID
        params["app_key"] = APP_KEY

    r = requests.get(base, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    filtered = [p for p in data if is_via_charing_cross(p)]
    filtered.sort(key=lambda p: p.get("timeToStation", 1e9))

    rows = []
    now = datetime.now()
    for p in filtered[:3]:
        secs = int(p.get("timeToStation", 0))
        mins = max(0, secs // 60)
        eta_str = "Due" if secs <= 30 else f"{mins} min"
        dest = (p.get("destinationName") or p.get("towards") or "").replace(" Underground Station", "")
        sched = (now + timedelta(seconds=secs)).strftime("%H:%M")
        rows.append({"eta": eta_str, "time": sched, "dest": dest})
    return rows

# ---- UI ----
class Board(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NORTHERN — Archway → Tottenham Court Road")
        self.configure(bg="black")
        self.geometry("760x260")
        self.resizable(False, False)

        # Optional: consistent sizing on Retina
        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        # --- Fonts ---
        fam, size_l, size_m, size_s = pick_pixel_font(self)
        self.font_h1   = (fam, size_l, "bold")
        self.font_col  = (fam, size_m, "bold")
        self.font_row  = (fam, size_l, "bold")
        self.font_foot = (fam, size_s)

        # ===== TOP BANNER =====
        self.hdr = tk.Frame(self, bg="black")
        self.hdr.pack(fill="x", padx=20, pady=(12, 6))

        lbl_line = tk.Label(self.hdr, text="NORTHERN", font=self.font_h1, fg="#FFD100", bg="black")
        lbl_line.pack(side="left")

        # spacer between “NORTHERN” and route text
        tk.Label(self.hdr, text="   ", font=self.font_h1, fg="#FFD100", bg="black").pack(side="left")

        lbl_route = tk.Label(
            self.hdr, text="Archway → Tottenham Court Road", font=self.font_h1, fg="#FFD100", bg="black"
        )
        lbl_route.pack(side="left")

        # ===== TABLE (headers + rows in one grid) =====
        self.table = tk.Frame(self, bg="black")
        self.table.pack(fill="x", padx=20)

        # Column sizing (in pixels)
        COL0_PX = 140  # DUE
        COL1_PX = 120  # TIME
        # COL2 (DESTINATION) expands to fill

        self.table.grid_columnconfigure(0, minsize=COL0_PX)
        self.table.grid_columnconfigure(1, minsize=COL1_PX)
        self.table.grid_columnconfigure(2, weight=1)

        # --- Headers ---
        hdr_due  = tk.Label(self.table, text="DUE",         anchor="w",
                            font=self.font_col, fg="#7CFC00", bg="black")
        hdr_time = tk.Label(self.table, text="TIME",        anchor="w",
                            font=self.font_col, fg="#7CFC00", bg="black")
        hdr_dest = tk.Label(self.table, text="DESTINATION", anchor="w",
                            font=self.font_col, fg="#7CFC00", bg="black")

        hdr_due.grid( row=0, column=0, sticky="w")
        hdr_time.grid(row=0, column=1, sticky="w", padx=(16, 0))
        hdr_dest.grid(row=0, column=2, sticky="w", padx=(32, 0))

        # --- Data rows ---
        self.rows = []
        for i in range(3):
            eta  = tk.Label(self.table, text="--",    anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            time = tk.Label(self.table, text="--:--", anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            dest = tk.Label(self.table, text="—",     anchor="w", font=self.font_row, fg="#FFD100", bg="black")

            eta.grid( row=i+1, column=0, sticky="w")
            time.grid(row=i+1, column=1, sticky="w", padx=(16, 0))
            dest.grid(row=i+1, column=2, sticky="w", padx=(32, 0))

            self.rows.append({"eta": eta, "time": time, "dest": dest})

        # ===== FOOTER =====
        self.footer = tk.Label(self, text="Last updated —", font=self.font_foot, fg="#7CFC00", bg="black")
        self.footer.pack(pady=(0, 10))

        # ===== START REFRESH LOOP =====
        self.after(200, self.refresh_loop)


    def refresh_loop(self):
        def work():
            try:
                preds = fetch_predictions()
                self.update_rows(preds)
                self.footer.config(text=f"Last updated {datetime.now().strftime('%H:%M:%S')}")
            except Exception as e:
                self.rows[0]["dest"].config(text=f"Error fetching data: {e}")
            self.after(REFRESH_SEC * 1000, self.refresh_loop)
        threading.Thread(target=work, daemon=True).start()

    def update_rows(self, preds):
        for i in range(3):
            if i < len(preds):
                r = preds[i]
                self.rows[i]["eta"].config(text=r["eta"])
                self.rows[i]["time"].config(text=r["time"])
                self.rows[i]["dest"].config(text=r["dest"])
            else:
                self.rows[i]["eta"].config(text="—")
                self.rows[i]["time"].config(text="—")
                self.rows[i]["dest"].config(text="No further trains")

if __name__ == "__main__":
    Board().mainloop()
