# The AI and Human Skill Atlas

A living atlas of randomized experiments on how generative AI affects human skill formation. Currently focused on learning outcomes; built on top of the meta-analysis in Contractor & Reyes (2026).

Live: https://germanr.github.io/ai-skill-atlas/

## Stack

- React 19 + Vite 8 single-page app
- Inline CSS-in-JS (no Tailwind, no separate CSS files)
- Data pipeline: Excel → JSON via Python

## Local development

```powershell
cd C:\Users\greyes\Dropbox\Admin\website\ai-skill-atlas
npm install
npm run dev
```

Opens at `http://localhost:5175/ai-skill-atlas/`.

## Updating data

1. Edit `C:\Users\greyes\Dropbox\Research\ai-learning\support_info\meta_analysis\papers_for_website.xlsx` (sheets `papers` and `estimates`).
2. Re-run the build script:
   ```powershell
   python C:\Users\greyes\Dropbox\Admin\website\ai-skill-atlas\code\build_website_data.py
   ```
3. This regenerates `src/papers.json` and `src/estimates.json`.

## Adding a new paper

1. Append a row to the `papers` sheet of `papers_for_website.xlsx`.
2. Append the paper's estimate(s) to the `estimates` sheet (matching `paper_key`).
3. Add an image to `public/images/paper-{paper_key}.jpg` (target ~800×500, JPG quality ~80).
4. Add the PDF to `public/pdfs/` (filename matching the `pdf_filename` column).
5. Run `python code/build_website_data.py`.
6. Commit and push — GitHub Pages will redeploy automatically.

## Deployment

GitHub Pages via `.github/workflows/deploy.yml`. Push to `main` triggers a build.

## Repo layout

```
ai-skill-atlas/
├── ai-skill-atlas-explorer.jsx     # main React component
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx
│   ├── papers.json              # generated
│   └── estimates.json           # generated
├── public/
│   ├── images/                  # one .jpg per paper
│   └── pdfs/                    # one .pdf per paper
├── code/
│   └── build_website_data.py    # XLSX → JSON pipeline
└── .github/workflows/deploy.yml
```
