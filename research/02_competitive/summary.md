# Summary — 02 Competitive

> GPT 1 결과 정리
> 적용: ROADMAP 9.2, 10.1-10.4, HARNESS_LAYER2 7.4

## 핵심 결정 (ROADMAP에 반영됨)

### 차별화 포지셔닝
- **서사형 (story-first)** > 동반자형 (companion-first)
- 한국 시장 검증된 패턴

### 4개 차별화 축
1. Plan review/edit workflow (다른 서비스에 X)
2. 4축 다양성 (entry / mode / genre / freedom)
3. Hybrid game mechanics (채팅 위주 서비스에 X)
4. Cross-Model verification (안전성 차별화)

### 가격 전략 (Tier 3+)
- 무료 진입 + 웹 구독 + 코인/에피소드 + creator economy
- 웹: 8,900~12,900원/월
- 앱: 11,900~15,900원/월 (수수료 반영)
- 웹 결제 우선 (수수료 회피)

## 핵심 발견

### 1. 한국 시장은 살아있음 (★★★)

```
검증된 활성도:
  제타 (스캐터랩):
    - MAU 402만 (2026-02)
    - 월 사용시간 5,248만 시간
    - 사용자 87%가 10-20대
    - 주당 12시간 사용
    
  Crack (뤼튼):
    - ARR $7000만 (2025년 말)
    - "AI 엔터테인먼트 사업 확장"
    
  사용 패턴:
    - 짧은 세션 반복
    - 게임 + 커뮤니티 + 소설 혼합형
    - 광고보다 반복 결제 적합
```

### 2. 승자 패턴 — "루프"가 핵심 (★★★)

```
Characters → Scenes/Plots → Public Chat/Fork → Creator Rewards → Subscription

각 서비스 검증:
  Character.AI: Feed/Scenes
  Crack: 오리지널 보상
  Janitor: public chats
  AI Dungeon: Story Cards
  
WorldFork 적용:
  - Plan review/edit = "Plot 분기"
  - 4축 다양성 = "Scenes" 다양화
  - 공유 가능한 시나리오 = "Public Fork"
  - Tier 3+ creator economy
```

### 3. 메모리가 가장 강한 결제 동기 (★★★)

```
모든 서비스가 "더 나은 메모리"로 유료화:
  c.ai+: $9.99/월
  AI Dungeon: $14.99/월
  Kindroid: $13.99/월
  NovelAI: $10/월
  Zeta Pass: 월 구독 (한국)
  Crack: 웹 vs 앱 가격 차

WorldFork 함의:
  - 메모리 = 차별화 + 결제 동기
  - HARNESS_LAYER2 메모리 시스템 가치 큼
  - 무료: 짧은 / 기본
  - 유료: 더 길게 / 더 정교하게
```

### 4. 한국 시장 위험 4축 (★★★ 진입 조건)

#### 위험 1: 개인정보 (이루다 사례)

```
이루다 사건 (2021 PIPC 제재 → 2025 손해배상 확정):
  - AI 학습 데이터 적법성 = 평판 X, 실질 법적 비용
  
WorldFork 대응:
  - 학습 활용 X 명시
  - 옵트인 동의 강제
  - AI Playtester 합성 데이터 의존 (사용자 데이터 회피)
```

#### 위험 2: 미성년자 보호 (Character.AI 사례)

```
Character.AI 소송 (자살 사건, 디즈니 경고장):
  - 2025-10 미성년자 오픈 채팅 단계적 중단
  - Kentucky AG 소송
  
WorldFork 대응:
  - 청소년 / 성인 모드 분리 from Tier 0
  - 안전 필터 + 응급 리소스
  - 나이 확인 강제
```

#### 위험 3: IP / 실존 인물

```
디즈니 → Character.AI 경고장
한국 저작권위원회 가이드라인
일본 문화청 AI·저작권 해석

WorldFork 대응:
  - Plan Verify에 IP Leakage 검증 (Debate Mode)
  - 실존 인물 / 미성년 캐릭터 강하게 차단
  - 공식 IP 라이선스 협업 (Tier 3+)
```

#### 위험 4: 메모리 비용 폭증

```
장기 RP의 핵심 = 비용 폭증 동인
WorldFork 대응:
  - Hierarchical memory (요약 + 관계 + 로어북)
  - 무료 / 유료 차별화
  - HARNESS_LAYER2 KV cache 추적
```

### 5. 일본 시장이 best benchmark (★★)

```
일본 = 한국과 유사 (캐릭터 + 장르 + 결제):
  MiraiMind: 일본 DAU 15만 (2025-10), 글로벌 200만 다운로드
  Wrtn 일본향 Kyarapu
  Scatter Lab 일본 진출

함의:
  - 한국 검증 → 일본 확장 가능
  - WorldFork 글로벌 확장 시 일본 1차 타겟
```

## 구체 권고 사항

### MVP (Tier 3 출시) 6개 기능

1. 한국어 장르 프리셋 (로맨스 / BL / 이세계 / 학원 / 추리 / 호러)
2. 요약 + 관계 + 로어북 3층 메모리
3. Scene/Plot 분기 + 퍼블릭 포크
4. 페이지당 길게 쓰는 편집기
5. 청소년 / 성인 이원화 safety
6. 웹 결제 + creator payout

### 유통 전략

1. 팬덤 도메인 우선 (앱스토어 X)
2. 웹소설/웹툰 독자 커뮤니티
3. 디시 / Reddit / Discord 팬덤
4. X / Threads / 틱톡 짧은 대화 캡처
5. 퍼블릭 대화 공유 = 마케팅 자산

### 파트너십 3갈래

1. 웹소설/웹툰 IP 홀더 (공식 라이선스)
2. 보이스 / TTS (ARPPU 상승)
3. 결제 / 통신 / 디바이스 (웹 결제 네이티브)

## KPI 제안

```
성장:
  - MAU, CAC, 첫 장면 완료율

몰입:
  - D1/D7/D30 유지율
  - 주간 세션 / 메시지 수
  - 시나리오 분기율 / 퍼블릭 포크율

품질:
  - 메모리 리콜 정확도
  - 반복문체 비율
  - p95 응답지연
  - 안전 필터 false positive/negative

수익:
  - 유료 전환율
  - ARPPU
  - 웹 결제 비중
```

## 신뢰도

- ★★★ 한국 시장 활성도: 풍부한 1차 출처 (스캐터랩 공시, 뤼튼 공식, Reuters)
- ★★★ 위험 사례: 법원 도켓, 정부 가이드라인 등
- ★★ 정확한 사용자 수치: GPT 환각 가능성 (검증 권장)
- ★★ 가격 추정: 공개 가격이지만 변동 가능
- ★ 일본 / 중국 시장: 영어 자료 제한적

## 미해결 / 검증 권장

1. 정확한 시장 규모 (한국 RP/IF 카테고리 TAM 비공개)
2. 한국 iOS/Android cohort data
3. 결제 패널 (한국 willingness-to-pay)
4. 일본 시장 진출 시점 / 방식

## Raw 결과 참조

- `gpt1_raw.md`: 한국 시장 경쟁 분석 (200줄, 한국어, 100+ citation)

citation 구조: `citeturnNNsearchM` 형식 — 본인이 무작위 5-10개 검증 권장.
