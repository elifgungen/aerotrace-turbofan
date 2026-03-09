# Webapp Guide

The web application is the fastest way to review the bundled results in a browser.

## Location

- App source: [`webapp/`](../webapp)
- App guide in the app folder: [`webapp/README.md`](../webapp/README.md)

## Requirements

- Node.js 18 or newer
- npm

## Run Locally

```bash
cd webapp
npm install
npm run dev
```

The development server runs at `http://localhost:5173`.

## Refresh Bundled JSON Data

The application already ships with prebuilt JSON files under [`webapp/public/data/`](../webapp/public/data), so no extra step is required for normal review.

If you need to regenerate the full multi-dataset JSON bundle from the repository outputs:

```bash
cd webapp
python3 preprocess_all_datasets.py
```

## Build a Production Bundle

```bash
cd webapp
npm run build
npm run preview
```

## Data Sources Used by the Webapp

- `FD001` is sourced from [`demo/decision_support_v2_outputs/fd001_decision_support_v2.csv`](../demo/decision_support_v2_outputs/fd001_decision_support_v2.csv)
- `FD002` to `FD004` are sourced from [`data/processed/outputs/C-MAPSS/`](../data/processed/outputs/C-MAPSS)
- `DS01` to `DS07` are sourced from [`demo/decision_support_v2_outputs/`](../demo/decision_support_v2_outputs)

## When to Use This Path

Use the webapp when you want the best presentation quality for public review, dataset switching, and engine-level drill-down.
