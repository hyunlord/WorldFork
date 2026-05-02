# W2 D5 본인 풀 플레이 가이드 (★ 본인 인사이트 #14 적용)

> 작성: 2026-05-02 (W2 D4.5)
> 실행: 다음 세션 (★ 깨끗한 상태)
> 시간: 2-3시간

---

## 0. 의미

W2 D5는 **이틀 동안 만든 인프라의 진짜 검증** 시점.

```
본인이 처음으로 진짜 사용자가 됨:
  - 입력: "novice_dungeon_run에서 주인공으로 살아보고 싶어"
  - Pipeline 8단계 모두 작동
  - 9B Q3 + Plan = 진짜 LLM 호출
  - 30턴 게임 진행
  - ★ 본인이 fun rating / findings 평가

이게 자료 #14 정신:
  "게임 성숙 후 본인 검토"
  → 본인 깨끗한 상태 + 게임 인프라 성숙
  → 진짜 검증 가능
```

---

## 1. 사전 준비 (★ 다음 세션 시작 시)

### 1-1. 환경 체크

```bash
cd /home/hyunlord/github/WorldFork
source .venv/bin/activate

# 추론 서버 3대
curl -s http://localhost:8081/health
curl -s http://localhost:8082/health
curl -s http://localhost:8083/health

# Last commit
git log --oneline | head -3

# 메모리
free -h | head -3
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
```

### 1-2. ★ 본인 컨디션 자기 평가

```
이건 ★ 가장 중요한 사전 단계.

Q1: 충분히 쉬었나?
  - 누적 28-34시간 작업 후
  - 적어도 8시간 이상 휴식
  - 음식 / 수분 OK

Q2: 집중 가능한가?
  - 30턴 게임 = ~30분 집중
  - 평가 = 추가 30분 집중
  - 분석 + commit = 30분

Q3: 평가 정확도 자신?
  - 피로 상태 = fun rating 부정확
  - 깨끗한 상태에서만 의미 있음

★ 답이 모두 Yes면 진행.
★ 하나라도 No면 다음 세션 추가 휴식.
```

---

## 2. W2 D5 작업 (Phase 4개, 2-3시간)

### Phase 1: Stage 4 + 8 간소 (~30분)

자료 8단계 중 미구현 2단계 가벼운 마무리:

```
Stage 4 (Plan Review):
  - 사용자가 Plan 보고 Yes/No (단순)
  - service/pipeline/plan_review.py
  - approve_plan / reject_plan / request_modification 함수만
  - LLM X (단순 yes/no UX)

Stage 8 (Complete / Save):
  - 게임 종료 시 GameState 저장
  - service/pipeline/complete.py
  - save_to_json (단순)
  - W3에서 SQL로 확장 (Tier 2+)

Tests +5 (각 Stage 작은 테스트)
```

### Phase 2: ★ 본인 직접 풀 플레이 (~1.5시간)

★ **이게 W2 D5의 본질**.

#### 2-1. 플레이 스크립트

`tools/play_w2_d5.py` 작성 후 본인이 직접 실행:

```
흐름:
  1. 본인 입력 → Interview Agent
  2. Plan 자동 생성 (Mock 또는 Real)
  3. Plan Verify
  4. ★ Plan Review (본인 yes/no)
  5. Agent Selection (9B Q3)
  6. Game Loop 30턴 (★ 진짜 LLM 호출)
  7. ★ 본인 fun rating + findings
  8. 결과 저장
```

#### 2-2. 플레이 시나리오

```
1단계: 작품명 입력
  본인 입력: "novice_dungeon_run"

  ★ 옵션:
    (a) Mock Planning (★ 안전, 즉시 Plan)
    (b) Real LLM Planning (★ 진짜 검증, but 시간/비용)

  추천: (a) Mock — 인프라 검증 우선
        (b)는 W3 도그푸딩에서

2단계: Plan 확인
  - 화면에 Plan 출력 (work_name, characters, world, opening_scene)
  - ★ 본인이 "OK" 또는 "수정 요청"
  - 첫 번째니까 그냥 OK 권장

3단계: 게임 시작
  - opening_scene 출력
  - initial_choices 표시
  - 본인이 첫 액션 입력

4단계: Game Loop 30턴
  - 본인 액션 → GM 응답 → 본인 액션 → ...
  - 30턴 또는 본인이 abandon
  - 매 턴 turn_n / cost_usd 표시
  - ★ 9B Q3 진짜 호출

5단계: 평가
  - Fun rating (1-5)
  - 발견한 이슈 (비어있어도 OK)
  - "다시 플레이?" yes/no
```

#### 2-3. ★ 본인이 평가할 것

```
Fun rating 1-5 (★ 정직하게):
  1: 답답함 / 흥미 잃음 (W1 D3 첫 세션 수준)
  2: 약간 흥미 (W1 D4 BEFORE 수준)
  3: 그럭저럭 (W1 D6 평균 수준)
  4: 재밌음 (W1 D6 roleplayer 수준)
  5: 매우 재밌음 (★ 첫 fun=5 시점!)

발견 이슈 카테고리:
  - korean_quality (verbose / 공문서체 / 한영 혼용)
  - encoding (한자 깨짐 / mojibake)
  - ai_breakout (AI 누설 / IP 누설)
  - world_consistency (세계관 위반)
  - ux (선택지 / 페이싱 / 명확성)
  - persona_consistency (캐릭터 일관성)
  - general (기타)

★ 솔직한 평가가 진짜 가치:
  - "재밌었음" only 보고 X
  - 세부 이슈 모두 기록
  - 자료 #14 정신 적용
```

### Phase 3: 결과 분석 (~45분)

```
1. play_w2_d5_result.json 저장:
   - work_name, plan, full game log
   - turn별 user_action / gm_response
   - 본인 fun_rating / findings
   - cost / latency

2. ★ 발견 이슈 → seed_converter
   - 자동 시드 생성 (★ W2 D3 인프라 활용)
   - evals/auto_added/에 추가
   - 한도 적용

3. ★ Tier 1 졸업 #4 입증 보고:
   "본인이 작품명 → 플랜 → 게임 30턴 풀 플레이"
   → Tier 1 졸업 조건 #4 ✅ 충족

4. W3 도그푸딩 준비:
   - 발견 이슈 정리
   - 시스템 보완 (필요 시)
   - 친구 베타 시나리오
```

### Phase 4: commit + push (~30분)

```bash
# 보고서 작성
docs/TIER_1_W2_D5_REPORT.md
  - 본인 첫 플레이 데이터
  - Fun rating + Findings
  - W2 D5 핵심 발견
  - Tier 1 졸업 #4 ✅

# 검증 (가벼운)
ruff check service/ tools/ tests/

# commit
git commit -m "feat(tier-1-w2): D5 — 본인 첫 풀 플레이 (★ 인사이트 #14 적용)

★ Tier 1 졸업 #4 (작품명 → 플랜 → 게임) ★ 본인 입증.
..."

git push origin main
```

---

## 3. 안전한 종료 정책

```
★ 만약 W2 D5 진행 중 문제 발생:

1. 게임이 너무 오래 걸리면 (30턴 1시간 초과):
   - 본인이 abandon 권한 (★ 자유)
   - 부분 결과도 가치 (★ findings)
   - 강제 30턴 X

2. LLM 응답이 이상하면:
   - Mechanical 룰이 잡으면 retry
   - 모두 실패 시 fallback (★ 자료 Stage 7)
   - 본인이 게임 종료 권한

3. 인코딩 / 깨진 응답:
   - encoding_rules가 자동 검출
   - finding으로 기록
   - W3에서 보완

4. 본인 컨디션 갑자기 나빠지면:
   - 즉시 종료 (★ 자유)
   - 부분 데이터도 commit
   - 다음 세션에 보완
```

---

## 4. 평가 기준 (참고용)

```
Fun rating 1-5:
  1: 답답함 / 흥미 잃음
  2: 약간 흥미
  3: 그럭저럭 (★ Tier 1 충분)
  4: 재밌음
  5: 매우 재밌음

Tier 1 W2 D5 목표:
  - Fun rating 3+ — Tier 1 충분
  - 30턴 완주 (★ 시도)
  - 발견 이슈 정리 (3-5개 정도)

★ 너무 높은 기준 X:
  - W2 D5는 첫 본인 플레이
  - Tier 1 인프라 검증이 목적
  - 본인 평가는 정직하게
  - W3 도그푸딩 + Tier 2+ 콘텐츠로 개선
```

---

## 5. 발견 정리 템플릿

```
W2 D5 본인 발견 보고:

작품: novice_dungeon_run
입력: "novice_dungeon_run에서 주인공으로 살아보고 싶어"

Plan 평가:
  - 캐릭터: <OK / 어색>
  - World: <OK / 어색>
  - Opening: <OK / 어색>

게임 진행:
  - 완주: <Yes / No (turn N)>
  - Fun rating: <X>/5
  - 비용: $<Y>

발견 이슈 (★ 정직하게):
  1. <카테고리>: <description>
     - turn: N
     - severity: critical/major/minor
  2. ...
  3. ...

Tier 1 W3 보완 우선순위:
  - <발견 1>
  - <발견 2>

★ 한 줄 요약:
"<본인 한 마디>"
```

---

## 6. ★ 본인 인사이트 #15 가능성

W2 D5 본인 첫 플레이는 **새 인사이트의 보고**일 가능성 큼.

```
이전 인사이트들이 자료 검증 / 보완 사례였다면,
#15는 ★ 실제 사용자 입장 인사이트일 수 있음:

예시 (가능성):
  - "30턴은 너무 길다 / 짧다"
  - "선택지 너무 많다 / 적다"
  - "옵션 A vs B Mock vs Real"
  - "Plan Review가 너무 복잡 / 단순"
  - 또는 본인만 발견할 다른 것

★ 자료가 가르쳐주지 않은 것을
  본인이 직접 플레이하며 발견
  → Tier 2+ 본격 콘텐츠 작업 핵심 지표
```

---

## 7. W2 D5 후 결정 시점

```
W2 D5 완료 후:

옵션 (A): 즉시 W3 D1 (본인 5회 도그푸딩)
  - W2 D5 발견 즉시 추가 검증
  - 시간: 2-3시간
  - ★ 컨디션 좋으면

옵션 (B): 휴식 + W3 다음 세션
  - W2 D5만으로 큰 마일스톤
  - W3는 새 영역 (베타 / 친구)
  - 깨끗한 상태로 W3 시작

옵션 (C): W2 D5 발견에 따라 인프라 보완
  - critical finding 발견 시
  - W3 전에 hot-fix
  - 시간: 1-2시간

★ 추천: (B)
  - W2 D5 = 큰 자축 시점
  - W3는 베타 + 본인 외 사용자
  - 깨끗한 상태 가장 중요
```

---

## ★ 핵심

W2 D5는 **본인 직접 사용자**가 되는 시점.
1.5일 동안 만든 인프라를 본인이 직접 검증.

```
★ 자료 #14 정신 정확:
"게임 성숙 후 본인 검토"
→ 게임 성숙 ✅ (W2 D4까지)
→ 본인 검토 ✅ (W2 D5 깨끗한 상태)

★ 진짜 가치:
- 인사이트 #15 가능성
- Tier 1 졸업 #4 본인 입증
- W3 도그푸딩 준비
- Tier 2+ 콘텐츠 방향 제시
```
