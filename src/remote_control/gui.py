from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

import pystray
from PIL import Image, ImageDraw

from .adapters.voice import VoiceAdapter
from .app_catalog import AppCatalog
from .autostart import autostart_enabled, install_autostart, remove_autostart
from .commands import Action, Command, CommandParser
from .config import Settings
from .executor import CommandExecutor
from .speech.vosk_recognizer import VoskRecognizer


class RemoteControlGUI:
    def __init__(
        self,
        recognizer: VoskRecognizer,
        command_parser: CommandParser,
        executor: CommandExecutor,
        app_catalog: AppCatalog,
        settings: Settings,
        start_hidden: bool = True,
    ) -> None:
        self.recognizer = recognizer
        self.command_parser = command_parser
        self.executor = executor
        self.app_catalog = app_catalog
        self.settings = settings
        self.start_hidden = start_hidden
        self.voice_adapter: Optional[VoiceAdapter] = None
        self.tray_icon: Optional[pystray.Icon] = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Remote control")
        self.root.geometry("860x620")
        self.root.minsize(720, 500)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self.voice_status = tk.StringVar(value="Voice starting…")
        self.app_filter = tk.StringVar()
        self.command_text = tk.StringVar()
        self.volume_text = tk.StringVar(value="50")

        self._configure_style()
        self._build_ui()
        self._populate_apps()
        self._start_tray()
        if self.start_hidden:
            self.root.withdraw()
        self.root.after(60, self._drain_events)
        self.root.after(300, self.start_voice)

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
        control_tab = ttk.Frame(notebook, padding=14)
        apps_tab = ttk.Frame(notebook, padding=14)
        commands_tab = ttk.Frame(notebook, padding=14)
        notebook.add(control_tab, text="Control")
        notebook.add(apps_tab, text="Installed apps")
        notebook.add(commands_tab, text="Commands")

        voice = ttk.LabelFrame(control_tab, text="Always-on voice", padding=12)
        voice.pack(fill="x", pady=(0, 10))
        ttk.Label(voice, textvariable=self.voice_status, style="Status.TLabel").pack(
            side="left", padx=(0, 12)
        )
        ttk.Button(voice, text="Start listening", command=self.start_voice).pack(side="left")
        ttk.Button(voice, text="Stop listening", command=self.stop_voice).pack(
            side="left", padx=6
        )
        ttk.Label(voice, text="Closing this window keeps the app running in the tray.").pack(
            side="right"
        )

        manual = ttk.LabelFrame(control_tab, text="Type or click a command", padding=12)
        manual.pack(fill="both", expand=True)
        entry = ttk.Entry(manual, textvariable=self.command_text)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda _event: self.run_typed_command())
        ttk.Button(
            manual, text="Run command", command=self.run_typed_command, style="Action.TButton"
        ).pack(anchor="w", pady=(7, 10))
        volume = ttk.Frame(manual)
        volume.pack(fill="x", pady=(0, 8))
        ttk.Label(volume, text="Exact volume:").pack(side="left")
        ttk.Spinbox(volume, from_=0, to=100, textvariable=self.volume_text, width=5).pack(
            side="left", padx=6
        )
        ttk.Button(volume, text="Set", command=self.set_typed_volume).pack(side="left")

        quick = ttk.Frame(manual)
        quick.pack(fill="x")
        for index, (label, action) in enumerate(
            (
                ("Volume −", Action.VOLUME_DOWN),
                ("Mute", Action.VOLUME_MUTE),
                ("Volume +", Action.VOLUME_UP),
                ("Previous song", Action.MEDIA_PREVIOUS),
                ("Play / Pause", Action.MEDIA_PLAY_PAUSE),
                ("Next song", Action.MEDIA_NEXT),
                ("Show desktop", Action.SHOW_DESKTOP),
                ("Switch window", Action.SWITCH_WINDOW),
                ("Screenshot", Action.SCREENSHOT),
                ("Copy", Action.COPY),
                ("Paste", Action.PASTE),
                ("Close window", Action.CLOSE_WINDOW),
            )
        ):
            ttk.Button(
                quick,
                text=label,
                command=lambda item=action, text=label: self.execute(Command(item, text.lower())),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=3, pady=3)
        for column in range(3):
            quick.columnconfigure(column, weight=1)

        ttk.Label(apps_tab, text="Search apps available to voice control:").pack(anchor="w")
        filter_entry = ttk.Entry(apps_tab, textvariable=self.app_filter)
        filter_entry.pack(fill="x", pady=(5, 8))
        self.app_filter.trace_add("write", lambda *_args: self._populate_apps())
        self.app_list = tk.Listbox(apps_tab, font=("Segoe UI", 11))
        self.app_list.pack(fill="both", expand=True)
        self.app_list.bind("<Double-Button-1>", self._open_selected_app)
        app_buttons = ttk.Frame(apps_tab)
        app_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(app_buttons, text="Open selected", command=self._open_selected_app).pack(side="left")
        ttk.Button(app_buttons, text="Close selected", command=self._close_selected_app).pack(
            side="left", padx=6
        )

        help_text = (
            "APPS\n  open/start/launch/run + app name\n  close/quit/exit/stop + app name\n\n"
            "VOLUME\n  volume 0–100 • set volume to 35 percent • louder • quieter • mute\n\n"
            "MEDIA\n  play • pause • resume • stop music • next song • previous song\n\n"
            "WINDOWS\n  show desktop • minimize/maximize/switch/close window • screenshot\n\n"
            "EDITING\n  copy • cut • paste • undo • redo • select all • enter • escape\n\n"
            "BROWSER\n  new/close/reopen tab • refresh • back/forward • zoom in/out/reset\n\n"
            "SYSTEM\n  show commands • quit remote control"
        )
        ttk.Label(commands_tab, text=help_text, font=("Segoe UI", 12), justify="left").pack(
            anchor="nw"
        )

        log_frame = ttk.LabelFrame(outer, text="Activity", padding=6)
        log_frame.pack(fill="x", pady=(12, 0))
        self.log = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x")

    @staticmethod
    def _tray_image() -> Image.Image:
        image = Image.new("RGBA", (64, 64), "#111827")
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((7, 7, 57, 57), radius=14, fill="#2563eb")
        draw.ellipse((25, 14, 39, 34), fill="white")
        draw.arc((18, 20, 46, 48), 0, 180, fill="white", width=5)
        draw.line((32, 46, 32, 53), fill="white", width=5)
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
            "RemoteControlVoice", self._tray_image(), "Remote control", menu
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

    def _selected_app(self) -> Optional[str]:
        selection = self.app_list.curselection()
        return self.app_list.get(selection[0]) if selection else None

    def _open_selected_app(self, _event=None) -> None:  # noqa: ANN001
        name = self._selected_app()
        if name:
            self.handle_text(f"open {name}")

    def _close_selected_app(self) -> None:
        name = self._selected_app()
        if name:
            self.handle_text(f"close {name}")

    def post(self, kind: str, value: object) -> None:
        self.events.put((kind, value))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "voice_status":
                    self.voice_status.set(str(value))
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

    def handle_text(self, text: str) -> bool:
        self.post("log", f'Heard: "{text}"')
        command = self.command_parser.parse(text)
        if command is None:
            self.post("log", "Command not recognized. Check the Commands tab.")
            return True
        return not self.execute(command)

    def execute(self, command: Command) -> bool:
        try:
            result = self.executor.execute(command)
            self.post("log", result.message)
            if result.should_quit:
                self.root.after(0, self.exit_app)
            return result.should_quit
        except Exception as error:
            self.post("error", str(error))
            return False

    def run_typed_command(self) -> None:
        text = self.command_text.get().strip()
        if text:
            self.command_text.set("")
            self.handle_text(text)

    def set_typed_volume(self) -> None:
        self.handle_text(f"volume {self.volume_text.get()}")

    def start_voice(self) -> None:
        self.stop_voice()
        adapter = VoiceAdapter(
            self.recognizer,
            timeout_seconds=self.settings.command_timeout_seconds,
            status=lambda text: self.post("voice_status", text),
        )
        self.voice_adapter = adapter
        self.voice_status.set("Starting voice…")

        def worker() -> None:
            try:
                adapter.run(self.handle_text)
            except Exception as error:
                self.post("error", f"Voice control stopped: {error}")
            finally:
                self.post("voice_status", "Voice stopped")

        threading.Thread(target=worker, name="voice-control", daemon=True).start()

    def stop_voice(self) -> None:
        if self.voice_adapter:
            self.voice_adapter.stop()
            self.voice_adapter = None
            self.voice_status.set("Voice stopped")

    def exit_app(self) -> None:
        self.stop_voice()
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
