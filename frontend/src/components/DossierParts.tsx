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

export function TrafficLight({ value, matches, alternatives }: { value: 'RED' | 'YELLOW' | 'GREEN'; matches: string[]; alternatives: string[] }) {
  const colors = { RED: '#fb7185', YELLOW: '#fbbf24', GREEN: '#4ade80' };
  return <section className="panel" style={{ padding: 20, borderColor: colors[value] }}>
    <div className="eyebrow">Name collision</div>
    <h2 style={{ color: colors[value], margin: '10px 0' }}>{value}</h2>
    <p className="muted">Public registry matches: {matches.length ? matches.join(', ') : 'none found'}</p>
    <div className="muted" style={{ fontSize: 13 }}>Safe alternatives: {alternatives.join(' · ') || 'none suggested'}</div>
  </section>;
}

const scoreDimensions: [keyof Score, string][] = [
  ['clarity', 'Clarity'], ['landscape_coverage', 'Landscape coverage'], ['originality', 'Originality'],
  ['gap_opportunity', 'Gap opportunity'], ['enhancement_potential', 'Enhancement potential'], ['evidence_quality', 'Evidence quality'],
];

export function NyxaScoreCard({ score, verified, stripped, delta }: { score: Score; verified: number; stripped: number; delta?: number | null }) {
  return <section className="panel" style={{ padding: 22 }}>
    <div style={{ display: 'flex', alignItems: 'end', justifyContent: 'space-between', gap: 10 }}>
      <div><div className="eyebrow">Nyxa score</div><div style={{ fontSize: 46, letterSpacing: '-.05em', marginTop: 5 }}>{score.composite}<span className="muted" style={{ fontSize: 20 }}>/100</span></div></div>
      <div style={{ textAlign: 'right' }}><div className="muted" style={{ fontSize: 12 }}>Projected after backlog</div><strong style={{ color: '#38BDF8', fontSize: 22 }}>{score.projected_post_enhancement}/100</strong>{delta != null && <div className="mono" style={{ color: delta >= 0 ? '#4ade80' : '#fb7185' }}>{delta >= 0 ? '+' : ''}{delta} vs parent scan</div>}</div>
    </div>
    <p className="muted">{score.verdict}</p>
    <div style={{ display: 'grid', gap: 12, marginTop: 20 }}>
      {scoreDimensions.map(([key, label]) => <div key={key}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 5 }}><span>{label}</span><span className="mono">{score[key]}/100</span></div>
        <div style={{ height: 5, background: '#263244', borderRadius: 9 }}><div style={{ width: score[key] + '%', height: '100%', background: '#38BDF8', borderRadius: 9 }} /></div>
      </div>)}
    </div>
    <div className="mono muted" style={{ fontSize: 12, marginTop: 18 }}>Deterministic {score.deterministic_points}/40 · Rubric {score.rubric_points}/60</div>
    <details style={{ marginTop: 14 }}><summary style={{ cursor: 'pointer' }}>Citation verification</summary>
      <p className="muted" style={{ fontSize: 13 }}>Verified citations: {verified} · Removed unverified citations: {stripped}</p>
    </details>
  </section>;
}

export function KillKeepInjectMatrix({ items }: { items: CitationItem[] }) {
  return <section className="panel" style={{ padding: 20 }}>
    <div className="eyebrow">Architecture triage</div>
    <div className="grid-auto" style={{ marginTop: 15 }}>
      {(['KILL', 'KEEP', 'INJECT'] as const).map(action => <div key={action} style={{ background: '#0b1220', padding: 14, borderRadius: 10 }}>
        <h3 className="mono" style={{ color: action === 'KILL' ? '#fb7185' : action === 'KEEP' ? '#4ade80' : '#38BDF8', marginTop: 0 }}>{action}</h3>
        {items.filter(item => item.action === action).map((item, i) => <article key={i} style={{ borderTop: '1px solid #263244', paddingTop: 10, marginTop: 10 }}>
          <strong>{item.target_component}</strong><p className="muted" style={{ fontSize: 13 }}>{item.rationale}</p>
          {item.citation_url && <a href={item.citation_url} target="_blank" rel="noreferrer">Verified source ↗</a>}
        </article>)}
      </div>)}
    </div>
  </section>;
}

export function AnalogyCard({ analogy, disclaimer }: { analogy: Dossier['analogies'][number]; disclaimer: string }) {
  return <section className="panel" style={{ padding: 20 }}>
    <div className="eyebrow">Cross-domain pattern · {analogy.pattern_id} · {(analogy.similarity_score * 100).toFixed(0)}% match</div>
    <h3 style={{ marginBottom: 6 }}>{analogy.canonical_mechanism}</h3>
    <p className="muted">{analogy.source_domain} · {analogy.evidence.standard} · <a href={analogy.evidence.reference_url} target="_blank" rel="noreferrer">Reference ↗</a></p>
    <p>{analogy.mechanism}</p>
    <div style={{ overflowX: 'auto' }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead><tr><th align="left">Source primitive</th><th align="left">Repo module</th><th align="left">Expected effect</th></tr></thead>
      <tbody>{analogy.mapping_table.map((row, i) => <tr key={i}><td>{row.source_primitive}</td><td className="mono">{row.target_repo_module}</td><td>{row.expected_effect}</td></tr>)}</tbody>
    </table></div>
    <p style={{ color: '#fbbf24', fontSize: 13 }}>Watch for: {analogy.anti_pattern_warning}</p>
    <p className="muted" style={{ fontSize: 12 }}>{disclaimer}</p>
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
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'dark' });
    mermaid.render('nyxa-' + id, source).then(result => { if (active) setSvg(result.svg); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [id, source]);
  if (failed) return <pre className="panel mono" style={{ padding: 16, whiteSpace: 'pre-wrap' }}>{source}</pre>;
  return <div className="panel" aria-label="Before and after architecture diagram" style={{ overflowX: 'auto', padding: 12 }} dangerouslySetInnerHTML={{ __html: svg }} />;
}

export function MermaidDiagram({ source }: { source: string }) {
  return <MermaidBoundary source={source}><MermaidRenderer source={source} /></MermaidBoundary>;
}

export function EnhancementBacklog({ items }: { items: BacklogItem[] }) {
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  return <section className="panel" style={{ padding: 20 }}>
    <div className="eyebrow">Build next</div>
    {items.map(item => <label key={item.rank} style={{ display: 'flex', gap: 12, padding: '14px 0', borderBottom: '1px solid #263244' }}>
      <input type="checkbox" checked={!!checked[item.rank]} onChange={e => setChecked({ ...checked, [item.rank]: e.target.checked })} />
      <span><strong>{item.rank}. {item.title}</strong><span className="muted" style={{ display: 'block', fontSize: 13, marginTop: 4 }}>{item.description} · {item.effort} effort · {item.impact} impact</span>
      {item.citation_url && <a href={item.citation_url} target="_blank" rel="noreferrer">Source ↗</a>}</span>
    </label>)}
  </section>;
}

export function BadgeSnippet({ scanId }: { scanId: string }) {
  const snippet = '![Nyxa Score](' + process.env.NEXT_PUBLIC_API_URL + '/badge/' + scanId + ')';
  const [copied, setCopied] = useState(false);
  return <section className="panel" style={{ padding: 16 }}>
    <div className="eyebrow">README badge</div><div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
      <code className="mono muted" style={{ overflowWrap: 'anywhere', flex: 1 }}>{snippet}</code>
      <button className="button" onClick={() => { void navigator.clipboard.writeText(snippet).then(() => setCopied(true)); }}>{copied ? 'Copied' : 'Copy'}</button>
    </div>
  </section>;
}

export function PipelineTracePanel({ traces }: { traces: NonNullable<Dossier['pipeline_trace']> }) {
  const longest = Math.max(1, ...traces.map(trace => trace.duration_ms));
  return <section className="panel" style={{ padding: 20 }}>
    <div className="eyebrow">Pipeline trace · {traces.length} stages</div>
    {traces.map((trace, i) => <article key={i} style={{ padding: '15px 0', borderBottom: '1px solid #263244' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><strong>{trace.subagent}</strong><span className="mono">{trace.duration_ms} ms · ${trace.estimated_usd.toFixed(6)}</span></div>
      <div style={{ height: 5, background: '#263244', borderRadius: 9, margin: '8px 0' }}><div style={{ width: Math.max(2, (trace.duration_ms / longest) * 100) + '%', height: '100%', background: '#38BDF8', borderRadius: 9 }} /></div>
      <div className="mono muted" style={{ fontSize: 11, overflowWrap: 'anywhere' }}>{trace.model_id} · {trace.input_tokens} in / {trace.output_tokens} out · {trace.citations_verified} citations verified · {trace.citations_stripped} stripped</div>
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
