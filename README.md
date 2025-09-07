# Tube Board (Archway → Tottenham Court Road)

Python Tkinter app that displays live Northern line departures from **Archway** to **Tottenham Court Road**, using the TfL Unified API.

## Features
- Pixel-style UI mimicking station dot-matrix boards
- Filters trains to show only those via Charing Cross branch
- Auto-refreshes every 15 seconds

## Setup
```bash
git clone https://github.com/your-username/tube-board.git
cd tube-board
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make run