#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# install.sh: set up OnDevice Speech To Text on a fresh Linux (XFCE, X11) laptop.
# Idempotent: safe to re-run; anything already in place is left alone.
#
#   ./install.sh           install everything, then run the checks
#   ./install.sh --check   only run the checks, change nothing
#
# Full explanation of every step: docs/REPLICATE.md
set -u

PROJECT="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
BREW_PREFIX="${HOMEBREW_PREFIX:-/home/linuxbrew/.linuxbrew}"
MODELS="$PROJECT/models"
CHECK_ONLY=false
[ "${1:-}" = "--check" ] && CHECK_ONLY=true

APT_PACKAGES="alsa-utils xdotool xclip x11-utils libnotify-bin pulseaudio-utils sound-theme-freedesktop python3-gi gir1.2-gtk-3.0 mesa-vulkan-drivers libvulkan1 curl"

# name|url|sha256
MODEL_LIST="
ggml-parakeet-tdt-0.6b-v3-q8_0.bin|https://huggingface.co/ggml-org/parakeet-GGUF/resolve/main/ggml-parakeet-tdt-0.6b-v3-q8_0.bin|4d64e9e96c2792186d072fde0034df0ad670cf680a2f53069052ead827fd600e
ggml-base.en.bin|https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin|a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002
ggml-silero-v5.1.2.bin|https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin|29940d98d42b91fbd05ce489f3ecf7c72f0a42f027e4875919a28fb4c04ea2cf
ggml-large-v3-turbo-q5_0.bin|https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin|394221709cd5ad1f40c46e6031ca61bce88931e6e088c188294c6d5a55ffa7e2
ggml-small.en.bin|https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin|c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d
ggml-tiny.en.bin|https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin|921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f
nemo_en_titanet_small.onnx|https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/nemo_en_titanet_small.onnx|ad4a1802485d8b34c722d2a9d04249662f2ece5d28a7a039063ca22f515a789e
"
# Speaker labels for meetings (lib/speakers.py) run on a project venv.
VENV_PACKAGES="sherpa-onnx==2.0.1 numpy"

ok() { printf '  [ok]   %s\n' "$1"; }
bad() { printf '  [FAIL] %s\n' "$1"; FAILED=$((FAILED + 1)); }
step() { printf '\n== %s\n' "$1"; }
FAILED=0

install_packages() {
  step "System packages (apt)"
  local missing=""
  for p in $APT_PACKAGES; do
    dpkg -s "$p" >/dev/null 2>&1 || missing="$missing $p"
  done
  if [ -z "$missing" ]; then ok "all present"; return; fi
  echo "  installing:$missing"
  sudo apt-get install -y $missing
}

install_whisper_cpp() {
  step "whisper.cpp (Homebrew)"
  if [ ! -x "$BREW_PREFIX/bin/brew" ]; then
    echo "  Homebrew not found at $BREW_PREFIX. Install it first:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    exit 1
  fi
  if [ -x "$BREW_PREFIX/bin/parakeet-cli" ]; then ok "already installed"; return; fi
  "$BREW_PREFIX/bin/brew" install whisper.cpp
}

download_models() {
  step "Models -> $MODELS"
  mkdir -p "$MODELS"
  local name url sum f
  while IFS='|' read -r name url sum; do
    [ -z "$name" ] && continue
    f="$MODELS/$name"
    if [ -f "$f" ] && echo "$sum  $f" | sha256sum -c --quiet - 2>/dev/null; then ok "$name"; continue; fi
    echo "  downloading $name"
    curl -fL --retry 3 -o "$f.part" "$url" && mv "$f.part" "$f"
    echo "$sum  $f" | sha256sum -c --quiet - || { echo "  checksum mismatch for $name"; exit 1; }
  done <<<"$MODEL_LIST"
}

make_venv() {
  step "Python venv for speaker labels -> $PROJECT/.venv"
  if "$PROJECT/.venv/bin/python" -c 'import sherpa_onnx, numpy' 2>/dev/null; then ok "already set up"; return; fi
  if ! command -v uv >/dev/null; then
    echo "  uv not found: install it (curl -LsSf https://astral.sh/uv/install.sh | sh) and re-run"
    exit 1
  fi
  uv venv "$PROJECT/.venv" --python 3.12 -q && uv pip install -q --python "$PROJECT/.venv/bin/python" $VENV_PACKAGES
}

link_into_system() {
  step "Links into the system"
  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/whisper-cpp"
  for cmd in dictate dictate-live dictate-stats dictate-compare; do
    ln -sfn "$PROJECT/bin/$cmd" "$HOME/.local/bin/$cmd"
  done
  local m="$HOME/.local/share/whisper-cpp/models"
  if [ -e "$m" ] && [ ! -L "$m" ]; then
    echo "  $m exists and is a real directory; move its models into $MODELS and remove it, then re-run"
  else
    ln -sfn "$MODELS" "$m"
  fi
  chmod +x "$PROJECT"/bin/* "$PROJECT/lib/active-app"
  ok "commands in ~/.local/bin, models linked"
}

bind_hotkey() {
  step "F9 hotkey (XFCE)"
  if ! command -v xfconf-query >/dev/null; then
    echo "  Not XFCE: bind F9 to $HOME/.local/bin/dictate-live in your desktop's keyboard settings"
    return
  fi
  xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9 -n -t string -s "$HOME/.local/bin/dictate-live"
  ok "F9 -> dictate-live"
}

run_checks() {
  step "Checks"
  [ "${XDG_SESSION_TYPE:-x11}" = x11 ] && ok "X11 session" || bad "session is ${XDG_SESSION_TYPE}; xdotool typing needs X11"
  for p in $APT_PACKAGES; do dpkg -s "$p" >/dev/null 2>&1 || bad "apt package missing: $p"; done
  for b in whisper-server whisper-cli parakeet-cli; do
    [ -x "$BREW_PREFIX/bin/$b" ] && ok "$b" || bad "$b missing (brew install whisper.cpp)"
  done
  /usr/bin/python3 -c 'import gi; gi.require_version("Gtk", "3.0"); from gi.repository import Gtk' 2>/dev/null \
    && ok "GTK 3 for /usr/bin/python3" || bad "python3-gi / gir1.2-gtk-3.0 not importable"
  local name url sum
  while IFS='|' read -r name url sum; do
    [ -z "$name" ] && continue
    [ -f "$MODELS/$name" ] && ok "model $name" || bad "model missing: $name (re-run ./install.sh)"
  done <<<"$MODEL_LIST"
  for cmd in dictate dictate-live dictate-stats dictate-compare; do
    [ "$(readlink -f "$HOME/.local/bin/$cmd")" = "$(readlink -f "$PROJECT/bin/$cmd")" ] && ok "~/.local/bin/$cmd" || bad "~/.local/bin/$cmd not linked"
  done
  if command -v xfconf-query >/dev/null; then
    [ "$(xfconf-query -c xfce4-keyboard-shortcuts -p /commands/custom/F9 2>/dev/null)" = "$HOME/.local/bin/dictate-live" ] \
      && ok "F9 bound to dictate-live" || bad "F9 not bound"
  fi
  arecord -l 2>/dev/null | grep -q '^card' && ok "microphone device present" || bad "no capture device (arecord -l)"
  "$PROJECT/.venv/bin/python" -c 'import sherpa_onnx, numpy' 2>/dev/null \
    && ok "speaker labels venv (.venv)" || bad "speaker labels venv missing (re-run ./install.sh)"
  command -v parec >/dev/null && command -v pactl >/dev/null \
    && ok "parec and pactl (call audio)" || bad "parec/pactl missing (call audio for meetings)"
  # End-to-end engine test on a synthetic clip: silence must give empty text, quickly.
  local wav
  wav="$(mktemp --suffix=.wav)"
  "$BREW_PREFIX/bin/ffmpeg" -v error -y -f lavfi -i anullsrc=r=16000:cl=mono -t 2 "$wav" 2>/dev/null \
    || head -c 64044 /dev/zero >"$wav"
  if "$BREW_PREFIX/bin/parakeet-cli" -m "$MODELS/ggml-parakeet-tdt-0.6b-v3-q8_0.bin" -f "$wav" -np >/dev/null 2>&1; then
    ok "parakeet runs"
  else
    bad "parakeet-cli failed on a test clip"
  fi
  "$BREW_PREFIX/bin/whisper-cli" -m "$MODELS/ggml-tiny.en.bin" -f "$wav" 2>&1 | grep -q 'using Vulkan0 backend' \
    && ok "GPU (Vulkan) in use" || echo "  [note] running on CPU only (slower; see docs/REPLICATE.md, GPU)"
  rm -f "$wav"
  echo
  if [ "$FAILED" -eq 0 ]; then
    echo "All checks passed. Press F9, speak, press F9 again."
  else
    echo "$FAILED check(s) failed; see docs/REPLICATE.md, Troubleshooting."
  fi
  return "$FAILED"
}

if ! $CHECK_ONLY; then
  install_packages
  install_whisper_cpp
  download_models
  make_venv
  link_into_system
  bind_hotkey
fi
run_checks
