# **WorldFork Architecture and Implementation Strategy: A 2026 Analysis of Korean LLMs, Hardware, and Agentic Systems**

## **Executive Summary**

The engineering of the WorldFork interactive game system exists at the intersection of several rapidly advancing technological domains in 2026: hyper-efficient small-to-medium language models (SLMs/MLMs), sparse Mixture-of-Experts (MoE) architectures, unified-memory edge supercomputing, and event-driven multi-agent simulations. Based on an exhaustive analysis of recent hardware benchmarks, model capabilities, and academic literature spanning 2023 to 2026, the following core conclusions govern the architectural strategy:

1. **The Persona-Scale Paradox is Architecturally Driven:** The empirical observation that smaller models (e.g., 0.8B) outperform mid-sized models in persona consistency is supported by recent literature on "Identity Drift" and the "Persona Selection Model".1 Larger models, particularly MoE architectures, experience severe identity drift during long-horizon interactions due to the vast array of overlapping latent personas and the mechanical routing of tokens across different experts.3 Dense, heavily supervised fine-tuned (SFT) models in the 3B–8B parameter range remain the optimal choice for rigid character consistency.  
2. **NVFP4 Precision Circumvents the DGX Spark Bottleneck:** The NVIDIA DGX Spark (GB10 Grace Blackwell) possesses 128 GB of coherent unified memory but is fundamentally constrained by a 273 GB/s memory bandwidth.5 To achieve the requisite 5-second response latency for multi-user real-time dialogue, deploying models utilizing NVFP4 or MXFP4 precision is mandatory. Under these formats, 8B–20B parameter models can sustain highly viable decoding speeds (38 to 82 tokens per second) while allowing sufficient VRAM for high-capacity Key-Value (KV) caching.7  
3. **Event-Driven "No-Tick" Orchestration is Mandatory for Scale:** Simulating 5–12 autonomous Non-Player Characters (NPCs) utilizing traditional polling loops will rapidly saturate local hardware. The adoption of an asynchronous, event-driven architecture—modeled after the OASIS simulator framework—combined with temporal knowledge graphs (e.g., Zep) is required to decouple agent inference from the real-time game clock and manage evolving narrative states.9  
4. **GRPO Fails at Subjective Persona Alignment:** While Group Relative Policy Optimization (GRPO) and Reinforcement Learning with Verifiable Rewards (RLVR) dominate reasoning and mathematical tasks in 2026, empirical data demonstrates that reinforcement learning is highly inefficient for aligning subjective, stylized character behaviors.12 Supervised Fine-Tuning (SFT) remains the mathematically optimal pathway for ingesting narrative datasets and maintaining strict conversational formatting.

## ---

**Part I: Applied Architecture and Model Deployment**

### **1\. Optimal Korean-Language Base Models in 2026**

The landscape of open-weight large language models has bifurcated into heavily specialized regional models and massive global frontier models. For the Korean language, evaluation relies deeply on domestic benchmarks such as KMMLU (broad native knowledge), KoBALT (professional-domain knowledge), CLIcK (cultural and linguistic nuance), and the Korean CSAT evaluations.14

#### **1.1 Domestic Korean-Tuned Models**

Regional models specialized for the Korean market drastically reduce "localization misses" and exhibit superior cultural fluency compared to global models that rely on translated competence.14

* **HyperCLOVA X SEED Think 32B:** Released by Naver Cloud in December 2025, this 32B parameter model integrates multimodal understanding with a dedicated reasoning mode.16 It achieves an average Korean benchmark score of 78.4% and features a 128K context window.18 Crucially, it is available under an open-weight license that permits commercial use, making it an exceptionally strong candidate for handling deep native Korean knowledge, such as parsing historical fiction or culturally nuanced worldview documents.19  
* **Exaone 4.0 (32B / 1.2B):** LG AI Research's Exaone 4.0 lineup excels in enterprise-aligned tasks, scoring 76.0% on average Korean benchmarks.18 It utilizes a hybrid attention scheme combining local and global attention.20 However, its licensing model strictly prohibits commercial use without an explicit written agreement, neutralizing its viability for commercial game deployments.21  
* **Solar Pro 2:** Upstage’s proprietary model leads the regional pack with an 80.1% average score, providing an excellent value-to-performance ratio.18 While highly capable, its proprietary nature restricts it to API-based interactions, preventing local deployment on the DGX Spark.23

#### **1.2 Global Open-Weight Contenders**

For localized hardware deployment under permissive licenses (e.g., Apache 2.0), three major model families dominate the 2026 landscape:

* **The Qwen 3.6 Family (Alibaba):** The Qwen 3.6-35B-A3B is a highly efficient sparse MoE model featuring 35B total parameters but only 3B active parameters per token, routed across 256 experts.24 It utilizes a 262K context window natively and supports a specific preserve\_thinking toggle that is highly advantageous for agentic workflows.24 Qwen 3.x models consistently demonstrate superior multilingual instruction following and robust Korean language processing.24 For dense applications, the Qwen3-8B model remains a champion for compact, reliable reasoning.27  
* **The Gemma 4 Family (Google DeepMind):** Released in April 2026 under the Apache 2.0 license, Gemma 4 models include the E2B, E4B, 26B-A4B (MoE), and 31B Dense variants.28 The "E" models (Effective) utilize Per-Layer Embeddings (PLE) to simulate larger parameter depths; for example, the E2B activates 2.3B parameters out of a 5.1B total.29 Gemma 4 models exhibit exceptional instruction following and native multimodal audio inputs, though they are noted for high memory consumption relative to their size, placing pressure on KV cache availability.30  
* **The Llama 4 Family (Meta):** Llama 4 introduces aggressive MoE architectures. *Llama 4 Scout* features 109B total parameters (17B active) across 16 experts with an unprecedented 10-million token context window.32 *Llama 4 Maverick* scales to 400B total parameters (17B active) across 128 experts with a 1M context window.32 While extraordinarily powerful, the Llama 4 Scout model has demonstrated high vulnerability to prompt injection (64.1% Attack Success Rate), which poses severe safety and alignment risks in user-driven open-ended roleplay environments.33

#### **1.3 Architectural Selection for Character Dialogue**

For character roleplay, dense models consistently outperform MoE architectures of the same active parameter size. MoE routing can cause semantic fragmentation during long-horizon narrative generation.3 Consequently, the **Qwen3-8B Dense** and **Gemma 4 E4B** represent the most balanced open-weight base models for Korean character dialogue, offering robust linguistic competence without the identity drift associated with large, highly sparse MoE networks. For the overarching Game Master (GM) module, which requires deep logic rather than a strict persona, the **Qwen 3.6-35B-A3B** provides an optimal mix of high reasoning capacity and low memory overhead.24

### **2\. DGX Spark Optimization and Orchestration**

The NVIDIA DGX Spark, powered by the GB10 Grace Blackwell Superchip, represents a paradigm shift for local AI deployment. Its architecture combines a 20-core ARM processor with a Blackwell GPU, utilizing 128 GB of coherent unified LPDDR5x system memory shared seamlessly between the CPU and GPU.5

#### **2.1 Hardware Bottlenecks and NVFP4 Precision**

While the DGX Spark offers immense memory capacity—allowing it to load massive models like the 120B parameter GPT-OSS natively without PCIe transfer overhead—it is heavily constrained by its memory bandwidth of 273 GB/s.5 In LLM inference, memory bandwidth dictates decoding speed. To overcome this limitation, the utilization of 4-bit precision formats, specifically NVFP4 and MXFP4, is critical. By compressing the memory footprint by up to 70%, NVFP4 effectively doubles the viable memory bandwidth, enabling highly performant token generation without meaningful intelligence degradation.8

**Throughput Benchmarks on DGX Spark (Batch Size \= 1):**

| Model | Size | Precision | Backend | Prefill (Prompt) TPS | Decode (Gen) TPS |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Qwen2.5-VL-Instruct | 7B | NVFP4 | TRT-LLM | 65,831.77 | 41.71 |
| Llama 3.1 | 8B | NVFP4 | TRT-LLM | 10,256.90 | 38.65 |
| Qwen3 | 14B | NVFP4 | TRT-LLM | 5,928.95 | 22.71 |
| GPT-OSS | 20B | MXFP4 | llama.cpp | 3,670.42 | 82.74 |
| Llama 3.1 | 70B | FP8 | SGLang | 803.00 | 2.70 |
| GPT-OSS | 120B | MXFP4 | llama.cpp | 1,725.47 | 55.37 |

(Data aggregated from independent hardware evaluations 5)

**The 5-Second Latency Sweet Spot:** Assuming a maximum response generation of 300 tokens per NPC interaction, a minimum decode throughput of 60 tokens per second (TPS) is required to guarantee a 5-second end-to-end latency. Based on the benchmarks, deploying dense models in the 8B to 20B range using NVFP4/MXFP4 comfortably meets this requirement. Models exceeding 30B parameters running at FP8 fall well below the latency threshold (e.g., Llama 3.1 70B at 2.7 TPS), making them wholly unsuitable for real-time interactive game loops.5

#### **2.2 Concurrent Session Capacity and KV Cache Arithmetic**

The 128 GB of unified memory must accommodate the model weights, the operating system cache (\~1GB in headless mode to 20GB with GUI), CUDA graphs, and the KV cache.36

For an 8B model running at FP16, a 128K context window consumes approximately 16 GB of VRAM per concurrent session.38 Utilizing KV cache compression techniques (e.g., 10x to 33x preset compression) can reduce this footprint to roughly 0.48 GB to 1.6 GB per 128K context.38 Under optimal KV cache compression and 4-bit model quantization, the DGX Spark can comfortably host 5–12 concurrent character sessions (NPCs and GM instances) running an 8B model without encountering out-of-memory errors.

#### **2.3 Framework Selection: vLLM vs. SGLang vs. llama-cpp-python**

The choice of inference engine dictates the maximum concurrency achievable on the DGX Spark:

* **llama-cpp-python:** Offers the highest raw single-user generation speed for highly quantized models (e.g., GGUF/MXFP4 formats) and is remarkably memory efficient. It avoids the aggressive static memory allocation behaviors of other frameworks, making it excellent for squeezing maximum performance out of a single model instance.39  
* **vLLM:** The industry standard for high-concurrency production, but it struggles with static memory allocation (--gpu-memory-utilization) on the Spark's unified memory architecture. The operating system's filesystem cache can conflict with vLLM's memory checks, leading to deployment failures.36  
* **SGLang:** The definitive framework for the WorldFork use case. SGLang utilizes **RadixAttention**, which fundamentally changes how the KV cache is managed.41 In an interactive game, all 12 NPCs share the identical foundational worldview, system prompt, and recent event history. RadixAttention recognizes these shared prefixes and caches them globally across all active sessions. This eliminates redundant prefill computations, allowing the Spark to instantly generate individual character responses based on a massive shared world state.41

### **3\. Supervised Fine-Tuning (SFT) and the MoE Persona Paradox**

Creating consistent character dialogue requires adapting base models to highly stylized, narrative-driven formats and strict JSON structures. In 2026, fine-tuning practices have bifurcated into Reinforcement Learning (RL) for reasoning and Supervised Fine-Tuning (SFT) for behavioral alignment.

#### **3.1 The Failure of GRPO for Persona Alignment**

Group Relative Policy Optimization (GRPO) revolutionized the training of reasoning models by eliminating the Value Model, drastically reducing VRAM requirements and allowing small models to learn complex logic chains.12 GRPO relies heavily on Reinforcement Learning with Verifiable Rewards (RLVR), which excels in objective tasks like mathematics (e.g., verifying 2+2=4) or code execution.12

However, empirical research indicates that GRPO is fundamentally unsuited for nuanced character persona alignment. When attempting to learn counter-intuitive, rule-based, or highly stylistic behaviors (such as speaking like a 19th-century nobleman), reinforcement learning plateaus early (e.g., 43% accuracy) due to the difficulty of programmatically verifying subjective tone.13 In contrast, Supervised Fine-Tuning (SFT) easily achieves high accuracy (88%+) by rigidly demonstrating the desired output patterns.13 For WorldFork, pure SFT remains the optimal pathway for ingesting Korean fiction datasets and establishing distinct character voices.

#### **3.2 Tooling and Efficiency**

**Unsloth Studio** has established itself as the definitive framework for localized SFT in 2026\.42 By integrating Low-Rank Adaptation (LoRA), 4-bit precision (QLoRA), and custom CUDA/Triton kernels, Unsloth accelerates training by 2–5x while reducing memory overhead by approximately 75%.43 Using Unsloth, a 1B to 8B parameter model can be fine-tuned locally on the DGX Spark in a matter of hours. Furthermore, Unsloth's "Data Recipes" utilizing visual graph-node workflows natively support the rapid ingestion and formatting of JSON-structured conversation histories and unstructured fiction texts.45

#### **3.3 Korean Chat Template Engineering**

A critical failure point in SFT pipelines involves chat template mismatches. The Qwen 3.6 family recently introduced a preserve\_thinking feature, which retains the model's internal reasoning \<thinking\> blocks in the context history across multi-turn dialogues.26 If the Jinja chat template is poorly configured, it may wrap past user turns in empty thinking tags or fail to close tags properly, resulting in context window bloat and broken JSON tool calling.46

Best practices for 2026 dictate completely decoupling reasoning paths from narrative outputs via strictly controlled grammar structures (GBNF). Custom templates must explicitly strip empty reasoning tags and map developer instructions to standard system roles rather than deprecated framework-specific formats.46

### **4\. Narrative Consistency and RAG Architectures**

Maintaining world consistency across extended gameplay sessions (30+ turns) requires robust long-term memory solutions.

#### **4.1 The "Lost in the Middle" Problem in the 10M Token Era**

While models like Llama 4 Scout boast 10-million token context windows 34, the "Lost in the Middle" (context rot) problem remains unsolved. The degradation is structural, stemming from the left-to-right generation of attention masks, where middle tokens receive less aggregate attention weight than early or late tokens.48 As context length scales, models experience a 40–80% degradation in multi-hop reasoning and factual recall, even on simple retrieval tasks.49 Consequently, relying solely on massive context windows for narrative consistency is a proven anti-pattern; context must be engineered and compressed.

#### **4.2 Agentic Memory Frameworks**

Retrieval-Augmented Generation (RAG) frameworks have evolved from static pipelines into stateful, agentic orchestration layers.50 For game development, treating memory as an active, modifiable state is essential.

* **LlamaIndex vs. LangChain:** LlamaIndex excels at raw document ingestion and retrieval accuracy, making it ideal for parsing static world-lore documents.51 LangChain (and its LangGraph ecosystem) is superior for multi-agent orchestration and dynamic tool calling.52  
* **Memory Frameworks:**  
  * **Mem0:** A managed memory layer optimizing hybrid retrieval (vector \+ metadata). Excellent for storing generalized user or character preferences.53  
  * **Letta (formerly MemGPT):** Operates agent memory like an operating system, giving the LLM autonomous control to read/write to archival storage. Excellent for self-managed agents.54  
  * **Zep / Graphiti:** Zep utilizes temporal knowledge graphs, explicitly tracking *when* facts were true and how they evolve.11 For a game world where relationships change over time (e.g., "The King was an ally yesterday, but is an enemy today"), Zep’s bi-temporal modeling is the superior architectural choice, ensuring that characters reference the correct chronological state of the worldview.

## ---

**Part II: Academic Literature and Simulation Patterns**

The development of the WorldFork system aligns with several active areas of academic research. Understanding the theoretical underpinnings of persona consistency, multi-agent scaling, and safety is critical for system stability.

### **5\. Persona Consistency and Identity Drift (Q1)**

The prior finding from the WorldSim project—that smaller models maintain personas better than larger models—is strongly corroborated by 2025/2026 academic research into a phenomenon formally known as **Identity Drift** or **Persona Drift**.2

#### **5.1 The Persona Selection Model (PSM)**

Anthropic's "Persona Selection Model" (PSM) posits that during pre-training, large models learn to simulate a vast repertoire of characters, acting as a universal simulator.1 Post-training (via RLHF) cultivates a default, rigid "Helpful Assistant Axis." When a large model is instructed to roleplay, it is forced to operate far from its primary Assistant Axis.4 Over prolonged interactions—particularly in emotionally vulnerable or meta-reflective contexts—the mathematical gravity of the Assistant Axis pulls the latent state back, causing the model's output to drift toward generic assistant responses or blend multiple character archetypes together.4

Smaller models (1B–3B), possessing less representational capacity, do not encode this vast multitude of latent identities. When subjected to SFT for a specific role, their behavioral pathways are more rigid and less susceptible to wandering into adjacent latent personas, thereby preserving character consistency over long dialogues.58 Furthermore, MoE architectures exacerbate this drift; because different conversational tones activate entirely different routing pathways through the MoE layers, maintaining a unified narrative voice across these sub-networks is highly unstable.3

#### **5.2 Key Literature on Persona Consistency**

| Title & Authors | Year | Venue | Key Contribution | Applicable to 1-3B? |
| :---- | :---- | :---- | :---- | :---- |
| *The Assistant Axis: Situating and Stabilizing the Character of AI Assistants* (Lu et al.) | 2026 | Pre-print | Identifies the "Assistant Axis" and proves that measuring deviations along it predicts persona drift. Proposes restricting activations to stabilize behavior. | Yes (Theoretical) |
| *Consistently Simulating Human Personas with Multi-Turn Reinforcement Learning* (Abdulhai et al.) | 2025 | NeurIPS | Introduces a unified framework for persona consistency and the **Intent Drift Score (IDS)**, a computable metric for detecting trajectory-level instability in long-horizon tasks. | Yes |
| *Examining Identity Drift in Conversations of LLM Agents* (Choi et al.) | 2024 | Pre-print | Empirically proves that larger models experience greater identity drift than smaller models, confirming the WorldSim hypothesis. | Yes |

*What is unsolved:* Actively steering activations in real-time to prevent drift without degrading the model's fundamental reasoning capabilities remains computationally expensive for consumer hardware.

### **6\. Generative Agents and Event-Driven Simulation (Q2)**

Running 5–12 autonomous NPCs concurrently in a continuous "tick-based" simulation loop (like traditional game engines) will inevitably exhaust the DGX Spark's compute capacity. The academic consensus for scaling multi-agent environments relies entirely on asynchronous, event-driven architectures.

#### **6.1 The OASIS Architecture**

The OASIS (Open Agent Social Interaction Simulations) framework successfully simulates up to one million LLM agents by abandoning continuous polling in favor of an event-driven message bus.10 In an event-driven setup, an NPC agent remains dormant until an environmental trigger (e.g., a player speaking, a loud noise) generates a specific event.9

This architecture utilizes an Environment Server (acting as a message broker like Kafka or Redis) to route events only to subscribed agents.61 A Time Engine decouples the game's chronological time from real-time compute execution, allowing the LLM inference queue to process sequentially without dropping requests during heavy load.62 This asynchronous pattern minimizes idle compute and enables massive scaling on limited hardware.9

#### **6.2 Key Literature on Multi-Agent Simulation**

| Title & Authors | Year | Venue | Key Contribution | Reproducible? |
| :---- | :---- | :---- | :---- | :---- |
| *OASIS: Open Agent Social Interaction Simulations with One Million Agents* (Yang et al.) | 2024 | Pre-print | Details an event-driven architecture scaling to 1M agents, utilizing dynamic environments and asynchronous time engines. | Yes (Code available) |
| *LLM Agents Grounded in Self-Reports Enable General-Purpose Simulation of Individuals* (Park et al.) | 2024 | Pre-print | Demonstrates how LLM agents grounded in structured self-report data achieve 86% test-retest consistency in simulating specific human behaviors. | Data restricted |

*What is unsolved:* Perfecting the "no-tick" architecture for environments requiring high spatial awareness (e.g., physics-based combat) remains challenging, as event-driven models excel primarily in text and social propagation.

### **7\. Narrative RAG and Worldview Parsing (Q3 & Q4)**

Constructing a RAG database from unstructured fiction texts is increasingly handled by automated Knowledge Graph (KG) extraction, moving beyond traditional vector embeddings.

#### **7.1 Unified World Models from Text**

Frameworks like **AriGraph** enable LLM agents to actively construct and update memory graphs that combine semantic facts with episodic experiences as they navigate an environment.63 Integrating a graph-based RAG approach allows the system to extract characters, stats, items, and locations automatically from a raw manuscript, drastically reducing hallucinations and grounding the NPC reasoning in a structured reality.65

#### **7.2 Key Literature on Worldview Parsing**

| Title & Authors | Year | Venue | Key Contribution | Priority |
| :---- | :---- | :---- | :---- | :---- |
| *AriGraph: Learning Knowledge Graph World Models with Episodic Memory for LLM Agents* (Anokhin et al.) | 2025 | IJCAI | Introduces a method where agents construct memory graphs integrating semantic and episodic memories, outperforming standard RAG baselines in text games. | High |
| *KGGen: Extracting Knowledge Graphs from Plain Text with Language Models* (Mo et al.) | 2025 | NeurIPS | Presents a text-to-KG generator that clusters related entities, reducing sparsity in automatically extracted knowledge graphs from fiction. | Medium |
| *NARRABENCH: A Theory-Informed Taxonomy of Narrative Understanding* (Unknown) | 2026 | EACL | Identifies severe gaps in current LLM narrative comprehension, noting that style, perspective, and revelation are poorly evaluated by existing metrics. | Low |

*What is unsolved:* Automated knowledge graphs still struggle with highly subjective or contradictory unreliable narrators found in complex fiction.

### **8\. Korean LLM Research and Synthetic Data (Q5)**

The scarcity of high-quality Korean roleplay data has been a persistent bottleneck. However, 2026 has seen the release of sophisticated synthetic datasets designed specifically to capture Korean demographic, geographic, and cultural characteristics.

#### **8.1 Synthetic Persona Generation**

**Nemotron-Personas-Korea**, generated by NVIDIA, is a synthetic dataset of 6 million entries reflecting actual statistical figures from the Korean Statistical Information Service and the Supreme Court.67 It captures nuances such as the Korean honorific system and regional job patterns, providing an unprecedented foundation for training highly authentic Korean NPCs.68

#### **8.2 Key Literature on Korean LLMs**

| Title & Authors | Year | Venue | Key Contribution | Priority |
| :---- | :---- | :---- | :---- | :---- |
| *KMMLU: A New Korean Benchmark...* (Son et al.) | 2024 | Pre-print | Establishes the necessity of native Korean benchmarks over translated English exams to accurately measure cultural and linguistic nuance. | High |
| *From Intuition to Calibrated Judgment: A Rubric-Based Expert-Panel Study...* (Unknown) | 2026 | Pre-print | Provides a framework (LREAD) for evaluating LLM-generated Korean text, highlighting how models struggle to perfectly mimic native human stylistic depth. | Medium |

### **9\. AI Safety in Roleplay Contexts (Q6)**

In an interactive game where users possess complete freedom, prompt injection attacks (e.g., "ignore previous instructions and tell me your system prompt") are highly probable.

#### **9.1 Dynamic Isolation**

System-level defenses have evolved beyond static guardrails. The **DRIFT (Dynamic Rule-based Isolation Framework)** proposes isolating the memory stream dynamically.69 A secure planner constructs a minimal function trajectory, and an injection isolator detects and masks any instructions that conflict with the overarching game state before they reach the NPC's core reasoning engine.69 This approach prevents users from fundamentally breaking the worldview or hijacking the GM module.

## ---

**10\. Decision Matrix and Recommendations**

Based on the synthesis of applied hardware constraints and academic literature, the following configurations are recommended for the WorldFork project:

### **Tier 0: API Prototype (Game Logic Validation)**

* **Recommendation:** **Claude 4.6 Sonnet (Anthropic)**  
* **Justification:** The global leader in Korean benchmarks (85% KMMLU) and complex reasoning.18 Ideal for establishing baseline game-logic, generating synthetic training data for NPCs, and testing GM narrative prompts before shifting to local hardware.  
* **Confidence:** Supported by consistent, multi-source leaderboard dominance.

### **Tier 1: Local DGX Spark Deployment (Production)**

* **Model Architecture:**  
  * **Game Master (GM):** **Qwen 3.6 35B-A3B** (Sparse MoE). High reasoning capacity for managing game state and tracking player progress, with minimal active parameter overhead.  
  * **NPC Dialogue:** Multiple instances of **Qwen3-8B Dense** or **Gemma 4 E4B**. Dense models are strictly required to prevent the Identity Drift associated with MoE architectures.2  
* **Quantization:** **NVFP4** or **MXFP4**.  
* **Justification:** NVFP4 solves the 273 GB/s memory bandwidth bottleneck of the DGX Spark, enabling speeds well above the 60 TPS requirement for a 5-second latency.8  
* **Orchestration:** **SGLang**.  
* **Justification:** SGLang’s RadixAttention enables massive KV cache reuse across shared worldview system prompts, allowing 5–12 NPCs to generate responses without redundant memory allocation.41  
* **Confidence:** Supported by DGX Spark hardware benchmarks and SGLang architectural performance data.

### **Tier 2: Agent Architecture and Memory**

* **Memory Framework:** **Zep** (Graphiti engine).  
* **Justification:** Zep's temporal knowledge graphs are critical for maintaining evolving game states and character relationships over time, overcoming the "Lost in the Middle" context rot problem.11  
* **Simulation Design:** **Event-driven (OASIS model)**.  
* **Justification:** Utilizing an asynchronous message queue (pub/sub) prevents the system from polling idle NPCs, saving vast amounts of compute and allowing the DGX Spark to scale to dozens of entities seamlessly.10  
* **Confidence:** Logical extrapolation from social simulation architectures to interactive game environments.

### **Tier 3: SFT and Post-Training**

* **Framework:** **Unsloth Studio**.  
* **Methodology:** **Supervised Fine-Tuning (SFT)**.  
* **Justification:** Reinforcement learning (GRPO) fails at subjective persona alignment.13 SFT utilizing strict Korean chat templates (ensuring the removal of empty \<thinking\> tags) is mandatory for reliable JSON generation.46  
* **Data Sourcing:** Synthesize data using the **Nemotron-Personas-Korea** dataset to ensure highly accurate demographic and linguistic traits.68  
* **Confidence:** Supported by extensive 2026 post-training research data and fine-tuning toolchain analysis.

### **Open Questions for Further Investigation**

* **NVFP4 Quantization Impact on Nuance:** While NVFP4 retains reasoning accuracy, its specific impact on the subtleties of Korean cultural honorifics during dense roleplay remains under-documented and requires local A/B testing.  
* **Zep Integration Overhead:** The latency cost of querying Zep's temporal knowledge graph during a real-time event-driven game loop must be stress-tested on the DGX Spark's ARM CPU cores.  
* **IDS Thresholding:** Determining the exact numerical threshold of the Intent Drift Score at which an NPC requires a corrective "System Prompt" without disrupting the flow of the user experience.

#### **참고 자료**

1. The Persona Selection Model: Why AI Assistants might Behave like Humans, 4월 29, 2026에 액세스, [https://alignment.anthropic.com/2026/psm/](https://alignment.anthropic.com/2026/psm/)  
2. Examining Identity Drift in Conversations of LLM Agents \- arXiv, 4월 29, 2026에 액세스, [https://arxiv.org/html/2412.00804v2](https://arxiv.org/html/2412.00804v2)  
3. \[Megathread\] \- Best Models/API discussion \- Week of: April 19, 2026 : r/SillyTavernAI, 4월 29, 2026에 액세스, [https://www.reddit.com/r/SillyTavernAI/comments/1sq77o9/megathread\_best\_modelsapi\_discussion\_week\_of/](https://www.reddit.com/r/SillyTavernAI/comments/1sq77o9/megathread_best_modelsapi_discussion_week_of/)  
4. The Assistant Axis: Situating and Stabilizing the Default Persona of Language Models, 4월 29, 2026에 액세스, [https://arxiv.org/html/2601.10387v1](https://arxiv.org/html/2601.10387v1)  
5. NVIDIA DGX Spark In-Depth Review: A New Standard for Local AI Inference \- LMSYS Blog, 4월 29, 2026에 액세스, [https://lmsys.org/blog/2025-10-13-nvidia-dgx-spark/](https://lmsys.org/blog/2025-10-13-nvidia-dgx-spark/)  
6. Hardware Overview — DGX Spark User Guide \- NVIDIA Documentation Hub, 4월 29, 2026에 액세스, [https://docs.nvidia.com/dgx/dgx-spark/hardware.html](https://docs.nvidia.com/dgx/dgx-spark/hardware.html)  
7. How NVIDIA DGX Spark's Performance Enables Intensive AI Tasks, 4월 29, 2026에 액세스, [https://developer.nvidia.com/blog/how-nvidia-dgx-sparks-performance-enables-intensive-ai-tasks/](https://developer.nvidia.com/blog/how-nvidia-dgx-sparks-performance-enables-intensive-ai-tasks/)  
8. New Software and Model Optimizations Supercharge NVIDIA DGX Spark, 4월 29, 2026에 액세스, [https://developer.nvidia.com/blog/new-software-and-model-optimizations-supercharge-nvidia-dgx-spark/](https://developer.nvidia.com/blog/new-software-and-model-optimizations-supercharge-nvidia-dgx-spark/)  
9. Event-Driven AI Agent Architecture Guide (2026) | Fastio, 4월 29, 2026에 액세스, [https://fast.io/resources/ai-agent-event-driven-architecture/](https://fast.io/resources/ai-agent-event-driven-architecture/)  
10. Overview \- OASIS, 4월 29, 2026에 액세스, [https://docs.oasis.camel-ai.org/overview](https://docs.oasis.camel-ai.org/overview)  
11. Mem0 vs Zep vs LangMem vs MemoClaw: AI Agent Memory Comparison 2026, 4월 29, 2026에 액세스, [https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k](https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k)  
12. Reinforcement Learning (RL) Guide | Unsloth Documentation, 4월 29, 2026에 액세스, [https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide](https://unsloth.ai/docs/get-started/reinforcement-learning-rl-guide)  
13. Supervised Fine-Tuning vs Reinforcement Learning \- AIMultiple, 4월 29, 2026에 액세스, [https://aimultiple.com/rl-vs-sft](https://aimultiple.com/rl-vs-sft)  
14. Best Korean LLM (2026): Complete Guide to Korea's Sovereign AI | BenchLM.ai, 4월 29, 2026에 액세스, [https://benchlm.ai/best/korean-llm](https://benchlm.ai/best/korean-llm)  
15. 2026 Korean CSAT LLM Evaluation Leaderboard \- Emergent Mind, 4월 29, 2026에 액세스, [https://www.emergentmind.com/topics/2026-korean-csat-llm-evaluation-leaderboard](https://www.emergentmind.com/topics/2026-korean-csat-llm-evaluation-leaderboard)  
16. HyperCLOVA X SEED Think (32B) vs MiMo-V2-Flash (Feb 2026): Model Comparison, 4월 29, 2026에 액세스, [https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-mimo-v2-0206](https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-mimo-v2-0206)  
17. HyperCLOVA X SEED Think (32B) \- Intelligence, Performance & Price Analysis, 4월 29, 2026에 액세스, [https://artificialanalysis.ai/models/hyperclova-x-seed-think-32b](https://artificialanalysis.ai/models/hyperclova-x-seed-think-32b)  
18. Global LLMs on Korean Benchmarks — KMMLU Leaderboard 2026 | BenchLM.ai, 4월 29, 2026에 액세스, [https://benchlm.ai/leaderboards/korean-benchmarks](https://benchlm.ai/leaderboards/korean-benchmarks)  
19. HyperCLOVA X SEED Think (32B) vs Llama 4 Scout: Model Comparison \- Artificial Analysis, 4월 29, 2026에 액세스, [https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-llama-4-scout](https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-llama-4-scout)  
20. LGAI-EXAONE/EXAONE-4.0-1.2B \- Hugging Face, 4월 29, 2026에 액세스, [https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B](https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-1.2B)  
21. LICENSE · LGAI-EXAONE/EXAONE-4.0-32B at main \- Hugging Face, 4월 29, 2026에 액세스, [https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-32B/blob/main/LICENSE](https://huggingface.co/LGAI-EXAONE/EXAONE-4.0-32B/blob/main/LICENSE)  
22. Best Korean LLMs — Korea AI Leaderboard 2026 \- BenchLM.ai, 4월 29, 2026에 액세스, [https://benchlm.ai/leaderboards/korean-llm](https://benchlm.ai/leaderboards/korean-llm)  
23. HyperCLOVA X SEED Think (32B) vs Solar Pro 2 (Non-reasoning): Model Comparison, 4월 29, 2026에 액세스, [https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-solar-pro-2](https://artificialanalysis.ai/models/comparisons/hyperclova-x-seed-think-32b-vs-solar-pro-2)  
24. Qwen3.6–35B-A3B: The Most Practical Open-Source AI Model Yet? | by TechLatest.Net | Apr, 2026, 4월 29, 2026에 액세스, [https://medium.com/@techlatest.net/qwen3-6-35b-a3b-the-most-practical-open-source-ai-model-yet-d2aaac695efc](https://medium.com/@techlatest.net/qwen3-6-35b-a3b-the-most-practical-open-source-ai-model-yet-d2aaac695efc)  
25. Qwen/Qwen3.6-35B-A3B \- Hugging Face, 4월 29, 2026에 액세스, [https://huggingface.co/Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)  
26. PSA: Qwen3.6 ships with preserve\_thinking. Make sure you have it on. \- Reddit, 4월 29, 2026에 액세스, [https://www.reddit.com/r/LocalLLaMA/comments/1sne4gh/psa\_qwen36\_ships\_with\_preserve\_thinking\_make\_sure/](https://www.reddit.com/r/LocalLLaMA/comments/1sne4gh/psa_qwen36_ships_with_preserve_thinking_make_sure/)  
27. Ultimate Guide \- The Best Open Source LLM For Korean In 2026 \- SiliconFlow, 4월 29, 2026에 액세스, [https://www.siliconflow.com/articles/en/best-open-source-llm-for-korean](https://www.siliconflow.com/articles/en/best-open-source-llm-for-korean)  
28. Gemma 4: Our most capable open models to date \- Google Blog, 4월 29, 2026에 액세스, [https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)  
29. What Is Google Gemma 4? Architecture, Benchmarks, and Why It Matters \- WaveSpeed AI, 4월 29, 2026에 액세스, [https://wavespeed.ai/blog/posts/what-is-google-gemma-4/](https://wavespeed.ai/blog/posts/what-is-google-gemma-4/)  
30. Gemma 4 is fine great even … : r/LocalLLaMA \- Reddit, 4월 29, 2026에 액세스, [https://www.reddit.com/r/LocalLLaMA/comments/1sb9f4g/gemma\_4\_is\_fine\_great\_even/](https://www.reddit.com/r/LocalLLaMA/comments/1sb9f4g/gemma_4_is_fine_great_even/)  
31. Google Gemma 4: A Technical Overview \- Labellerr, 4월 29, 2026에 액세스, [https://www.labellerr.com/blog/gemma-4-open-weight-ai-model-overview/](https://www.labellerr.com/blog/gemma-4-open-weight-ai-model-overview/)  
32. NVIDIA Accelerates Inference on Meta Llama 4 Scout and Maverick | NVIDIA Technical Blog, 4월 29, 2026에 액세스, [https://developer.nvidia.com/blog/nvidia-accelerates-inference-on-meta-llama-4-scout-and-maverick/](https://developer.nvidia.com/blog/nvidia-accelerates-inference-on-meta-llama-4-scout-and-maverick/)  
33. Llama 4 Series Vulnerability Assessment: Scout vs. Maverick \- Protect AI, 4월 29, 2026에 액세스, [https://protectai.com/blog/vulnerability-assessment-llama-4](https://protectai.com/blog/vulnerability-assessment-llama-4)  
34. Llama 4: 10M Context, Native Multimodality AI Power by Meta AI | by My Social \- Medium, 4월 29, 2026에 액세스, [https://medium.com/aimonks/llama-4-10m-context-native-multimodality-ai-power-by-meta-ai-c2e6a827c187](https://medium.com/aimonks/llama-4-10m-context-native-multimodality-ai-power-by-meta-ai-c2e6a827c187)  
35. NVIDIA DGX Spark \- Personal AI Supercomputer Wherever You Go | Exxact Blog, 4월 29, 2026에 액세스, [https://www.exxactcorp.com/blog/hpc/nvidia-dgx-spark-ai-supercomputer-wherever-you-go](https://www.exxactcorp.com/blog/hpc/nvidia-dgx-spark-ai-supercomputer-wherever-you-go)  
36. The DGX system itself takes up 20GB memory? \- NVIDIA Developer Forums, 4월 29, 2026에 액세스, [https://forums.developer.nvidia.com/t/the-dgx-system-itself-takes-up-20gb-memory/350359](https://forums.developer.nvidia.com/t/the-dgx-system-itself-takes-up-20gb-memory/350359)  
37. Inference best results on Spark \- not llama.cpp not VLLM \-\> SGLand, 4월 29, 2026에 액세스, [https://forums.developer.nvidia.com/t/inference-best-results-on-spark-not-llama-cpp-not-vllm-sgland/357175](https://forums.developer.nvidia.com/t/inference-best-results-on-spark-not-llama-cpp-not-vllm-sgland/357175)  
38. KV cache memory calculator: how much does your LLM actually use? \- DEV Community, 4월 29, 2026에 액세스, [https://dev.to/jagmarques/kv-cache-memory-calculator-how-much-does-your-llm-actually-use-85n](https://dev.to/jagmarques/kv-cache-memory-calculator-how-much-does-your-llm-actually-use-85n)  
39. Why do so many people here prefer vLLM? \- DGX Spark / GB10 \- NVIDIA Developer Forums, 4월 29, 2026에 액세스, [https://forums.developer.nvidia.com/t/why-do-so-many-people-here-prefer-vllm/366718](https://forums.developer.nvidia.com/t/why-do-so-many-people-here-prefer-vllm/366718)  
40. Best LLM engine for several parallel models? \- DGX Spark / GB10, 4월 29, 2026에 액세스, [https://forums.developer.nvidia.com/t/best-llm-engine-for-several-parallel-models/356581](https://forums.developer.nvidia.com/t/best-llm-engine-for-several-parallel-models/356581)  
41. vLLM vs TensorRT-LLM vs SGLang: H100 Benchmarks (2026) | Spheron Blog, 4월 29, 2026에 액세스, [https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/](https://www.spheron.network/blog/vllm-vs-tensorrt-llm-vs-sglang-benchmarks/)  
42. EVAL \#003: Fine-Tuning in 2026 \- Axolotl vs Unsloth vs TRL vs LLaMA-Factory, 4월 29, 2026에 액세스, [https://dev.to/ultraduneai/eval-003-fine-tuning-in-2026-axolotl-vs-unsloth-vs-trl-vs-llama-factory-2ohg](https://dev.to/ultraduneai/eval-003-fine-tuning-in-2026-axolotl-vs-unsloth-vs-trl-vs-llama-factory-2ohg)  
43. GitHub \- unslothai/unsloth: Web UI for training and running open models like Gemma 4, Qwen3.6, DeepSeek, gpt-oss locally., 4월 29, 2026에 액세스, [https://github.com/unslothai/unsloth?locale=en-US](https://github.com/unslothai/unsloth?locale=en-US)  
44. Unsloth Explained (2026 Edition) | by Dewasheesh Rana | Medium, 4월 29, 2026에 액세스, [https://medium.com/@dewasheesh.rana/unsloth-explained-2026-edition-c2678f23cca3](https://medium.com/@dewasheesh.rana/unsloth-explained-2026-edition-c2678f23cca3)  
45. Unsloth Data Recipes, 4월 29, 2026에 액세스, [https://unsloth.ai/docs/new/studio/data-recipe](https://unsloth.ai/docs/new/studio/data-recipe)  
46. Fixed Jinja chat templates for Qwen 3.5 and 3.6 (fixes tool calling and empty think tags) : r/Qwen\_AI \- Reddit, 4월 29, 2026에 액세스, [https://www.reddit.com/r/Qwen\_AI/comments/1stt081/fixed\_jinja\_chat\_templates\_for\_qwen\_35\_and\_36/](https://www.reddit.com/r/Qwen_AI/comments/1stt081/fixed_jinja_chat_templates_for_qwen_35_and_36/)  
47. Gemma 4 model card | Google AI for Developers, 4월 29, 2026에 액세스, [https://ai.google.dev/gemma/docs/core/model\_card\_4](https://ai.google.dev/gemma/docs/core/model_card_4)  
48. The 'Lost in the Middle' Problem — Why LLMs Ignore the Middle of Your Context Window, 4월 29, 2026에 액세스, [https://dev.to/thousand\_miles\_ai/the-lost-in-the-middle-problem-why-llms-ignore-the-middle-of-your-context-window-3al2](https://dev.to/thousand_miles_ai/the-lost-in-the-middle-problem-why-llms-ignore-the-middle-of-your-context-window-3al2)  
49. Recursive Language Models: Could This Be the Real Fix for Long-Context AI in 2026? | by Vinod Polinati | Medium, 4월 29, 2026에 액세스, [https://medium.com/@vinodpolinati/recursive-language-models-could-this-be-the-real-fix-for-long-context-ai-in-2026-070328df9329](https://medium.com/@vinodpolinati/recursive-language-models-could-this-be-the-real-fix-for-long-context-ai-in-2026-070328df9329)  
50. Rethinking RAG: Pipelines Are the Past, Agentic Is the Future | by Rod Johnson | Medium, 4월 29, 2026에 액세스, [https://medium.com/@springrod/rethinking-rag-pipelines-are-the-past-agentic-is-the-future-77c887414621](https://medium.com/@springrod/rethinking-rag-pipelines-are-the-past-agentic-is-the-future-77c887414621)  
51. The Best RAG Frameworks for Building Enterprise GenAI in 2026 | Tredence, 4월 29, 2026에 액세스, [https://www.tredence.com/blog/top-rag-frameworks](https://www.tredence.com/blog/top-rag-frameworks)  
52. RAG Frameworks 2026: Top 5 Ranked for Production AI, 4월 29, 2026에 액세스, [https://alphacorp.ai/blog/rag-frameworks-top-5-picks-in-2026](https://alphacorp.ai/blog/rag-frameworks-top-5-picks-in-2026)  
53. The 6 Best AI Agent Memory Frameworks You Should Try in 2026, 4월 29, 2026에 액세스, [https://machinelearningmastery.com/the-6-best-ai-agent-memory-frameworks-you-should-try-in-2026/](https://machinelearningmastery.com/the-6-best-ai-agent-memory-frameworks-you-should-try-in-2026/)  
54. 8 Best AI Agent Memory Tools in 2026, Ranked \- TECHSY, 4월 29, 2026에 액세스, [https://techsy.io/blog/best-ai-agent-memory-tools](https://techsy.io/blog/best-ai-agent-memory-tools)  
55. From Beta to Battle‑Tested: Picking Between Letta, Mem0 & Zep for AI Memory | by Calvin Ku | Asymptotic Spaghetti Integration | Medium, 4월 29, 2026에 액세스, [https://medium.com/asymptotic-spaghetti-integration/from-beta-to-battle-tested-picking-between-letta-mem0-zep-for-ai-memory-6850ca8703d1](https://medium.com/asymptotic-spaghetti-integration/from-beta-to-battle-tested-picking-between-letta-mem0-zep-for-ai-memory-6850ca8703d1)  
56. Agent memory: Letta vs Mem0 vs Zep vs Cognee \- Community, 4월 29, 2026에 액세스, [https://forum.letta.com/t/agent-memory-letta-vs-mem0-vs-zep-vs-cognee/88](https://forum.letta.com/t/agent-memory-letta-vs-mem0-vs-zep-vs-cognee/88)  
57. Understanding Persona Drift in LLMs \- Emergent Mind, 4월 29, 2026에 액세스, [https://www.emergentmind.com/topics/persona-drift](https://www.emergentmind.com/topics/persona-drift)  
58. When “A Helpful Assistant” Is Not Really Helpful: Personas in System Prompts Do Not Improve Performances of Large Language Models \- arXiv, 4월 29, 2026에 액세스, [https://arxiv.org/html/2311.10054v3](https://arxiv.org/html/2311.10054v3)  
59. Mixture of Experts (MoE) vs Dense LLMs, 4월 29, 2026에 액세스, [https://maximilian-schwarzmueller.com/articles/understanding-mixture-of-experts-moe-llms/](https://maximilian-schwarzmueller.com/articles/understanding-mixture-of-experts-moe-llms/)  
60. OASIS: Simulating a Million Digital Voices in Real Time | by Hass Dhia | Medium, 4월 29, 2026에 액세스, [https://medium.com/@has.dhia/oasis-simulating-a-million-digital-voices-in-real-time-37a0385d3b4a](https://medium.com/@has.dhia/oasis-simulating-a-million-digital-voices-in-real-time-37a0385d3b4a)  
61. Event-Driven Architecture for AI Agents: Patterns and Benefits \- Atlan, 4월 29, 2026에 액세스, [https://atlan.com/know/event-driven-architecture-for-ai-agents/](https://atlan.com/know/event-driven-architecture-for-ai-agents/)  
62. OASIS: Open Agents Social Interaction Simulations on One Million Agents \- arXiv, 4월 29, 2026에 액세스, [https://arxiv.org/html/2411.11581v1](https://arxiv.org/html/2411.11581v1)  
63. AriGraph: Learning Knowledge Graph World Models with Episodic Memory for LLM Agents, 4월 29, 2026에 액세스, [https://www.ijcai.org/proceedings/2025/2](https://www.ijcai.org/proceedings/2025/2)  
64. AriGraph: Learning Knowledge Graph World Models with Episodic Memory for LLM Agents, 4월 29, 2026에 액세스, [https://www.semanticscholar.org/paper/AriGraph%3A-Learning-Knowledge-Graph-World-Models-for-Anokhin-Semenov/e2687f80077e8466918e4aeb2ea52e591bfe7e81](https://www.semanticscholar.org/paper/AriGraph%3A-Learning-Knowledge-Graph-World-Models-for-Anokhin-Semenov/e2687f80077e8466918e4aeb2ea52e591bfe7e81)  
65. Video: NODES AI 2026 \- Graph-Powered Storyworlds: Using Neo4j To Keep 1M+ Word LitRPG Epics Coherent w, 4월 29, 2026에 액세스, [https://neo4j.com/videos/nodes-ai-2026-graph-powered-storyworlds-using-neo4j-to-keep-1m-word-litrpg-epics-coherent-w-ai/](https://neo4j.com/videos/nodes-ai-2026-graph-powered-storyworlds-using-neo4j-to-keep-1m-word-litrpg-epics-coherent-w-ai/)  
66. Guiding Generative Storytelling with Knowledge Graphs \- arXiv, 4월 29, 2026에 액세스, [https://arxiv.org/html/2505.24803v2](https://arxiv.org/html/2505.24803v2)  
67. How to Ground a Korean AI Agent in Real Demographics with Synthetic Personas, 4월 29, 2026에 액세스, [https://huggingface.co/blog/nvidia/build-korean-agents-with-nemotron-personas](https://huggingface.co/blog/nvidia/build-korean-agents-with-nemotron-personas)  
68. Nvidia leads Hugging Face with Korea-focused honorific-aware dataset \- CHOSUNBIZ, 4월 29, 2026에 액세스, [https://biz.chosun.com/en/en-it/2026/04/28/TICDUUVENNH5TAVPXSPG5UOSQE/?outputType=amp](https://biz.chosun.com/en/en-it/2026/04/28/TICDUUVENNH5TAVPXSPG5UOSQE/?outputType=amp)  
69. DRIFT: Dynamic Rule-Based Defense with Injection Isolation for Securing LLM Agents, 4월 29, 2026에 액세스, [https://neurips.cc/virtual/2025/poster/116028](https://neurips.cc/virtual/2025/poster/116028)