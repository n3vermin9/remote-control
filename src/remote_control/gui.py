from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from .adapters.telegram import TelegramAdapter
from .app_catalog import AppCatalog
from .autostart import autostart_enabled, install_autostart, remove_autostart
from .commands import CommandParser
from .config import Settings
from .executor import CommandExecutor


class RemoteControlGUI:
    def __init__(
        self,
        command_parser: CommandParser,
        executor: CommandExecutor,
        app_catalog: AppCatalog,
        settings: Settings,
        start_hidden: bool = True,
    ) -> None:
        self.command_parser = command_parser
        self.executor = executor
        self.app_catalog = app_catalog
        self.settings = settings
        self.start_hidden = start_hidden
        self.telegram_adapter: Optional[TelegramAdapter] = None
        self.tray_icon: Optional[pystray.Icon] = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Remote control")
        self.root.geometry("860x620")
        self.root.minsize(720, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.telegram_status = tk.StringVar(value="Telegram not connected")
        self.telegram_token = tk.StringVar(value=settings.telegram_token)
        self.authorized_chat_id = tk.StringVar(
            value="" if settings.authorized_chat_id is None else str(settings.authorized_chat_id)
        )
        self.app_filter = tk.StringVar()

        self._configure_style()
        self._build_ui()
        self._populate_apps()
        self._start_tray()
        if self.start_hidden and self.settings.telegram_token:
            self.root.withdraw()
        self.root.after(60, self._drain_events)
        if self.settings.telegram_token:
            self.root.after(300, self.start_telegram)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Status.TLabel", font=("Segoe UI", 10, "bold"))
        style.configure("Action.TButton", padding=(14, 8))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Remote control", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=f"{len(self.app_catalog)} installed apps recognized").pack(
            side="right", pady=(12, 0)
        )

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        setup_tab = ttk.Frame(notebook, padding=14)
        apps_tab = ttk.Frame(notebook, padding=14)
        commands_tab = ttk.Frame(notebook, padding=14)
        notebook.add(setup_tab, text="Telegram setup")
        notebook.add(apps_tab, text="Installed apps")
        notebook.add(commands_tab, text="Commands")

        setup = ttk.LabelFrame(setup_tab, text="Telegram bot connection", padding=14)
        setup.pack(fill="x")
        setup.columnconfigure(1, weight=1)
        ttk.Label(setup, text="Bot token:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(setup, textvariable=self.telegram_token, show="•").grid(
            row=0, column=1, sticky="ew", padx=(10, 0), pady=5
        )
        ttk.Label(setup, text="Authorized chat ID:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(setup, textvariable=self.authorized_chat_id).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=5
        )
        ttk.Label(
            setup,
            text=(
                "Create a bot with @BotFather and paste its token. Start the bot, send /id, "
                "then copy the returned chat ID here. Only that chat can control this PC."
            ),
            wraplength=680,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 10))
        buttons = ttk.Frame(setup)
        buttons.grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Button(
            buttons,
            text="Save and connect",
            command=self.save_and_connect,
            style="Action.TButton",
        ).pack(side="left")
        ttk.Button(buttons, text="Disconnect", command=self.stop_telegram).pack(
            side="left", padx=6
        )
        ttk.Label(setup, textvariable=self.telegram_status, style="Status.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )

        security = ttk.LabelFrame(setup_tab, text="Security", padding=12)
        security.pack(fill="x", pady=(12, 0))
        ttk.Label(
            security,
            text=(
                "The token is stored locally in your Windows user profile. Commands from every "
                "chat except the authorized chat ID are ignored. App names are matched only "
                "against the installed-app catalog."
            ),
            wraplength=700,
            justify="left",
        ).pack(anchor="w")

        ttk.Label(apps_tab, text="Names accepted in Telegram commands:").pack(anchor="w")
        filter_entry = ttk.Entry(apps_tab, textvariable=self.app_filter)
        filter_entry.pack(fill="x", pady=(5, 8))
        self.app_filter.trace_add("write", lambda *_args: self._populate_apps())
        self.app_list = tk.Listbox(apps_tab, font=("Segoe UI", 11))
        self.app_list.pack(fill="both", expand=True)

        help_text = (
            "APPS\n  open/start/launch/run + app name\n  close/quit/exit/stop + app name\n\n"
            "VOLUME\n  volume 0–100 • set volume to 35 percent • louder • quieter • mute\n\n"
            "MEDIA\n  play • pause • resume • stop music • next song • previous song\n\n"
            "WINDOWS\n  show desktop • minimize/maximize/switch/close window • screenshot\n\n"
            "EDITING\n  copy • cut • paste • undo • redo • select all • enter • escape\n\n"
            "BROWSER\n  new/close/reopen tab • refresh • back/forward • zoom in/out/reset\n\n"
            "BOT\n  /id • /start • /help • /commands\n\n"
            "SYSTEM\n  show commands • quit remote control"
        )
        ttk.Label(commands_tab, text=help_text, font=("Segoe UI", 12), justify="left").pack(
            anchor="nw"
        )

        log_frame = ttk.LabelFrame(outer, text="Telegram activity", padding=6)
        log_frame.pack(fill="x", pady=(12, 0))
        self.log = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x")

    @staticmethod
    def _tray_image() -> Image.Image:
        image = Image.new("RGBA", (64, 64), "#111827")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((7, 7, 57, 57), radius=14, fill="#229ED9")
        draw.polygon(((16, 31), (50, 17), (42, 49), (31, 39), (24, 45)), fill="white")
        return image

    def _start_tray(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Open Remote control", self._tray_show, default=True),
            pystray.MenuItem(
                "Start with Windows",
                self._tray_toggle_autostart,
                checked=lambda _item: autostart_enabled(),
            ),
            pystray.MenuItem("Exit", self._tray_exit),
        )
        self.tray_icon = pystray.Icon(
            "RemoteControlTelegram", self._tray_image(), "Remote control", menu
        )
        threading.Thread(target=self.tray_icon.run, name="tray-icon", daemon=True).start()

    def _tray_show(self, _icon, _item) -> None:  # noqa: ANN001
        self.root.after(0, self.show_window)

    def _tray_exit(self, _icon, _item) -> None:  # noqa: ANN001
        self.root.after(0, self.exit_app)

    def _tray_toggle_autostart(self, icon, _item) -> None:  # noqa: ANN001
        try:
            if autostart_enabled():
                remove_autostart()
            else:
                install_autostart()
            icon.update_menu()
        except Exception as error:
            self.post("error", f"Could not change Windows startup: {error}")

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_to_tray(self) -> None:
        self.root.withdraw()

    def _populate_apps(self) -> None:
        if not hasattr(self, "app_list"):
            return
        query = self.app_filter.get().casefold().strip()
        self.app_list.delete(0, "end")
        for app in self.app_catalog.entries:
            if not query or query in app.name.casefold():
                self.app_list.insert("end", app.name)

    def post(self, kind: str, value: object) -> None:
        self.events.put((kind, value))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "telegram_status":
                    self.telegram_status.set(str(value))
                elif kind == "error":
                    messagebox.showerror("Remote control", str(value))
        except queue.Empty:
            pass
        self.root.after(60, self._drain_events)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def handle_telegram_command(self, text: str) -> str:
        self.post("log", f'Telegram command: "{text}"')
        command = self.command_parser.parse(text)
        if command is None:
            message = "Command not recognized. Send /commands for the supported list."
            self.post("log", message)
            return message
        try:
            result = self.executor.execute(command)
            self.post("log", result.message)
            if result.should_quit:
                self.root.after(500, self.exit_app)
            return result.message
        except Exception as error:
            message = f"Command failed: {error}"
            self.post("log", message)
            return message

    def save_and_connect(self) -> None:
        token = self.telegram_token.get().strip()
        chat_text = self.authorized_chat_id.get().strip()
        try:
            chat_id = int(chat_text) if chat_text else None
        except ValueError:
            messagebox.showerror("Remote control", "The authorized chat ID must be a number.")
            return
        self.settings.telegram_token = token
        self.settings.authorized_chat_id = chat_id
        self.settings.save()
        self.start_telegram()

    def start_telegram(self) -> None:
        self.stop_telegram()
        try:
            adapter = TelegramAdapter(
                self.settings.telegram_token,
                self.settings.authorized_chat_id,
                status=lambda text: self.post("telegram_status", text),
            )
        except ValueError as error:
            self.post("error", str(error))
            return
        self.telegram_adapter = adapter
        self.telegram_status.set("Connecting to Telegram…")

        def worker() -> None:
            try:
                adapter.run(self.handle_telegram_command)
            except Exception as error:
                self.post("error", f"Telegram control stopped: {error}")
            finally:
                self.post("telegram_status", "Telegram disconnected")

        threading.Thread(target=worker, name="telegram-control", daemon=True).start()

    def stop_telegram(self) -> None:
        if self.telegram_adapter:
            self.telegram_adapter.stop()
            self.telegram_adapter = None
        self.telegram_status.set("Telegram disconnected")

    def exit_app(self) -> None:
        self.stop_telegram()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
