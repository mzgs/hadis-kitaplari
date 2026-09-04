#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROGRESS_FILE="$PROJECT_DIR/progress.md"
LOG_FILE="$PROJECT_DIR/buhari-logs.md"
MAX_RUNS="${1:-0}"
RUN_COUNT=0

if command -v cop >/dev/null 2>&1; then
  COP_RUNNER="direct"
# Etkileşimli Bash, Ubuntu'da /etc/bash.bashrc ile ~/.bashrc dosyalarını yükler.
elif command -v bash >/dev/null 2>&1 && bash -ic 'type cop >/dev/null 2>&1' >/dev/null 2>&1; then
  COP_RUNNER="bash"
# Login Bash, ~/.bash_profile dosyasını yükler.
elif command -v bash >/dev/null 2>&1 && bash -lic 'type cop >/dev/null 2>&1' >/dev/null 2>&1; then
  COP_RUNNER="bash_login"
elif command -v zsh >/dev/null 2>&1 && zsh -ic 'whence -w cop >/dev/null' >/dev/null 2>&1; then
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
      command cop "$@"
      ;;
    bash)
      bash -ic 'cop "$@"' -- "$@"
      ;;
    bash_login)
      bash -lic 'cop "$@"' -- "$@"
      ;;
    zsh)
      zsh -ic 'cop "$@"' -- "$@"
      ;;
  esac
}

PROMPT='progress.md ve buhari-logs.md dosyalarını oku. progress.md içindeki kalıcı talimatlara aynen uyarak yalnızca sıradaki 5 hadislik tek çalışma grubunu incele, gerekli doğrulanabilir düzeltmeleri yap, JSON ve referans sırası kontrollerini çalıştır, değişiklik günlüğünü ve progress.md içindeki güncel ilerleme alanlarını güncelle. Grup geçmişini progress.md içine ekleme. Koleksiyonda incelenecek hadis kalmadıysa Durum alanını Tamamlandı olarak güncelle.'

while true; do
  STATUS="$(progress_value 'Durum')"
  if [[ "$STATUS" == "Tamamlandı" ]]; then
    echo "İşlem tamamlandı: progress.md durumu Tamamlandı."
    break
  fi

  if (( MAX_RUNS > 0 && RUN_COUNT >= MAX_RUNS )); then
    echo "Belirlenen maksimum tur sayısına ulaşıldı: $MAX_RUNS"
    break
  fi

  BEFORE="$(progress_value 'Son tamamlanan hadis')"
  ((RUN_COUNT += 1))

  echo
  echo "Codex turu $RUN_COUNT başlıyor. Mevcut ilerleme: ${BEFORE:-bilinmiyor}"
  echo "Çalıştırıcı: $COP_RUNNER | Çalışma dizini: $PROJECT_DIR"

  run_cop exec \
    --skip-git-repo-check \
    "$PROMPT"

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
