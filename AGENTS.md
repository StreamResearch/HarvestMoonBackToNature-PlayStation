# Context: HarvestMoonBackToNature-PlayStation

- **Tier R (`ps1`):** `D4/S4` (`goalStudyTier: S5`, target engine `reStation` `0.2.x`). Zero `Builds`/`Installers`/`Releases`; `Corpus` & `Dev/data/` gitignored (`-xr!Corpus\*`, `standalone/` RO).
- **Control:** [research.manifest.json](Dev/research.manifest.json) | [HarvestMoonBackToNature-PlayStation.code-workspace](Dev/HarvestMoonBackToNature-PlayStation.code-workspace) | Downstream: `HMBackToNature-Recomp` (`read-only`)

## 1. Quartet, Security & State
- [README.md](README.md) | [FEATURES.md](FEATURES.md) | [ROADMAP.md](ROADMAP.md) | [CHANGELOG.md](CHANGELOG.md) | [SECURITY.md](SECURITY.md) | [active.state](active.state)

## 2. Manuals (`Dev/docs/`)
- [ARCHITECTURE.md](Dev/docs/ARCHITECTURE.md) | [SPECIFICATIONS.md](Dev/docs/SPECIFICATIONS.md) | [FINDINGS.md](Dev/docs/FINDINGS.md) | [OPERATIONS.md](Dev/docs/OPERATIONS.md)
- **Specs, Plans & Reports:** [specifications/](Dev/docs/specifications/) | [stages/](Dev/docs/stages/) | Local-only gitignored: `Dev/docs/plans/`, `Dev/docs/reports/`

## 3. Governance & Notion
- **Notion:** `<NOTION_PROJECT_PAGE_ID>` (`<NOTION_TASK_LIST_COLLECTION>` — local IDs in gitignored `Dev/data/notion_hub.local.json`)
- **Commit `/post` Hook:** Every commit & release pushes `/post` via `active.state` -> `discordPost` (`DISCORD_WEBHOOK_FOUNDATION`), tagging `@StreamDoesDev`.
