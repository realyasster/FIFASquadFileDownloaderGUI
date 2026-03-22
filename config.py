import os
from pathlib import Path

ROSTERUPDATE_XML = "rosterupdate.xml"

PLATFORMS = {
    "PC64": "pc64",
    "PlayStation 5": "ps5",
    "PlayStation 4": "ps4",
    "Xbox Series X|S": "xbsx",
    "Xbox One": "xone",
    "Nintendo Switch": "nx",
}

PLATFORM_DISPLAY = {v: k for k, v in PLATFORMS.items()}

LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))

GAMES = {
    "FC 26": {
        "content_url": "https://eafc26.content.easports.com/fc/fltOnlineAssets/26E4D4D6-8DBB-4A9A-BD99-9C47D3AA341D/2026/",
        "settings_path": LOCAL_APPDATA / "EA SPORTS FC 26" / "settings",
        "archive_dir": "fc26",
    },
    "FC 25": {
        "content_url": "https://eafc25.content.easports.com/fc/fltOnlineAssets/25E4CDAE-799B-45BE-B257-667FDCDE8044/2025/",
        "settings_path": LOCAL_APPDATA / "EA SPORTS FC 25" / "settings",
        "archive_dir": "fc25",
    },
    "FC 24": {
        "content_url": "https://eafc24.content.easports.com/fc/fltOnlineAssets/24B23FDE-7835-41C2-87A2-F453DFDB2E82/2024/",
        "settings_path": LOCAL_APPDATA / "EA SPORTS FC 24" / "settings",
        "archive_dir": "fc24",
    },
}

BASE_DIR = Path(__file__).parent
RESULT_DIR = BASE_DIR / "result"
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
ARCHIVE_DIR = DATA_DIR / "archive"
SETTINGS_FILE = DATA_DIR / "settings.json"

T3DB = b"\x44\x42\x00\x08"
FBCHUNKS = b"\x46\x42\x43\x48\x55\x4e\x4b\x53\x01\x00"
BNRY = (
    b"\x42\x4e\x52\x59\x00\x00\x00\x02\x4c\x54\x4c\x45\x01\x01\x03\x00"
    b"\x00\x00\x63\x64\x73\x01\x00\x00\x00\x00\x01\x03\x00\x00\x00\x63\x64\x73"
)
