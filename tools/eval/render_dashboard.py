"""results.json → 정적 HTML 대시보드 (★ 모델 × 지표 매트릭스 + 그래프 + 샘플).

외부 CDN 0(오프라인 동작). 데이터는 HTML에 임베드. 모델/지표 늘면 자동 반영.
사용: python tools/eval/render_dashboard.py [--data results.json] [--out eval_dashboard.html]
"""
# ruff: noqa: E501  (임베드 HTML/CSS/JS 템플릿 — 긴 줄 불가피)

from __future__ import annotations

import argparse
import json
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent

_HTML = """<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<title>WorldFork 모델 평가 대시보드</title>
<style>
 body{{font-family:system-ui,'Apple SD Gothic Neo',sans-serif;margin:0;background:#0e1c20;color:#dfe;}}
 .wrap{{max-width:1100px;margin:0 auto;padding:24px;}}
 h1{{color:#66e0ff;font-size:1.5rem;}} h2{{color:#9fd;border-bottom:1px solid #2a4;padding-bottom:4px;margin-top:32px;}}
 .sub{{color:#7a9;font-size:.85rem;}}
 table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:.9rem;}}
 th,td{{border:1px solid #244;padding:8px 10px;text-align:center;}}
 th{{background:#13282e;color:#9fd;}} td.m{{text-align:left;font-weight:600;color:#cfe;}}
 .bar{{height:14px;border-radius:3px;background:linear-gradient(90deg,#2a8,#6e0);display:inline-block;vertical-align:middle;}}
 .barwrap{{background:#1a2e33;border-radius:3px;width:120px;display:inline-block;vertical-align:middle;}}
 .num{{font-variant-numeric:tabular-nums;}}
 .good{{color:#6e6;}} .warn{{color:#fb4;}} .bad{{color:#f66;}}
 details{{background:#12242a;border:1px solid #244;border-radius:6px;margin:8px 0;padding:8px 12px;}}
 summary{{cursor:pointer;color:#9fd;font-weight:600;}}
 .samp{{white-space:pre-wrap;background:#0b181c;padding:10px;border-radius:4px;margin:6px 0;line-height:1.55;}}
 .jx{{color:#7c9;font-size:.8rem;}} .tag{{background:#1a3a44;border-radius:4px;padding:1px 6px;font-size:.75rem;color:#8df;}}
 .legend{{color:#7a9;font-size:.8rem;margin:4px 0 16px;}}
</style></head><body><div class="wrap">
<h1>WorldFork 모델 평가 대시보드</h1>
<p class="sub">생성: {ts} · 샘플링: temp {temp} top_k {topk} top_p {topp} rep {rep} · runs {runs} (비결정 평균)</p>
<div id="root"></div>
<script>
const DATA = {data};
const root = document.getElementById('root');
function bar(v,max,inv){{ let pct=Math.max(0,Math.min(100, v/max*100)); if(inv) pct=100-pct;
  return `<span class="barwrap"><span class="bar" style="width:${{pct.toFixed(0)}}%"></span></span>`; }}
function cls(v,g,w){{ return v>=g?'good':(v>=w?'warn':'bad'); }}
const M = DATA.models;
// 매트릭스
let h = '<h2>모델 × 지표 매트릭스</h2><div class="legend">속도 t/s↑ · TTFT s↓ · 한글순도 %↑ · 글리치 건수↓ · 서사 G-Eval 1~5↑ · 구조화 %↑ · 메모리 GB↓</div><table><tr><th>모델</th><th>역할</th><th>메모리 GB</th><th>속도 t/s</th><th>TTFT s</th><th>한글순도 %</th><th>글리치(글루/반복)</th><th>서사 G-Eval</th><th>구조화 %</th></tr>';
for(const m of M){{
  const g=m.judge.overall, hp=m.hangul.purity_pct, st=m.structured.pct;
  h += `<tr><td class="m">${{m.label}}</td><td class="jx">${{m.role}}</td>`+
    `<td class="num">${{m.size_gb}}</td>`+
    `<td class="num">${{bar(m.latency.tps,25)}} <b>${{m.latency.tps}}</b></td>`+
    `<td class="num">${{m.latency.ttft}}</td>`+
    `<td class="num ${{cls(hp,99,95)}}">${{bar(hp,100)}} ${{hp}}</td>`+
    `<td class="num ${{cls(10-(m.hangul.glue_glitch+m.hangul.dup_glitch),9,7)}}">${{m.hangul.glue_glitch}}/${{m.hangul.dup_glitch}}</td>`+
    `<td class="num ${{cls(g,4,3)}}"><b>${{g}}</b>/5</td>`+
    `<td class="num ${{cls(st,100,80)}}">${{st}}</td></tr>`;
}}
h += '</table>';
// G-Eval 4축
h += '<h2>서사 품질 G-Eval (1~5, cross-model judge)</h2><table><tr><th>모델</th>';
for(const ax of ['문체','persona','고증','시스템']) h+=`<th>${{ax}}</th>`;
h+='<th>종합</th><th>judge</th></tr>';
for(const m of M){{ h+=`<tr><td class="m">${{m.label}}</td>`;
  for(const ax of ['문체','persona','고증','시스템']){{ const v=m.judge.axes[ax]; h+=`<td class="num ${{cls(v,4,3)}}">${{v}}</td>`; }}
  h+=`<td class="num"><b>${{m.judge.overall}}</b></td><td class="jx">${{m.judge_by}}</td></tr>`; }}
h+='</table>';
// 출력 샘플
h += '<h2>출력 샘플 (정성 비교)</h2>';
for(const m of M){{ h+=`<details><summary>${{m.label}} — 서사 ${{m.samples.length}}건 + 구조화 ${{m.structured.pass}}/${{m.structured.total}}</summary>`;
  for(const s of m.samples){{ const j=s.judge?Object.entries(s.judge).filter(e=>e[0]!=='한줄평').map(e=>e[0]+':'+e[1]).join(' '):'judge 실패';
    h+=`<div><span class="tag">${{s.scenario}}</span> <span class="jx">${{j}}</span><div class="samp">${{(s.text||'(없음)').replace(/</g,'&lt;')}}</div></div>`; }}
  for(const s of m.structured_samples){{ h+=`<div><span class="tag">구조화</span> ${{s.valid?'<span class=good>✓</span>':'<span class=bad>✗</span>'}} <span class="jx">${{s.case}}</span> <span class="jx">${{s.parsed?JSON.stringify(s.parsed):''}}</span></div>`; }}
  h+='</details>'; }}
root.innerHTML = h;
</script>
<p class="sub">★ 확장: models.yaml에 모델 줄 추가 → run_eval.py → 이 대시보드 자동 갱신. 파인튜닝 모델도 같은 틀.</p>
</div></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(EVAL_DIR / "results.json"))
    ap.add_argument("--out", default=str(EVAL_DIR / "eval_dashboard.html"))
    ap.add_argument("--ts", default="")
    args = ap.parse_args()

    data = json.loads(Path(args.data).read_text(encoding="utf-8"))
    s = data["sampling"]
    html = _HTML.format(
        data=json.dumps(data, ensure_ascii=False), ts=args.ts or "(시각 미기입)",
        temp=s["temperature"], topk=s["top_k"], topp=s["top_p"], rep=s["repeat_penalty"],
        runs=s["runs"],
    )
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"DONE → {args.out}", flush=True)


if __name__ == "__main__":
    main()
