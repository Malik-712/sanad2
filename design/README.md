# Design sources (not deployed)

- `Sanad Logo.html`: exported logo board (primary lockup, header lockup, favicon, colour variants).
- `sanad-mark.source.svg`: the logo source with its comments and metadata.

The site serves only `public/sanad-mark.svg` (the deployed copy) and the favicons in `public/`.
Vercel deploys `public/` only (`vercel.json` → `outputDirectory`), so nothing here is served.
