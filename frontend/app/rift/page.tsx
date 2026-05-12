"use client";

/**
 * Rift Entry — Phase 7f implement (★ Phase 6 rift_entry.html → React).
 *
 * 본 page 본격:
 * - 4 균열 본격 카드 (★ floor1_rifts.py 정합):
 *   bloody_castle / glacier_cave / green_mine / iron_tomb
 * - world.active_rifts (list[str] rift_id) 본격 binding
 * - location.rift_id 본격 current 본격
 * - OFFER_TO_STONE 본격 panel (★ 비석 공동 위치 + 정수)
 */

import { useCallback } from "react";

import { GameLayout } from "@/components/GameLayout";
import { ActivateRiftPanel } from "@/components/rift/ActivateRiftPanel";
import { RiftCard } from "@/components/rift/RiftCard";
import { RiftStatus } from "@/components/rift/RiftStatus";
import { useGameState } from "@/lib/hooks/useGameState";

interface RiftTemplate {
  riftId: string;
  name: string;
  imageSrc: string;
  grade: number;
  rewardColor: string;
  description: string;
  bossName?: string;
}

// ★ 본문 정합 (★ service/game/floors/floor1_rifts.py):
const RIFT_TEMPLATES: ReadonlyArray<RiftTemplate> = [
  {
    riftId: "bloody_castle",
    name: "핏빛성채",
    imageSrc: "/assets/worldfork/ui_rift_bloody_castle.png",
    grade: 5,
    rewardColor: "빨강",
    description:
      "핏빛 성채 내부. 시체골렘 일반 + 변종 뱀파이어 수호자 (★ 33화).",
    bossName: "뱀파이어 공작 캠브로미어",
  },
  {
    riftId: "glacier_cave",
    name: "빙하굴",
    imageSrc: "/assets/worldfork/ui_rift_glacier_cave.png",
    grade: 7,
    rewardColor: "파랑",
    description:
      "얼어붙은 설산 + 호수 30분 도보 → 얼음 동굴. 7등급 예티 문지기.",
  },
  {
    riftId: "green_mine",
    name: "녹색탄광",
    imageSrc: "/assets/worldfork/ui_rift_green_mine.png",
    grade: 8,
    rewardColor: "초록",
    description:
      "갱도 + 철로 + 나무 폐자재. 천장 무너진 곳 시작. 고블린 광부 8등급 등장.",
  },
  {
    riftId: "iron_tomb",
    name: "강철의 묘",
    imageSrc: "/assets/worldfork/ui_rift_iron_tomb.png",
    grade: 8,
    rewardColor: "노랑",
    description:
      "강철 갑주 묘 영역. 1층 균열 4종 중 하나 (★ 456-457화).",
  },
];

interface CharLite {
  essences?: unknown[];
}

export default function RiftPage() {
  const { data, loading, error } = useGameState();

  const handleEnter = useCallback((riftId: string) => {
    // eslint-disable-next-line no-console
    console.log("ENTER_RIFT:", riftId);
  }, []);

  const handleActivate = useCallback(() => {
    // eslint-disable-next-line no-console
    console.log("OFFER_TO_STONE");
  }, []);

  if (loading) {
    return (
      <GameLayout>
        <div className="screen rift-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen rift-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const world = data.state.world;
  const location = data.state.location;
  const characters = data.state.characters;

  const activeRifts = world.active_rifts;
  const activeIds = new Set(activeRifts);

  const currentRiftId = location.rift_id ?? null;
  const inRift = Boolean(currentRiftId);
  const currentRiftTemplate = currentRiftId
    ? RIFT_TEMPLATES.find((r) => r.riftId === currentRiftId)
    : null;
  const currentRiftName = currentRiftTemplate?.name ?? currentRiftId;

  // 비석 공동 위치 본격
  const subArea = location.sub_area ?? "";
  const inStoneChamber = subArea === "비석 공동";

  // 정수 합산 본격 (★ characters[name].essences)
  const totalEssences = Object.values(characters).reduce<number>(
    (sum, c) => {
      const charLite = c as unknown as CharLite;
      const list = charLite.essences;
      return sum + (Array.isArray(list) ? list.length : 0);
    },
    0
  );

  return (
    <GameLayout>
      <div className="screen rift-screen-bg">
        <div className="rift-page-header">
          <h2 className="rift-page-title">균열 진입</h2>
          <RiftStatus
            activeRiftCount={activeRifts.length}
            totalRiftCount={RIFT_TEMPLATES.length}
            inRift={inRift}
            currentRiftName={currentRiftName}
          />
        </div>

        <div className="rift-grid-4">
          {RIFT_TEMPLATES.map((rift) => (
            <RiftCard
              key={rift.riftId}
              riftId={rift.riftId}
              name={rift.name}
              imageSrc={rift.imageSrc}
              grade={rift.grade}
              rewardColor={rift.rewardColor}
              description={rift.description}
              active={activeIds.has(rift.riftId)}
              current={rift.riftId === currentRiftId}
              bossName={rift.bossName}
              onEnter={handleEnter}
            />
          ))}
        </div>

        <div className="rift-actions">
          <ActivateRiftPanel
            inStoneChamber={inStoneChamber}
            essenceCount={totalEssences}
            onActivate={handleActivate}
          />
        </div>
      </div>
    </GameLayout>
  );
}
