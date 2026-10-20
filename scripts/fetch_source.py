"""Download an official web page and save it as a knowledge-base source file."""
import re
import sys
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"User-Agent": "Mozilla/5.0 (ESBC-AI student capstone project)"}


def fetch(url):
    try:
        return requests.get(url, timeout=30, headers=HEADERS)
    except requests.exceptions.SSLError:
        print("Warning: SSL certificate problem, retrying without verification.")
        return requests.get(url, timeout=30, headers=HEADERS, verify=False)


def main():
    if len(sys.argv) != 5:
        sys.exit("Usage: python scripts/fetch_source.py <service> <en|bn> <number> <url>")
    service, lang, num, url = sys.argv[1:]
    res = fetch(url)
    res.raise_for_status()
    res.encoding = res.apparent_encoding or "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "form", "noscript", "aside"]):
        tag.decompose()
    title = re.sub(r"\s+", " ", soup.title.get_text()).strip() if soup.title else url
    lines, last = [], ""
    for raw in soup.get_text("\n").splitlines():
        line = re.sub(r"[ \t\u00a0]+", " ", raw).strip()
        if len(line) > 1 and line != last:
            lines.append(line)
            last = line
    body = "\n\n".join(lines)

    out_dir = ROOT / "data" / "sources" / service
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{service}_{lang}_{num}.md"
    header = (
        f"---\nservice: {service}\ntitle: {title}\nurl: {url}\n"
        f"date_checked: {date.today().isoformat()}\nlanguage: {lang}\n---\n\n"
    )
    out.write_text(header + body + "\n", encoding="utf-8")
    print(f"Saved {out} ({len(body)} characters)")
    if len(body) < 500:
        print("Warning: very little text. The page may load content with JavaScript; copy it manually.")
    print("--- preview ---")
    print(body[:600])


if __name__ == "__main__":
    main()
