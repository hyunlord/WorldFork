"""namuwiki 본문 정합 크롤러 — 게임 속 바바리안으로 살아남기 + 직접 link.

본 commit (Phase 9.19-a):
- 시작: https://namu.wiki/w/게임 속 바바리안으로 살아남기
- BFS depth-limited (★ DEPTH_LIMIT=2, 직접 + 1-hop)
- robots.txt 정합 (★ /w/ allowed)
- rate 1.5s (★ polite)
- stdlib only — urllib + html.parser
- 출력: .local/canon/namuwiki/<slug>.md

본격 본격:
- User-Agent 본격 명시 (★ "WorldForkAuditBot/1.0")
- HTTP 5xx / 4xx 본격 graceful skip + log
- duplicate URL 본격 visited set
- output 본격 markdown — title + body text (★ link 본격 본격)
- checkpoint: 본격 본격 본격 본격 본격 idempotent (★ 본격 본격 본격 skip)

사용:
  python scripts/crawl_namuwiki.py [--max-pages N]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

START_URL = (
    "https://namu.wiki/w/"
    + urllib.parse.quote("게임 속 바바리안으로 살아남기")
)
ALLOWED_PREFIX = "https://namu.wiki/w/"
OUT_DIR = Path(".local/canon/namuwiki")
DEPTH_LIMIT = 2
RATE_DELAY = 1.5  # seconds between requests (★ polite)
TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (compatible; WorldForkAuditBot/1.0; "
    "personal research; +https://github.com/hyunlord/WorldFork)"
)

# Skip patterns (★ off-topic / disambig / template / file pages)
SKIP_NAME_PATTERNS = (
    re.compile(r"^분류:"),
    re.compile(r"^틀:"),
    re.compile(r"^파일:"),
    re.compile(r"^사용자:"),
    re.compile(r"^토론:"),
    re.compile(r"^더 보기"),
)


def _safe_slug(page_title: str) -> str:
    """page title → filesystem-safe slug.

    한국어 본격 보존 + 슬래시/특수문자 본격 본격 본격.
    """
    s = page_title.replace("/", "_").replace("\\", "_")
    s = re.sub(r"[<>:\"|?*\x00-\x1f]", "", s)
    return s[:200]  # max length


def _fetch(url: str) -> str | None:
    """Polite HTTP GET — returns HTML text or None on error."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko,en;q=0.5",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status != 200:
                print(f"  HTTP {resp.status}", file=sys.stderr)
                return None
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        print(f"  HTTPError {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  fetch error: {e}", file=sys.stderr)
        return None


class _NamuParser(HTMLParser):
    """namuwiki HTML → (title, body_text, internal_links).

    naive HTML parser — strips tags, extracts text + /w/* hrefs.
    SSR 본격 본격 content 본격 page 본격 본격 본격 (★ 본격 본격 visible).
    """

    def __init__(self) -> None:
        super().__init__()
        self.title: str = ""
        self._in_title = False
        self._in_body = False
        self._depth_in_skip = 0  # nav/script/style/noscript 본격 skip
        self.text_parts: list[str] = []
        self.links: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "title":
            self._in_title = True
        elif tag in ("script", "style", "noscript", "header", "nav", "footer"):
            self._depth_in_skip += 1
        elif tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    if value.startswith("/w/"):
                        self.links.add(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style", "noscript", "header", "nav", "footer"):
            self._depth_in_skip = max(0, self._depth_in_skip - 1)

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._depth_in_skip == 0 and data.strip():
            self.text_parts.append(data)


def _parse_page(html: str) -> tuple[str, str, set[str]]:
    """HTML → (title, body_text, /w/ links set)."""
    parser = _NamuParser()
    try:
        parser.feed(html)
    except Exception as e:  # noqa: BLE001
        print(f"  parse error: {e}", file=sys.stderr)

    title = parser.title.replace(" - 나무위키", "").strip()
    body = "\n".join(p.strip() for p in parser.text_parts if p.strip())
    # 본격 본격 본격 본격 본격 본격 본격 본격
    body = re.sub(r"\n{3,}", "\n\n", body)
    return title, body, parser.links


def _resolve_link(link: str) -> str | None:
    """relative /w/* → absolute URL, filter unwanted namespaces."""
    if not link.startswith("/w/"):
        return None
    name = urllib.parse.unquote(link[3:])
    # strip query/fragment
    name = name.split("#", 1)[0].split("?", 1)[0]
    if not name:
        return None
    for pat in SKIP_NAME_PATTERNS:
        if pat.search(name):
            return None
    return ALLOWED_PREFIX + urllib.parse.quote(name)


def crawl(max_pages: int) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(START_URL, 0)]
    saved = 0
    skipped_existing = 0
    errors = 0

    print(f"start: {START_URL}")
    print(f"depth limit: {DEPTH_LIMIT}")
    print(f"max pages: {max_pages}")
    print(f"rate delay: {RATE_DELAY}s")

    while queue and saved < max_pages:
        url, depth = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        if depth > DEPTH_LIMIT:
            continue

        # Determine output path early (★ resume support)
        name = urllib.parse.unquote(url[len(ALLOWED_PREFIX):])
        slug = _safe_slug(name)
        out_path = OUT_DIR / f"{slug}.md"
        if out_path.exists():
            # Already saved — but still parse for outbound links if depth < limit
            skipped_existing += 1
            if depth < DEPTH_LIMIT:
                try:
                    existing_html = _fetch(url)
                    if existing_html:
                        _, _, links = _parse_page(existing_html)
                        for link in links:
                            target = _resolve_link(link)
                            if target and target not in visited:
                                queue.append((target, depth + 1))
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(RATE_DELAY)
            continue

        print(f"[depth {depth}, saved {saved}/{max_pages}] {url}")
        html = _fetch(url)
        if html is None:
            errors += 1
            time.sleep(RATE_DELAY)
            continue

        title, body, links = _parse_page(html)
        if not body or len(body) < 100:
            # 너무 짧은 page 본격 본격 skip (★ 본격 본격 본격 본격)
            print("  skipped (body too short)")
            time.sleep(RATE_DELAY)
            continue

        md_content = (
            f"# {title or name}\n\n"
            f"source: {url}\n"
            f"depth: {depth}\n\n"
            f"{body}\n"
        )
        out_path.write_text(md_content, encoding="utf-8")
        saved += 1
        print(f"  saved {out_path.name} ({len(md_content)} chars, {len(links)} links)")

        # Enqueue links if within depth
        if depth < DEPTH_LIMIT:
            for link in links:
                target = _resolve_link(link)
                if target and target not in visited:
                    queue.append((target, depth + 1))

        time.sleep(RATE_DELAY)

    print()
    print("=== summary ===")
    print(f"saved:           {saved}")
    print(f"skipped (exists):{skipped_existing}")
    print(f"errors:          {errors}")
    print(f"visited total:   {len(visited)}")
    print(f"queue remaining: {len(queue)}")
    print(f"output: {OUT_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--max-pages", type=int, default=200,
        help="max pages to save in this run (★ resume-safe)",
    )
    args = parser.parse_args()
    return crawl(args.max_pages)


if __name__ == "__main__":
    raise SystemExit(main())
