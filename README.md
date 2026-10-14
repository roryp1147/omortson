# Omortson

A retro-industrial CRT system monitor for Windows. Four analog gauges show CPU load, memory, GPU load and GPU temperature, with a teletype terminal, a network radar, warning lamps, rotary knobs and optional ambient station noises.

![Omortson](https://roryp1147.github.io/img/omortson.webp)

## Download

**[Download Omortson for Windows (v1.0.0)](https://github.com/roryp1147/omortson/releases/latest/download/Omortson-1.0.0-win64.zip)** · [Project page](https://roryp1147.github.io/projects/omortson.html)

Windows 10/11 (64-bit). No Python required: extract the zip and run `Omortson.exe`. The app isn't code-signed, so SmartScreen may warn you; click **More info → Run anyway**.

**GPU gauges need an AMD Radeon GPU.** GPU load, temperature and VRAM are read through AMD's ADLX library. On NVIDIA or Intel graphics the CPU, memory, disk and network readouts still work, but the GPU gauges show no signal.

## Run from source

Requires Windows 10/11 and Python 3.14.

```bat
git clone https://github.com/roryp1147/omortson.git
cd omortson
py -3.14 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

`run_omortson.bat` starts it without a console window. Press **F1** in the app for the key reference. `OMORTSON_MUTE=1` silences everything, and `OMORTSON_BOOT=0` skips the boot sequence. Settings live in the registry under `HKCU\Software\Omortson`.

### Custom terminal lines

The terminal types a random line every few minutes. To use your own, create `quotes_local.py` next to `main.py` (or next to `Omortson.exe`); it's gitignored and never bundled:

```python
QUOTE_SETS = {"mine": ["FIRST LINE", "SECOND LINE"]}
ACTIVE_QUOTES = "mine"
```

## Build the exe (PyInstaller)

```bat
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean --onedir --windowed --name Omortson ^
  --icon Omortson.ico --add-data "sounds;sounds" --add-data "Omortson.ico;." ^
  --exclude-module quotes_local main.py
```

The app ends up in `dist\Omortson\`. Zip that folder to share it.

## License

The **code** is MIT licensed, (c) 2026 Rory. The **icon and sounds** are free for personal use only and may not be redistributed or resold. See [LICENSE](LICENSE) (code) and [ASSETS-LICENSE.txt](ASSETS-LICENSE.txt) (assets). Not affiliated with any company.
