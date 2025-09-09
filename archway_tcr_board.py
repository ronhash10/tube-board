import os
import threading
import requests
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime, timedelta

# ======= Config =======
# Tube
TUBE_STATION_ID = "940GZZLUACY"      # Archway (Northern)
TUBE_LINE_ID = "northern"

# Bus (41 towards Tottenham Hale) – Archway Station, stop G
# Verified StopPoint id from TfL site:
BUS_STOPPOINT_ID = "490000008Z"      # Archway Station (Stop G) -> Tottenham Hale direction
BUS_LINE_ID = "41"

REFRESH_SEC = 15

# Optional TfL keys for higher rate limits
APP_ID = os.getenv("TFL_APP_ID")
APP_KEY = os.getenv("TFL_APP_KEY")

# ======= Fonts =======
def pick_pixel_font(root):
    preferred = ["VT323", "Press Start 2P", "Pixel Operator Mono", "Menlo", "DejaVu Sans Mono"]
    families = {f.lower(): f for f in tkfont.families(root)}
    chosen = None
    for fam in preferred:
        if fam.lower() in families:
            chosen = families[fam.lower()]
            break
    if chosen is None:
        chosen = "DejaVu Sans Mono"
    if chosen.lower() == "vt323":
        return chosen, 28, 16, 12
    if chosen.lower() == "press start 2p":
        return chosen, 18, 12, 10
    if chosen.lower() == "pixel operator mono":
        return chosen, 24, 14, 12
    return chosen, 24, 14, 12

# ======= Filters =======
def is_via_charing_cross(pred):
    text = " ".join([
        str(pred.get("platformName") or ""),
        str(pred.get("towards") or ""),
        str(pred.get("destinationName") or "")
    ]).lower()
    southbound = "southbound" in text or pred.get("direction", "").lower() == "inbound"
    via_cx = ("via charing cross" in text) or ("battersea power station" in text and "via bank" not in text)
    return southbound and via_cx

def is_bus_towards_tothale(pred):
    # being at stop G already picks the correct direction; still be explicit
    dest = (pred.get("destinationName") or "").lower()
    towards = (pred.get("towards") or "").lower()
    return ("tottenham hale" in dest) or ("tottenham hale" in towards)

# ======= Fetchers =======
def tfL_get(url, params):
    if APP_ID and APP_KEY:
        params = dict(params or {})
        params["app_id"] = APP_ID
        params["app_key"] = APP_KEY
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_tube_rows():
    base = f"https://api.tfl.gov.uk/StopPoint/{TUBE_STATION_ID}/Arrivals"
    data = tfL_get(base, {"line": TUBE_LINE_ID})
    filtered = [p for p in data if is_via_charing_cross(p)]
    filtered.sort(key=lambda p: p.get("timeToStation", 1e9))
    now = datetime.now()
    rows = []
    for p in filtered[:3]:
        secs = int(p.get("timeToStation", 0))
        mins = max(0, secs // 60)
        eta_str = "Due" if secs <= 30 else f"{mins} min"
        dest = (p.get("destinationName") or p.get("towards") or "").replace(" Underground Station", "")
        sched = (now + timedelta(seconds=secs)).strftime("%H:%M")
        rows.append({"eta": eta_str, "time": sched, "dest": dest})
    return rows

def fetch_bus_rows():
    base = f"https://api.tfl.gov.uk/StopPoint/{BUS_STOPPOINT_ID}/Arrivals"
    data = tfL_get(base, {"line": BUS_LINE_ID})
    filtered = [p for p in data if is_bus_towards_tothale(p)]
    filtered.sort(key=lambda p: p.get("timeToStation", 1e9))
    now = datetime.now()
    rows = []
    for p in filtered[:3]:
        secs = int(p.get("timeToStation", 0))
        mins = max(0, secs // 60)
        eta_str = "Due" if secs <= 30 else f"{mins} min"
        dest = (p.get("destinationName") or p.get("towards") or "")
        sched = (now + timedelta(seconds=secs)).strftime("%H:%M")
        rows.append({"eta": eta_str, "time": sched, "dest": dest})
    return rows

# ======= UI =======
class Board(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NORTHERN — Archway → Tottenham Court Road")
        self.configure(bg="black")
        self.geometry("820x300")
        self.resizable(False, False)

        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass

        fam, size_l, size_m, size_s = pick_pixel_font(self)
        self.font_h1   = (fam, size_l, "bold")
        self.font_col  = (fam, size_m, "bold")
        self.font_row  = (fam, size_l, "bold")
        self.font_foot = (fam, size_s)

        # mode: "tube" or "bus"
        self.mode = "tube"

        # ===== Banner with Toggle =====
        self.hdr = tk.Frame(self, bg="black")
        self.hdr.pack(fill="x", padx=20, pady=(12, 6))

        self.lbl_line  = tk.Label(self.hdr, text="NORTHERN", font=self.font_h1, fg="#FFD100", bg="black")
        self.lbl_route = tk.Label(self.hdr, text="Archway → Tottenham Court Road", font=self.font_h1, fg="#FFD100", bg="black")

        self.lbl_line.pack(side="left")
        tk.Label(self.hdr, text="   ", font=self.font_h1, fg="#FFD100", bg="black").pack(side="left")
        self.lbl_route.pack(side="left")

        # Toggle button
        self.toggle_btn = tk.Button(
            self.hdr, text="Show: Bus 41", relief="ridge",
            font=self.font_col, fg="#000000", bg="#FFD100",
            activeforeground="#000000", activebackground="#FFC700",
            command=self.toggle_mode
        )
        self.toggle_btn.pack(side="right")

        # ===== Table (headers + rows in one grid) =====
        self.table = tk.Frame(self, bg="black")
        self.table.pack(fill="x", padx=20)

        COL0_PX = 140  # DUE
        COL1_PX = 120  # TIME
        self.table.grid_columnconfigure(0, minsize=COL0_PX)
        self.table.grid_columnconfigure(1, minsize=COL1_PX)
        self.table.grid_columnconfigure(2, weight=1)  # DEST expands

        hdr_due  = tk.Label(self.table, text="DUE",         anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_time = tk.Label(self.table, text="TIME",        anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_dest = tk.Label(self.table, text="DESTINATION", anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_due.grid( row=0, column=0, sticky="w")
        hdr_time.grid(row=0, column=1, sticky="w", padx=(16, 0))
        hdr_dest.grid(row=0, column=2, sticky="w", padx=(32, 0))

        self.rows = []
        for i in range(3):
            eta  = tk.Label(self.table, text="--",    anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            tim  = tk.Label(self.table, text="--:--", anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            des  = tk.Label(self.table, text="—",     anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            eta.grid(row=i+1, column=0, sticky="w")
            tim.grid(row=i+1, column=1, sticky="w", padx=(16, 0))
            des.grid(row=i+1, column=2, sticky="w", padx=(32, 0))
            self.rows.append({"eta": eta, "time": tim, "dest": des})

        self.footer = tk.Label(self, text="Last updated —", font=self.font_foot, fg="#7CFC00", bg="black")
        self.footer.pack(pady=(0, 10))

        # Start loop
        self.after(200, self.refresh_loop)

    # ----- Toggle -----
    def toggle_mode(self):
        self.mode = "bus" if self.mode == "tube" else "tube"
        if self.mode == "bus":
            self.lbl_line.config(text="BUS 41")
            self.lbl_route.config(text="Archway → Tottenham Hale Bus Station")
            self.toggle_btn.config(text="Show: Tube")
        else:
            self.lbl_line.config(text="NORTHERN")
            self.lbl_route.config(text="Archway → Tottenham Court Road")
            self.toggle_btn.config(text="Show: Bus 41")
        # refresh immediately on toggle
        self.refresh_now()

    # ----- Refresh loop -----
    def refresh_now(self):
        try:
            if self.mode == "tube":
                preds = fetch_tube_rows()
            else:
                preds = fetch_bus_rows()
            self.update_rows(preds)
            self.footer.config(text=f"Last updated {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            self.rows[0]["dest"].config(text=f"Error: {e}")

    def refresh_loop(self):
        def work():
            self.refresh_now()
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
                self.rows[i]["dest"].config(text="No further services")
                
if __name__ == "__main__":
    Board().mainloop()
