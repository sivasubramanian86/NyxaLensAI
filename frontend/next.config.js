/** @type {import('next').NextConfig} */
// Static export: the hosted demo serves pre-rendered pages from stored dossiers and needs no server.
const nextConfig = { output: 'export', trailingSlash: true, images: { unoptimized: true } };
module.exports = nextConfig;
