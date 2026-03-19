# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Static personal portfolio website for Sureh San. No build system, bundler, or dependencies — open any HTML file directly in a browser or serve with a local static server.

## Running Locally

```bash
# Any simple static server works, e.g.:
python -m http.server 8080
# Then open http://localhost:8080
```

## Architecture

This is a flat, multi-page static site. All pages share a single stylesheet (`styles.css`) and load Google Fonts (JetBrains Mono, Inter, Space Grotesk, etc.) from CDN.

### Page Structure

- **`index.html`** — Landing page only. Renders the animated neural-network navigation canvas; no content of its own.
- **All other pages** — Self-contained content pages with a simple `← Back` nav link to `index.html`.

### Navigation (`neural-nav.js`)

The entire nav is a `<canvas>` element driven by `neural-nav.js`. It renders a fully-connected 5-layer neural network where clickable nodes link to pages:

| Layer | Nodes |
|---|---|
| 0 (input) | Sureh San (decorative) |
| 1 | About, Education, Experience |
| 2 | Projects, Competitions, Publications, Honors |
| 3 | Certifications, Skills, My Tech, Contact |
| 4 (output) | Engineer, Researcher, Tinkerer (decorative) |

Particles animate along every edge (one per connection, evenly staggered). Hover highlights connected edges; click navigates. Touch is supported. To add a new page, add a node entry to the `sections` array in `neural-nav.js` and create the corresponding HTML file.

### Styling

All styles live in `styles.css`. Key CSS variables (defined on `:root`):
- `--primary`, `--dark`, `--light`, `--accent`, `--border`, `--bg-subtle`
- Body font: `JetBrains Mono` (monospace)
- Accent/link color: `#7a1e2e` (dark red)
- Dark background theme (`--dark: #1a1a1a`)

The `index.html` body uses class `landing` for canvas-specific layout; all other pages use default body styling.
