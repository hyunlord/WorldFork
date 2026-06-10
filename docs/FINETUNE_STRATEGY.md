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

## 9. labeler 보강 + 한자 누출 (2026-06-08 — best 재선정 → 35B)

**계기**: ① 빠진 모델(35B-A3B/Gemma31B) 미평가 ② Claude 웹 발견 — 27B에 한자(중국어) 누출.
검증: v2 데이터(27B) output 한자 누출 **86/1500(5.7%)** 확인(实话/背影/这等/踉踉跄跄). 순도
필터(≥95%)가 1~2자 누출을 통과시킴 → 학습 위험(1단계 음성도 누출 문제였음, 같은 함정).

**6 labeler 재비교(judge 4종=35b/gemma31b/27b/gemma self제외, 한자0 우선)**:

| labeler | overall | 문어체 | 자기완결 | 충실 | 한자(5청크) |
|---|---|---|---|---|---|
| **qwen36-35b** | **4.15** | 3.8 | 4.47 | 4.53 | **0** ★ |
| qwen35-122b Q4 | 3.61 | 3.45 | 4.2 | 3.8 | 0 |
| gemma31b | 3.58 | 3.13 | 4.4 | 3.8 | 0 |
| gemma-4-12b | 3.53 | 2.73 | 4.4 | 3.87 | 0 |
| qwen36-27b | 3.83 | 3.13 | 4.4 | 4.47 | **1** ✗ |
| qwen35-9b | 3.04 | 2.1 | 3.9 | 3.5 | 0 |

**★ 새 best=qwen36-35b**: 문어체·자기완결·충실 전부 최고 + 한자 누출 0. 기존 27B를 문체·안전
둘 다 능가. 35B-A3B는 MoE(3B active)라 27B보다 3배 빠름(정제콜 6.6s vs 18.6s). 큰 모델
(122B/Gemma31B)은 한자0이나 문어체 35B 미달 — "큰 모델≠나음" 재확인.

**데이터 v3**: best 교체 → 35B로 1500쌍 재생성(gm_narrative_v3.jsonl). 필터 강화 **cjk=0
+ 순도 97%+**(v2의 5.7% 누출 차단). gen_rewrite_dataset.py --labeler 추가. **2차 LoRA는 후속.**

## 10. 2차 LoRA 실행 결과 (2026-06-08 — 음성 4원인 수정 ✅)

**4원인 수정**: ①base Qwen3-4B-Instruct-2507(한국어 강·qwen3 arch 인식, Qwen3.5-4B는
transformers 5.x 필요라 동급 대체) ②assistant-only loss(템플릿 {% generation %} — 1단계
Llama 차단 극복, entropy 1.18=마스킹 활성) ③v3 1500쌍(한자 0) ④lr 5e-5 + eval holdout 5%
+ EarlyStopping. 학습: 3ep 3.7h, train_loss 2.08, eval_loss 2.13→2.04 플래토(과적합 없음).

**A/B(base vs 2차 LoRA, 동일 Q8·judge gemma+27B self제외)**:

| 축 | base | 2차 GM | Δ | 1단계 GM(참고) |
|---|---|---|---|---|
| **문체** | 2.67 | **3.0** | **+0.33 ↑** | 1.83(정체) |
| persona | 3.17 | 2.83 | −0.34 | 1.67 |
| 고증 | 4.5 | 3.83 | −0.67 | 3.5 |
| 시스템(메타) | 5.0 | 4.83 | −0.17 | 3.17(누출) |
| overall | 3.83 | 3.62 | −0.21 | 2.25 |

**★ 4원인 수정 검증**: ①문체 +0.33(1단계 정체→향상) ②메타 누출 0(시스템 4.83 유지,
"## 메타·규칙" 사라짐 — assistant-only 성공) ③한자 0(순도 100%) ④과적합 없음(eval_loss 플래토).
1단계(2.92→2.25, -0.67, 메타누출)와 비교해 대폭 개선. 단 **고증 -0.67 trade-off**(문체 SFT가
lore-grounding 일부 희생) + 강한 base(3.83)라 overall LoRA 이득 제한적. 도구: train_lora/
merge_lora/eval_ab v2화. **다음: 고증 완화(데이터 혼합) or 큰 모델 범용 SFT(12B/35B-A3B).**

## 11. 여러 base SFT 매트릭스 (2026-06-09 — 약한 base 가설 반증)

**목표**: 같은 v3 + 2차 레시피로 여러 base SFT → "약한 base가 LoRA 이득 큰가"(크기×목적) 검증.

**툴체인 측정(가정 아닌 실측)**:
- ❌ Qwen3.5/3.6 + Gemma 4: transformers 5.x 필요 → peft(릴리스 0.19.1 + git main 0.19.2dev)
  모두 tf5 미지원(`PreTrainedModel` top-level export 제거) → LoRA 불가. 별도 ft_venv 복제까지
  검증. (게임 런타임·테스트는 transformers 미사용이라 무관.)
- ❌ Phi-4-mini/Bllossom: TRL assistant-only는 템플릿 {% generation %} 마커 필요 — 부재.
  → 검증된 ChatML generation 템플릿 주입 + SFTTrainer processing_class로 Bllossom은 살림.

**작동 base 3종 A/B(judge gemma+27B self제외)**:

| base | base | gm(LoRA) | Δ overall | 문체 base→gm | 순도 |
|---|---|---|---|---|---|
| SmolLM3-3B (약) | 3.42 | 2.83 | −0.59 | 3.0→2.33 ↓ | 100% |
| Bllossom-8B (한국어, 1ep) | 3.46 | 2.04 | −1.42 | 2.67→1.83 ↓ | 86.5% |
| **Qwen3-4B (강)** | 3.83 | 3.62 | −0.21 | 2.67→**3.0 ↑** | 100% |

**★ 매트릭스 결론 — 가설 반증**: 약한 base(SmolLM3/Bllossom)는 LoRA 이득이 크기는커녕 **더
악화**. 강한 Qwen3-4B만 문체 향상 + 최소 하락(유일하게 문체↑). = 좁은 문체 SFT엔 base 품질이
중요(약한 base는 v3 문어체를 흡수하며 기존 능력 손상). Bllossom은 ChatML 주입+1ep 미완 영향
일부(순도 86.5%=템플릿 토큰 누출 의심). **채택 best=Qwen3-4B(2차)** 유지. 큰 모델 범용 SFT가
다음 후보(강한 base일수록 LoRA 이득 — 매트릭스 시사). 도구: train_lora --base/--out + 템플릿 폴백.

## 12. Unsloth 트랙 + 큰 모델 SFT (2026-06-09)

**트랙 A — Unsloth로 peft⊥tf5 갭 우회(Qwen3.5/3.6/Gemma4)**:
★ **Unsloth가 GB10에서 Qwen3.5-4B 로드 성공** — peft가 못 한 arch 인식 갭을 우회(자체 tf5.5 호환 +
FastLanguageModel). Torch 2.9.1+cu128/CUDA 12.1/Triton 3.5.1 작동, 모델 로드 + LoRA + eos/pad
토큰 검증까지 통과. **단 auto-resolved unsloth2026.6.1+tf5.5+trl0.24 스택이 학습 진입에서 연쇄
버전 버그**: ① CPU torch(→.venv torch 복사) ② torchvision 불일치(제거) ③ trl.chat_template_utils
모듈 변경 ④ SFTConfig eos/pad '<EOS_TOKEN>'/'<PAD_TOKEN>' placeholder(→토큰 등록으로 통과)
⑤ **dill pickle ConfigModuleInstance**(torch config 직렬화 — num_proc=1로도 미해결). → **경로 입증
(최신 모델 GB10 로드 가능), 학습 하니스는 Unsloth 공식 핀 버전 필요(후속)**. 도구: train_unsloth.py.

**트랙 B — 큰 모델 범용 SFT(강한 base 유리 매트릭스 시사)**: Qwen3-8B(qwen3, .venv peft 작동)로
v3 + 2차 레시피 SFT. (※ Gemma4/27B=qwen3.6/35B-A3B는 모두 tf5 필요라 .venv peft 불가, Unsloth는
하니스 버그 → 작동 큰 모델 = Qwen3 계열.) 결과는 후속 커밋.

## 13. 큰 모델 SFT 결과 — 강한 base 가설 확정 (2026-06-09)

**Qwen3-8B(qwen3, .venv peft 작동) v3 + 2차 레시피 A/B(judge gemma+27B self제외, 1ep)**:

| base | base | gm | Δ overall | 문체 Δ | 시스템(메타) |
|---|---|---|---|---|---|
| SmolLM3-3B(약) | 3.42 | 2.83 | −0.59 | −0.67 | ↓ |
| Bllossom-8B(약,1ep) | 3.46 | 2.04 | −1.42 | −0.84 | ↓ |
| Qwen3-4B(강) | 3.83 | 3.62 | −0.21 | +0.33 | 4.83 |
| **Qwen3-8B(더 강)** | 3.75 | **3.79** | **+0.04 ↑** | **+0.50 ↑** | 4.33→4.83 |

**★ 매트릭스 확정**: Qwen3-8B는 **LoRA가 overall을 올린 첫 base**(+0.04) + 문체 최대 향상(+0.50)
+ 메타 누출 0(시스템 4.83) + 순도 100%. 강할수록(SmolLM3 약→Qwen3-4B→8B) LoRA 결과 단조 개선.
"강한/큰 base 유리" 확정 — 약한 base는 v3 흡수하며 손상, 강한 base는 기존 능력 보존하며 문체 흡수.
**채택 best=Qwen3-8B**(overall 양성). 다음: 더 큰 강한 base(14B/Qwen3.5 — Unsloth 핀 해결 시) /
ep 늘려 8B 완전 학습 / 게임 배선(8B는 4B보다 느리나 품질↑ — 속도-품질 trade 검토).

## 14. ★ Unsloth 트랙 성공 — Qwen3.5-4B GB10 학습 완성 (2026-06-09)

**직전(§12) 학습 하니스 차단을 측정으로 전부 해소** — Unsloth로 의도한 최신 모델 학습 성공:
- **dill pickle ConfigModuleInstance** → `UNSLOTH_COMPILE_DISABLE=1` + `TORCHDYNAMO_DISABLE=1`
  (torch.compile/_dynamo config가 dataset.map 클로저에 잡히던 문제, num_proc 무관)
- **Triton PTXAS sm_121a 미지원** → `TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas`
  (번들 ptxas=CUDA12.8 sm_120까지 / 시스템 CUDA13.0이 sm_121a 컴파일 지원)
- **GGUF 변환** → unsloth_venv(tf5.5, qwen3_5 인식) + gguf 패키지로 변환, **llama.cpp는 QWEN35
  arch 지원**(서빙 OK). .venv tf4.57.1로는 qwen3_5_text 미인식이라 불가.

**Qwen3.5-4B(Base, Unsloth r16 1.1ep) A/B(judge gemma+27B self제외)**:
base 3.67 → gm **3.83 (+0.16 overall ↑)** — 매트릭스 **최대 양성**. 고증 4.33→5.0·persona↑,
문체 3.0→2.67(소폭↓ — 1.1ep 미완 영향 가능), 순도 100%, 메타0(시스템 5.0).

**★ 최종 매트릭스(강한/큰/최신 base 유리 확정)**:
| base | base | gm | Δ overall |
|---|---|---|---|
| SmolLM3-3B | 3.42 | 2.83 | −0.59 |
| Bllossom-8B | 3.46 | 2.04 | −1.42 |
| Qwen3-4B | 3.83 | 3.62 | −0.21 |
| Qwen3-8B | 3.75 | 3.79 | +0.04 |
| **Qwen3.5-4B(Unsloth)** | 3.67 | **3.83** | **+0.16** ★ |

**도구**: train_unsloth.py(env 4종 필수 — docstring). Gemma 4/Qwen3.6은 동일 경로지만 gated HF
접근(라이선스+토큰) 필요 — 툴체인 아닌 접근 장벽. 채택 best=Qwen3.5-4B(의도 최신, 최대 LoRA 이득).

## 15. Gemma 4 시도 + repo명 정정 (2026-06-09)

**repo명 정정(앞 §의 "gated 미승인"은 오판)**: 404는 **존재하지 않는 이름**(gemma-4-4b-it,
Qwen3.5-4B-Instruct) 때문이었지 라이선스 아님. HfApi 실측 — 실제 이름 전부 gated=None(Apache/접근가능):
Gemma4=E2B/E4B/12B/26B-A4B/31B(+-it), Qwen3.5=0.8B/2B/4B/9B/27B/35B-A3B/122B-A10B/397B-A17B
(post-trained는 "-Instruct" 없이 Qwen3.5-4B), Qwen3.6=27B/35B-A3B. HF_TOKEN 유효(접근 OK).

**Gemma 4 E4B-it Unsloth SFT 시도 → device-side assert**: gemma-4 HF 토크나이저는 chat_template
부재 → ChatML 토큰 주입 + resize 필요한데, **E-series(MatFormer/elastic arch)에서 forward assert**
(4bit·bf16 둘 다). 접근/이름 아닌 arch별 토큰처리 이슈. → 후속: gemma-4-12B(dense, 현 GM)로 재시도
or gemma-native 템플릿(토큰 무주입). train_unsloth.py에 --no-4bit + ChatML 직접주입 폴백 추가.

## 16. Gemma 4 E4B 확정 차단 — elastic arch (2026-06-09)

**근본 원인 발견**: gemma-4는 chat_template을 `chat_template.jinja`(별도 파일)에 둠 — generation
마커 有, 마커 `<|turn>user`/`<|turn>model`. 앞 시도의 빈 템플릿은 다운로드 allow_patterns가
`.jinja` 누락 탓. train_unsloth.py에 **네이티브 템플릿 우선 + turn마커 자동감지 + eos 동적** 로직 추가.

**그러나 gemma-4-E4B-it는 4회 모두 device-side assert**(position_ids forward) — chatml주입/4bit/
bf16/네이티브 템플릿 전부 동일. = 토큰처리 아닌 **E-series(MatFormer/elastic) arch가 Unsloth+GB10
(sm_121) 비호환**. 접근/이름/라이선스 무관(토큰 유효, 이름 정확). **E4B 확정 차단**.
→ Gemma 4는 dense(gemma-4-12B/31B) 또는 Unsloth의 gemma-4 elastic 지원 갱신 후 재시도(후속).
채택 best 유지 = Qwen3.5-4B(Unsloth, +0.16).

## 17. Qwen 큰 사이즈 + Gemma 4 dense (2026-06-09 — 데이터 천장 + dense 학습 성공)

**트랙 C — Qwen 더 큰 사이즈(Unsloth)**: Qwen3.5-9B A/B → base **4.58**(전 base 최강) →
gm **4.08(−0.50)**. ★ 매트릭스 **비단조 정제**: 9B base가 v3 데이터 품질 천장(35B 증류)을
**넘어서** LoRA가 끌어내림. 최종 곡선: SmolLM3 −0.59 / Bllossom −1.42 / Qwen3-4B −0.21 /
Qwen3-8B +0.04 / **Qwen3.5-4B +0.16(sweet spot)** / Qwen3.5-9B −0.50. **결론: best=데이터
천장 아래의 강한 base(Qwen3.5-4B)**. 9B급은 v3보다 고품질 데이터 필요(원작 본문 직접 or 더 큰 정제기).

**트랙 A — Gemma 4 dense(★ E4B 가설 검증)**: gemma-4-12B-it는 transformers 5.5.0 미지원 →
**5.10.2 업글로 로드 성공** → Unsloth SFT **학습 작동**(step 120, device assert 없음). ★ E4B
(elastic/MatFormer)만 assert였고 **dense는 정상** — 사용자 가설 적중. 단 병합모델 arch가
`Gemma4UnifiedForConditionalGeneration`(멀티모달 통합) → llama.cpp convert 미지원으로 GGUF eval
보류(후속: 텍스트-only 추출 or 신 llama.cpp). 학습·병합은 성공. env 4종 + 네이티브/.jinja 처리 동일.

## 15. 게임 GM 배선 검증 — Qwen3.5-4B LoRA 속도×품질 A/B (2026-06-10)

**무작정 교체 X — 측정 후 판단**. Qwen3.5-4B LoRA(matrix best +0.16) vs 현 pivotal GM Gemma4-12B:

| 항목 | Qwen3.5-4B LoRA | Gemma4-12B(현 GM) |
|---|---|---|
| 속도 | **27.6 t/s** (TTFT 0.16s) | 16.0 t/s |
| 서사 길이 | ~130자 (짧음) | ~340자 (풍부) |
| 품질(27B+gemma judge, 매트릭스) | overall 3.83 | ~4.5 |

**자가평가(1차)**: 같은 장면 A/B에서 12B가 확연히 풍부·몰입(감각 묘사 "습기 머금은 공기 속
비린내/번뜩이는 안광"), 4B LoRA는 1.7× 빠르나 서사가 2.6배 짧고 일부 비논리("물음이 대답을
기다렸으나"). 품질 격차(3.83 vs 4.5)가 게임 서사에서 가시적. 단 9B judge 1차는 전부 5점=변별력
없음(약judge) → Claude 웹 2차가 권위(샘플 game_ab.zip).

**★ 배선 권장**: pivotal GM 교체 X — **Gemma4-12B 유지**(품질·풍부함이 GM 가치). Qwen3.5-4B
LoRA는 **빠른/단순 tier**(현 하이브리드 9B 자리)에 배치 — GM 문체 학습본이라 raw 9B보다 단순
서사에 적합 + 27.6 t/s. = 멀티모델 하이브리드(pivotal 12B / 빠른 4B), 전면 교체 아님. 둘 다 이미
playable(>15t/s)이라 속도 이득이 새 UX tier를 못 열고, 품질·길이 손실은 사용자 가시 → trade가 12B 유지 지지.

## 16. 4B 서빙 가속 진단 — qwen35 arch 커널 병목 (2026-06-10)

**27.6 t/s 비정상 원인 측정(llama-bench pp/tg 분리)**:
- pp256 **1240 t/s**(연산 빠름) vs tg256 **27.65 t/s**(생성 느림) — 연산·오프로드 정상, **decode 병목**.
- LoRA는 병합 단일 GGUF, -ngl 99 전 GPU — 설정 문제 아님.
- ★ 근본: Qwen3.5 = **Gated Delta Net(선형 어텐션 하이브리드)** 신규 arch. 고정 per-token 상태
  트래픽 + llama.cpp qwen35 tg 커널 미최적 → 4B Q8 대역폭 한계(~65)의 42%만.

**Q4_K_M 최적화**: tg 27.65 → **36.40 t/s(+32%)**. 단 가중치 0.6×인데 tg 1.32×만 = 순수
대역폭 아님(고정 비용 천장). Q4가 llama.cpp 최선. (Q8→Q4 재양자화 금지 — bf16 재병합 필요.)

**엔진 교체 차단(측정)**: Qwen3.5(`qwen3_5_text`)가 너무 신규라 **sglang(.venv tf4.57)/.venv/
vLLM 도커 전부 미인식**(transformers <5.5). tf5.5는 unsloth_venv뿐(sglang/vLLM 미설치).
→ **Qwen3.5-4B 서빙 엔진은 llama.cpp가 유일**(QWEN35 네이티브, transformers 무관). 100+ t/s는
vLLM/sglang에 tf5.5+FLA 최적 커널+GB10 sm_121 지원이 모두 갖춰져야 — 현재 부재.

**배선 함의**: 4B 빠른 tier는 **Q4 36.4 t/s**(12B 16의 2.3×)가 현실값(100+ 아님). 속도가 더
중요하면 표준 arch(Qwen3-8B 등 — Gated Delta Net 없음)가 llama.cpp서 더 빠를 수 있음(후속 비교).

## 15. ★ 원작 직접 데이터 — 9B 천장 돌파 (2026-06-10)

**가설**: v3는 원작→35B 증류(rewrite)라 천장 ~4.15. 강한 base(Qwen3.5-9B 4.33~4.58)는 v3로
오히려 -0.50 음성(증류 천장에 눌림). 원작 직접(output=원작 prose 원문, 증류 0)은 35B 손실 없어
9B base 위에서 양성 가능?

**데이터**: build_canon_direct.py — output=원작 chunk 원문(instruction만 labeler 역생성),
cjk=0 필터(한국 web novel 한자 0.3%뿐). canon_direct.jsonl 1500쌍(한자0/중복0/원작 prose).
★ 저작권: .local 전용(git 금지), zip 공유 시 본문 제외.

**9B Unsloth SFT(원작 직접, ~0.67ep) A/B(judge gemma+27B self제외)**:
| 데이터 | 9B base | gm | Δ overall | 문체 | persona |
|---|---|---|---|---|---|
| v3(35B 증류) | ~4.58 | ~4.08 | **−0.50** ✗ | | |
| **원작 직접** | 4.33 | **4.92** | **+0.59** ★ | 3.67→4.67(+1.0) | 3.67→5.0(+1.33) |

**★ 천장 돌파 확정**: 원작 직접 9B = **+0.59**(매트릭스 최대 양성) + 최고 절대품질 4.92
(persona·고증·시스템 5.0, 문체 4.67, 순도 98.75%). v3 -0.50 → 원작직접 +0.59 완전 반전 —
**증류 데이터의 천장이 진짜 병목이었음**(35B 증류 < 원작 prose). 전체 매트릭스 최종:
SmolLM3 -0.59 < Bllossom -1.42 < Qwen3-4B -0.21 < Qwen3-8B +0.04 < Qwen3.5-4B(v3) +0.16
< **Qwen3.5-9B(원작직접) +0.59**. 강한 base + 무증류 원작 = 최적. 게임 GM 최고 후보(9B 4.92).

**도구**: build_canon_direct.py(.local), train_unsloth --data. llama.cpp convert에 9B-Base
tokenizer hash(1444df5) qwen35 pre 등록(로컬 llama.cpp 패치).

## 16. ★ 깨끗한 재평가 — 4.92/+0.59 think 부풀림 정정 (2026-06-10)

**발견**: 9B canon GM은 thinking-on(주입 ChatML 템플릿이 enable_thinking 무시) → eval(max_tokens
200)서 think 텍스트가 채점에 포함돼 점수 부풀림. base(Qwen3.5-9B-Base)는 think 안 해 불공정.

**수정**: run_eval._stream_call에 `<think>` strip 추가(공정 — 모든 eval) + eval_ab `--no-think`
(user에 /no_think — thinking 토큰 소진 방지, 게임 배포 일치). 둘 다 적용 후 재평가:

| 데이터(9B) | think 포함(기존) | ★ 깨끗(--no-think+strip) |
|---|---|---|
| base | 4.33 | 4.42~4.50 |
| canon(원작 직접) | **4.92** | **4.50** (Δ +0.08) |
| v3(35B 증류) | (-0.50) | 4.25 (Δ −0.25) |

**★ 정정 결론**: 4.92→실제 4.50(think가 ~0.42 부풀림). 천장 돌파 +0.59→실제 **+0.08**(modest).
단 **방향은 실재**: 원작 직접(+0.08) > 35B 증류(−0.25), 격차 +0.33 — 강한 9B에 증류는 해롭고
원작은 약간 이롭다. 그러나 base 점수 자체가 run간 ±0.1 변동이라 +0.08은 marginal.
**게임 함의**: 9B canon 깨끗 4.50 ≈ 12B 4.5 — 4.92 우위는 환상. 현 배선(12B pivotal +
4B Q8 빠른tier) 유지가 타당. ★ qwen3.5 배포엔 thinking 억제(/no_think + strip) 필수.

## 17. ★ 평가 모순 재검증 — judge 변별력 결함 (2026-06-10)

**모순**: 깨끗한 서사 A/B서 12B가 압도(440~495자, 대사+분위기+「」)인데 점수 9B 4.50 ≈ 12B 4.5.
사용자 지적 — judge가 격차 못 잡음.

**규명 ①**: 현 pivotal 12B = **원본 Gemma 4 12B-it**(파인튜닝 아님, /poc/ GGUF, Apache). gemma
파인튜닝본(gemma4-12b-gm-unsloth)은 GGUF 변환 차단(멀티모달 arch)으로 미배포. → 파인튜닝 9B(4.50)는
원본 12B(4.5)를 못 넘음.

**규명 ② (★ 핵심)**: 기존 4축(문체/persona/고증/시스템)은 전부 "오류부재" 체크 → **짧을수록 유리**
(에러 기회 적음). 고증·시스템은 5.0 포화. 빈출력도 평균에 거의 반영 안 됨. 중립 judge 재채점:

| rubric | 9B(57~211자) | 12B(316~495자) |
|---|---|---|
| **lenient(기존 4축)** | **4.75** | 4.35 (★ 터스한 9B가 오히려 높음!) |
| **strict(+구체성/몰입)** | 2.57 | **3.53** (★ 12B 매 장면 우위 +0.96) |

**★ 결론**: 기존 점수는 "품질"이 아닌 "오류부재"라 서사 격차를 못 잡았다(짧으면 고득점). 구체성/몰입
(깊이·흡인력) 추가 시 12B >> 9B로 서사 체감과 일치. thinking 부풀림(§16)에 이은 2차 측정 결함 —
**전체 매트릭스 점수는 품질 순위가 아닌 오류부재 순위**(상대 델타는 참고만). 수정: metrics.py
JUDGE_AXES에 구체성·몰입 추가(6축, 빈약 감점 명시). **현 배선(12B pivotal) 정당 — 12B가 진짜 최고
서사**, 파인튜닝 9B는 대체 불가. ★ 향후 평가는 6축으로.

## 18. ★ 6축 전체 재평가 — 파인튜닝 품질 저하 반전 (2026-06-10)

기존 점수는 4축(오류부재)이라 부풀림(§16 think + §17 변별결함). 6축(+구체성/몰입, 빈약 감점)으로
같은 크기 원본 vs 파인튜닝 재평가(--no-think, gemma 중립 judge):

| 크기 | 원본 6축 | 파인튜닝 6축 | Δ(진짜 효과) |
|---|---|---|---|
| 4B | 3.50 | 3.28 (v3 GM-LoRA) | **−0.22** |
| 9B | 3.56 | 3.00 (원작직접) | **−0.56** |
| 12B | ~3.53(원본, strict 게임장면) | (GGUF 차단 미배포) | — |

**★ 결정적 반전**: 모든 파인튜닝이 6축서 원본보다 **낮음**. 기존 "양성"(4B +0.16 / 9B 천장돌파
+0.59→clean +0.08)은 전부 변별없는 rubric + think 부풀림 artifact. 원작 chunk(평균 140자) 학습이
출력을 **터스하게**(구체성/몰입↓) 만들어 품질 저하. 6축은 lenient에서 안 보이던 이 손실을 잡음.

**결론**:
- ★ GM 파인튜닝(전 base·전 데이터)은 **서사 품질을 못 올림**(오히려 터스화로 저하). 기존 매트릭스
  "best/천장돌파"는 측정 결함의 산물.
- ★ **원본 ≥ 파인튜닝** 확정 → 현 배선(원본 Gemma 12B pivotal) 강력 정당. Gemma 12B 파인튜닝도
  품질 이득 기대 어려움(GGUF 차단 + 6축상 FT 무익) — **원본 유지가 정답**.
- 파인튜닝 가치는 "품질 향상"이 아니라 좁은 태스크/포맷/속도(소형) 한정. 게임 GM 품질엔 큰 원본이 우위.
- 측정 교훈: rubric 변별력(구체성/몰입) + thinking 억제 없이는 점수가 품질을 호도. 향후 6축+/no_think 표준.
