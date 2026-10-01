# Remote control

A first working prototype for controlling a Windows PC with **English voice commands**. Speech recognition uses Vosk locally: no cloud API, subscription, account, or per-minute fee is required.

The default interaction is push-to-talk: hold **F8**, say one command, and release F8. An optional always-listening mode is included.

## Privacy and cost

- Microphone audio is processed in memory on this PC and is not saved or uploaded.
- Recognition works without internet after the model has been downloaded once.
- The model and Python libraries are free and open source. No API key is used.
- `scripts/download_model.py` makes one HTTPS download from the official Vosk model host. You can instead download and copy the model manually from another computer.

## Windows setup

Install 64-bit Python 3.9–3.12 from [python.org](https://www.python.org/downloads/windows/) and select **Add Python to PATH** during installation. Then open PowerShell in this project folder:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
python scripts\download_model.py
remote-control
```

If PowerShell blocks virtual-environment activation, use Command Prompt instead:

```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install -e .
python scripts\download_model.py
remote-control
```

The first run does not need administrator privileges. Windows may show a microphone privacy prompt; allow microphone access for desktop apps under **Settings → Privacy & security → Microphone**.

## Listening modes

F8 push-to-talk is the default and minimizes accidental commands and CPU usage:

```powershell
remote-control
```

Hold F8, speak, then release F8. The microphone stream is opened only while the command is being captured.

Always-listening mode continuously waits for one of the supported phrases:

```powershell
remote-control --mode always
```

Press Ctrl+C to stop. To make always-listening persistent, run the app once so it creates `%LOCALAPPDATA%\RemoteControlVoice\config.json`, then edit that file and set `"mode": "always"`. F8 remains the default when no config exists.

## Supported commands

| Say | Result |
| --- | --- |
| `open notepad` | Opens Windows Notepad |
| `open calculator` | Opens Windows Calculator |
| `volume up` / `volume down` | Changes system volume one step |
| `mute` / `unmute` | Toggles system mute |
| `play` / `pause` | Toggles media playback |
| `next track` / `previous track` | Changes media track |
| `show commands` | Prints help |
| `quit remote control` | Exits the program |

The prototype intentionally contains no shutdown, restart, file deletion, shell-command, or arbitrary-program command. Therefore none of the current commands needs a confirmation prompt. Any future disruptive command should set `needs_confirmation=True` and be confirmed by an interaction policy before it reaches the platform controller.

## Model, speed, and memory expectations

The default `vosk-model-small-en-us-0.15` download is about **40 MB** compressed and roughly **70 MB** after extraction. Vosk describes small models as suitable for desktop and mobile use; in practice, budget roughly **200–350 MB total RAM** for Python, Vosk, and the model. Actual use varies by Python build and audio driver.

The recognizer automatically uses the selected microphone's native default sample rate. A lightweight small English-only model and a constrained grammar (only supported command phrases) reduce recognition latency and false matches. This should work on ordinary 64-bit Windows 10/11 hardware without a GPU. Very noisy rooms, far-field microphones, and strong accents can still reduce accuracy.

To inspect microphone device numbers:

```powershell
remote-control --list-devices
```

Set `input_device` to the desired numeric device ID in `%LOCALAPPDATA%\RemoteControlVoice\config.json`. You may also set `sample_rate`; leave it `null` for automatic hardware detection.

## Architecture

```text
VoiceAdapter → recognized text → CommandParser → CommandExecutor → WindowsController
future Telegram adapter ────────────────┘
```

- `adapters/voice.py` owns F8 and always-listening behavior.
- `speech/vosk_recognizer.py` owns local speech-to-text.
- `commands.py` converts exact phrases into typed actions.
- `executor.py` is input-agnostic and applies command policy.
- `platform/windows.py` is the only layer that controls Windows.

A future Telegram adapter only needs to implement the small `InputAdapter` protocol and pass message text to the same parser/executor. It does not need to duplicate or rewrite Windows command logic. Telegram is intentionally not included in version one.

## Development checks

```powershell
python -m unittest discover -s tests
python -m compileall src scripts tests
```

The parser, config, grammar, and executor can be tested on macOS/Linux. Global F8 capture, microphone input, Vosk decoding, app launching, and media keys require final testing on Windows.
