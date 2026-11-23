'use client';

import { Component, useEffect, useId, useState, type ErrorInfo, type ReactNode } from 'react';
import mermaid from 'mermaid';

export type Score = {
  composite: number; clarity: number; landscape_coverage: number; originality: number;
  gap_opportunity: number; enhancement_potential: number; evidence_quality: number;
  deterministic_points: number; rubric_points: number; projected_post_enhancement: number; verdict: string;
};
export type CitationItem = { action: 'KILL' | 'KEEP' | 'INJECT'; target_component: string; rationale: string; citation_url?: string | null };
export type BacklogItem = { rank: number; title: string; description: string; effort: string; impact: string; citation_url?: string | null };
export type Dossier = {
  name_collision: { traffic_light: 'RED' | 'YELLOW' | 'GREEN'; exact_matches: string[]; fuzzy_matches: string[]; phonetic_matches: string[]; safe_alternatives: string[] };
  landscape: { direct_competitors: { name: string; url: string; stars?: number; limitations?: string }[] };
  analogies: { pattern_id: string; source_domain: string; canonical_mechanism: string; mechanism: string; mapping_table: { source_primitive: string; target_repo_module: string; expected_effect: string }[]; expected_lift: string; anti_pattern_warning: string; evidence: { standard: string; reference_url: string }; similarity_score: number }[];
  kill_keep_inject: CitationItem[]; ranked_backlog: BacklogItem[]; mermaid_before_after: string;
  nyxa_score: Score; verified_citations_count: number; stripped_hallucinations_count: number;
  project_profile: { project_name: string; repo_url?: string; input_type: string };
  disclaimer: string; score_delta?: number | null; pipeline_trace?: { subagent: string; duration_ms: number; model_id: string; input_tokens: number; output_tokens: number; estimated_usd: number; citations_verified: number; citations_stripped: number }[];
};

const LIGHT = {
  RED: { color: '#fb7185', pill: 'pill-rose', note: 'High collision risk. Pick a different name.' },
  YELLOW: { color: '#fbbf24', pill: 'pill-amber', note: 'Similar names exist. Differentiate before launch.' },
  GREEN: { color: '#4ade80', pill: 'pill-green', note: 'No close matches found in the registries checked.' },
} as const;

export function TrafficLight({ value, matches, alternatives }: { value: 'RED' | 'YELLOW' | 'GREEN'; matches: string[]; alternatives: string[] }) {
  const tone = LIGHT[value];
  return <section className="panel" style={{ padding: 22, boxShadow: '0 1px 0 rgba(255,255,255,.10) inset, 0 24px 60px -28px rgba(0,0,0,.75), 0 0 0 1px ' + tone.color + '33, 0 0 40px -12px ' + tone.color + '55' }}>
    <div className="section-title"><div className="eyebrow">Name collision</div><span className={'pill ' + tone.pill}>GitHub · PyPI · npm</span></div>
    <h2 style={{ color: tone.color, display: 'flex', alignItems: 'center', gap: 12, fontSize: 34, letterSpacing: '-.03em' }}><span className="dot" aria-hidden="true" style={{ width: 14, height: 14 }} />{value}</h2>
    <p className="muted" style={{ margin: '8px 0 14px', fontSize: 14 }}>{tone.note}</p>
    <div className="muted" style={{ fontSize: 12, marginBottom: 8, letterSpacing: '.06em', textTransform: 'uppercase' }}>Public registry matches</div>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
      {matches.length ? matches.map(match => <span key={match} className="pill pill-rose mono">{match}</span>) : <span className="pill pill-green">none found</span>}
    </div>
    <div className="muted" style={{ fontSize: 12, marginBottom: 8, letterSpacing: '.06em', textTransform: 'uppercase' }}>Safe alternatives</div>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {alternatives.length ? alternatives.map(name => <span key={name} className="pill pill-cyan">{name}</span>) : <span className="pill">none suggested</span>}
    </div>
  </section>;
}

const scoreDimensions: [keyof Score, string][] = [
  ['clarity', 'Clarity'], ['landscape_coverage', 'Landscape coverage'], ['originality', 'Originality'],
  ['gap_opportunity', 'Gap opportunity'], ['enhancement_potential', 'Enhancement potential'], ['evidence_quality', 'Evidence quality'],
];

function ScoreRing({ value, projected }: { value: number; projected: number }) {
  const id = useId().replace(/:/g, '');
  const r = 70; const c = 2 * Math.PI * r;
  const arc = (v: number) => Math.max(0, Math.min(100, v)) / 100 * c + ' ' + c;
  return <div className="ring-wrap" role="img" aria-label={'Nyxa score ' + value + ' out of 100, projected ' + projected}>
    <svg viewBox="0 0 168 168">
      <defs><linearGradient id={'g' + id} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#38bdf8" /><stop offset="1" stopColor="#8b5cf6" /></linearGradient></defs>
      <circle cx="84" cy="84" r={r} fill="none" stroke="rgba(255,255,255,.08)" strokeWidth="12" />
      <circle cx="84" cy="84" r={r} fill="none" stroke="rgba(167,139,250,.35)" strokeWidth="12" strokeLinecap="round" strokeDasharray={arc(projected)} />
      <circle cx="84" cy="84" r={r} fill="none" stroke={'url(#g' + id + ')'} strokeWidth="12" strokeLinecap="round" strokeDasharray={arc(value)} style={{ filter: 'drop-shadow(0 0 8px rgba(56,189,248,.7))' }} />
    </svg>
    <div className="ring-center"><div className="ring-value">{value}</div><div className="ring-sub">out of 100</div></div>
  </div>;
}

export function NyxaScoreCard({ score, verified, stripped, delta }: { score: Score; verified: number; stripped: number; delta?: number | null }) {
  return <section className="panel" style={{ padding: 24 }}>
    <div className="section-title"><div className="eyebrow">Nyxa score</div><span className="pill pill-cyan mono">Deterministic {score.deterministic_points}/40 · Rubric {score.rubric_points}/60</span></div>
    <div style={{ display: 'flex', alignItems: 'center', gap: 24, flexWrap: 'wrap' }}>
      <ScoreRing value={score.composite} projected={score.projected_post_enhancement} />
      <div style={{ flex: 1, minWidth: 190 }}>
        <div className="muted" style={{ fontSize: 12, letterSpacing: '.06em', textTransform: 'uppercase' }}>Projected after backlog</div>
        <div style={{ fontSize: 40, fontWeight: 800, letterSpacing: '-.04em' }} className="gradient-text">{score.projected_post_enhancement}<span style={{ fontSize: 18, fontWeight: 600 }}>/100</span></div>
        {delta != null && <div className="mono" style={{ color: delta >= 0 ? '#4ade80' : '#fb7185', fontSize: 13 }}>{delta >= 0 ? '+' : ''}{delta} vs parent scan</div>}
        <p className="muted" style={{ margin: '10px 0 0', fontSize: 14, lineHeight: 1.5 }}>{score.verdict}</p>
      </div>
    </div>
    <div style={{ display: 'grid', gap: 13, marginTop: 24 }}>
      {scoreDimensions.map(([key, label]) => <div key={key}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 6 }}><span>{label}</span><span className="mono muted">{score[key]}/100</span></div>
        <div className="bar"><span style={{ width: score[key] + '%' }} /></div>
      </div>)}
    </div>
    <details style={{ marginTop: 18 }}><summary style={{ cursor: 'pointer', fontSize: 14 }}>Citation verification</summary>
      <p className="muted" style={{ fontSize: 13 }}>Verified citations: {verified} · Removed unverified citations: {stripped}</p>
    </details>
  </section>;
}

const ACTION_BLURB = {
  KILL: 'Nothing flagged for removal. No commodity code was identified in the evidence.',
  KEEP: 'No unique core identified in the evidence.',
  INJECT: 'No cross-domain pattern cleared the similarity threshold.',
} as const;

export function KillKeepInjectMatrix({ items }: { items: CitationItem[] }) {
  return <section className="panel" style={{ padding: 22 }}>
    <div className="section-title"><div className="eyebrow">Architecture triage</div><span className="pill">Kill · Keep · Inject</span></div>
    <div className="kki">
      {(['KILL', 'KEEP', 'INJECT'] as const).map(action => {
        const rows = items.filter(item => item.action === action);
        return <div key={action} className="kki-col" data-action={action}>
          <div className="kki-head"><h3>{action}</h3><span className="pill mono">{rows.length}</span></div>
          {rows.map((item, i) => <article key={i} className="kki-item">
            <strong>{item.target_component}</strong><p className="muted" style={{ fontSize: 13, margin: '6px 0 8px', lineHeight: 1.5 }}>{item.rationale}</p>
            {item.citation_url && <a href={item.citation_url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>Verified source ↗</a>}
          </article>)}
          {!rows.length && <p className="muted" style={{ fontSize: 13, margin: '10px 0 0', lineHeight: 1.5 }}>{ACTION_BLURB[action]}</p>}
        </div>;
      })}
    </div>
  </section>;
}

export function AnalogyCard({ analogy, disclaimer }: { analogy: Dossier['analogies'][number]; disclaimer: string }) {
  return <section className="panel lift" style={{ padding: 22 }}>
    <div className="section-title">
      <div className="eyebrow">Cross-domain pattern · {analogy.pattern_id}</div>
      <span className="pill pill-cyan mono">{(analogy.similarity_score * 100).toFixed(0)}% match</span>
    </div>
    <h3 style={{ fontSize: 22, letterSpacing: '-.02em', marginBottom: 8 }}>{analogy.canonical_mechanism}</h3>
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
      <span className="pill">{analogy.source_domain}</span>
      <span className="pill">{analogy.evidence.standard}</span>
      <a className="pill pill-cyan" href={analogy.evidence.reference_url} target="_blank" rel="noreferrer" style={{ textDecoration: 'none' }}>Reference ↗</a>
    </div>
    <p style={{ lineHeight: 1.6, margin: '0 0 12px' }}>{analogy.mechanism}</p>
    <div style={{ overflowX: 'auto' }}><table className="table-glass">
      <thead><tr><th>Source primitive</th><th>Repo module</th><th>Expected effect</th></tr></thead>
      <tbody>{analogy.mapping_table.map((row, i) => <tr key={i}><td>{row.source_primitive}</td><td className="mono">{row.target_repo_module}</td><td>{row.expected_effect}</td></tr>)}</tbody>
    </table></div>
    <div className="callout" style={{ marginTop: 12 }}><span aria-hidden="true">⚠</span><span>Watch for: {analogy.anti_pattern_warning}</span></div>
    <p className="muted" style={{ fontSize: 12, margin: '12px 0 0' }}>{disclaimer}</p>
  </section>;
}

class MermaidBoundary extends Component<{ source: string; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) {}
  render() { return this.state.failed ? <pre className="panel mono" style={{ padding: 16, whiteSpace: 'pre-wrap' }}>{this.props.source}</pre> : this.props.children; }
}

function MermaidRenderer({ source }: { source: string }) {
  const id = useId().replace(/:/g, '');
  const [svg, setSvg] = useState('');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    mermaid.initialize({
      startOnLoad: false, securityLevel: 'strict', theme: 'base',
      themeVariables: {
        background: 'transparent', primaryColor: '#12304a', primaryBorderColor: '#38bdf8', primaryTextColor: '#e7eefb',
        lineColor: '#7dd3fc', secondaryColor: '#241a4a', tertiaryColor: '#0b1220', fontFamily: 'Inter, system-ui, sans-serif', fontSize: '15px',
      },
    });
    mermaid.render('nyxa-' + id, source).then(result => { if (active) setSvg(result.svg); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [id, source]);
  if (failed) return <pre className="panel mono" style={{ padding: 16, whiteSpace: 'pre-wrap' }}>{source}</pre>;
  return <div className="panel mermaid-wrap" aria-label="Before and after architecture diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}

export function MermaidDiagram({ source }: { source: string }) {
  return <MermaidBoundary source={source}><MermaidRenderer source={source} /></MermaidBoundary>;
}

const LEVEL_PILL: Record<string, string> = { LOW: 'pill-green', MEDIUM: 'pill-amber', HIGH: 'pill-rose', 'VERY HIGH': 'pill-rose' };
const IMPACT_PILL: Record<string, string> = { LOW: '', MEDIUM: 'pill-cyan', HIGH: 'pill-cyan', 'VERY HIGH': 'pill-green' };

export function EnhancementBacklog({ items }: { items: BacklogItem[] }) {
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  return <section className="panel" style={{ padding: 22 }}>
    <div className="section-title"><div className="eyebrow">Build next</div><span className="pill mono">{Object.values(checked).filter(Boolean).length}/{items.length} done</span></div>
    {items.map(item => <label key={item.rank} style={{ display: 'flex', gap: 14, padding: '16px 0', borderTop: '1px solid rgba(255,255,255,.07)', cursor: 'pointer' }}>
      <input className="check" type="checkbox" checked={!!checked[item.rank]} onChange={e => setChecked({ ...checked, [item.rank]: e.target.checked })} />
      <span style={{ flex: 1 }}>
        <strong style={{ textDecoration: checked[item.rank] ? 'line-through' : 'none', opacity: checked[item.rank] ? .6 : 1 }}>{item.rank}. {item.title}</strong>
        <span className="muted" style={{ display: 'block', fontSize: 13, margin: '5px 0 8px', lineHeight: 1.5 }}>{item.description}</span>
        <span style={{ display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
          <span className={'pill ' + (LEVEL_PILL[item.effort] ?? '')}>{item.effort} effort</span>
          <span className={'pill ' + (IMPACT_PILL[item.impact] ?? '')}>{item.impact} impact</span>
          {item.citation_url && <a href={item.citation_url} target="_blank" rel="noreferrer" style={{ fontSize: 13 }}>Source ↗</a>}
        </span>
      </span>
    </label>)}
  </section>;
}

export function BadgeSnippet({ scanId }: { scanId: string }) {
  const snippet = '![Nyxa Score](' + process.env.NEXT_PUBLIC_API_URL + '/badge/' + scanId + ')';
  const [copied, setCopied] = useState(false);
  return <section className="panel" style={{ padding: 18 }}>
    <div className="eyebrow">README badge</div><div style={{ display: 'flex', gap: 10, marginTop: 12, alignItems: 'center' }}>
      <code className="mono muted inset" style={{ overflowWrap: 'anywhere', flex: 1, padding: 10, fontSize: 12 }}>{snippet}</code>
      <button className="button" onClick={() => { void navigator.clipboard.writeText(snippet).then(() => setCopied(true)); }}>{copied ? 'Copied' : 'Copy'}</button>
    </div>
  </section>;
}

export function PipelineTracePanel({ traces }: { traces: NonNullable<Dossier['pipeline_trace']> }) {
  const longest = Math.max(1, ...traces.map(trace => trace.duration_ms));
  return <section className="panel" style={{ padding: 22 }}>
    <div className="section-title"><div className="eyebrow">Pipeline trace · {traces.length} stages</div></div>
    {traces.map((trace, i) => <article key={i} style={{ padding: '16px 0', borderTop: '1px solid rgba(255,255,255,.07)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><strong>{trace.subagent}</strong><span className="mono muted">{trace.duration_ms} ms · ${trace.estimated_usd.toFixed(6)}</span></div>
      <div className="bar" style={{ margin: '10px 0' }}><span style={{ width: Math.max(2, (trace.duration_ms / longest) * 100) + '%' }} /></div>
      <div className="mono muted" style={{ fontSize: 11.5, overflowWrap: 'anywhere' }}>{trace.model_id} · {trace.input_tokens} in / {trace.output_tokens} out · {trace.citations_verified} citations verified · {trace.citations_stripped} stripped</div>
    </article>)}
    {!traces.length && <p className="muted">No trace records attached to this scan.</p>}
  </section>;
}

export function ReScanButton({ scanId, onStarted }: { scanId: string; onStarted: (message: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const rescan = async () => {
    const api = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
    const saved = localStorage.getItem('nyxa:input:' + scanId);
    if (!api || !saved) { setError('Original scan input is unavailable in this browser. Start a new scan from the home page.'); return; }
    setBusy(true); setError('');
    try {
      const response = await fetch(api + '/scans', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...JSON.parse(saved), session_id: localStorage.getItem('nyxa:session:' + scanId) || localStorage.getItem('nyxa:session') || scanId, parent_scan_id: scanId, force_refresh: true }) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Re-scan could not start.');
      localStorage.setItem('nyxa:input:' + result.scan_id, saved);
      localStorage.setItem('nyxa:session:' + result.scan_id, localStorage.getItem('nyxa:session:' + scanId) || scanId);
      onStarted(result.scan_id);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Re-scan could not start.'); }
    finally { setBusy(false); }
  };
  return <div><button className="button button-primary" onClick={rescan} disabled={busy}>{busy ? 'Starting…' : 'Re-scan after improvements'}</button>{error && <p role="alert" style={{ color: '#fda4af' }}>{error}</p>}</div>;
}
