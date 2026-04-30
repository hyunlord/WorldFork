# Tier 1 W1 D1 보고서 — Local LLM 인프라

날짜: 2026-04-30  
작업자: hyunlord  
하드웨어: DGX Spark (NVIDIA GB10, 119GB Unified Memory, Ubuntu 24.04 ARM64, CUDA 13.0)

---

## 목표

DGX Spark에서 llama-server 3대를 띄우고, LocalLLMClient를 구현해  
Tier 1 추론 인프라의 첫 번째 레이어를 완성한다.

---

## 완료 항목

### 1. 모델 다운로드

| 모델 | 파일 | 크기 | 경로 |
|------|------|------|------|
| Qwen3.6-27B Q3_K_XL | Qwen3.6-27B-UD-Q3_K_XL.gguf | 약 15 GB | `/home/hyunlord/models/gguf/qwen36-27b/` |
| Qwen3.6-27B Q2_K_XL | Qwen3.6-27B-UD-Q2_K_XL.gguf | 약 11 GB | `/home/hyunlord/models/gguf/qwen36-27b/` |
| Qwen3.5-9B Q3_K_XL | Qwen3.5-9B-UD-Q3_K_XL.gguf | 약 4.7 GB | `/home/hyunlord/models/gguf/qwen35-9b/` |

> **Qwen3.5-9B**: Qwen3-8B의 직접 후속. unsloth/Qwen3.5-9B-GGUF 확인.

### 2. llama.cpp 소스 빌드

```bash
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=121
cmake --build build --config Release -j $(nproc)
```

- GB10 (CC 12.1, sm_121a) 정상 빌드 확인
- `llama-server` 바이너리 생성 완료

### 3. 서버 3대 구성

| 포트 | 모델 | 역할 |
|------|------|------|
| 8081 | qwen36-27b-q3 | GM 후보, 높은 품질 |
| 8082 | qwen36-27b-q2 | 본인 직관 baseline |
| 8083 | qwen35-9b-q3 ★ | NPC dialogue (실시간) |

**Thinking OFF** (`chat_template_kwargs: {"enable_thinking": false}`) 기본 적용.  
Qwen3.x 계열은 thinking 모드 기본 ON → 반드시 OFF 해야 latency 정상.

### 4. 성능 측정 (thinking OFF, 200 tokens, 개별)

| 모델 | Latency | Tok/s | 게임 적합성 |
|------|---------|-------|-------------|
| 27B Q3 (8081) | 16.3s | 12.3 | GM 후보 (긴 묘사) |
| 27B Q2 (8082) | 13.8s | 14.5 | ★ GM baseline |
| 9B Q3 (8083) ★ | 5.26s | 38.0 | ★ NPC (5초 목표 근접) |

> 9B Q3: 게임 NPC 응답 5초 목표에 충분히 근접. GM은 27B Q2(baseline).

### 5. LocalLLMClient 구현

`core/llm/local_client.py`:

- `LocalLLMClient`: LLMClient ABC 상속, OpenAI-compat `/v1/chat/completions` 호출
- thinking OFF 기본값 (`_THINKING_OFF = {"enable_thinking": False}`)
- 팩토리 함수 5개: `get_qwen36_27b_q3`, `get_qwen36_27b_q2`, `get_qwen35_9b_q3`, `get_default_npc`, `get_default_gm`

### 6. Registry/Config 업데이트

- `config/llm_registry.yaml`: local_http 엔트리 3개 추가, tier_1 권장사항 기재
- `config/cross_model.yaml`: tier_1 generator/verifier, qwen 모델 meta 추가

### 7. 단위 테스트

`tests/unit/test_local_client.py`: 19개 테스트, 전원 통과

- `TestLocalLLMClientInit` (5): defaults, trailing slash, chat_template_kwargs 변형, thinking OFF payload 검증
- `TestLocalLLMClientGenerate` (9): 성공, system 포함/제외, kwargs 전달, HTTP 에러, RequestException, 응답 형식 에러, cost=0.0, raw base_url
- `TestFactoryFunctions` (5): 팩토리 함수 전체 포트/키/thinking_off 검증

### 8. Ship Gate

```
✅ Ship gate PASSED (A 등급, 100/100)
  [1/5] Build:    20/20
  [2/5] Lint:     15/15
  [3/5] Unit:     20/20  (242 passed total)
  [4/5] Eval:     20/20
  [5/5] Verify:   25/25
```

---

## 트러블슈팅 기록

### hf-xet Permission Denied

`/home/user/.cache/` 하드코딩된 Rust 바이너리 문제.  
→ `uv pip uninstall hf-xet`, Python `hf_hub_download()` API 직접 사용.

### Qwen3.x thinking 모드 (content empty)

`max_tokens=150` 환경에서 모델이 모든 토큰을 `reasoning_content`에 소진,  
`content` 필드가 빈 문자열로 반환됨.  
→ payload에 `"chat_template_kwargs": {"enable_thinking": false}` 추가. 즉시 해결.

### SGLang SKIP (W1 D1)

`sgl_kernel 0.3.21`: sm_121a(CC 12.1) 미지원, CC ≤ 12.0 only.  
→ llama-server 단독 운영으로 전환. 성능 요구사항 충족 확인.

---

## 다음 단계 (W1 D2 예정)

- NPC dialogue 파이프라인 연결 (`LocalLLMClient` → 게임 루프)
- 27B 동시 추론 테스트 (Batching, 멀티 NPC 시나리오)
- LLM Judge cross-model 검증 (qwen36-27b-q3 as verifier)
