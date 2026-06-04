"""던전 픽셀 타일/스프라이트 생성기 (★ 게임 화면 ASCII 해소).

순수 stdlib(zlib/struct)로 16x16 RGBA PNG를 생성한다 — 외부 패키지/다운로드 0.
여기서 만드는 스프라이트는 원작(직접 디자인) CC0 자산이라 라이선스 모호성이 없다.
DungeonView가 TileType별로 이 타일을 격자 렌더해 문자(@/g/b) 화면을 픽셀화한다.

생성:
  python tools/gen_pixel_tiles.py
→ frontend/public/assets/pixel/{floor,wall,player,enemy,npc,item,stair,door}.png

타일 매핑은 에셋 무관 — 더 정교한 팩(Kenney CC0 등)으로 PNG만 교체 가능.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend/public/assets/pixel"
SIZE = 16

# 팔레트 — char → RGBA. ' '(공백) = 투명. 던전 톤(앰버 횃불 + 돌).
PALETTE: dict[str, tuple[int, int, int, int]] = {
    " ": (0, 0, 0, 0),
    # 돌 바닥/벽
    # ★ 수정동굴 청록 톤 (★ 본문 1층 — 배경 ui_gameplay_bg_crystal과 조화)
    "d": (26, 42, 46, 255),    # 바닥 베이스(어두운 청록 슬레이트)
    "D": (18, 32, 36, 255),    # 바닥 음영
    "f": (42, 64, 68, 255),    # 바닥 하이라이트 결(청록 광택)
    "v": (74, 160, 176, 255),  # 수정 글린트(시안 결정 반짝)
    "w": (40, 66, 74, 255),    # 벽 — 청록 광물 암석
    "W": (58, 92, 102, 255),   # 벽 상단 하이라이트(결정 면)
    "m": (16, 30, 34, 255),    # 벽 틈(어두운 청록)
    # 캐릭터
    "s": (224, 184, 144, 255),  # 살색
    "h": (74, 53, 32, 255),     # 머리/갈색
    "b": (106, 143, 208, 255),  # 본인 청색 튜닉
    "B": (74, 104, 160, 255),   # 청색 음영
    "x": (200, 200, 216, 255),  # 검/금속
    "g": (106, 154, 74, 255),   # 고블린 초록
    "G": (74, 116, 50, 255),    # 초록 음영
    "r": (220, 70, 70, 255),    # 적 눈/위험
    "a": (200, 160, 96, 255),   # NPC 앰버 로브
    "A": (160, 124, 64, 255),   # 앰버 음영
    # 아이템/지형
    "c": (102, 224, 255, 255),  # 시안 보석
    "C": (160, 240, 255, 255),  # 보석 하이라이트
    "k": (22, 38, 42, 255),     # 계단 어둠(청록)
    "K": (90, 130, 138, 255),   # 계단 돌(청록-회)
    "o": (138, 90, 48, 255),    # 문 나무
    "O": (170, 116, 64, 255),   # 나무 하이라이트
    "n": (90, 58, 30, 255),     # 나무 음영
    "i": (90, 84, 104, 255),    # 금속 손잡이/테
}

# ── 16x16 스프라이트 (16행 × 16열) ──────────────────────────────────────────

FLOOR = [
    "dddddddddddddddd",
    "dddddfvddddddddd",
    "ddDddddddddvfddd",
    "ddddddddDddddddd",
    "dddffdddddddddDd",
    "dddddddddvddddd"[:16],
    "dDddddddddffddddd"[:16],
    "ddddddddddddddDdd"[:16],
    "ddfvdddddddddddd",
    "dddddddDdddddddd",
    "ddddddddddddfvdd",
    "dDdddddffddddddd",
    "ddddddddddvdddDd"[:16],
    "ddffddddddDddddd",
    "dddddddddddddddd",
    "dddddddddddffdddd"[:16],
]

WALL = [
    "WWWWWWWWWWWWWWWW",
    "wwwwwwwwwwwvwwww",
    "wwwwwwwmwwwwwwww",
    "wwvwwwwmwwwwwwww",
    "mmmmmmmmmmmmmmmm",
    "wwwwWWWWwwwwwvww",
    "wwwwwwwwwwwwWWWw",
    "wwwmwwwwwwwwwwww",
    "wwwmwwwwvwwmwwww",
    "mmmmmmmmmmmmmmmm",
    "wwwwwwwwWWWWwwww",
    "WWWwwwwwwwwwwvww",
    "wwwwwwwmwwwwwwww",
    "wvwwwwwmwwwwwwww",
    "wwwwwwwmwwwwwwww",
    "wwwwwwwmwwwwwwww",
]

PLAYER = [
    "                ",
    "      hhhh      ",
    "     hhhhhh     ",
    "     hssssh     ",
    "     ssssss     ",
    "     srssrs     ",
    "      ssss    x ",
    "     bbbbbb  xx ",
    "    bBbbbbBb xx ",
    "    bBbbbbBb x  ",
    "    bbbbbbbb    ",
    "     bb  bb     ",
    "     BB  BB     ",
    "     hh  hh     ",
    "    hhh  hhh    ",
    "                ",
]

ENEMY = [
    "                ",
    "    g      g    ",
    "    gg    gg    ",
    "    gggggggg    ",
    "   gggggggggg   ",
    "   ggrggggrgg   ",
    "   gggggggggg   ",
    "   ggGggggGgg   ",
    "   gggGGGGggg   ",
    "    gggggggg    ",
    "    GgggggggG   "[:16],
    "    gg    gg    ",
    "    GG    GG    ",
    "    gg    gg    ",
    "   ggg    ggg   ",
    "                ",
]

NPC = [
    "                ",
    "      hhhh      ",
    "     hhhhhh     ",
    "     hssssh     ",
    "     ssssss     ",
    "      ssss      ",
    "     aaaaaa     ",
    "    aAaaaaAa    ",
    "    aaaaaaaa    ",
    "    aAaaaaAa    ",
    "    aaaaaaaa    ",
    "    aaaaaaaa    ",
    "    aA    Aa    ",
    "    aa    aa    ",
    "   aaa    aaa   ",
    "                ",
]

ITEM = [
    "                ",
    "                ",
    "       C        ",
    "      CcC       ",
    "     CccccC     ",
    "    CcccCccC    ",
    "   CcccccCccC   ",
    "   ccCcccccCc   "[:16],
    "    cccccccc    ",
    "     cccccc     ",
    "      cccc      ",
    "       cc       ",
    "        c       "[:16],
    "                ",
    "                ",
    "                ",
]

STAIR = [
    "                ",
    "                ",
    "  KKKKKKKKKKKK  ",
    "  KkkkkkkkkkkK  ",
    "  KKKKKKKKKKkK  "[:16],
    "  Kkkkkkkkk Kk  "[:16],
    "  KKKKKKKKKKkK  "[:16],
    "  Kkkkkkk KkkK  "[:16],
    "  KKKKKKKKKKkK  "[:16],
    "  Kkkkk KkkkkK  "[:16],
    "  KKKKKKKKKKkK  "[:16],
    "  Kkk KkkkkkkK  "[:16],
    "  KKKKKKKKKKKK  ",
    "  KkkkkkkkkkkK  ",
    "  KKKKKKKKKKKK  ",
    "                ",
]

DOOR = [
    "   iiiiiiiiii   ",
    "   iooooooooi   ",
    "   iononnonoi   ",
    "   iooooooooi   ",
    "   ionoonono i  "[:16],
    "   iooooooooi   ",
    "   ionoononoi   ",
    "   iooooiiooi   "[:16],
    "   ionooiiono   "[:16],
    "   ioooo  ooi   "[:16],
    "   ionoonono i  "[:16],
    "   iooooooooi   ",
    "   iononnonoi   ",
    "   iooooooooi   ",
    "   iiiiiiiiii   ",
    "                ",
]

SPRITES: dict[str, list[str]] = {
    "floor": FLOOR,
    "wall": WALL,
    "player": PLAYER,
    "enemy": ENEMY,
    "npc": NPC,
    "item": ITEM,
    "stair": STAIR,
    "door": DOOR,
}


def _normalize(rows: list[str]) -> list[str]:
    """각 행을 정확히 SIZE 폭으로 보정(부족분 공백, 초과분 절단) + SIZE 행."""
    out: list[str] = []
    for r in rows[:SIZE]:
        out.append((r + " " * SIZE)[:SIZE])
    while len(out) < SIZE:
        out.append(" " * SIZE)
    return out


def _png_bytes(rows: list[str]) -> bytes:
    """16x16 RGBA 픽셀맵 → PNG 바이트 (순수 stdlib)."""
    raw = bytearray()
    for r in _normalize(rows):
        raw.append(0)  # 각 스캔라인 filter type 0
        for ch in r:
            raw.extend(PALETTE.get(ch, PALETTE[" "]))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0)  # 8bit RGBA
    idat = zlib.compress(bytes(raw), 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in SPRITES.items():
        (OUT_DIR / f"{name}.png").write_bytes(_png_bytes(rows))
    print(f"생성 완료: {len(SPRITES)}개 타일 → {OUT_DIR}")


if __name__ == "__main__":
    main()
