# Replicating this system on another laptop

Last updated: 2026-11-16T12:52:17+00:00

Written so that a person or an AI agent with shell access can rebuild the setup from this document alone. The automated path is `install.sh`; the manual path below explains every step it performs, for machines where the script does not fit.

## 0. Requirements

| Item | Reference machine | Requirement |
|---|---|---|
| OS | Linux Mint 22.1 (Ubuntu 24.04 base), kernel 6.8 | Debian or Ubuntu family for the apt names below; other distros need equivalent packages |
| Desktop | XFCE 4.18 on **X11** | Any X11 desktop. Wayland is not supported (see Limits) |
| CPU | Intel i7-11390H (4 cores, AVX-512) | Any x86-64; slower CPUs mean longer waits |
| GPU | Intel Iris Xe via Mesa Vulkan | Optional; without a Vulkan GPU, whisper large-v3-turbo is about 3x slower. Parakeet and base.en stay usable |
| RAM | 16 GB | 8 GB is enough (a session uses under 1 GB) |
| Disk | 1.9 GB for all models | 0.8 GB minimum (Parakeet + base.en + VAD) |
| Microphone | Built-in | Any ALSA/PipeWire capture device |
| uv | User install | Creates `.venv` for speaker labels (`curl -LsSf https://astral.sh/uv/install.sh \| sh`) |

## 1. Copy the project

Copy the whole folder to the new laptop (any path; spaces are fine), **excluding** `models/` (1.9 GB, re-downloaded and checksummed), `.venv/` (rebuilt), `data/` and `transcripts/` (personal). For example:

```bash
rsync -a --exclude models/ --exclude .venv/ --exclude data/ --exclude transcripts/ "OnDevice Speech To Text/" newlaptop:"Documents/OnDevice Speech To Text/"
```

## 2. Automated install

```bash
cd ~/Documents/"OnDevice Speech To Text"
./install.sh
```

It is idempotent. It installs apt packages (asks for sudo), installs whisper.cpp with Homebrew, downloads and verifies the models, links the commands, binds F9 on XFCE, then runs the checks. `./install.sh --check` runs only the checks. If every check prints `[ok]`, press F9 and speak.

Homebrew itself is a prerequisite; if missing, the script prints the official install command and stops.

## 3. Manual install (what install.sh does)

### 3.1 System packages

```bash
sudo apt-get install -y alsa-utils xdotool xclip x11-utils libnotify-bin pulseaudio-utils \
  sound-theme-freedesktop python3-gi gir1.2-gtk-3.0 mesa-vulkan-drivers libvulkan1 curl
```

| Package | Used for |
|---|---|
| alsa-utils | `arecord` (microphone capture; Homebrew's ffmpeg lacks PulseAudio input) |
| xdotool | Typing the text into the focused window; finding the focused window |
| xclip | Pasting long text into terminals; handing text over when the window changed |
| x11-utils | `xprop` (app name for analytics) |
| libnotify-bin | `notify-send` (basic mode notifications) |
| pulseaudio-utils, sound-theme-freedesktop | Start and stop sounds (`paplay`, freedesktop `.oga` files); `pactl` (is a call open?) and `parec` (computer sound during calls) |
| python3-gi, gir1.2-gtk-3.0 | GTK 3 overlay window in `/usr/bin/python3` |
| mesa-vulkan-drivers, libvulkan1 | GPU acceleration through Vulkan |

### 3.2 whisper.cpp

```bash
# Homebrew, if not installed: https://brew.sh
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install whisper.cpp        # reference: whisper.cpp 1.9.5, ggml 0.27.0
```

This provides `whisper-server`, `whisper-cli` and `parakeet-cli` in `/home/linuxbrew/.linuxbrew/bin`. The scripts call them by that absolute path because hotkeys run with a minimal PATH. If Homebrew lives elsewhere, export `HOMEBREW_PREFIX` in the session environment and edit `BREW=` at the top of `bin/dictate` and `bin/dictate-compare`.

Verify the GPU backend: `whisper-cli -m models/ggml-tiny.en.bin -f some.wav 2>&1 | grep 'using Vulkan0 backend'`.

### 3.3 Models

Put them in `models/` inside the project. Verify every file with `sha256sum -c`.

| File | URL | SHA-256 |
|---|---|---|
| ggml-parakeet-tdt-0.6b-v3-q8_0.bin | https://huggingface.co/ggml-org/parakeet-GGUF/resolve/main/ggml-parakeet-tdt-0.6b-v3-q8_0.bin | 4d64e9e96c2792186d072fde0034df0ad670cf680a2f53069052ead827fd600e |
| ggml-base.en.bin | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin | a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002 |
| ggml-silero-v5.1.2.bin | https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin | 29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf |
| ggml-large-v3-turbo-q5_0.bin | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin | 394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2 |
| ggml-small.en.bin | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin | c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d |
| ggml-tiny.en.bin | https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin | 921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f |
| nemo_en_titanet_small.onnx | https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/nemo_en_titanet_small.onnx | ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e |

The first three are required for the default setup; `nemo_en_titanet_small.onnx` is required for meetings; the rest are alternatives.

Speaker labels run on a project venv (needs `uv`):

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python sherpa-onnx==2.0.1 numpy
```

Without the venv or the model, dictation works as before and meeting mode stays off.

### 3.4 Links

```bash
P=~/Documents/"OnDevice Speech To Text"
mkdir -p ~/.local/bin ~/.local/share/whisper-cpp
for c in dictate dictate-live dictate-stats dictate-compare; do ln -sfn "$P/bin/$c" ~/.local/bin/$c; done
ln -sfn "$P/models" ~/.local/share/whisper-cpp/models     # optional, for other whisper.cpp tools
chmod +x "$P"/bin/* "$P/lib/active-app"
```

### 3.5 Hotkey

XFCE:

```bash
xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9 -n -t string -s "$HOME/.local/bin/dictate-live"
```

Other X11 desktops: create a custom shortcut for F9 running `~/.local/bin/dictate-live` (an absolute path). Make sure nothing else uses plain F9 (on XFCE, Ctrl+F9 and Alt+F9 are window-manager keys and are unaffected). On laptops whose F keys default to media functions, toggle Fn Lock or bind the key the media function emits.

### 3.6 Settings

`config/dictate.conf` travels with the folder. Adjust per machine:

- `threads`: physical core count (4 on the reference machine; hyper-threads gave no gain).
- `final_engine`: `parakeet` (English and European languages, fast) or `whisper` (Indian languages, vocabulary prompt, slower).
- `hotkey_label`: the key name shown in the box, if not F9.

### 3.7 Verify

```bash
./install.sh --check          # every line should be [ok]
dictate-compare               # speak a sentence, press Enter; check the transcripts
```

Then press F9 in a text editor, speak, press F9 again.

## 4. Porting notes for other environments

| Environment | What changes |
|---|---|
| GNOME/KDE on X11 | Hotkey through the desktop's keyboard settings; everything else is the same |
| Wayland | `xdotool type` cannot type into other apps: use `ydotool type` (needs the ydotoold service) or `wtype`; the GTK POPUP overlay positioning and drag rely on X11 and need a layer-shell approach. Not tested |
| No Homebrew | Build whisper.cpp from source (https://github.com/ggml-org/whisper.cpp, `cmake -B build -DGGML_VULKAN=ON && cmake --build build`), then point `BREW` in the scripts at the build's `bin` |
| NVIDIA GPU | Vulkan works with the NVIDIA driver; a CUDA build of whisper.cpp would be faster still |
| macOS | Not applicable: macOS has built-in dictation |

## 5. Troubleshooting a fresh install

| Check fails | Fix |
|---|---|
| `X11 session` | Log in to an X11 session (login screen session menu) |
| apt package missing | `sudo apt-get install <package>` |
| `whisper-server` / `parakeet-cli` missing | `brew install whisper.cpp`; older formula versions lack `parakeet-cli` (needs 1.9.5 or newer) |
| GTK 3 not importable | `sudo apt-get install python3-gi gir1.2-gtk-3.0`; must be `/usr/bin/python3`, not Homebrew's |
| model missing or checksum mismatch | Delete the file in `models/` and re-run `./install.sh` |
| no capture device | Connect or enable a microphone; check `arecord -l` |
| CPU only note | Install `mesa-vulkan-drivers` (Intel/AMD) or the NVIDIA driver; check `vulkaninfo --summary` |

## 6. What is intentionally not copied

- `models/`: large and re-downloadable with checksums.
- `data/sessions.jsonl`: personal usage analytics (numbers only).
- `data/dictations.txt`, `data/live/`, `transcripts/`: private text (docs/SECURITY.md).
- `.venv/`: platform-specific; `install.sh` rebuilds it.
- `data/overlay-position.json`: depends on screen size.
