"""엔진(작품 무관) — ContentPack 인터페이스 + active 싱글톤(A1 콘텐츠팩 분리).

엔진 메커니즘(narrative_gm/scene_effect/gm_session_router/rag/disposition)은 작품 데이터를
ContentPack으로만 소비한다(A1.2부터 파라미터화). 팩 데이터는 service/content/<work>/에 산다.
"""
