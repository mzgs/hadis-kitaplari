#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROGRESS_FILE="$PROJECT_DIR/progress.md"
LOG_FILE="$PROJECT_DIR/buhari-logs.md"
MAX_RUNS="${1:-0}"
RUN_COUNT=0
SCRIPT_VERSION="pm2-v5"
COP_FUNCTION_FILE=""

USER_HOME="${HOME:-}"
if [[ -z "$USER_HOME" ]] && command -v getent >/dev/null 2>&1; then
  USER_HOME="$(getent passwd "$(id -u)" | awk -F: 'NR == 1 { print $6 }')"
fi

if [[ -z "$USER_HOME" && -r /etc/passwd ]]; then
  USER_HOME="$(awk -F: -v uid="$(id -u)" '$3 == uid { print $6; exit }' /etc/passwd)"
fi

if [[ -z "$USER_HOME" || ! -d "$USER_HOME" ]]; then
  echo "Hata: Çalışan kullanıcının ev dizini belirlenemedi." >&2
  exit 1
fi

# Snap yerine standalone Codex kurulumunu önceliklendir.
export PATH="$USER_HOME/.local/bin:$USER_HOME/bin:$USER_HOME/.codex/bin:$PATH"

cleanup() {
  if [[ -n "$COP_FUNCTION_FILE" && -f "$COP_FUNCTION_FILE" ]]; then
    rm -f -- "$COP_FUNCTION_FILE"
  fi
}

trap cleanup EXIT

if command -v cop >/dev/null 2>&1; then
  COP_RUNNER="direct"
# Etkileşimli Bash, Ubuntu'da /etc/bash.bashrc ile ~/.bashrc dosyalarını yükler.
elif command -v bash >/dev/null 2>&1 && HOME="$USER_HOME" bash -ic 'type cop >/dev/null 2>&1' >/dev/null 2>&1; then
  COP_RUNNER="bash"
  COP_FUNCTION_FILE="$(mktemp)"
  HOME="$USER_HOME" bash -ic 'declare -f cop > "$1"' -- "$COP_FUNCTION_FILE" </dev/null 2>/dev/null
# Login Bash, ~/.bash_profile dosyasını yükler.
elif command -v bash >/dev/null 2>&1 && HOME="$USER_HOME" bash -lic 'type cop >/dev/null 2>&1' >/dev/null 2>&1; then
  COP_RUNNER="bash_login"
  COP_FUNCTION_FILE="$(mktemp)"
  HOME="$USER_HOME" bash -lic 'declare -f cop > "$1"' -- "$COP_FUNCTION_FILE" </dev/null 2>/dev/null
elif command -v zsh >/dev/null 2>&1 && HOME="$USER_HOME" zsh -ic 'whence -w cop >/dev/null' >/dev/null 2>&1; then
  COP_RUNNER="zsh"
else
  echo "Hata: cop komutu veya shell fonksiyonu bulunamadı." >&2
  echo "Ubuntu için cop fonksiyonunun /etc/bash.bashrc, ~/.bashrc veya ~/.bash_profile içinde tanımlı olduğundan emin ol." >&2
  exit 1
fi

if [[ ! -f "$PROGRESS_FILE" || ! -f "$LOG_FILE" ]]; then
  echo "Hata: progress.md veya buhari-logs.md bulunamadı." >&2
  exit 1
fi

cd "$PROJECT_DIR"

echo "Betik sürümü: $SCRIPT_VERSION"

CODEX_PATH="$(command -v codex || true)"
CODEX_REAL_PATH=""

if [[ -n "$CODEX_PATH" ]]; then
  CODEX_REAL_PATH="$(readlink -f "$CODEX_PATH" 2>/dev/null || printf '%s' "$CODEX_PATH")"
fi

if [[ -z "$CODEX_PATH" ]]; then
  echo "Hata: cop fonksiyonunun kullanacağı codex binary'si bulunamadı." >&2
  exit 1
fi

if [[ "$CODEX_PATH" == /snap/* || "$CODEX_REAL_PATH" == /snap/* ]]; then
  echo "Hata: Snap Codex tespit edildi: $CODEX_REAL_PATH" >&2
  echo "Snap, /var/www çalışma dizinini /var/lib/snapd/void olarak değiştirir." >&2
  echo "Standalone Codex'i kur ve ~/.local/bin dizinini PATH başına ekle." >&2
  exit 1
fi

if [[ -n "$COP_FUNCTION_FILE" ]] && grep -q '/snap/' "$COP_FUNCTION_FILE"; then
  echo "Hata: cop fonksiyonu doğrudan bir Snap yolunu çağırıyor." >&2
  echo "cop içindeki /snap/.../codex yolunu $CODEX_REAL_PATH olarak değiştir." >&2
  exit 1
fi

echo "Codex binary: $CODEX_REAL_PATH"
echo "Başlangıç dizini: $(pwd -P)"

if [[ ! "$MAX_RUNS" =~ ^[0-9]+$ ]]; then
  echo "Kullanım: $0 [maksimum_tur]" >&2
  echo "maksimum_tur verilmezse veya 0 olursa tamamlanana kadar çalışır." >&2
  exit 1
fi

progress_value() {
  local label="$1"
  awk -v label="$label" 'index($0, "- " label ": ") == 1 {
    sub("^- " label ": ", "")
    print
    exit
  }' "$PROGRESS_FILE"
}

run_cop() {
  case "$COP_RUNNER" in
    direct)
      HOME="$USER_HOME" command cop "$@"
      ;;
    bash)
      HOME="$USER_HOME" bash --noprofile --norc -c 'source "$1"; shift; cop "$@"' \
        bash "$COP_FUNCTION_FILE" "$@"
      ;;
    bash_login)
      HOME="$USER_HOME" bash --noprofile --norc -c 'source "$1"; shift; cop "$@"' \
        bash "$COP_FUNCTION_FILE" "$@"
      ;;
    zsh)
      HOME="$USER_HOME" zsh -ic 'cop "$@"' -- "$@"
      ;;
  esac
}

PROMPT='progress.md ve buhari-logs.md dosyalarını oku. progress.md içindeki kalıcı talimatlara aynen uyarak yalnızca sıradaki 5 hadislik tek çalışma grubunu incele, gerekli doğrulanabilir düzeltmeleri yap, JSON ve referans sırası kontrollerini çalıştır, değişiklik günlüğünü ve progress.md içindeki güncel ilerleme alanlarını güncelle. Grup geçmişini progress.md içine ekleme. Koleksiyonda incelenecek hadis kalmadıysa Durum alanını Tamamlandı olarak güncelle. Bu Codex çağrısında tam olarak bir çalışma grubu tamamladıktan sonra başka bir gruba başlama; son yanıtını verip hemen çık.'

while (( MAX_RUNS == 0 || RUN_COUNT < MAX_RUNS )); do
  STATUS="$(progress_value 'Durum')"
  if [[ "$STATUS" == "Tamamlandı" ]]; then
    echo "İşlem tamamlandı: progress.md durumu Tamamlandı."
    break
  fi

  BEFORE="$(progress_value 'Son tamamlanan hadis')"
  ((RUN_COUNT += 1))

  echo
  echo "Codex turu $RUN_COUNT başlıyor. Mevcut ilerleme: ${BEFORE:-bilinmiyor}"
  echo "Çalıştırıcı: $COP_RUNNER | Çalışma dizini: $PROJECT_DIR"

  run_cop exec \
    --cd "$PROJECT_DIR" \
    --skip-git-repo-check \
    "$PROMPT" </dev/null

  AFTER="$(progress_value 'Son tamamlanan hadis')"
  STATUS="$(progress_value 'Durum')"

  if [[ "$STATUS" == "Tamamlandı" ]]; then
    echo "İşlem tamamlandı: $AFTER"
    break
  fi

  if [[ -z "$AFTER" || "$AFTER" == "$BEFORE" ]]; then
    echo "Hata: Codex turu progress.md içindeki ilerlemeyi değiştirmedi; döngü durduruldu." >&2
    exit 2
  fi

  echo "Tur $RUN_COUNT tamamlandı. Yeni ilerleme: $AFTER"
done

if [[ "${STATUS:-}" != "Tamamlandı" ]] && (( MAX_RUNS > 0 && RUN_COUNT >= MAX_RUNS )); then
  echo "Belirlenen maksimum tur sayısına ulaşıldı: $MAX_RUNS"
fi
