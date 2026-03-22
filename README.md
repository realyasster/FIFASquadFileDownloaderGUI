# FC Squad Downloader GUI

A modern GUI application to download squad files for EA Sports FC 24/25/26 directly from EA servers.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## If you like my work

                    buymeacoffee.com/realyasster                

## Features

- **Multi-Game Support**: FC 24, FC 25, FC 26
- **Multi-Platform**: PC64, PlayStation 5, PlayStation 4, Xbox Series X|S, Xbox One, Nintendo Switch
- **9 Languages**: English, Türkçe, Deutsch, Français, Italiano, Español, Português, 日本語, Русский
- **Auto-Import**: Automatically copy files to game settings folder
- **Archive Management**: Save and restore previous squad files
- **Download History**: Track all your downloads
- **No Credentials Required**: Downloads directly from EA public servers

## Screenshot

<img width="1717" height="1388" alt="image" src="https://github.com/user-attachments/assets/27a93c18-ca41-4c12-b5d5-3581cb2b2cba" />


## Installation

### Option 1: Download EXE (Recommended)

Download the latest release from [Releases](https://github.com/realyasster/FIFASquadFileDownloaderGUI/releases)

1. Download `FC_Squad_Downloader.exe`
2. Run the application
3. No installation required!

### Option 2: Run from Source

```bash
# Clone the repository
git clone https://github.com/realyasster/FIFASquadFileDownloaderGUI.git
cd FIFASquadFileDownloaderGUI

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Usage

1. **Select Game**: Choose FC 24, FC 25, or FC 26
2. **Select Platform**: PC64, PS5, PS4, Xbox Series X|S, Xbox One, or Nintendo Switch
3. **Choose File Types**: Check Squads and/or FUT
4. **Download**: Click "Download Latest Version"
5. **Import**: Click "Import to Game"

### In-Game Import

After importing, go to:
```
Profile > Squad Management > Import Squads
```

## Supported Games

| Game | Status | Server URL |
|------|--------|------------|
| FC 26 | ✅ Active | eafc26.content.easports.com |
| FC 25 | ✅ Active | eafc25.content.easports.com |
| FC 24 | ✅ Active | eafc24.content.easports.com |
| FIFA 23 | ❌ Closed | - |
| FIFA 22 | ❌ Closed | - |

## Game Settings Paths

| Game | Path |
|------|------|
| FC 26 | `%LOCALAPPDATA%\EA SPORTS FC 26\settings` |
| FC 25 | `%LOCALAPPDATA%\EA SPORTS FC 25\settings` |
| FC 24 | `%LOCALAPPDATA%\EA SPORTS FC 24\settings` |

## Building from Source

### Prerequisites

- Python 3.10 or higher
- pip

### Build EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller --onefile --windowed --name "FC_Squad_Downloader" main.py
```

The executable will be created in `dist/FC_Squad_Downloader.exe`

## Project Structure

```
FIFASquadFileDownloaderGUI/
├── main.py              # GUI application (CustomTkinter)
├── downloader.py        # Core download/unpack logic
├── config.py            # Constants, paths, game configs
├── translations.py      # Multi-language support
├── requirements.txt     # Python dependencies
├── LICENSE              # MIT License
└── README.md            # This file
```

## How It Works

1. Fetches `rosterupdate.xml` from EA servers
2. Parses platform-specific download URLs
3. Downloads compressed `.bin` files
4. Decompresses using custom LZ77 algorithm
5. Repackages into game-compatible format
6. Imports to game settings folder

## Technical Details

- **Compression**: Custom LZ77 variant used by EA
- **File Format**: FBCHUNKS header with SaveType_Squads/FUTSqu
- **Threading**: Background downloads with progress callbacks
- **Storage**: JSON for history and user settings

## Credits

- Original concept by [xAranaktu](https://github.com/xAranaktu/FIFASquadFileDownloader)
- GUI and enhancements by [realyasster](https://github.com/realyasster)

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

This tool is for educational purposes. Use at your own risk. Not affiliated with EA Sports.
