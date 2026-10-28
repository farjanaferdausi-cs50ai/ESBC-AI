"""Embed the architecture diagram in README.md and add a License section."""
import re
from pathlib import Path

readme = Path("README.md")
text = readme.read_text(encoding="utf-8")

img = (
    '<p align="center">\n'
    '  <a href="docs/architecture.svg">\n'
    '    <img src="docs/architecture.png" alt="ESBC-AI system architecture" width="100%">\n'
    "  </a>\n"
    "</p>"
)

if "docs/architecture.png" in text:
    print("Diagram already embedded.")
else:
    new_text, n = re.subn(r"```mermaid.*?```", img, text, count=1, flags=re.S)
    if n:
        text = new_text
        print("Replaced the Mermaid block with the new diagram.")
    else:
        print("No Mermaid block found. Paste the image tag where you want it:")
        print(img)

if "## License" not in text:
    text = text.rstrip() + (
        "\n\n## License\n\n"
        "The code in this repository is released under the [MIT License](LICENSE). "
        "Copyright (c) 2026 Farjana Ferdausi.\n\n"
        "The files under `data/sources/` summarize official Bangladesh government web pages. "
        "Each file keeps its source URL and the date I checked it. "
        "English and Bangla translations in those files are my own and are not official texts.\n"
    )
    print("Added the License section.")

readme.write_text(text, encoding="utf-8")
