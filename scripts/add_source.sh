#!/usr/bin/env bash
# Usage: bash scripts/add_source.sh <service> <lang> <number> "<title>" "<url>"
set -e
service="$1"; lang="$2"; num="$3"; title="$4"; url="$5"
dir="data/sources/$service"
mkdir -p "$dir"
file="$dir/${service}_${lang}_${num}.md"
{
  echo "---"
  echo "service: $service"
  echo "title: $title"
  echo "url: $url"
  echo "date_checked: $(date +%F)"
  echo "language: $lang"
  echo "---"
  echo
  powershell.exe -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; Get-Clipboard" | tr -d '\r'
} > "$file"
echo "Created $file"
wc -c "$file"
head -n 15 "$file"
