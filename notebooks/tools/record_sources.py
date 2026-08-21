#!/usr/bin/env python3
"""Record the hash of each notebook's Markdown next to its rendered PDF.

Both formats of a notebook are committed together. The risk in that arrangement
is editing the Markdown and forgetting to re-render, leaving a PDF that claims
to be the same document and is not. This writes the hash of each notebook so
that mismatch is detectable in CI.

Hashing the source rather than comparing PDFs is deliberate: Chrome stamps a
creation date into every render, so two PDFs of identical content never match
byte for byte.

Run after rendering, and commit the result with the .md and .pdf:

    python3 notebooks/tools/render_pdf.py notebooks/<name>.md
    python3 notebooks/tools/record_sources.py
"""

import hashlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOTEBOOKS = os.path.dirname(HERE)
RECORD = os.path.join(NOTEBOOKS, "pdf-sources.sha256")


def main():
    lines, missing = [], []
    for name in sorted(os.listdir(NOTEBOOKS)):
        if not name.endswith(".md") or name == "README.md":
            continue
        path = os.path.join(NOTEBOOKS, name)
        if not os.path.isfile(os.path.splitext(path)[0] + ".pdf"):
            missing.append(name)
        digest = hashlib.sha256(io.open(path, "rb").read()).hexdigest()
        lines.append("{}  {}\n".format(digest, name))

    if missing:
        sys.exit("no PDF rendered yet for: " + ", ".join(missing))

    io.open(RECORD, "w", encoding="utf-8", newline="\n").writelines(lines)
    print("recorded {} notebook(s) in {}".format(len(lines), os.path.basename(RECORD)))


if __name__ == "__main__":
    main()
