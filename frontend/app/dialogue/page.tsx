"use client";

/**
 * Dialogue — Phase 7h implement (★ Phase 6 dialogue_screen.html → React).
 *
 * 본 page 본격:
 * - 좌 화자 (★ DialogueSpeaker)
 * - 중 대화 + 선택지 (★ DialogueContent + ChoiceList)
 * - 우 정보 (★ DialogueInfo)
 *
 * 본격 본질:
 * - state V2 본격 current_dialogue 본격 X — 본격 idle fallback (★ 7j 본격 API)
 */

import { useCallback } from "react";

import { GameLayout } from "@/components/GameLayout";
import { ChoiceList } from "@/components/dialogue/ChoiceList";
import type { DialogueChoice } from "@/components/dialogue/ChoiceList";
import { DialogueContent } from "@/components/dialogue/DialogueContent";
import { DialogueInfo } from "@/components/dialogue/DialogueInfo";
import type {
  Clue,
  DiscoveryItem,
} from "@/components/dialogue/DialogueInfo";
import { DialogueSpeaker } from "@/components/dialogue/DialogueSpeaker";
import { useGameState } from "@/lib/hooks/useGameState";

const MAX_HOURS = 168;

const SPEAKER_PORTRAITS: Record<string, string> = {
  message_stone: "/assets/worldfork/ui_dialogue_message_stone.png",
  "메시지 스톤": "/assets/worldfork/ui_dialogue_message_stone.png",
  other_party_male: "/assets/worldfork/ui_dialogue_other_male.png",
  other_party_female: "/assets/worldfork/ui_dialogue_other_female.png",
  ancient_stone: "/assets/worldfork/ui_dialogue_ancient_stone.png",
  비석: "/assets/worldfork/ui_dialogue_ancient_stone.png",
};

const DEFAULT_PORTRAIT = "/assets/worldfork/ui_dialogue_ancient_stone.png";

function getSpeakerPortrait(type: string | undefined | null): string {
  if (!type) return DEFAULT_PORTRAIT;
  return SPEAKER_PORTRAITS[type] ?? DEFAULT_PORTRAIT;
}

interface DialogueLike {
  speaker_type?: string;
  speaker_name?: string;
  relation_label?: string;
  communication_limit?: { current: number; max: number };
  signal_stability?: number;
  text?: string;
  narration?: string;
  line_speaker?: string;
  choices?: DialogueChoice[];
  discovery_items?: DiscoveryItem[];
  clues?: Clue[];
  mode_label?: string;
}

export default function DialoguePage() {
  const { data, loading, error } = useGameState();

  const handleChoose = useCallback((choiceId: string) => {
    // ★ Phase 7h: console.log only — POST API 본격 7j
    // eslint-disable-next-line no-console
    console.log("Dialogue choice:", choiceId);
  }, []);

  if (loading) {
    return (
      <GameLayout>
        <div className="screen dialogue-screen-bg">
          <div className="loading-center">불러오는 중...</div>
        </div>
      </GameLayout>
    );
  }

  if (error || !data) {
    return (
      <GameLayout>
        <div className="screen dialogue-screen-bg">
          <div className="error-center">
            상태 API 본격 X: {error?.message ?? "no data"}
          </div>
        </div>
      </GameLayout>
    );
  }

  const location = data.state.location;
  const world = data.state.world;
  const subArea = location.sub_area ?? "1층";
  const hoursRemaining = Math.max(0, MAX_HOURS - (world.hours_in_dungeon ?? 0));

  // ★ 본 commit: current_dialogue 본격 v2 API 본격 X — idle 본격 본격
  const dialogue = (
    data.state as { current_dialogue?: DialogueLike }
  ).current_dialogue;

  if (!dialogue) {
    return (
      <GameLayout>
        <div className="screen dialogue-screen-bg">
          <div className="dialogue-header-bar">
            <div className="header-context">{subArea}</div>
            <div className="header-mode">▣ 대화 본격</div>
          </div>
          <div className="dialogue-idle">
            <p>현재 대화 중이 아닙니다.</p>
            <p className="hint">
              메시지 스톤을 발견하거나 비석 공동에서 공물을 바치면 대화가 시작됩니다.
            </p>
            <p className="hint">
              (★ 본 commit skeleton — current_dialogue API 본격 7j)
            </p>
          </div>
        </div>
      </GameLayout>
    );
  }

  const speakerType = dialogue.speaker_type ?? "ancient_stone";
  const speakerName = dialogue.speaker_name ?? "미상";
  const headerMode =
    dialogue.mode_label ??
    (speakerType.includes("stone")
      ? "▣ 메시지 스톤 통신"
      : "▣ 대화");

  return (
    <GameLayout>
      <div className="screen dialogue-screen-bg">
        <div className="dialogue-header-bar">
          <div className="header-context">{subArea}</div>
          <div className="header-mode">{headerMode}</div>
        </div>

        <div className="dialogue-grid">
          <DialogueSpeaker
            speaker={{
              name: speakerName,
              type: speakerType,
              portraitSrc: getSpeakerPortrait(speakerType),
              relationLabel: dialogue.relation_label,
              communicationLimit: dialogue.communication_limit,
              signalStability: dialogue.signal_stability,
            }}
          />

          <div className="dialogue-center">
            <DialogueContent
              speakerLabel={dialogue.line_speaker ?? speakerName}
              text={dialogue.text ?? ""}
              narration={dialogue.narration}
            />
            <ChoiceList
              choices={dialogue.choices ?? []}
              onChoose={handleChoose}
            />
          </div>

          <DialogueInfo
            discoveryItems={dialogue.discovery_items ?? []}
            clues={dialogue.clues ?? []}
            hoursRemaining={hoursRemaining}
          />
        </div>
      </div>
    </GameLayout>
  );
}
