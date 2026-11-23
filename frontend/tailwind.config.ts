import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: { extend: { colors: { obsidian: '#0B0F19', cyan: '#38BDF8' }, fontFamily: { mono: ['var(--font-mono)'] } } },
  plugins: [],
};
export default config;
