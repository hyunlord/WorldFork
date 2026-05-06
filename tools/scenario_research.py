"""시나리오 자료 크롤링 도구 — httpx + playwright hybrid.

URL 진짜 fetch + 본문 추출 → docs/scenarios/<name>/ 저장.

전략:
- httpx 우선 (★ 동기 client, 빠름)
- 403/503/JS-render 시 playwright fallback (★ Cloudflare 등)
- 추출: playwright page API 또는 stdlib re

사용:
  python tools/scenario_research.py \
    --name barbarian \
    --urls "https://namu.wiki/...,https://gall.dcinside.com/..."

출력:
  docs/scenarios/barbarian/
    namu_<hash>.html (raw)
    namu_<hash>.txt  (extracted JSON)
    dc_<hash>.html
    dc_<hash>.txt
    summary.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    # ★ 옵션 C: 'br' 제거 — httpx 기본이 brotli 미지원 (binary 깨짐 회피)
    "Accept-Encoding": "gzip, deflate",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


def _url_domain(url: str) -> str:
    return urlparse(url).netloc


def _domain_prefix(url: str) -> str:
    domain = _url_domain(url)
    if "namu" in domain:
        return "namu"
    if "dcinside" in domain:
        return "dc"
    return re.sub(r"[^a-z0-9]", "_", domain.lower())[:20]


# stdlib 단순 추출 (★ httpx fetch 시)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.DOTALL | re.IGNORECASE)


def strip_html(html: str) -> str:
    """stdlib만으로 본문 추출 (★ 단순)."""
    text = SCRIPT_RE.sub("", html)
    text = STYLE_RE.sub("", text)
    text = TAG_RE.sub("\n", text)
    text = (
        text.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
    )
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_title(html: str) -> str:
    m = TITLE_RE.search(html)
    return m.group(1).strip() if m else ""


def fetch_with_httpx(
    url: str, timeout: float = 30.0
) -> tuple[int, str | None, str | None]:
    """httpx로 진짜 fetch.

    Returns: (status_code, html, error_msg)
    """
    try:
        with httpx.Client(
            headers=HEADERS, follow_redirects=True, timeout=timeout
        ) as client:
            resp = client.get(url)
            return resp.status_code, resp.text, None
    except httpx.HTTPError as e:
        return 0, None, f"httpx 실패: {e}"


def fetch_with_playwright(
    url: str, timeout_ms: int = 30000
) -> tuple[int, dict[str, Any] | None, str | None]:
    """playwright headless로 진짜 fetch + 추출.

    page API로 직접 본문 추출 (★ bs4 X).

    Returns: (status, payload, error)
      payload = {
        "html": str,
        "title": str,
        "body_text": str,
        "headings": list[dict],
        "main_blocks": dict,
      }
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return 0, None, "playwright import 실패"

    domain = _url_domain(url)
    payload: dict[str, Any] = {
        "html": "",
        "title": "",
        "body_text": "",
        "headings": [],
        "main_blocks": {},
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=HEADERS["User-Agent"],
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            response = page.goto(
                url, timeout=timeout_ms, wait_until="domcontentloaded"
            )

            # Cloudflare challenge + 본문 로드 대기
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            time.sleep(3.0)

            payload["html"] = page.content()
            payload["title"] = page.title()
            payload["body_text"] = page.inner_text("body")

            for level in range(1, 7):
                try:
                    headings = page.locator(f"h{level}").all_inner_texts()
                    for h in headings:
                        h_text = h.strip()
                        if h_text:
                            payload["headings"].append(
                                {"level": level, "text": h_text}
                            )
                except Exception:
                    continue

            if "namu" in domain:
                for sel in (".wiki-content", "#content", "article"):
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0:
                            text = loc.inner_text()
                            if len(text) > 100:
                                payload["main_blocks"][sel] = text
                                break
                    except Exception:
                        continue
            elif "dcinside" in domain:
                for sel in (
                    ".write_div",
                    ".gallview_contents",
                    ".view_content_wrap",
                ):
                    try:
                        loc = page.locator(sel).first
                        if loc.count() > 0:
                            payload["main_blocks"][sel] = loc.inner_text()
                            break
                    except Exception:
                        continue
                try:
                    comments = page.locator(
                        ".cmt_box, .ub-content"
                    ).all_inner_texts()
                    if comments:
                        payload["main_blocks"]["comments"] = comments[:50]
                except Exception:
                    pass

            status = response.status if response else 0
            browser.close()
            return status, payload, None
    except Exception as e:
        return 0, None, f"playwright 실패: {e}"


def process_url(url: str, output_dir: Path) -> dict[str, Any]:
    """URL 진짜 fetch + 추출 + 저장."""
    print(f"\n{'=' * 70}")
    print(f"URL: {url}")
    print(f"{'=' * 70}")

    prefix = _domain_prefix(url)
    base_name = f"{prefix}_{_url_hash(url)}"

    report: dict[str, Any] = {
        "url": url,
        "domain": _url_domain(url),
        "fetch_method": None,
        "status_code": 0,
        "html_path": None,
        "text_path": None,
        "summary": None,
        "error": None,
    }

    extracted: dict[str, Any] = {}
    html_to_save: str = ""
    domain = _url_domain(url)

    # ★ 옵션 C: 나무위키는 playwright 직진 (★ JS 렌더링 + Cloudflare 우회)
    if "namu" in domain:
        print("[1/3] playwright direct (namu domain)...")
        status, payload, err = fetch_with_playwright(url)
        report["status_code"] = status
        if status == 200 and payload:
            print("  ✅ playwright OK")
            print(f"     title: {payload['title'][:80]}")
            print(f"     body_text: {len(payload['body_text']):,} chars")
            print(f"     headings: {len(payload['headings'])}")
            report["fetch_method"] = "playwright"
            extracted = payload
            html_to_save = payload["html"]
        else:
            print(f"  ❌ playwright fail: {err}")
            report["error"] = f"playwright: {err}"
            return report
    else:
        # 디시 등 — httpx 우선
        print("[1/3] httpx fetch...")
        status, html, err = fetch_with_httpx(url)
        report["status_code"] = status

        if status == 200 and html:
            print(f"  ✅ httpx OK ({len(html):,} chars)")
            report["fetch_method"] = "httpx"
            extracted = {
                "title": extract_title(html),
                "body_text": strip_html(html),
                "headings": [],
                "main_blocks": {},
            }
            html_to_save = html
        elif status in (403, 503) or err:
            print(f"  ⚠️ httpx {status} ({err}) — playwright fallback")
            print("[2/3] playwright fallback...")
            status, payload, err = fetch_with_playwright(url)
            report["status_code"] = status
            if status == 200 and payload:
                print("  ✅ playwright OK")
                print(f"     title: {payload['title'][:80]}")
                print(f"     body_text: {len(payload['body_text']):,} chars")
                print(f"     headings: {len(payload['headings'])}")
                report["fetch_method"] = "playwright"
                extracted = payload
                html_to_save = payload["html"]
            else:
                print(f"  ❌ playwright fail: {err}")
                report["error"] = f"playwright: {err}"
                return report
        else:
            print(f"  ❌ httpx fail: status={status} err={err}")
            report["error"] = f"httpx: status={status} err={err}"
            return report

    html_path = output_dir / f"{base_name}.html"
    html_path.write_text(html_to_save, encoding="utf-8")
    report["html_path"] = str(html_path)

    text_path = output_dir / f"{base_name}.txt"
    text_path.write_text(
        json.dumps(extracted, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report["text_path"] = str(text_path)
    report["summary"] = {
        "title": extracted.get("title", ""),
        "body_length": len(extracted.get("body_text", "")),
        "headings_count": len(extracted.get("headings", [])),
        "main_blocks_keys": list(extracted.get("main_blocks", {}).keys()),
    }

    print(f"  💾 raw: {html_path}")
    print(f"  💾 extracted: {text_path}")
    print(f"  📊 body: {report['summary']['body_length']:,} chars")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="시나리오 이름")
    parser.add_argument("--urls", required=True, help="콤마 구분 URL list")
    parser.add_argument(
        "--output-dir", default="docs/scenarios", help="저장 디렉토리"
    )
    args = parser.parse_args()

    urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    output_dir = Path(args.output_dir) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n시나리오: {args.name}")
    print(f"URLs: {len(urls)}건")
    print(f"Output: {output_dir}\n")

    reports: list[dict[str, Any]] = []
    for url in urls:
        try:
            r = process_url(url, output_dir)
        except Exception as e:
            r = {"url": url, "error": f"unexpected: {e}"}
        reports.append(r)
        time.sleep(2.0)

    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {"scenario": args.name, "reports": reports},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n{'=' * 70}")
    print(f"Summary: {summary_path}")
    print(f"{'=' * 70}\n")

    success = sum(1 for r in reports if r.get("error") is None)
    print(f"✅ {success}/{len(reports)} 성공")
    for r in reports:
        if r.get("error"):
            print(f"  ❌ {r['url']}: {r['error']}")
        else:
            method = r.get("fetch_method", "?")
            body_len = (r.get("summary") or {}).get("body_length", 0)
            print(f"  ✅ {r['url']}: {method}, body {body_len:,} chars")

    return 0 if success == len(reports) else 1


if __name__ == "__main__":
    sys.exit(main())
