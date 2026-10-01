# Remote control

A Windows desktop interface for controlling a PC with **English voice commands and webcam gestures**. Speech recognition uses Vosk locally and gesture recognition uses MediaPipe locally: no cloud API, subscription, account, or per-minute fee is required.

The interface discovers installed Windows apps automatically, shows every recognized name, and can launch them with phrases such as **“open Spotify”** or **“launch Visual Studio Code.”** The default voice interaction is push-to-talk: hold **F8**, say one command, and release F8. Always-listening and webcam gesture modes are also included.

## Easy Windows installation

1. On GitHub, click **Code → Download ZIP**, then extract the ZIP.
2. Open the extracted `remote-control-main` folder.
3. Double-click **`INSTALL.bat`**. It creates an isolated environment, installs the app, and downloads the offline English voice and gesture models automatically.
4. Double-click **`START.bat`** whenever you want to run the recommended push-to-talk mode.

For continuous listening, double-click **`START_ALWAYS_LISTENING.bat`** instead. The launchers automatically start `INSTALL.bat` if setup has not been completed yet. `START_F8.bat` is also included as an explicit name for the default mode.

The only prerequisite is 64-bit Python 3.9–3.12. If Python is missing, the installer shows the official download address and the exact option to select. Installation needs internet once for the free dependencies and models; normal use is fully offline.

## Privacy and cost

- Microphone audio and webcam frames are processed in memory on this PC and are not saved or uploaded by Remote control.
- Recognition works without internet after the model has been downloaded once.
- The model and Python libraries are free and open source. No API key is used.
- `scripts/download_model.py` downloads the speech model from Vosk and the hand/pose models from Google's official MediaPipe model host. You can instead download and copy the models manually from another computer.

## Interface

The GUI opens automatically and contains:

- Voice mode controls for F8 and always-listening modes.
- A webcam preview with start/stop controls.
- Buttons for volume, mute, play/pause, and changing songs.
- A text command box for testing without a microphone.
- A searchable **Installed apps** tab containing the names available to voice control.
- A live activity log showing recognized commands and actions.

Webcam access is off until **Start webcam** is clicked. Voice control starts automatically in the selected mode.

For troubleshooting or automation without the GUI, run `remote-control --headless`. Use `remote-control --list-apps` to print the discovered app names.

## Manual Windows setup

Use this section only if you prefer the command line or the easy installer cannot run. Install 64-bit Python 3.9–3.12 from [python.org](https://www.python.org/downloads/windows/) and select **Add Python to PATH** during installation. Then open PowerShell in this project folder:

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
| `open Spotify` | Opens Spotify if installed |
| `start Photoshop` | Opens Photoshop if installed |
| `launch Visual Studio Code` | Opens Visual Studio Code if installed |
| `volume up` / `volume down` | Changes system volume one step |
| `mute` / `unmute` | Toggles system mute |
| `play` / `pause` | Toggles media playback |
| `next song` / `previous song` | Changes song |
| `show commands` | Prints help |
| `quit remote control` | Exits the program |

App names are rebuilt at startup from the Windows Start Menu, registered App Paths, and Windows `Get-StartApps` catalog. The GUI shows the exact recognized list. This covers normal desktop programs, Start Menu shortcuts, and Microsoft Store apps without allowing arbitrary voice-generated shell commands.

## Webcam gestures

Click **Start webcam** in the interface and keep your upper body and hands visible:

| Gesture | Result |
| --- | --- |
| Move from sitting to standing | Play/pause |
| Swipe one hand left | Previous song |
| Swipe one hand right | Next song |

Standing detection uses knee angles, so the camera must see the hips, knees, and ankles. The first detected standing pose does not trigger playback; the app must first observe a seated pose. Swipes use deliberate horizontal wrist movement and a cooldown to reduce accidental repeated commands. Lighting, camera angle, occlusion, and motion blur affect reliability.

The prototype intentionally contains no shutdown, restart, file deletion, shell-command, or arbitrary-program command. Therefore none of the current commands needs a confirmation prompt. Any future disruptive command should set `needs_confirmation=True` and be confirmed by an interaction policy before it reaches the platform controller.

## Model, speed, and memory expectations

The default `vosk-model-small-en-us-0.15` download is about **40 MB** compressed and roughly **70 MB** after extraction. The MediaPipe hand and lightweight pose task models add roughly **15 MB**, while OpenCV, MediaPipe, and their runtime dependencies make the initial Python installation substantially larger. Budget roughly **300–700 MB RAM** when voice, GUI, and webcam recognition are all active. Actual use varies by camera resolution, Python build, and audio/video drivers.

The recognizer automatically uses the selected microphone's native default sample rate. A lightweight small English-only model and a grammar containing the base commands plus discovered app names reduce recognition latency and false matches. Webcam processing uses CPU by default. This should work on ordinary 64-bit Windows 10/11 hardware without a GPU, though webcam gestures benefit from a modern multi-core CPU. Very noisy rooms, far-field microphones, and strong accents can still reduce voice accuracy.

To inspect microphone device numbers:

```powershell
remote-control --list-devices
```

Set `input_device` to the desired numeric device ID in `%LOCALAPPDATA%\RemoteControlVoice\config.json`. You may also set `sample_rate`; leave it `null` for automatic hardware detection.

## Architecture

```text
VoiceAdapter → recognized text → CommandParser → CommandExecutor → WindowsController
GUI buttons/text ───────────────────────┤
Camera gestures ────────────────────────┤
future Telegram adapter ────────────────┘
```

- `adapters/voice.py` owns F8 and always-listening behavior.
- `adapters/camera.py` turns local hand/body landmarks into debounced gestures.
- `app_catalog.py` discovers installed applications and safe launch targets.
- `gui.py` provides the Windows desktop interface.
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
