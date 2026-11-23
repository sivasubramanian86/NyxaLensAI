import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'NyxaLensAI — See in the dark. Build in the light.',
  description: 'See what exists, how your architecture differs, and what to build next.',
};

// System font stacks keep the build offline-safe: no font download is needed at build time.
export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
