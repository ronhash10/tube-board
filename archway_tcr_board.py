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
BUS_STOPPOINT_ID = "490000008Z"      # Archway Station (Stop G) -> Tottenham Hale direction
BUS_LINE_ID = "41"

REFRESH_SEC = 15

# Optional TfL keys for higher rate limits
APP_ID = os.getenv("TFL_APP_ID")
APP_KEY = os.getenv("TFL_APP_KEY")

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
        self.title("Archway Departures")
        self.configure(bg="black")

        # Fullscreen + stable DPI
        self.attributes("-fullscreen", True)
        try:
            self.tk.call("tk", "scaling", 1.0)
        except Exception:
            pass
        self.bind("<Escape>", lambda e: self.destroy())

        # Screen-aware font sizes (tuned for 1280x720)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        size_l = max(36, int(sh * 0.070))      # row text
        size_h = max(40, int(sh * 0.080))      # section headers
        size_m = max(22, int(size_l * 0.60))   # column headers
        size_s = max(16, int(size_l * 0.42))   # footer

        families = {f.lower(): f for f in tkfont.families(self)}
        if "vt323" in families:
            fam = families["vt323"]
        elif "press start 2p" in families:
            fam = families["press start 2p"]
        else:
            fam = families.get("dejavu sans mono", "DejaVu Sans Mono")

        self.font_h1   = (fam, size_h, "bold")
        self.font_col  = (fam, size_m, "bold")
        self.font_row  = (fam, size_l, "bold")
        self.font_foot = (fam, size_s)

        # Outer container with bezel padding
        root = tk.Frame(self, bg="black")
        root.pack(fill="both", expand=True, padx=24, pady=16)

        # Shared column sizing
        self.sw = sw
        self.COL0_PX = max(140, int(sw * 0.16))  # DUE
        self.COL1_PX = max(120, int(sw * 0.14))  # TIME

        # ---- Section A: Tube (NORTHERN) ----
        self._section(
            parent=root,
            title_left="NORTHERN",
            title_right="Archway → Tottenham Court Road",
            table_key="tube"
        )

        # Spacer between sections
        tk.Frame(root, bg="black", height=10).pack(fill="x")

        # ---- Section B: Bus 41 ----
        self._section(
            parent=root,
            title_left="BUS 41",
            title_right="Archway → Tottenham Hale Bus Station",
            table_key="bus"
        )

        # Footer
        self.footer = tk.Label(root, text="Last updated —", font=self.font_foot, fg="#7CFC00", bg="black")
        self.footer.pack(pady=(8, 0))

        # Refresh loop
        self.after(200, self.refresh_loop)

    def _section(self, parent, title_left, title_right, table_key):
        # Banner
        hdr = tk.Frame(parent, bg="black")
        hdr.pack(fill="x", pady=(0, 8))
        tk.Label(hdr, text=title_left,  font=self.font_h1, fg="#FFD100", bg="black").pack(side="left")
        tk.Label(hdr, text="   ",       font=self.font_h1, fg="#FFD100", bg="black").pack(side="left")
        tk.Label(hdr, text=title_right, font=self.font_h1, fg="#FFD100", bg="black").pack(side="left")

        # Table
        table = tk.Frame(parent, bg="black")
        table.pack(fill="both", expand=True)

        table.grid_columnconfigure(0, minsize=self.COL0_PX)
        table.grid_columnconfigure(1, minsize=self.COL1_PX)
        table.grid_columnconfigure(2, weight=1)

        hdr_due  = tk.Label(table, text="DUE",         anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_time = tk.Label(table, text="TIME",        anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_dest = tk.Label(table, text="DESTINATION", anchor="w", font=self.font_col, fg="#7CFC00", bg="black")
        hdr_due.grid( row=0, column=0, sticky="w")
        hdr_time.grid(row=0, column=1, sticky="w", padx=(16, 0))
        hdr_dest.grid(row=0, column=2, sticky="we", padx=(32, 0))

        rows = []
        for i in range(3):
            eta  = tk.Label(table, text="--",    anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            tim  = tk.Label(table, text="--:--", anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            des  = tk.Label(table, text="—",     anchor="w", font=self.font_row, fg="#FFD100", bg="black")
            eta.grid(row=i+1, column=0, sticky="w")
            tim.grid(row=i+1, column=1, sticky="w", padx=(16, 0))
            des.grid(row=i+1, column=2, sticky="we", padx=(32, 0))
            des.configure(wraplength=0)
            rows.append({"eta": eta, "time": tim, "dest": des})

        # Store handle for updates
        if table_key == "tube":
            self.tube_rows = rows
        else:
            self.bus_rows = rows

    # -------- Refresh logic --------
    def refresh_loop(self):
        def work():
            try:
                tube = fetch_tube_rows()
            except Exception as e:
                tube = [{"eta": "—", "time": "—", "dest": f"TfL error: {e}"}]
            try:
                bus = fetch_bus_rows()
            except Exception as e:
                bus = [{"eta": "—", "time": "—", "dest": f"TfL error: {e}"}]

            self.after(0, lambda: self.update_section(self.tube_rows, tube))
            self.after(0, lambda: self.update_section(self.bus_rows,  bus))
            self.after(0, lambda: self.footer.config(text=f"Last updated {datetime.now().strftime('%H:%M:%S')}"))

            self.after(REFRESH_SEC * 1000, self.refresh_loop)

        threading.Thread(target=work, daemon=True).start()

    def update_section(self, row_widgets, preds):
        for i in range(3):
            if i < len(preds):
                r = preds[i]
                row_widgets[i]["eta"].config(text=r["eta"])
                row_widgets[i]["time"].config(text=r["time"])
                row_widgets[i]["dest"].config(text=r["dest"])
            else:
                row_widgets[i]["eta"].config(text="—")
                row_widgets[i]["time"].config(text="—")
                row_widgets[i]["dest"].config(text="No further services")

if __name__ == "__main__":
    Board().mainloop()
