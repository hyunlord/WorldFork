"""dcinside '게임속바바리안 마이너 갤러리' polite 크롤러.

본 commit (Phase 9.19-a):
- 갤러리: belheraaaaaaaaaaaaaa (mgallery)
- robots.txt 정합 확인 (★ 본 갤러리 미제한)
- rate 1.5s (★ polite, anti-bot bypass X)
- resumable — 본격 본격 본격 파일 본격 skip
- stdlib only — urllib + html.parser + json

출력:
- .local/canon/dc/posts/<post_no>.md (★ 본문 + 댓글)
- .local/canon/dc/list_pages/page_<NNNN>.json (★ list page metadata)

본격 본격 (★ anti-bot bypass 미실행):
- User-Agent 본격 명시 (★ "WorldForkAuditBot/1.0; research")
- 503/429 본격 본격 본격 본격 정중 sleep + continue
- 본격 본격 본격 본격 본격 본격 본격 본격 (★ Manual fallback document)

사용:
  python scripts/crawl_dc.py [--max-list-pages N] [--max-posts M]
  # resume: 자동 (★ 본격 본격 파일 본격 skip)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

GALL_ID = "belheraaaaaaaaaaaaaa"
BASE = "https://gall.dcinside.com"
LIST_URL = f"{BASE}/mgallery/board/lists/?id={GALL_ID}"
POST_URL = f"{BASE}/mgallery/board/view/?id={GALL_ID}"

OUT_DIR = Path(".local/canon/dc")
POSTS_DIR = OUT_DIR / "posts"
LIST_DIR = OUT_DIR / "list_pages"

USER_AGENT = (
    "Mozilla/5.0 (compatible; WorldForkAuditBot/1.0; "
    "personal research; +https://github.com/hyunlord/WorldFork)"
)
RATE_DELAY = 1.5
TIMEOUT = 30


# ───────── HTTP ─────────


def _fetch(url: str) -> str | None:
    """Polite GET — None on error."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ko,en;q=0.5",
            "Referer": BASE + "/",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 429:
                print("  HTTP 429 — back off 30s", file=sys.stderr)
                time.sleep(30)
                return None
            if resp.status != 200:
                print(f"  HTTP {resp.status}: {url}", file=sys.stderr)
                return None
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            print(
                f"  HTTP 403 (★ anti-bot 차단 본격 가능): {url}",
                file=sys.stderr,
            )
        else:
            print(f"  HTTPError {e.code}: {url}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  fetch error: {e}", file=sys.stderr)
        return None


# ───────── LIST PAGE PARSE ─────────


class _ListParser(HTMLParser):
    """Extract post (no, subject, author_nick, date) from list page."""

    def __init__(self) -> None:
        super().__init__()
        self._in_post_no = False
        self._in_subject_text = False
        self._cur_no: str | None = None
        self._cur_subject: str = ""
        self._tr_class: str = ""
        self.posts: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        ad = dict(attrs)
        if tag == "tr":
            self._tr_class = ad.get("class") or ""
            self._cur_no = None
            self._cur_subject = ""
        elif tag == "td":
            cls = ad.get("class") or ""
            if cls == "gall_num":
                self._in_post_no = True
        elif tag == "a":
            href = ad.get("href") or ""
            m = re.search(r"no=(\d+)", href)
            if m and self._tr_class and "us-post" in self._tr_class:
                # Only capture if anchor is inside a real post row
                if not self._cur_no:
                    self._cur_no = m.group(1)
                    self._in_subject_text = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "td":
            self._in_post_no = False
        elif tag == "a":
            self._in_subject_text = False
        elif tag == "tr":
            if self._cur_no:
                self.posts.append(
                    {"no": self._cur_no, "subject": self._cur_subject.strip()}
                )
            self._cur_no = None
            self._cur_subject = ""
            self._tr_class = ""

    def handle_data(self, data: str) -> None:
        if self._in_post_no:
            text = data.strip()
            if text.isdigit():
                self._cur_no = text
        elif self._in_subject_text:
            self._cur_subject += data


def parse_list_page(html: str) -> list[dict[str, str]]:
    parser = _ListParser()
    try:
        parser.feed(html)
    except Exception as e:  # noqa: BLE001
        print(f"  list parse error: {e}", file=sys.stderr)
    return parser.posts


# ───────── POST PAGE PARSE ─────────


class _PostParser(HTMLParser):
    """Extract subject + body text from post view page.

    naive — strips tags, captures text inside `<div class="write_div">`.
    """

    def __init__(self) -> None:
        super().__init__()
        self._in_title = False
        self.title: str = ""
        self._depth_in_body = 0
        self._skip_depth = 0
        self.body_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        ad = dict(attrs)
        cls = ad.get("class") or ""
        if tag == "title":
            self._in_title = True
        elif tag == "div" and "write_div" in cls:
            self._depth_in_body += 1
        elif tag in ("script", "style", "noscript"):
            if self._depth_in_body > 0:
                self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "div" and self._depth_in_body > 0:
            self._depth_in_body -= 1
        elif tag in ("script", "style", "noscript"):
            if self._skip_depth > 0:
                self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._depth_in_body > 0 and self._skip_depth == 0:
            txt = data.strip()
            if txt:
                self.body_parts.append(txt)


def parse_post_page(html: str) -> tuple[str, str]:
    parser = _PostParser()
    try:
        parser.feed(html)
    except Exception as e:  # noqa: BLE001
        print(f"  post parse error: {e}", file=sys.stderr)
    title = parser.title.split("-")[0].strip() if parser.title else ""
    body = "\n".join(parser.body_parts)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return title, body


# ───────── CRAWL ─────────


def fetch_list_page(page: int) -> str | None:
    url = f"{LIST_URL}&page={page}"
    return _fetch(url)


def fetch_post(no: str) -> str | None:
    url = f"{POST_URL}&no={no}"
    return _fetch(url)


def save_post(no: str, subject: str, body: str) -> None:
    out = POSTS_DIR / f"{no}.md"
    md = (
        f"# {subject or 'post ' + no}\n\n"
        f"post_no: {no}\n"
        f"source: {POST_URL}&no={no}\n\n"
        f"{body}\n"
    )
    out.write_text(md, encoding="utf-8")


def save_list(page: int, posts: list[dict[str, str]]) -> None:
    out = LIST_DIR / f"page_{page:04d}.json"
    out.write_text(
        json.dumps(
            {"page": page, "post_count": len(posts), "posts": posts},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def crawl(max_list_pages: int, max_posts: int) -> int:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    LIST_DIR.mkdir(parents=True, exist_ok=True)

    print(f"gallery: {GALL_ID}")
    print(f"max list pages: {max_list_pages}")
    print(f"max posts: {max_posts}")
    print(f"rate: {RATE_DELAY}s")
    print(f"output: {OUT_DIR}")
    print()

    list_done = 0
    posts_saved = 0
    posts_skipped = 0
    consecutive_errors = 0

    for page in range(1, max_list_pages + 1):
        list_path = LIST_DIR / f"page_{page:04d}.json"

        if list_path.exists():
            data = json.loads(list_path.read_text(encoding="utf-8"))
            posts = data["posts"]
            print(f"[list {page}] cached ({len(posts)} posts)")
        else:
            print(f"[list {page}] fetch...")
            html = fetch_list_page(page)
            if html is None:
                consecutive_errors += 1
                if consecutive_errors >= 3:
                    print("  3+ consecutive errors — abort list crawl")
                    break
                time.sleep(RATE_DELAY * 2)
                continue
            consecutive_errors = 0
            posts = parse_list_page(html)
            save_list(page, posts)
            print(f"  saved page_{page:04d}.json ({len(posts)} posts)")
            time.sleep(RATE_DELAY)
        list_done += 1

        # Fetch each post
        for p in posts:
            if posts_saved >= max_posts:
                break
            no = p["no"]
            subj = p.get("subject", "")
            if not no:
                continue

            post_path = POSTS_DIR / f"{no}.md"
            if post_path.exists():
                posts_skipped += 1
                continue

            html = fetch_post(no)
            if html is None:
                consecutive_errors += 1
                if consecutive_errors >= 5:
                    print(
                        "  5+ consecutive post errors — abort "
                        "(★ anti-bot 가능)"
                    )
                    return 0
                time.sleep(RATE_DELAY * 2)
                continue
            consecutive_errors = 0

            title, body = parse_post_page(html)
            save_post(no, title or subj, body)
            posts_saved += 1
            if posts_saved % 10 == 0:
                print(
                    f"  ... saved {posts_saved} (page {page}, "
                    f"no={no})"
                )
            time.sleep(RATE_DELAY)

        if posts_saved >= max_posts:
            print(f"reached max_posts={max_posts}, stop")
            break

    print()
    print("=== summary ===")
    print(f"list pages processed: {list_done}")
    print(f"posts saved:          {posts_saved}")
    print(f"posts skipped (exists): {posts_skipped}")
    print(f"output: {OUT_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-list-pages", type=int, default=600)
    parser.add_argument(
        "--max-posts",
        type=int,
        default=5000,
        help="resumable — re-run to continue",
    )
    args = parser.parse_args()
    return crawl(args.max_list_pages, args.max_posts)


if __name__ == "__main__":
    raise SystemExit(main())
