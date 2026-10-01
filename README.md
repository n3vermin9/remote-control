# Remote control

An always-listening Windows tray app for controlling installed applications, media, volume, windows, editing, and browsers with English voice commands. Speech recognition runs locally with Vosk: there is no cloud API, account, subscription, or per-minute fee.

The app discovers Windows Start Menu shortcuts, registered App Paths, and Microsoft Store applications. Those recognized names are used for both opening and gracefully closing apps, so spoken text is never executed as an arbitrary shell command.

## Easy Windows installation

1. On GitHub, click **Code → Download ZIP**, then extract it.
2. Open the extracted `remote-control-main` folder.
3. Double-click **`INSTALL.bat`**.
4. Double-click **`START.bat`** to start it immediately.

Installation creates a private Python environment, installs the app, downloads the offline English speech model, and enables **Start with Windows** for the current user. No administrator access is required. The only prerequisite is 64-bit Python 3.9–3.12.

Remote control starts hidden in the Windows system tray and begins listening automatically. Double-click the tray icon to open the interface. Closing the window returns it to the tray; choose **Exit** from the tray menu or say `quit remote control` to stop it completely. The tray menu can also enable or disable Windows startup.

Normal use is offline. Microphone audio is processed in memory and is not saved or uploaded.

## Interface

The GUI provides:

- Current always-listening status and start/stop controls.
- An exact-volume control from 0 to 100.
- Quick buttons for media, windows, editing, and screenshots.
- A text command box for testing commands without a microphone.
- A searchable list of every discovered app, with **Open selected** and **Close selected** buttons.
- A complete command reference and activity log.

Run `remote-control --show-window` to start with the window visible, `remote-control --headless` for console mode, or `remote-control --list-apps` to print recognized app names.

## Voice commands

### Applications

Use any discovered app name:

| Examples | Result |
| --- | --- |
| `open Spotify`, `start Spotify`, `launch Spotify`, `run Spotify` | Opens Spotify |
| `close Spotify`, `quit Spotify`, `exit Spotify`, `stop Spotify` | Gracefully closes Spotify windows |

App closing sends the normal Windows close request, allowing an app to prompt about unsaved work. It does not force-kill processes.

### Volume and media

| Examples | Result |
| --- | --- |
| `volume 35`, `volume thirty five`, `set volume to 35 percent` | Sets the exact master volume from 0–100 |
| `volume up`, `louder`, `turn it up` | Raises volume |
| `volume down`, `quieter`, `turn it down` | Lowers volume |
| `mute`, `unmute`, `toggle mute` | Toggles mute |
| `play`, `pause`, `resume music` | Toggles playback |
| `next song`, `skip this song` | Goes to the next song |
| `previous song`, `back one song` | Goes to the previous song |
| `stop music`, `stop playback` | Stops playback |

### Windows and navigation

- `show desktop`, `minimize window`, `maximize window`, `switch window`, `close window`
- `take screenshot`, `capture screen`
- `browser back`, `browser forward`, `scroll up`, `scroll down`
- `new tab`, `close tab`, `reopen tab`, `refresh page`
- `zoom in`, `zoom out`, `reset zoom`

### Editing

- `copy`, `cut`, `paste`
- `undo`, `redo`, `select all`
- `press enter`, `press escape`

Say `show commands` for help or `quit remote control` to exit the tray app.

## Manual setup

Install 64-bit Python 3.9–3.12, then run in PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python scripts\download_model.py
remote-control --install-autostart
remote-control
```

To disable Windows startup:

```powershell
remote-control --remove-autostart
```

Allow desktop-app microphone access under **Windows Settings → Privacy & security → Microphone**. To inspect microphone device numbers, run `remote-control --list-devices`, then set `input_device` in `%LOCALAPPDATA%\RemoteControlVoice\config.json`. Leave `sample_rate` as `null` for automatic hardware detection.

## Architecture

```text
Microphone → VoskRecognizer → CommandParser → CommandExecutor → WindowsController
GUI text/buttons ────────────────────────────────┘
System tray → show, autostart toggle, exit
```

- `adapters/voice.py` owns continuous listening.
- `app_catalog.py` discovers safe installed-app targets.
- `commands.py` handles phrases, app names, and spoken numbers.
- `executor.py` maps parsed commands to platform actions.
- `platform/windows.py` controls Windows and gracefully closes app windows.
- `autostart.py` manages the current user's Windows startup registration.
- `gui.py` provides the tray icon and desktop interface.

## Development checks

```powershell
python -m unittest discover -s tests
python -m compileall src scripts tests
```

Parser, grammar, configuration, and executor tests run on macOS/Linux. Windows tray behavior, Core Audio volume control, microphone capture, app-window closing, and keyboard shortcuts require final verification on Windows.
