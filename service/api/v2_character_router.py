"""POST /api/v2/character/create — 캐릭터 설정 + 세션 생성 (Phase E-2)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from service.api.schemas.character import CharacterConfigRequest, CharacterConfigResponse
from service.canon.races import get_race_config, race_from_string
from service.canon.scenario import (
    SCENARIO_CONFIGS,
    build_starting_narrative,
    resolve_race_for_scenario,
    scenario_from_string,
)
from service.sim.session_manager import get_session_manager

router = APIRouter(prefix="/api/v2/character", tags=["tier2-character"])


@router.post("/create", response_model=CharacterConfigResponse)
async def character_create(req: CharacterConfigRequest) -> CharacterConfigResponse:
    mode = scenario_from_string(req.scenario_mode)
    if mode is None:
        raise HTTPException(status_code=400, detail=f"unknown scenario_mode: {req.scenario_mode}")

    user_race = None
    if req.race:
        user_race = race_from_string(req.race)
        if user_race is None:
            raise HTTPException(status_code=400, detail=f"unknown race: {req.race}")

    resolved_race = resolve_race_for_scenario(mode, user_race)
    race_cfg = get_race_config(resolved_race)
    scenario_cfg = SCENARIO_CONFIGS[mode]

    # ★ 무기는 성인식(weapon_choice 단계)에서 게임 내 선택 — 생성 시 방패 선점 제거.
    #   선점 시 시작 narrative '방패 골랐다' + 장착 vs weapon_choice 추천 '무기 선택'이
    #   모순(manual play 버그2). req.weapon만 존중하고, 미지정이면 무기 미장착 상태로
    #   시작해 성인식에서 첫 선택(방패는 inventory에 캐논대로 잔존 — ep_0005).
    use_weapon: str | None = req.weapon

    mgr = get_session_manager()
    state = await mgr.create_session(
        race=resolved_race,
        scenario_mode=mode,
        inventory=list(req.inventory) if req.inventory else None,
        location=req.location,
        weapon=use_weapon,
    )

    narrative = build_starting_narrative(mode, resolved_race, use_weapon)
    # ★ 시작 장착 무기 (★ NEW_EXPLORER는 종족 기본 inventory 첫 항목)
    starting_weapon = use_weapon or (state.inventory[0] if state.inventory else "")

    return CharacterConfigResponse(
        session_id=state.session_id,
        scenario_mode=mode.value,
        race=resolved_race.value,
        starting_location=state.location,
        starting_floor=scenario_cfg.starting_floor,
        hp=state.current_hp,
        max_hp=state.max_hp,
        soul_power=state.soul_power,
        max_essences=state.max_essences,
        race_traits=list(race_cfg.traits),
        scenario_description=scenario_cfg.description,
        starting_narrative=narrative,
        starting_weapon=starting_weapon,
    )
