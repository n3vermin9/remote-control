# Remote control

A Windows tray app controlled exclusively through an authorized Telegram bot chat. It can open and gracefully close installed apps, control media and exact volume, manage windows, and send editing or browser shortcuts.

There is no microphone access, speech recognition, webcam access, or local command-control interface. The setup window is only for Telegram pairing, connection status, the installed-app catalog, and command documentation.

## Easy Windows installation

1. On GitHub, click **Code → Download ZIP**, then extract it.
2. Open the extracted `remote-control-main` folder.
3. Double-click **`INSTALL.bat`**.
4. Double-click **`START.bat`**.

The installer creates a private Python environment, installs the application, removes components left by older speech/webcam releases, and enables **Start with Windows** for the current user. No administrator access is required. The prerequisite is 64-bit Python 3.9–3.12.

## Telegram setup

1. Open Telegram and create a bot with **@BotFather**.
2. Copy the bot token supplied by BotFather.
3. Open Remote control from the system tray and paste the token.
4. In Telegram, open the new bot and send `/id`.
5. Copy the numeric chat ID returned by the bot into **Authorized chat ID**.
6. Click **Save and connect**.

The bot token is stored locally under `%LOCALAPPDATA%\RemoteControlTelegram\config.json`. Only messages from the configured private chat ID can execute PC commands. Groups and other chats are ignored. Before pairing, `/id` is the only useful bot command.

Telegram control needs an internet connection. The app uses Telegram’s HTTPS Bot API with long polling; it does not expose an inbound server or require router configuration.

Queued messages are cleared whenever the desktop app establishes a fresh bot session, so commands sent while the PC was offline are not replayed later.

## Running in the tray

Remote control starts with Windows and stays in the system tray. Closing the setup window keeps the bot active. Double-click the tray icon to reopen setup, or choose **Exit** to stop it.

Run `remote-control --show-window` to show setup immediately, `remote-control --list-apps` to print recognized app names, or `remote-control --remove-autostart` to disable Windows startup.

## Telegram commands

### Applications

Use a name shown in the **Installed apps** tab:

| Send | Result |
| --- | --- |
| `open Spotify`, `start Spotify`, `launch Spotify`, `run Spotify` | Opens the app |
| `close Spotify`, `quit Spotify`, `exit Spotify`, `stop Spotify` | Gracefully closes its windows |

App closing sends the normal Windows close request, allowing apps to prompt about unsaved work. It does not force-kill processes.

### Volume and media

- `volume 35`, `volume thirty five`, `set volume to 35 percent`
- `volume up`, `louder`, `volume down`, `quieter`, `mute`, `unmute`
- `play`, `pause`, `resume music`, `stop music`
- `next song`, `skip this song`, `previous song`, `back one song`

### Windows, editing, and browsers

- `show desktop`, `minimize window`, `maximize window`, `switch window`, `close window`
- `take screenshot`, `browser back`, `browser forward`, `scroll up`, `scroll down`
- `copy`, `cut`, `paste`, `undo`, `redo`, `select all`, `press enter`, `press escape`
- `new tab`, `close tab`, `reopen tab`, `refresh`, `zoom in`, `zoom out`, `reset zoom`

Send `/commands`, `/help`, or `/start` for the command list. Send `/status` or `/ping` to confirm the PC controller is online. Send `quit remote control` to exit the tray app.

## Safety model

- A Telegram chat ID allowlist is mandatory for PC actions.
- Application names must exist in the catalog built from Windows Start Menu shortcuts, App Paths, and Store apps.
- Telegram message text is never executed as a shell command.
- There are no shutdown, restart, file deletion, or forced process-kill commands.
- Bot tokens are masked in the GUI and never written to activity logs.

## Manual setup

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
remote-control --install-autostart
remote-control --show-window
```

## Architecture

```text
Authorized Telegram chat → TelegramAdapter → CommandParser → CommandExecutor → WindowsController
System tray → setup window, autostart toggle, exit
```

- `adapters/telegram.py` handles Bot API long polling and chat authorization.
- `app_catalog.py` discovers safe installed-app targets.
- `commands.py` parses Telegram text into typed actions.
- `executor.py` dispatches validated actions.
- `platform/windows.py` is the only layer that controls Windows.
- `gui.py` provides Telegram setup, status, and the tray icon.

## Development checks

```powershell
python -m unittest discover -s tests
python -m compileall src tests
```

Parser, Telegram authorization, configuration, and executor tests run on macOS/Linux. Windows tray behavior, Core Audio, app-window closing, and keyboard shortcuts require final verification on Windows.
