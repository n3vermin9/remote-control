from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional

from PIL import Image, ImageTk

from .adapters.camera import CameraGestureAdapter
from .adapters.voice import VoiceAdapter
from .app_catalog import AppCatalog
from .commands import Action, Command, CommandParser
from .config import HAND_MODEL_PATH, POSE_MODEL_PATH, Settings
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
        initial_mode: str = "f8",
    ) -> None:
        self.recognizer = recognizer
        self.command_parser = command_parser
        self.executor = executor
        self.app_catalog = app_catalog
        self.settings = settings
        self.voice_adapter: Optional[VoiceAdapter] = None
        self.camera_adapter: Optional[CameraGestureAdapter] = None
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Remote control")
        self.root.geometry("980x680")
        self.root.minsize(820, 560)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.mode = tk.StringVar(value=initial_mode)
        self.voice_status = tk.StringVar(value="Voice stopped")
        self.camera_status = tk.StringVar(value="Webcam stopped")
        self.camera_index = tk.StringVar(value=str(settings.camera_index))
        self.app_filter = tk.StringVar()
        self.command_text = tk.StringVar()
        self._camera_photo = None
        self._latest_frame = None
        self._frame_lock = threading.Lock()

        self._configure_style()
        self._build_ui()
        self._populate_apps()
        self.root.after(60, self._drain_events)
        self.root.after(500, self.start_voice)

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
        ttk.Label(
            header,
            text=f"{len(self.app_catalog)} installed apps recognized",
        ).pack(side="right", pady=(12, 0))

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True)
        control_tab = ttk.Frame(notebook, padding=14)
        apps_tab = ttk.Frame(notebook, padding=14)
        commands_tab = ttk.Frame(notebook, padding=14)
        notebook.add(control_tab, text="Control")
        notebook.add(apps_tab, text="Installed apps")
        notebook.add(commands_tab, text="Commands")

        control_tab.columnconfigure(0, weight=1)
        control_tab.columnconfigure(1, weight=1)
        control_tab.rowconfigure(1, weight=1)

        voice = ttk.LabelFrame(control_tab, text="Voice", padding=12)
        voice.grid(row=0, column=0, sticky="nsew", padx=(0, 7), pady=(0, 10))
        ttk.Radiobutton(voice, text="Hold F8 to speak", variable=self.mode, value="f8").pack(anchor="w")
        ttk.Radiobutton(voice, text="Always listening", variable=self.mode, value="always").pack(anchor="w")
        ttk.Label(voice, textvariable=self.voice_status, style="Status.TLabel").pack(anchor="w", pady=(8, 5))
        voice_buttons = ttk.Frame(voice)
        voice_buttons.pack(anchor="w")
        ttk.Button(voice_buttons, text="Start voice", command=self.start_voice, style="Action.TButton").pack(side="left")
        ttk.Button(voice_buttons, text="Stop", command=self.stop_voice, style="Action.TButton").pack(side="left", padx=6)

        camera = ttk.LabelFrame(control_tab, text="Webcam gestures", padding=12)
        camera.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(7, 0), pady=(0, 10))
        self.camera_preview = tk.Label(camera, text="Camera preview", bg="#111827", fg="white", width=48, height=16)
        self.camera_preview.pack(fill="both", expand=True)
        ttk.Label(camera, textvariable=self.camera_status, style="Status.TLabel").pack(anchor="w", pady=(8, 3))
        ttk.Label(camera, text="Stand up: play/pause   •   Swipe left/right: previous/next song").pack(anchor="w")
        camera_buttons = ttk.Frame(camera)
        camera_buttons.pack(anchor="w", pady=(8, 0))
        ttk.Label(camera_buttons, text="Camera:").pack(side="left", padx=(0, 4))
        ttk.Combobox(
            camera_buttons,
            textvariable=self.camera_index,
            values=("0", "1", "2", "3", "4", "5"),
            width=3,
            state="readonly",
        ).pack(side="left", padx=(0, 8))
        ttk.Button(camera_buttons, text="Start webcam", command=self.start_camera, style="Action.TButton").pack(side="left")
        ttk.Button(camera_buttons, text="Stop", command=self.stop_camera, style="Action.TButton").pack(side="left", padx=6)

        manual = ttk.LabelFrame(control_tab, text="Type or click a command", padding=12)
        manual.grid(row=1, column=0, sticky="nsew", padx=(0, 7))
        entry = ttk.Entry(manual, textvariable=self.command_text)
        entry.pack(fill="x")
        entry.bind("<Return>", lambda _event: self.run_typed_command())
        ttk.Button(manual, text="Run command", command=self.run_typed_command, style="Action.TButton").pack(anchor="w", pady=(7, 10))
        quick = ttk.Frame(manual)
        quick.pack(fill="x")
        for label, action in (
            ("Volume −", Action.VOLUME_DOWN),
            ("Mute", Action.VOLUME_MUTE),
            ("Volume +", Action.VOLUME_UP),
            ("Previous song", Action.MEDIA_PREVIOUS),
            ("Play / Pause", Action.MEDIA_PLAY_PAUSE),
            ("Next song", Action.MEDIA_NEXT),
            ("Show desktop", Action.SHOW_DESKTOP),
            ("Switch window", Action.SWITCH_WINDOW),
            ("Screenshot", Action.SCREENSHOT),
        ):
            index = len(quick.winfo_children())
            ttk.Button(
                quick,
                text=label,
                command=lambda item=action, text=label: self.execute(
                    Command(item, text.lower())
                ),
            ).grid(row=index // 3, column=index % 3, sticky="ew", padx=3, pady=3)
        for column in range(3):
            quick.columnconfigure(column, weight=1)

        ttk.Label(apps_tab, text="Search the app names available to voice control:").pack(anchor="w")
        filter_entry = ttk.Entry(apps_tab, textvariable=self.app_filter)
        filter_entry.pack(fill="x", pady=(5, 8))
        self.app_filter.trace_add("write", lambda *_args: self._populate_apps())
        self.app_list = tk.Listbox(apps_tab, font=("Segoe UI", 11))
        self.app_list.pack(fill="both", expand=True)
        self.app_list.bind("<Double-Button-1>", self._open_selected_app)
        ttk.Label(apps_tab, text='Say “open” followed by any name here, or double-click an app.').pack(anchor="w", pady=(8, 0))

        help_text = (
            "APP CONTROL\n  open / open up / start / launch / run + installed app name\n\n"
            "MEDIA\n  play • pause • resume • stop music • next song • previous song\n\n"
            "VOLUME\n  volume up • louder • volume down • quieter • mute • unmute\n\n"
            "WINDOWS\n  show desktop • minimize window • maximize window • switch window\n"
            "  screenshot • browser back/forward • scroll up/down\n\n"
            "SYSTEM\n  show commands • quit remote control\n\n"
            "WEBCAM\n  stand up → play/pause\n  swipe hand left → previous song\n  swipe hand right → next song"
        )
        ttk.Label(commands_tab, text=help_text, font=("Segoe UI", 12), justify="left").pack(anchor="nw")

        log_frame = ttk.LabelFrame(outer, text="Activity", padding=6)
        log_frame.pack(fill="x", pady=(12, 0))
        self.log = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.log.pack(fill="x")

    def _populate_apps(self) -> None:
        if not hasattr(self, "app_list"):
            return
        query = self.app_filter.get().casefold().strip()
        self.app_list.delete(0, "end")
        for app in self.app_catalog.entries:
            if not query or query in app.name.casefold():
                self.app_list.insert("end", app.name)

    def _open_selected_app(self, _event=None) -> None:  # noqa: ANN001
        selection = self.app_list.curselection()
        if selection:
            name = self.app_list.get(selection[0])
            self.handle_text(f"open {name}")

    def post(self, kind: str, value: object) -> None:
        if kind == "frame":
            with self._frame_lock:
                self._latest_frame = value
            return
        self.events.put((kind, value))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(str(value))
                elif kind == "voice_status":
                    self.voice_status.set(str(value))
                elif kind == "camera_status":
                    self.camera_status.set(str(value))
                elif kind == "frame":
                    self._show_frame(value)
                elif kind == "error":
                    messagebox.showerror("Remote control", str(value))
        except queue.Empty:
            pass
        with self._frame_lock:
            frame = self._latest_frame
            self._latest_frame = None
        if frame is not None:
            self._show_frame(frame)
        self.root.after(60, self._drain_events)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _show_frame(self, frame: object) -> None:
        image = Image.fromarray(frame).resize((440, 330))
        self._camera_photo = ImageTk.PhotoImage(image=image)
        self.camera_preview.configure(image=self._camera_photo, text="")

    def handle_text(self, text: str) -> bool:
        self.post("log", f'Heard: "{text}"')
        command = self.command_parser.parse(text)
        if command is None:
            self.post("log", "Command not recognized. Check the Commands or Installed apps tab.")
            return True
        result = self.execute(command)
        return not result

    def execute(self, command: Command) -> bool:
        try:
            result = self.executor.execute(command)
            self.post("log", result.message)
            if result.should_quit:
                self.root.after(0, self.close)
            return result.should_quit
        except Exception as error:  # Keep the GUI alive when one OS action fails.
            self.post("error", str(error))
            return False

    def run_typed_command(self) -> None:
        text = self.command_text.get().strip()
        if text:
            self.command_text.set("")
            self.handle_text(text)

    def start_voice(self) -> None:
        self.stop_voice()
        self.settings.mode = self.mode.get()
        self.settings.save()
        adapter = VoiceAdapter(
            self.recognizer,
            mode=self.mode.get(),
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

    def start_camera(self) -> None:
        self.stop_camera()
        self.settings.camera_index = int(self.camera_index.get())
        self.settings.save()
        adapter = CameraGestureAdapter(
            HAND_MODEL_PATH,
            POSE_MODEL_PATH,
            camera_index=self.settings.camera_index,
            status=lambda text: self.post("camera_status", text),
        )
        self.camera_adapter = adapter
        self.camera_status.set("Starting webcam…")

        def on_gesture(gesture: str) -> None:
            actions = {
                "stand_up": (Action.MEDIA_PLAY_PAUSE, "Stand up → play/pause"),
                "swipe_left": (Action.MEDIA_PREVIOUS, "Swipe left → previous song"),
                "swipe_right": (Action.MEDIA_NEXT, "Swipe right → next song"),
            }
            action, message = actions[gesture]
            self.post("log", message)
            self.execute(Command(action, gesture))

        def worker() -> None:
            try:
                adapter.run(on_gesture, lambda frame: self.post("frame", frame))
            except Exception as error:
                self.post("error", f"Webcam control stopped: {error}")
            finally:
                self.post("camera_status", "Webcam stopped")

        threading.Thread(target=worker, name="camera-control", daemon=True).start()

    def stop_camera(self) -> None:
        if self.camera_adapter:
            self.camera_adapter.stop()
            self.camera_adapter = None
        self.camera_status.set("Webcam stopped")
        self.camera_preview.configure(image="", text="Camera preview")
        self._camera_photo = None

    def close(self) -> None:
        self.stop_voice()
        self.stop_camera()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
