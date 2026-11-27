#!/usr/bin/env python3
"""Check that every h2 section heading on the site's HTML pages carries a
copy-permalink button (the "#" button that copies the section URL).

For every HTML file in the repository:
  * each <h2> must have an id attribute;
  * inside the <h2> there must be a <button class="permalink"> whose
    data-section matches that id;
  * a page with at least one <h2> must also carry the permalink CSS
    (an h2 .permalink rule) and the click handler (closest(".permalink")).

Pages without any <h2> pass automatically.

Run from the repository root: python3 tools/check_section_permalinks.py
Exits 1 and lists every violation when the check fails.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CSS_RE = re.compile(r"\.permalink\s*\{")
JS_RE = re.compile(r"closest\(\s*[\"']\.permalink[\"']\s*\)")


class H2Scanner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h2s = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h2":
            self._current = {"id": attrs.get("id"), "sections": []}
        elif tag == "button" and self._current is not None:
            if "permalink" in (attrs.get("class") or "").split():
                self._current["sections"].append(attrs.get("data-section"))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag == "h2":
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag == "h2" and self._current is not None:
            self.h2s.append(self._current)
            self._current = None


LINK_RE = re.compile(r'<link[^>]+rel=["\']stylesheet["\'][^>]*>', re.I)
HREF_RE = re.compile(r'href=["\']([^"\']+)["\']', re.I)
SCRIPT_SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)


def load_linked_text(path, text):
    """Return the page text plus the text of its in-repo stylesheets and scripts."""
    parts = [text]
    refs = [HREF_RE.search(m.group(0)) for m in LINK_RE.finditer(text)]
    refs = [m.group(1) for m in refs if m]
    refs += SCRIPT_SRC_RE.findall(text)
    for ref in refs:
        if ref.startswith(("http://", "https://", "//", "data:")):
            continue
        target = (path.parent / ref.split("#")[0].split("?")[0]).resolve()
        if target.is_file() and ROOT in target.parents:
            parts.append(target.read_text(encoding="utf-8"))
    return "\n".join(parts)


def check_file(path):
    text = path.read_text(encoding="utf-8")
    scanner = H2Scanner()
    scanner.feed(text)
    scanner.close()
    problems = []
    for h2 in scanner.h2s:
        if not h2["id"]:
            problems.append("an h2 heading has no id attribute")
        elif h2["id"] not in h2["sections"]:
            problems.append(
                f'h2 "{h2["id"]}" has no permalink button with a matching data-section'
            )
    if scanner.h2s:
        full_text = load_linked_text(path, text)
        if not CSS_RE.search(full_text):
            problems.append("the permalink CSS rule (h2 .permalink) is missing")
        if not JS_RE.search(full_text):
            problems.append('the permalink click handler (closest(".permalink")) is missing')
    return problems


def main():
    files = sorted(p for p in ROOT.rglob("*.html") if ".git" not in p.parts)
    failed = False
    total_h2 = 0
    for path in files:
        problems = check_file(path)
        rel = path.relative_to(ROOT)
        if problems:
            failed = True
            for problem in problems:
                print(f"{rel}: {problem}")
        else:
            scanner = H2Scanner()
            scanner.feed(path.read_text(encoding="utf-8"))
            scanner.close()
            total_h2 += len(scanner.h2s)
    if failed:
        print(
            "\nEvery h2 section heading needs the copy-permalink button: give the h2 an id, "
            "add <button class=\"permalink\" data-section=\"<id>\">#</button> inside it, and "
            "make sure the page carries the h2 .permalink CSS and the click handler "
            "(copy the pattern from any existing page).",
            file=sys.stderr,
        )
        sys.exit(1)
    print(f"ok: {len(files)} HTML pages checked, {total_h2} section headings all have copy-permalink buttons")


if __name__ == "__main__":
    main()
