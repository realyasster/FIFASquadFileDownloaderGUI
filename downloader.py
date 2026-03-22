import json
import os
import re
import shutil
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, NamedTuple

from config import (
    ROSTERUPDATE_XML,
    RESULT_DIR,
    ARCHIVE_DIR,
    GAMES,
    PLATFORMS,
    T3DB,
    FBCHUNKS,
    BNRY,
)
from translations import format_date_localized, get_translation

ssl._create_default_https_context = ssl._create_unverified_context


def get_installed_squads(game: str, lang: str = "en") -> Dict:
    """
    Scan game settings folder for installed squad files.
    Extracts date from filename.
    """
    result = {"squads": None, "fut": None}

    if game not in GAMES:
        return result

    settings_path = GAMES[game]["settings_path"]

    if not settings_path.exists():
        return result

    for file in settings_path.rglob("Squads*"):
        if file.is_file():
            match = re.search(r"Squads(\d{8})\d+", file.name)
            if match:
                date_str = match.group(1)
                result["squads"] = {
                    "date": date_str,
                    "display": format_date_localized(lang, date_str),
                    "path": str(file),
                }
                break

    for file in settings_path.rglob("FutSquads*"):
        if file.is_file():
            match = re.search(r"FutSquads(\d{8})\d+", file.name)
            if match:
                date_str = match.group(1)
                result["fut"] = {
                    "date": date_str,
                    "display": format_date_localized(lang, date_str),
                    "path": str(file),
                }
                break

    return result


class SquadDownloader:
    def __init__(
        self, game: str = "FC 26", progress_callback: Optional[Callable] = None
    ):
        self.game = game
        self.progress_callback = progress_callback
        self._ensure_dirs()

        if game not in GAMES:
            raise ValueError(f"Unknown game: {game}")

        self.content_url = GAMES[game]["content_url"]
        self.game_archive_dir = GAMES[game]["archive_dir"]

    def _ensure_dirs(self):
        RESULT_DIR.mkdir(parents=True, exist_ok=True)

    def _report_progress(self, message: str, percent: int = 0):
        if self.progress_callback:
            self.progress_callback(message, percent)

    def download_file(self, fpath: Path, url: str) -> bool:
        self._report_progress(f"Downloading...", 0)
        try:
            fpath.parent.mkdir(parents=True, exist_ok=True)
            response = urllib.request.urlopen(url)
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            chunk_size = 8192

            with open(fpath, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        self._report_progress(f"Downloading... {percent}%", percent)

            return True
        except Exception as e:
            self._report_progress(f"Error: {e}", 0)
            return False

    def download_rosterupdate(self) -> Optional[str]:
        roster_update_url = f"{self.content_url}fc/fclive/genxtitle/rosterupdate.xml"
        xml_path = RESULT_DIR / self.game_archive_dir / ROSTERUPDATE_XML
        if self.download_file(xml_path, roster_update_url):
            return str(xml_path)
        return None

    def process_rosterupdate(self) -> Dict:
        result = {"platforms": []}
        to_collect = ["dbMajor", "dbFUTVer", "dbMajorLoc", "dbFUTLoc"]

        xml_path = self.download_rosterupdate()
        if not xml_path:
            return result

        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            squadinfoset = root[0]
            for child in squadinfoset:
                platform = {"name": child.attrib.get("platform", "unknown"), "tags": {}}
                for node in list(child.iter()):
                    if node.tag in to_collect:
                        platform["tags"][node.tag] = node.text

                result["platforms"].append(platform)
        except Exception as e:
            self._report_progress(f"XML parse hatası: {e}", 0)

        return result

    def unpack(self, fpath: Path) -> tuple:
        self._report_progress("Dosya açılıyor...", 0)

        SHORT_COPY = 0x80
        MEDIUM_COPY = 0x40
        LONG_COPY = 0x20

        with open(fpath, "rb") as f:
            data = f.read()

        size = int.from_bytes(data[2:5], "big")
        outbuf = bytearray(size)
        outbuf[: len(T3DB)] = T3DB

        ipos = 10
        opos = len(T3DB)
        in_len, out_len = len(data), len(outbuf)
        last_control = 0

        while ipos < in_len and opos < out_len:
            control = data[ipos]
            last_control = control
            ipos += 1

            if not (control & SHORT_COPY):
                b1 = data[ipos]
                ipos += 1
                lit = control & 3
                if lit:
                    outbuf[opos : opos + lit] = data[ipos : ipos + lit]
                    ipos += lit
                    opos += lit
                length = ((control >> 2) & 7) + 3
                offset = b1 + ((control & 0x60) << 3) + 1
                src = opos - offset
                for _ in range(length):
                    outbuf[opos] = outbuf[src]
                    opos += 1
                    src += 1

            elif not (control & MEDIUM_COPY):
                b2, b3 = data[ipos : ipos + 2]
                ipos += 2
                lit = b2 >> 6
                if lit:
                    outbuf[opos : opos + lit] = data[ipos : ipos + lit]
                    ipos += lit
                    opos += lit
                length = (control & 0x3F) + 4
                offset = ((b2 & 0x3F) << 8 | b3) + 1
                src = opos - offset
                for _ in range(length):
                    outbuf[opos] = outbuf[src]
                    opos += 1
                    src += 1

            elif not (control & LONG_COPY):
                b2, b3, b4 = data[ipos : ipos + 3]
                ipos += 3
                lit = control & 3
                if lit:
                    outbuf[opos : opos + lit] = data[ipos : ipos + lit]
                    ipos += lit
                    opos += lit
                length = b4 + ((control & 0x0C) << 6) + 5
                offset = (((control & 0x10) << 12) | (b2 << 8) | b3) + 1
                src = opos - offset
                for _ in range(length):
                    outbuf[opos] = outbuf[src]
                    opos += 1
                    src += 1

            else:
                lit = (control & 0x1F) * 4 + 4
                if lit > 0x70:
                    break
                outbuf[opos : opos + lit] = data[ipos : ipos + lit]
                ipos += lit
                opos += lit

        trailing = last_control & 3
        if trailing and opos < out_len:
            end_pos = min(opos + trailing, out_len)
            outbuf[opos:end_pos] = data[ipos : ipos + (end_pos - opos)]

        return bytes(outbuf), size

    def save_squads(self, buf: bytes, path: Path, filename: str) -> str:
        fullpath = path / filename
        is_fut = "Fut" in filename
        db_size = len(buf)

        save_type_squads = b"SaveType_Squads\x00"
        save_type_fut = b"SaveType_FUTSqu\x00"
        author_sign = b"Aranaktu"

        prefix_header_size = 1126
        main_header_size = 48
        bnry_size = 45985 if not is_fut else 0
        file_size = main_header_size + 4 + db_size + bnry_size

        prefix_header = bytearray(prefix_header_size)
        pos = 0

        prefix_header[pos : pos + len(FBCHUNKS)] = FBCHUNKS
        pos += len(FBCHUNKS)

        main_header_offset = prefix_header_size - pos - 8
        prefix_header[pos : pos + 4] = main_header_offset.to_bytes(4, "little")
        pos += 4

        prefix_header[pos : pos + 4] = file_size.to_bytes(4, "little")
        pos += 4

        ingame_name = f"EA_{filename}".encode()[:40]
        prefix_header[pos : pos + len(ingame_name)] = ingame_name
        pos += len(ingame_name)

        sign_size = 4 if is_fut else 7
        pos += sign_size
        prefix_header[pos : pos + len(author_sign)] = author_sign

        main_header = bytearray(main_header_size)
        save_type = save_type_fut if is_fut else save_type_squads
        main_header[: len(save_type)] = save_type

        crc_pos = len(save_type)
        main_header[crc_pos : crc_pos + 4] = (0).to_bytes(4, "little")

        data_size = 0 if is_fut else db_size + bnry_size

        with open(fullpath, "wb") as f:
            f.write(bytes(prefix_header))
            f.write(bytes(main_header))
            f.write(data_size.to_bytes(4, "little"))
            f.write(buf)

            if not is_fut:
                f.write(BNRY)
                remaining_bnry = bnry_size - len(BNRY)
                f.write(b"\x00" * remaining_bnry)

        return filename

    def download_squad(
        self, platform: str, download_squads: bool = True, download_fut: bool = True
    ) -> Dict:
        result = {"success": False, "squads": None, "fut": None, "error": None}

        self._report_progress("Fetching server data...", 5)
        roster_data = self.process_rosterupdate()

        if not roster_data.get("platforms"):
            result["error"] = f"Failed to fetch roster data from server"
            return result

        platform_data = None
        for p in roster_data.get("platforms", []):
            if p["name"] == platform:
                platform_data = p
                break

        if not platform_data:
            available = [p["name"] for p in roster_data.get("platforms", [])]
            result["error"] = f"Platform '{platform}' not found. Available: {available}"
            return result

        tags = platform_data["tags"]
        platform_path = RESULT_DIR / self.game_archive_dir / platform

        try:
            if download_squads:
                self._report_progress("Squads indiriliyor...", 20)
                ver = tags.get("dbMajor", "unknown")
                ver_path = platform_path / "squads" / ver
                ver_path.mkdir(parents=True, exist_ok=True)

                loc = tags.get("dbMajorLoc", "")
                if loc:
                    bin_fname = os.path.basename(loc)
                    bin_path = ver_path / bin_fname

                    if self.download_file(bin_path, f"{self.content_url}{loc}"):
                        self._report_progress("Squads işleniyor...", 50)
                        buf, sz = self.unpack(bin_path)
                        fdate = bin_fname.split("_")[1]
                        squad_name = f"Squads{fdate}000000"
                        self.save_squads(buf, ver_path, squad_name)
                        result["squads"] = str(ver_path / squad_name)
                        result["squads_date"] = fdate

            if download_fut:
                self._report_progress("FUT Squads indiriliyor...", 60)
                ver = tags.get("dbFUTVer", "unknown")
                ver_path = platform_path / "FUT" / ver
                ver_path.mkdir(parents=True, exist_ok=True)

                loc = tags.get("dbFUTLoc", "")
                if loc:
                    bin_fname = os.path.basename(loc)
                    bin_path = ver_path / bin_fname

                    if self.download_file(bin_path, f"{self.content_url}{loc}"):
                        self._report_progress("FUT Squads işleniyor...", 90)
                        buf, sz = self.unpack(bin_path)
                        fdate = bin_fname.split("_")[1]
                        fut_name = f"FutSquads{fdate}000000"
                        self.save_squads(buf, ver_path, fut_name)
                        result["fut"] = str(ver_path / fut_name)
                        result["fut_date"] = fdate

            result["success"] = True
            self._report_progress("Tamamlandı!", 100)

        except Exception as e:
            result["error"] = str(e)
            self._report_progress(f"Hata: {e}", 0)

        return result


class ArchiveEntry(NamedTuple):
    path: Path
    platform: str
    squad_type: str
    date_str: str
    display_name: str


class SquadArchiver:
    @staticmethod
    def _ensure_archive_dir():
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def archive_squad(
        source_path: Path,
        game: str,
        platform: str,
        squad_type: str,
        date_str: str,
    ) -> Optional[Path]:
        SquadArchiver._ensure_archive_dir()

        if not source_path.exists():
            return None

        if game not in GAMES:
            return None

        game_archive_dir = GAMES[game]["archive_dir"]

        archive_name = f"{squad_type}_{date_str}"
        archive_path = ARCHIVE_DIR / game_archive_dir / platform / archive_name

        archive_path.mkdir(parents=True, exist_ok=True)

        dest_file = archive_path / source_path.name
        if not dest_file.exists():
            shutil.copy2(source_path, dest_file)

        meta = {
            "platform": platform,
            "squad_type": squad_type,
            "date": date_str,
            "display_date": format_date_localized("en", date_str),
            "archived_at": datetime.now().isoformat(),
            "game": game,
        }

        meta_path = archive_path / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        return archive_path

    @staticmethod
    def list_archives(game: str = None, platform: str = None) -> List[ArchiveEntry]:
        SquadArchiver._ensure_archive_dir()

        archives = []

        if game and game in GAMES:
            search_path = ARCHIVE_DIR / GAMES[game]["archive_dir"]
            if platform:
                search_path = search_path / platform
        else:
            search_path = ARCHIVE_DIR

        if not search_path.exists():
            return archives

        for meta_file in search_path.rglob("meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                archive_path = meta_file.parent

                squad_files = list(archive_path.glob("Squads*")) + list(
                    archive_path.glob("FutSquads*")
                )
                if not squad_files:
                    squad_files = [
                        p
                        for p in archive_path.iterdir()
                        if p.is_file() and not p.suffix == ".json"
                    ]

                for squad_file in squad_files:
                    entry = ArchiveEntry(
                        path=squad_file,
                        platform=meta.get("platform", "unknown"),
                        squad_type=meta.get("squad_type", "unknown"),
                        date_str=meta.get("date", "unknown"),
                        display_name=f"{meta.get('squad_type', 'Squads')} - {meta.get('display_date', meta.get('date', 'unknown'))}",
                    )
                    archives.append(entry)
                    break
            except Exception:
                continue

        archives.sort(key=lambda x: x.date_str, reverse=True)
        return archives

    @staticmethod
    def restore_archive(archive_path: Path, game: str) -> bool:
        if game not in GAMES:
            return False

        dest_path = GAMES[game]["settings_path"]

        if not archive_path.exists():
            return False

        try:
            dest_path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(archive_path, dest_path / archive_path.name)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_archive(archive_path: Path) -> bool:
        archive_dir = archive_path.parent
        if (
            archive_dir.exists()
            and archive_dir.parent == ARCHIVE_DIR
            or archive_dir.parent.parent == ARCHIVE_DIR
            or archive_dir.parent.parent.parent == ARCHIVE_DIR
        ):
            try:
                shutil.rmtree(archive_dir)
                return True
            except Exception:
                return False
        return False


class SquadFile(NamedTuple):
    path: Path
    source: str
    platform: str
    squad_type: str
    date_str: str
    display_name: str


def list_available_squads(
    game: str, platform: str, lang: str = "en"
) -> List[SquadFile]:
    """
    List all available squads from both archive and result directories.
    """
    squads = []

    if game not in GAMES:
        return squads

    game_archive_dir = GAMES[game]["archive_dir"]
    platform_code = PLATFORMS.get(platform, "pc64")

    # Scan RESULT_DIR
    result_path = RESULT_DIR / game_archive_dir / platform_code
    if result_path.exists():
        for squad_file in result_path.rglob("Squads*"):
            if squad_file.is_file():
                match = re.search(r"Squads(\d{8})\d+", squad_file.name)
                if match:
                    date_str = match.group(1)
                    squads.append(
                        SquadFile(
                            path=squad_file,
                            source="result",
                            platform=platform_code,
                            squad_type="Squads",
                            date_str=date_str,
                            display_name=f"Squads - {format_date_localized(lang, date_str)} (downloaded)",
                        )
                    )

        for fut_file in result_path.rglob("FutSquads*"):
            if fut_file.is_file():
                match = re.search(r"FutSquads(\d{8})\d+", fut_file.name)
                if match:
                    date_str = match.group(1)
                    squads.append(
                        SquadFile(
                            path=fut_file,
                            source="result",
                            platform=platform_code,
                            squad_type="FUT",
                            date_str=date_str,
                            display_name=f"FUT - {format_date_localized(lang, date_str)} (downloaded)",
                        )
                    )

    # Scan ARCHIVE_DIR
    archive_path = ARCHIVE_DIR / game_archive_dir / platform_code
    if archive_path.exists():
        for meta_file in archive_path.rglob("meta.json"):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta = json.load(f)

                meta_dir = meta_file.parent
                for squad_file in meta_dir.glob("Squads*"):
                    if squad_file.is_file():
                        date_str = meta.get("date", "unknown")
                        squads.append(
                            SquadFile(
                                path=squad_file,
                                source="archive",
                                platform=meta.get("platform", platform_code),
                                squad_type=meta.get("squad_type", "Squads"),
                                date_str=date_str,
                                display_name=f"{meta.get('squad_type', 'Squads')} - {format_date_localized(lang, date_str)} (archived)",
                            )
                        )
                        break

                for fut_file in meta_dir.glob("FutSquads*"):
                    if fut_file.is_file():
                        date_str = meta.get("date", "unknown")
                        squads.append(
                            SquadFile(
                                path=fut_file,
                                source="archive",
                                platform=meta.get("platform", platform_code),
                                squad_type=meta.get("squad_type", "FUT"),
                                date_str=date_str,
                                display_name=f"{meta.get('squad_type', 'FUT')} - {format_date_localized(lang, date_str)} (archived)",
                            )
                        )
                        break
            except Exception:
                continue

    # Sort by date descending, deduplicate by date+squad_type
    squads.sort(key=lambda x: x.date_str, reverse=True)

    seen = set()
    unique_squads = []
    for squad in squads:
        key = (squad.date_str, squad.squad_type)
        if key not in seen:
            seen.add(key)
            unique_squads.append(squad)

    return unique_squads
