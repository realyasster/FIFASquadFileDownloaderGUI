import json
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from tkinter import messagebox

from config import (
    PLATFORMS,
    RESULT_DIR,
    DATA_DIR,
    HISTORY_FILE,
    ARCHIVE_DIR,
    GAMES,
    SETTINGS_FILE,
)
from downloader import (
    SquadDownloader,
    SquadArchiver,
    get_installed_squads,
    list_available_squads,
)
from translations import (
    TRANSLATIONS,
    LANGUAGE_FLAGS,
    LANGUAGE_NAMES,
    SUPPORTED_LANGUAGES,
    get_translation,
    format_date_localized,
)


class LanguageSelectorPopup(ctk.CTkToplevel):
    def __init__(self, parent, current_lang: str, on_select_callback):
        super().__init__(parent)

        self.on_select_callback = on_select_callback
        self.selected_lang = current_lang

        self.title("Select Language")
        self.geometry("280x420")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self):
        label = ctk.CTkLabel(
            self, text="Select Language", font=ctk.CTkFont(size=18, weight="bold")
        )
        label.pack(pady=15)

        for lang_code in SUPPORTED_LANGUAGES:
            flag = LANGUAGE_FLAGS.get(lang_code, "🌐")
            name = LANGUAGE_NAMES.get(lang_code, lang_code)

            btn = ctk.CTkButton(
                self,
                text=f"{flag}  {name}",
                command=lambda lc=lang_code: self._on_select(lc),
                height=40,
                font=ctk.CTkFont(size=14),
                anchor="w",
            )
            btn.pack(fill="x", padx=20, pady=5)

    def _on_select(self, lang_code: str):
        self.selected_lang = lang_code
        self.on_select_callback(lang_code)
        self.destroy()


class SquadSelectorDialog(ctk.CTkToplevel):
    def __init__(
        self, parent, game: str, platform: str, lang: str, on_restore_callback
    ):
        super().__init__(parent)

        self.game = game
        self.platform = platform
        self.lang = lang
        self.on_restore_callback = on_restore_callback

        self.title(self.t("archived_squads"))
        self.geometry("550x450")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self._load_squads()

    def t(self, key: str, **kwargs) -> str:
        return get_translation(self.lang, key, **kwargs)

    def _create_widgets(self):
        label = ctk.CTkLabel(
            self,
            text=self.t("archived_squads"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        label.pack(pady=15)

        self.squad_frame = ctk.CTkScrollableFrame(self)
        self.squad_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.squad_vars = []

        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=20, pady=15)

        self.restore_btn = ctk.CTkButton(
            button_frame,
            text=self.t("load_selected"),
            command=self._restore_selected,
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self.restore_btn.pack(side="left", padx=10, fill="x", expand=True)

        self.delete_btn = ctk.CTkButton(
            button_frame,
            text=self.t("delete"),
            command=self._delete_selected,
            height=40,
            fg_color="red",
            hover_color="darkred",
            font=ctk.CTkFont(size=14),
        )
        self.delete_btn.pack(side="left", padx=10, fill="x", expand=True)

        self.close_btn = ctk.CTkButton(
            button_frame,
            text="Close",
            command=self.destroy,
            height=40,
            fg_color="#4a4a4a",
            font=ctk.CTkFont(size=14),
        )
        self.close_btn.pack(side="left", padx=10, fill="x", expand=True)

    def _load_squads(self):
        for widget in self.squad_frame.winfo_children():
            widget.destroy()

        self.squad_vars = []

        platform_code = PLATFORMS.get(self.platform, "pc64")
        squads = list_available_squads(self.game, platform_code, self.lang)

        if not squads:
            no_squad = ctk.CTkLabel(
                self.squad_frame, text=self.t("no_archives"), text_color="gray"
            )
            no_squad.pack(pady=20)
            return

        self.squads = squads

        for i, squad in enumerate(squads):
            var = ctk.IntVar(value=0)
            self.squad_vars.append(var)

            frame = ctk.CTkFrame(self.squad_frame)
            frame.pack(fill="x", pady=5, padx=5)

            rb = ctk.CTkRadioButton(
                frame,
                text=squad.display_name,
                variable=var,
                value=i,
                font=ctk.CTkFont(size=13),
            )
            rb.pack(side="left", padx=10, pady=10)

            source_icon = "📁" if squad.source == "archive" else "📥"
            info = ctk.CTkLabel(frame, text=source_icon, font=ctk.CTkFont(size=16))
            info.pack(side="right", padx=10, pady=10)

    def _restore_selected(self):
        for i, var in enumerate(self.squad_vars):
            if var.get() == i:
                squad = self.squads[i]

                settings_path = GAMES.get(self.game, {}).get("settings_path")
                if not settings_path:
                    messagebox.showerror(self.t("error"), self.t("error_no_game_path"))
                    return

                try:
                    settings_path.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(squad.path, settings_path / squad.path.name)

                    messagebox.showinfo(
                        "Success", self.t("success_restore", name=squad.display_name)
                    )
                    self.on_restore_callback()
                    self.destroy()
                except Exception as e:
                    messagebox.showerror(self.t("error"), str(e))
                return

        messagebox.showwarning("Warning", self.t("warning_select_archive"))

    def _delete_selected(self):
        for i, var in enumerate(self.squad_vars):
            if var.get() == i:
                squad = self.squads[i]

                if squad.source != "archive":
                    messagebox.showinfo(
                        "Info",
                        "Downloaded files cannot be deleted from here.\nDelete from result folder.",
                    )
                    return

                if messagebox.askyesno(
                    self.t("delete"), self.t("confirm_delete", name=squad.display_name)
                ):
                    if SquadArchiver.delete_archive(squad.path):
                        self._load_squads()
                    else:
                        messagebox.showerror(self.t("error"), "Delete failed!")
                return

        messagebox.showwarning("Warning", self.t("warning_select_archive"))


class FC26SquadDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._ensure_dirs()
        self._load_settings()
        self._load_history()

        self.title(self.t("title"))
        self.geometry("650x700")
        self.minsize(650, 700)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._create_widgets()
        self._update_installed_squads()

    def t(self, key: str, **kwargs) -> str:
        return get_translation(self.current_lang, key, **kwargs)

    def _ensure_dirs(self):
        RESULT_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        if not HISTORY_FILE.exists():
            with open(HISTORY_FILE, "w") as f:
                json.dump({"downloads": []}, f)
        if not SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "w") as f:
                json.dump(
                    {"language": "en", "last_game": "FC 26", "last_platform": "PC64"}, f
                )

    def _load_settings(self):
        try:
            with open(SETTINGS_FILE, "r") as f:
                self.settings = json.load(f)
        except:
            self.settings = {
                "language": "en",
                "last_game": "FC 26",
                "last_platform": "PC64",
            }

        self.current_lang = self.settings.get("language", "en")

    def _save_settings(self):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=2)

    def _load_history(self):
        try:
            with open(HISTORY_FILE, "r") as f:
                self.history = json.load(f)
        except:
            self.history = {"downloads": []}

    def _save_history(self):
        with open(HISTORY_FILE, "w") as f:
            json.dump(self.history, f, indent=2)

    def _add_to_history(
        self, game: str, platform: str, squad_type: str, squad_date: str, path: str
    ):
        entry = {
            "date": datetime.now().isoformat(),
            "game": game,
            "platform": platform,
            "type": squad_type,
            "squad_date": squad_date,
            "path": path,
        }
        self.history["downloads"].insert(0, entry)
        if len(self.history["downloads"]) > 50:
            self.history["downloads"] = self.history["downloads"][:50]
        self._save_history()
        self._update_history_list()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title bar with language selector
        title_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 15))

        self.title_label = ctk.CTkLabel(
            title_frame, text=self.t("title"), font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title_label.pack(side="left")

        flag = LANGUAGE_FLAGS.get(self.current_lang, "🌐")
        name = LANGUAGE_NAMES.get(self.current_lang, self.current_lang)
        lang_display = f"{flag} {name}"

        self.lang_var = ctk.StringVar(value=lang_display)
        self.lang_menu = ctk.CTkOptionMenu(
            title_frame,
            variable=self.lang_var,
            values=[
                f"{LANGUAGE_FLAGS[l]} {LANGUAGE_NAMES[l]}" for l in SUPPORTED_LANGUAGES
            ],
            command=self._on_language_change,
            width=130,
        )
        self.lang_menu.pack(side="right")

        # Selection frame (left: game/platform, right: installed squads)
        selection_frame = ctk.CTkFrame(main_frame)
        selection_frame.pack(fill="x", pady=10)
        selection_frame.grid_columnconfigure(0, weight=1)
        selection_frame.grid_columnconfigure(1, weight=1)

        # Left frame
        left_frame = ctk.CTkFrame(selection_frame)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        self.game_label = ctk.CTkLabel(
            left_frame, text=self.t("game"), font=ctk.CTkFont(size=13)
        )
        self.game_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.game_var = ctk.StringVar(value=self.settings.get("last_game", "FC 26"))
        self.game_menu = ctk.CTkOptionMenu(
            left_frame,
            variable=self.game_var,
            values=list(GAMES.keys()),
            command=self._on_game_change,
        )
        self.game_menu.pack(fill="x", padx=10, pady=5)

        self.platform_label = ctk.CTkLabel(
            left_frame, text=self.t("platform"), font=ctk.CTkFont(size=13)
        )
        self.platform_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.platform_var = ctk.StringVar(
            value=self.settings.get("last_platform", "PC64")
        )
        self.platform_menu = ctk.CTkOptionMenu(
            left_frame,
            variable=self.platform_var,
            values=list(PLATFORMS.keys()),
            command=self._on_platform_change,
        )
        self.platform_menu.pack(fill="x", padx=10, pady=5)

        # Checkboxes
        checkbox_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        checkbox_frame.pack(fill="x", padx=10, pady=10)

        self.squads_var = ctk.BooleanVar(value=True)
        self.fut_var = ctk.BooleanVar(value=True)

        self.squads_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text=self.t("squads"),
            variable=self.squads_var,
            font=ctk.CTkFont(size=13),
        )
        self.squads_checkbox.pack(side="left", padx=5)

        self.fut_checkbox = ctk.CTkCheckBox(
            checkbox_frame,
            text=self.t("fut"),
            variable=self.fut_var,
            font=ctk.CTkFont(size=13),
        )
        self.fut_checkbox.pack(side="left", padx=5)

        # Right frame
        right_frame = ctk.CTkFrame(selection_frame)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        self.installed_label = ctk.CTkLabel(
            right_frame,
            text=self.t("installed_squads"),
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.installed_label.pack(anchor="w", padx=10, pady=(10, 5))

        self.squads_installed_label = ctk.CTkLabel(
            right_frame, text="Squads: ...", font=ctk.CTkFont(size=12)
        )
        self.squads_installed_label.pack(anchor="w", padx=20, pady=2)

        self.fut_installed_label = ctk.CTkLabel(
            right_frame, text="FUT: ...", font=ctk.CTkFont(size=12)
        )
        self.fut_installed_label.pack(anchor="w", padx=20, pady=2)

        self.refresh_btn = ctk.CTkButton(
            right_frame,
            text=self.t("refresh"),
            command=self._update_installed_squads,
            width=80,
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.refresh_btn.pack(anchor="w", padx=20, pady=10)

        # Download buttons
        download_frame = ctk.CTkFrame(main_frame)
        download_frame.pack(fill="x", pady=10)

        self.download_btn = ctk.CTkButton(
            download_frame,
            text=self.t("download_latest"),
            command=self._start_download,
            height=45,
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self.download_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.archive_btn = ctk.CTkButton(
            download_frame,
            text=self.t("load_archive"),
            command=self._open_squad_dialog,
            height=45,
            fg_color="#4a4a4a",
            font=ctk.CTkFont(size=14),
        )
        self.archive_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        # Progress
        self.progress_bar = ctk.CTkProgressBar(main_frame, height=15)
        self.progress_bar.pack(fill="x", pady=5)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(
            main_frame,
            text=self.t("ready"),
            text_color="gray",
            font=ctk.CTkFont(size=13),
        )
        self.status_label.pack(pady=5)

        # History
        self.history_label = ctk.CTkLabel(
            main_frame,
            text=self.t("download_history"),
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.history_label.pack(pady=(15, 5))

        self.history_scroll = ctk.CTkScrollableFrame(main_frame, height=120)
        self.history_scroll.pack(fill="both", expand=True, pady=5)

        self._update_history_list()

        # Action buttons
        action_frame = ctk.CTkFrame(main_frame)
        action_frame.pack(fill="x", pady=15)

        self.open_folder_btn = ctk.CTkButton(
            action_frame,
            text=self.t("open_folder"),
            command=self._open_folder,
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self.open_folder_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.import_btn = ctk.CTkButton(
            action_frame,
            text=self.t("import_to_game"),
            command=self._import_to_game,
            height=40,
            font=ctk.CTkFont(size=14),
        )
        self.import_btn.pack(side="left", padx=10, pady=10, fill="x", expand=True)

    def _on_language_change(self, choice: str):
        for lang_code in SUPPORTED_LANGUAGES:
            if choice.startswith(LANGUAGE_FLAGS[lang_code]):
                self.current_lang = lang_code
                self.settings["language"] = lang_code
                self._save_settings()
                self._update_ui_texts()
                self._update_installed_squads()
                self._update_history_list()
                break

    def _update_ui_texts(self):
        self.title(self.t("title"))
        self.title_label.configure(text=self.t("title"))
        self.game_label.configure(text=self.t("game"))
        self.platform_label.configure(text=self.t("platform"))
        self.squads_checkbox.configure(text=self.t("squads"))
        self.fut_checkbox.configure(text=self.t("fut"))
        self.installed_label.configure(text=self.t("installed_squads"))
        self.refresh_btn.configure(text=self.t("refresh"))
        self.download_btn.configure(text=self.t("download_latest"))
        self.archive_btn.configure(text=self.t("load_archive"))
        self.status_label.configure(text=self.t("ready"))
        self.history_label.configure(text=self.t("download_history"))
        self.open_folder_btn.configure(text=self.t("open_folder"))
        self.import_btn.configure(text=self.t("import_to_game"))

    def _on_game_change(self, game: str):
        self.settings["last_game"] = game
        self._save_settings()
        self._update_installed_squads()

    def _on_platform_change(self, platform: str):
        self.settings["last_platform"] = platform
        self._save_settings()

    def _update_installed_squads(self):
        game = self.game_var.get()
        installed = get_installed_squads(game, self.current_lang)

        if installed["squads"]:
            self.squads_installed_label.configure(
                text=f"Squads: {installed['squads']['display']}"
            )
        else:
            self.squads_installed_label.configure(
                text=f"Squads: {self.t('not_installed')}"
            )

        if installed["fut"]:
            self.fut_installed_label.configure(
                text=f"FUT: {installed['fut']['display']}"
            )
        else:
            self.fut_installed_label.configure(text=f"FUT: {self.t('not_installed')}")

    def _update_history_list(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        downloads = self.history.get("downloads", [])
        if not downloads:
            no_history = ctk.CTkLabel(
                self.history_scroll, text=self.t("no_downloads"), text_color="gray"
            )
            no_history.pack(pady=20)
            return

        for entry in downloads[:20]:
            date_str = entry.get("date", "")[:10]
            game = entry.get("game", "")
            platform = entry.get("platform", "")
            squad_type = entry.get("type", "")
            squad_date = entry.get("squad_date", "")

            text = f"{date_str} | {game} | {platform} | {squad_type} | {squad_date}"

            item = ctk.CTkLabel(
                self.history_scroll, text=text, anchor="w", font=ctk.CTkFont(size=11)
            )
            item.pack(fill="x", padx=10, pady=2)

    def _progress_callback(self, message: str, percent: int):
        self.status_label.configure(text=message)
        self.progress_bar.set(percent / 100)

    def _start_download(self):
        if not self.squads_var.get() and not self.fut_var.get():
            messagebox.showwarning("Warning", self.t("warning_select_type"))
            return

        self.download_btn.configure(state="disabled")
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._download_thread)
        thread.daemon = True
        thread.start()

    def _download_thread(self):
        game = self.game_var.get()
        platform_key = self.platform_var.get()
        platform = PLATFORMS.get(platform_key, "pc64")

        try:
            downloader = SquadDownloader(
                game=game, progress_callback=self._progress_callback
            )

            result = downloader.download_squad(
                platform=platform,
                download_squads=self.squads_var.get(),
                download_fut=self.fut_var.get(),
            )

            self.after(0, lambda: self._download_complete(result, game, platform))
        except Exception as e:
            self.after(0, lambda: self._download_error(str(e)))

    def _download_error(self, error: str):
        self.download_btn.configure(state="normal")
        messagebox.showerror(self.t("error"), self.t("error_download", error=error))

    def _download_complete(self, result: dict, game: str, platform: str):
        self.download_btn.configure(state="normal")

        if result.get("success"):
            if result.get("squads"):
                squad_date = result.get("squads_date", "unknown")
                squad_path = Path(result["squads"])
                self._add_to_history(
                    game,
                    self.platform_var.get(),
                    "Squads",
                    squad_date,
                    result["squads"],
                )
                SquadArchiver.archive_squad(
                    squad_path, game, platform, "Squads", squad_date
                )

            if result.get("fut"):
                fut_date = result.get("fut_date", "unknown")
                fut_path = Path(result["fut"])
                self._add_to_history(
                    game, self.platform_var.get(), "FUT", fut_date, result["fut"]
                )
                SquadArchiver.archive_squad(fut_path, game, platform, "FUT", fut_date)

            self._update_installed_squads()
            messagebox.showinfo("Success", self.t("success_download"))
        else:
            error = result.get("error", "Unknown error")
            messagebox.showerror(self.t("error"), self.t("error_download", error=error))

    def _open_squad_dialog(self):
        SquadSelectorDialog(
            self,
            self.game_var.get(),
            self.platform_var.get(),
            self.current_lang,
            self._on_squad_restored,
        )

    def _on_squad_restored(self):
        self._update_installed_squads()
        self.status_label.configure(text=self.t("success_download").split("!")[0])

    def _open_folder(self):
        game = self.game_var.get()
        game_archive_dir = GAMES.get(game, {}).get("archive_dir", "fc26")
        platform = PLATFORMS.get(self.platform_var.get(), "pc64")
        folder = RESULT_DIR / game_archive_dir / platform
        if folder.exists():
            subprocess.run(["explorer", str(folder)])
        else:
            subprocess.run(["explorer", str(RESULT_DIR)])

    def _import_to_game(self):
        game = self.game_var.get()
        game_archive_dir = GAMES.get(game, {}).get("archive_dir", "fc26")
        platform = PLATFORMS.get(self.platform_var.get(), "pc64")
        source_path = RESULT_DIR / game_archive_dir / platform

        if not source_path.exists():
            messagebox.showerror(self.t("error"), self.t("error_no_squads"))
            return

        settings_path = GAMES.get(game, {}).get("settings_path")
        if not settings_path:
            messagebox.showerror(self.t("error"), self.t("error_no_game_path"))
            return

        if not settings_path.exists():
            settings_path.mkdir(parents=True, exist_ok=True)

        try:
            for item in source_path.rglob("*"):
                if item.is_file() and not item.suffix == ".bin":
                    relative = item.relative_to(source_path)
                    dest = settings_path / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)

            messagebox.showinfo(
                "Success",
                self.t("success_import", path=settings_path),
            )
            self._update_installed_squads()
        except Exception as e:
            messagebox.showerror(self.t("error"), self.t("error_import", error=e))


if __name__ == "__main__":
    app = FC26SquadDownloaderApp()
    app.mainloop()
