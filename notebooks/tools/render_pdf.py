#!/usr/bin/env python3
"""Render a notebook in notebooks/ to a print-ready PDF.

Markdown -> styled HTML -> headless Chrome -> PDF. Chrome is the only renderer
this needs, and it is present both on the authoring machine and on GitHub's
Ubuntu runners, so a PDF built in CI is the same document as one built by hand.

    python3 notebooks/tools/render_pdf.py notebooks/<name>.md

Writes alongside the input unless -o is given. Requires the `markdown` package.

Chrome writes the PDF and then does not always exit, so this does not wait for
the process: it waits for the output file to appear and stop growing, then kills
it. Waiting on the process instead can hang indefinitely.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

CHROME_CANDIDATES = [
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }

html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font: 10.2pt/1.5 "Charter", "Georgia", "Times New Roman", serif;
  color: #1a1a1a; margin: 0;
}

h1 {
  font-size: 19pt; line-height: 1.25; margin: 0 0 2mm 0;
  font-weight: 600; letter-spacing: -0.01em;
}
h1 + p { margin-top: 0; }
h2 {
  font-size: 13pt; margin: 9mm 0 2.5mm 0; padding-bottom: 1.2mm;
  border-bottom: 0.6pt solid #b8b8b8; font-weight: 600;
  break-after: avoid; page-break-after: avoid;
}
h3 {
  font-size: 11pt; margin: 6mm 0 2mm 0; font-weight: 600;
  break-after: avoid; page-break-after: avoid;
}
h2:first-of-type { margin-top: 6mm; }

p, li { orphans: 2; widows: 2; }
p { margin: 0 0 2.6mm 0; }
ul, ol { margin: 0 0 2.6mm 0; padding-left: 6mm; }
li { margin: 0 0 1.2mm 0; }

code, kbd {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 0.86em; background: #f0f0f0; padding: 0.3mm 0.9mm;
  border-radius: 1px; white-space: nowrap;
}
pre {
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 7.6pt; line-height: 1.35; background: #f7f7f7;
  border: 0.5pt solid #ddd; border-radius: 2px;
  padding: 2.5mm 3mm; margin: 0 0 3mm 0; overflow: hidden;
  break-inside: avoid; page-break-inside: avoid;
}
pre code { background: none; padding: 0; font-size: 1em; white-space: pre; }

blockquote {
  margin: 0 0 3mm 0; padding: 2.5mm 3.5mm; background: #f4f6f8;
  border-left: 1.6pt solid #7a8a99;
}
blockquote p:last-child { margin-bottom: 0; }

table {
  border-collapse: collapse; width: 100%; margin: 0 0 3.5mm 0;
  font-size: 8.6pt; line-height: 1.38;
}
thead { display: table-header-group; }
tr { break-inside: avoid; page-break-inside: avoid; }
th {
  text-align: left; font-weight: 600; background: #ebeef0;
  border: 0.5pt solid #c4c4c4; padding: 1.3mm 1.8mm; vertical-align: bottom;
}
td {
  border: 0.5pt solid #d4d4d4; padding: 1.3mm 1.8mm; vertical-align: top;
}
tbody tr:nth-child(even) td { background: #fafafa; }
td code, th code { font-size: 0.92em; white-space: normal; padding: 0.2mm 0.6mm; }
td:empty { background: #f4f4f4; }

hr {
  border: 0; border-top: 0.5pt solid #ccc; margin: 7mm 0 5mm 0;
}

a { color: #1a4a7a; text-decoration: none; border-bottom: 0.4pt solid #b9cbdb; }
a code { color: inherit; }
.sources a { word-break: break-all; }

.footer {
  margin-top: 8mm; padding-top: 2.5mm; border-top: 0.5pt solid #ccc;
  font-size: 7.6pt; color: #666;
}
"""

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head><body>
{body}
<div class="footer">{footer}</div>
</body></html>
"""


def find_chrome():
    for path in CHROME_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def wait_for_pdf(path, timeout, settle=0.6):
    """Return True once `path` exists and has stopped growing."""
    deadline = time.time() + timeout
    last, stable_since = -1, None
    while time.time() < deadline:
        size = os.path.getsize(path) if os.path.isfile(path) else -1
        if size > 0 and size == last:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since >= settle:
                return True
        else:
            stable_since = None
        last = size
        time.sleep(0.2)
    return False


def to_html(md_text, title, footer):
    try:
        import markdown
    except ImportError:
        sys.exit("need the markdown package: python3 -m pip install --user markdown")
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    return HTML.format(title=title, css=CSS, body=body, footer=footer)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="Markdown file to render")
    ap.add_argument("-o", "--output", help="output PDF (default: source with .pdf)")
    ap.add_argument("--title", help="PDF title (default: first heading)")
    ap.add_argument("--footer", default="", help="footer line")
    ap.add_argument("--keep-html", action="store_true", help="leave the intermediate HTML in place and report it")
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds to wait for Chrome to finish the PDF")
    args = ap.parse_args()

    chrome = find_chrome()
    if not chrome:
        sys.exit("no Chrome/Chromium found; cannot render a PDF on this machine")

    src = os.path.abspath(args.source)
    with open(src, encoding="utf-8") as fh:
        md_text = fh.read()

    title = args.title
    if not title:
        m = re.search(r"^#\s+(.+)$", md_text, re.M)
        title = re.sub(r"[`*_]", "", m.group(1)).strip() if m else os.path.basename(src)

    out = os.path.abspath(args.output or os.path.splitext(src)[0] + ".pdf")
    html = to_html(md_text, title, args.footer)

    tmp = tempfile.mkdtemp(prefix="render_pdf_")
    try:
        html_path = os.path.join(tmp, "doc.html")
        pdf_path = os.path.join(tmp, "doc.pdf")
        with open(html_path, "w", encoding="utf-8") as fh:
            fh.write(html)

        cmd = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--user-data-dir=" + os.path.join(tmp, "profile"),
            "--no-pdf-header-footer",
            "--print-to-pdf=" + pdf_path,
            "file://" + html_path,
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            if not wait_for_pdf(pdf_path, args.timeout):
                proc.kill()
                err = proc.stderr.read().decode("utf-8", "replace")[-2000:]
                sys.exit("Chrome produced no PDF within {}s:\n{}".format(args.timeout, err))
        finally:
            proc.kill()
            proc.wait()
        shutil.copyfile(pdf_path, out)
        if args.keep_html:
            kept = os.path.splitext(out)[0] + ".html"
            shutil.copyfile(html_path, kept)
            print("html:", kept)
        print("{}  ({:,} bytes)".format(out, os.path.getsize(out)))
    finally:
        if not args.keep_html:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print("intermediate:", tmp)


if __name__ == "__main__":
    main()
