import type { ReactNode } from 'react';

export function AppHeader({ right }: { right?: ReactNode }) {
  return (
    <div className="topbar-wrap">
      <header className="shell topbar" role="banner">
        <a href="/" className="brand" aria-label="NyxaLensAI home">
          <span className="brand-mark" aria-hidden="true">N</span>
          <span>NyxaLens<span className="gradient-text">AI</span> <small>· architecture intelligence</small></span>
        </a>
        <div className="topbar-right">{right}</div>
      </header>
    </div>
  );
}
