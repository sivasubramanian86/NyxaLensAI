'use client';

import { useEffect, useState } from 'react';

type ScanStatus = { status: string; progress?: number; completed_subagents?: Record<string, boolean> };
type Props = { scanId: string; onCompleted: () => void; onFailure: (message: string) => void };

const stages = [
  ['repo_scan', 'Repo AST'],
  ['name_collision', 'Name Collision'],
  ['landscape', 'Ecosystem Scout'],
  ['analogy', 'Systems Ontology'],
  ['enhancement', 'Grounded Synthesis'],
];

export function LivePollingStatus({ scanId, onCompleted, onFailure }: Props) {
  const [scan, setScan] = useState<ScanStatus>({ status: 'INITIALIZED', progress: 5 });

  useEffect(() => {
    const api = process.env.NEXT_PUBLIC_API_URL;
    let active = true;
    let checking = false;
    const poll = async () => {
      if (checking || !active || !api) return;
      checking = true;
      try {
        const response = await fetch(api + '/scans/' + scanId);
        if (!response.ok) throw new Error('Scan status returned ' + response.status);
        const status = await response.json() as ScanStatus;
        if (!active) return;
        setScan(status);
        if (status.status === 'COMPLETED') {
          active = false;
          onCompleted();
        } else if (status.status === 'FAILED') {
          active = false;
          onFailure('Scan failed. Check API and Lambda logs, then retry.');
        }
      } catch (error) {
        if (active) onFailure(error instanceof Error ? error.message : 'Could not read scan status.');
      } finally {
        checking = false;
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [scanId, onCompleted, onFailure]);

  return (
    <section aria-live="polite" className="panel" style={{ padding: 20, marginTop: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16 }}>
        <div><div className="eyebrow">Live scan</div><div className="mono" style={{ marginTop: 5 }}>{scan.status}</div></div>
        <div className="mono" style={{ color: '#38BDF8' }}>{scan.progress ?? 0}%</div>
      </div>
      <div style={{ height: 5, background: '#263244', borderRadius: 9, margin: '14px 0 18px' }}>
        <div style={{ width: (scan.progress ?? 0) + '%', height: '100%', background: '#38BDF8', borderRadius: 9, transition: 'width .3s' }} />
      </div>
      <div className="grid-auto">
        {stages.map(([key, label], index) => {
          const done = scan.completed_subagents?.[key];
          return <div key={key} className="mono muted" style={{ fontSize: 12 }}>
            {done ? '[✓]' : index === 4 && scan.status === 'SYNTHESIZING' ? '[⚡]' : '[·]'} {label}
          </div>;
        })}
      </div>
    </section>
  );
}
