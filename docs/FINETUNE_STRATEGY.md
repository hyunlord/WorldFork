# 파인튜닝 전략 — 범용 향상 vs 태스크 특화 (크기 × 목적)

평가 프레임워크(tools/eval/) 측정으로 도출한 파인튜닝 전략. 측정 근거 → 베이스/목적 매칭.

## 1. 측정 근거 (왜 파인튜닝)

| 모델 | G-Eval 종합 | 문체 | 비고 |
|---|---|---|---|
| Gemma 4 12B (배선) | ~4.6 | ~4.0 | 현 pivotal GM, 15 t/s |
| Qwen 27B fp8 | ~4.5 | ~4.2 | 품질 최상, 2.3 t/s(느림) |
| Qwen3.5-4B (소형 최고) | 3.59 | ~3.0 | bf16, 2bit서도 한글순도 100% |
| 소형 3-4B 일반 | 2.1~3.6 | 낮음 | ★ 12B에 못 미침 → 파인튜닝 필수 |

- 약점 축 = **문체(조선·중세풍 문어체) + persona**. 고증/시스템은 양호(canon RAG + contract 프롬프트).
- 소형은 좁은 태스크면 작아도 가능 / 큰 모델은 범용 향상으로 천장 돌파.

## 2. ★ 크기 × 목적 매트릭스 (설계 핵심)

|  | 범용 향상(모델 자체 한글/전반) | 태스크 특화(태스크별 LoRA) |
|---|---|---|
| **소형 3-4B** | △ (12B 추격엔 한계) | ★◎ 좁게=작아도 충분 + 멀티 LoRA 효율 |
| **중형 12B** | ◎ 문체 완성 (현 배선 Gemma) | △ 이미 범용 — LoRA 이득 적음 |
| **대형 27B/35B-A3B** | ◎ 천장 돌파(최상 GM) | ✕ 멀티 LoRA 메모리 부담 |

**자연 매칭:**
- 소형 **Qwen3.5-4B** = 태스크 특화 멀티 LoRA (GM서사 / intent / 전투 / 고증 어댑터) — 빠른 경로.
- 큰 모델 **12B(Gemma) / 35B-A3B(MoE 3B active — 큰 품질+빠른 속도)** = 범용 향상(문체 SFT).
- ★ 현 하이브리드(단순 9B / pivotal 12B)의 진화: 단순 경로를 **Qwen3.5-4B + 태스크 LoRA**로,
  pivotal을 **범용 향상 12B/35B-A3B**로.

## 3. 데이터 전략 (LLM-as-labeler + 함정 회피)

원작 본문(.local/novel_bodies/ episode_*.txt, 19MB — ★ 저작권: gitignored, 학습 데이터도 git 금지)
→ instruction-output 쌍 역설계.

1. **청킹**: 3-4문장 단위(서사 호흡).
2. **labeler(27B 8081 or Claude)**: chunk → `{instruction: 게임로그/행동, output: 본문 그대로}`.
   - Narrative output은 **본문 원문 보존**(문체 학습 핵심).
3. **★ 함정 회피 (mode collapse / 과적합):**
   - 격식체 필터: 챗봇 말투("~해요/~에요") 정규식 제거 — 문어체만.
   - 문체 일관 + 플롯 다양: 같은 문체, 다른 상황(특정 플롯 암기 방지).
   - 합성 데이터: 원작에 없는 상황을 문체만 추상화해 생성(일반화).
   - 1500-3000 쌍(품질 > 양 — 소형 과적합 회피).
   - holdout 분리(PPL/문체 모방 평가용).

## 4. 학습 (단계적)

**1단계(검증) — 소형 태스크 LoRA**: Qwen3.5-4B + GM서사 LoRA.
- r=16-32, alpha=2r, target=attention proj. 2-3 epoch + 체크포인트(과적합 조기 발견).
- Unsloth or ai-toolkit(비요른 SDXL LoRA 전례). 병합 → GGUF → tools/eval 서빙.

**2단계 — 큰 모델 범용 향상**: 12B/35B-A3B 문체 SFT(파이프라인 재사용, 비싼 학습은 1단계 검증 후).

## 5. 평가 (프레임워크 전후 — 같은 틀)

tools/eval/ 6+지표 전후 비교:
- 문체/persona 향상(목표 +1.0 이상) · 한글순도·구조화 **유지**(Catastrophic Forgetting 체크)
- PPL holdout(문체 모방) · ★ mode collapse 체크(플롯 복사 여부 — 다judge + Claude 웹)
- 이중 평가(로컬 다judge → Claude 웹 권위).

## 6. ★ 실행 선결 조건 (현재 상태)

| 항목 | 상태 |
|---|---|
| 원작 본문(labeler 입력) | ✅ .local/novel_bodies/ |
| labeler(27B) | ✅ 8081 |
| 데이터 파이프라인 코드 | ✅ tools/finetune/build_dataset.py |
| 학습 패키지(unsloth/peft/trl) | ❌ 미설치 — ★ 외부 패키지 정책상 승인 필요(exception 목록 밖) |
| Qwen3.5-4B safetensors(LoRA 베이스) | ❌ GGUF만 보유 — HF safetensors 다운로드 필요 |
| GB10 Blackwell 학습 호환 | ❓ 미검증(torch 2.11 sm_121 + unsloth/triton) |

→ 데이터 파이프라인은 즉시 실행 가능. **LoRA 학습은 패키지 승인 + safetensors + GB10 호환 검증 후.**
대안: Mac(MLX-LM LoRA) 또는 승인된 학습 환경에서 1단계 검증 후 GGUF 반입.

## 7. 1단계 실행 결과 (2026-06-08 — 파이프라인 검증 ✅ / 품질 ❌ 음성)

**환경 해소**: 사용자(DGX 소유자) peft/trl 승인. GB10 sm_121 호환 = PEFT 0.19.1 + TRL 1.5.1
+ transformers 4.57.1 동작(단, torchao 0.9.0 제거 필요 — PEFT는 >0.16.0 요구).

**파이프라인 5단계 전부 작동 검증**: 데이터(Gemma labeler 100쌍) → LoRA SFT(r16, 3ep,
train_loss 2.80, loss 4.59→2.13 단조 하강) → 병합 → GGUF(Q8) → tools/eval A/B 평가.
도구: `tools/finetune/{train_lora,merge_lora,eval_ab}.py`.

**A/B 결과(base vs LoRA, 동일 Q8·동일 시나리오·judge=gemma+27b)** — ★ 음성:

| 모델 | judge overall | 문체 | persona | 고증 | 시스템 | 한글순도 |
|---|---|---|---|---|---|---|
| Llama-3.2-3B base | 2.92 | 1.83 | 2.33 | 3.50 | 4.00 | 95.1% |
| + GM-LoRA | **2.25** | 1.83 | 1.67 | 2.33 | 3.17 | **90.8%** |

**근본 원인(measurement-first)**:
1. **base가 부적합** — Llama-3.2-3B는 영어 중심(한자 누출 `修`/`narrowing`). 파이프라인 검증용
   fallback이지 의도한 Qwen3.5-4B(한국어 강함) 아님. transformers 4.57.1이 `qwen3_5` arch
   미인식이라 부득이 대체 → **production base는 transformers 업그레이드 후 Qwen3.5-4B 재시도**.
2. **Full SFT(assistant-only loss 미지원)** — Llama 템플릿에 `{% generation %}` 마커 부재로
   프롬프트까지 학습 → 포맷 모방·메타 누출("## 메타·규칙"). assistant-only 가능한 base 필요.
3. **타깃=원작 본문 청크** — 문맥 끊긴 중간 파편 + 한자를 문체로 학습 → 순도 하락.
4. **100쌍 3ep lr2e-4** = 파편 과적합. 다음: 1500-3000쌍·lr5e-5·early-stop.

**결론**: 도구·파이프라인 검증 완료(재사용 가능). 품질 개선은 base+레시피 교체 후 2차 시도.
헛된 비싼 학습(2단계 12B)을 막은 값싼 음성 신호 — 1단계 검증의 본래 목적 달성.

## 8. labeler 비교 + 정제 데이터 (2026-06-08 — 음성 원인#3 직격)

**★ 핵심 통찰**: 음성 원인#3 "데이터 파편"은 *labeler*가 아니라 *output(원작 본문 청크)* 문제.
데이터=[instruction(labeler) → output]. 큰 모델 최고 레버리지 = labeler가 아니라 **청크
정제기**(원작 파편 → 자기완결 순한국어 GM 서사). → 비교를 두 역할(역설계+정제)로 평가.

**GGUF 가용성(128GB 적합)**: 397B-A17B ❌(2bit 115GB·3bit 140GB, 192GB+ 필요 / 1bit 107GB=
품질 붕괴), Kimi 1T·DeepSeek 284B ❌(더 큼). **122B-A10B ✅**(Q4_K_XL 72GB)가 현실적 최대.

**비교(같은 본문 5청크 × 역설계+정제, judge=27B+gemma+122B self-제외)** — ★ best=27B:

| labeler | overall | 자기완결 | 문어체 | 메타제거 | 충실 | 순도 |
|---|---|---|---|---|---|---|
| **qwen36-27b** | **3.9** | 3.9 | 3.9 | 3.7 | 4.1 | 99.3% |
| gemma-4-12b | 3.5 | 3.9 | 2.9 | 3.5 | 3.7 | 100% |
| qwen35-122b Q4 | 3.4 | 3.8 | 3.2 | 3.1 | 3.5 | 100% |
| qwen35-9b | 2.75 | 3.27 | 2.33 | 2.6 | 2.8 | 99.4% |

**★ 큰 모델≠나음**: 최대 122B가 27B보다 낮음(좁은 한국어 역설계/정제는 27B 충분). 게임메타
과다 청크("히든피스")는 전 모델 저점 → 청크 선별 필요. 도구: compare_labelers/judge_raw.py.

**정제 데이터 v2**: 27B 동시 8 병렬로 [instruction → 정제 rewrite] 1500쌍 생성
(gen_rewrite_dataset.py, 순도 95%+ 필터). output=자기완결 문어체 서사(파편 X) → 음성#3 해결.
.local/finetune/gm_narrative_v2.jsonl. **2차 LoRA(base 교체 + assistant-only)는 후속.**
