# AeroTrace Web Application

The AeroTrace web application is the interactive presentation layer of the turbofan maintenance decision-support MVP. It combines multi-dataset fleet analytics, per-engine inspection, and a digital twin view in a single browser-based interface.

Live deployment: [https://dist-ebon-nine.vercel.app](https://dist-ebon-nine.vercel.app)

## Quick Start

```bash
cd webapp
npm install
npm run dev
```

The local development server runs at `http://localhost:5173`.

## What the Application Covers

| Area | Description |
| --- | --- |
| Intro | Product framing, maintenance decision levels, and pipeline overview. |
| Home | Fleet statistics and dataset selection across all supported scenarios. |
| Fleet View | Risk matrix, decision distribution, and engine table. |
| Engine Detail | Cycle-level RUL and anomaly timelines, decision rationale, and transition history. |
| Digital Twin | 3D turbofan model with component health and degradation playback. |
| Audit | Policy snapshot, data-quality checks, and evidence-oriented review panels. |

## Supported Datasets

The interface is prepared for 11 scenarios:

- C-MAPSS: `FD001`, `FD002`, `FD003`, `FD004`
- N-CMAPSS: `DS01` through `DS07`

Selecting a dataset updates the fleet summary, engine detail views, and digital twin content.

## Decision Support Model

The application presents four maintenance outcomes derived from anomaly and RUL thresholds:

| Anomaly Status | RUL Status | Recommendation |
| --- | --- | --- |
| Low | Above threshold | `Normal Operation` |
| High | Above threshold | `Enhanced Monitoring` |
| Low | At or below threshold | `Planned Maintenance` |
| High | At or below threshold | `Immediate Maintenance` |

Every record carries audit fields such as policy version, thresholds, reasoning codes, and smoothing parameters so the final recommendation remains explainable.

## Project Layout

```text
webapp/
├── index.html
├── main.js
├── style.css
├── package.json
├── vite.config.js
├── preprocess_data.py
├── preprocess_all_datasets.py
└── public/
    ├── data/
    └── logos and static assets
```

## Available Scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Starts the local development server. |
| `npm run build` | Builds the production bundle into `dist/`. |
| `npm run preview` | Serves the built output locally for review. |
| `npm run preprocess` | Regenerates JSON assets from CSV sources. |

## Technology Stack

- Vite
- Vanilla JavaScript
- Plotly.js
- CSS custom properties
- Static deployment on Vercel
