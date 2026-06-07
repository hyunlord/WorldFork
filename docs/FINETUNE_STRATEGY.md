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
