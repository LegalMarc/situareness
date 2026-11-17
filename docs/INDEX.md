# Docs index

<!-- docs-sync
roots: docs/ home-assistant/ README.md AGENTS.md CLAUDE.md skills/situareness-sources/
exclude: .git/ work/ .venv/ __pycache__/ ignored-resources/ node_modules/ dist/
code: extension/ custom_components/ tools/ tests/ skills/situareness-sources/scripts/ package.json playwright.config.js
-->

Start with the [project context](CONTEXT.md) and [continuation guide](plans/RESUME.md). Source catalog entries are research, not runtime inputs. Configuration exports and personal settings are sensitive.

## (root)
- `AGENTS.md` — Agent workflow, privacy boundaries, review, and safety instructions.
- `CLAUDE.md` — Shared agent entry point.
- `README.md` — Project overview, links, privacy, and source limitations.

## docs/
- `docs/CONTEXT.md` — Domain terms, operating model, sources, and current boundaries. anchors: purpose, domain-language, operating-model, sources-and-configuration, current-boundaries
- `docs/extension-quickstart.md` — Packaged room installation and configuration privacy.
- `docs/setup.md` — Room operation, source freshness, private settings, and development checks. anchors: what-runs-where, load-into-chrome, settings-and-privacy, sources-and-freshness, develop-and-verify, future-work covers: extension/**, tools/**, tests/browser/**, tests/runtime/**, tests/ui/**, package.json, playwright.config.js

## docs/adr/
- `docs/adr/0001-confirmed-operating-model.md` — Independent monitoring and conservative household alarm decisions. anchors: status, decision, consequences
- `docs/adr/0002-o3-local-room-and-independent-monitor.md` — Local room, separate monitor, and deferred managed-compute alternative. anchors: status, decision, consequences

## docs/ha/
- `docs/ha/README.md` — Home Assistant configuration, eligibility, delivery, and verification. anchors: setup-for-a-future-authorized-installation, health-reconciliation-and-limits, verification-and-references, local-home-assistant-runtime-test covers: custom_components/**, tests/ha/**

## docs/plans/
- `docs/plans/HANDOFF.md` — Supervisor continuation brief, interrupted WIP status, failing checks, source-semantics questions, and delegation/review workflow. anchors: first-instruction-for-the-new-supervisor, what-stopped-and-what-is-actually-known, immediate-work-before-more-features, critical-source-semantics-correction, parallel-work-and-supervision, independent-review-that-worked, local-environment-and-privacy-boundary, suggested-skills
- `docs/plans/RESUME.md` — Current state, verification commands, privacy boundaries, and remaining work. anchors: current-state, read-first, verification, remaining-work
- `docs/plans/primary-source-roadmap.md` — Prioritized primary-source roadmap with data contracts, location setup, adapter work packages, acceptance checks, and coding handoff. anchors: goal-and-priority, decisions-for-the-public-baseline, current-baseline-and-remaining-gaps, source-order-and-evidence, work-packages-in-order, coding-and-review-operating-plan
- `docs/plans/supervision-20261117.md` — Bounded delegated repair plan, immutable review gates, checkpoint discipline, and continuation priorities. anchors: initial-repair-and-evidence-gate, completion-evidence

## docs/reference/
- `docs/reference/cap-cancellation.md` — Primary CAP/NWS evidence, observed branch fixtures, conservative cancellation policy, and unresolved scope limits. anchors: evidence-and-its-limits, conservative-processing-policy
- `docs/reference/primary-sources.md` — Verified official-channel references and access limitations for weather, earthquakes, NYC/DC, IPAWS, hurricanes, and space weather. anchors: weather-warnings-and-faster-transports, earthquakes, nyc-and-dc-local-authority-channels, national-all-hazards-coverage, preparation-and-national-impact-candidates, how-to-maintain-this-evidence

## docs/reports/
- `docs/reports/REVIEW.md` — Immutable review candidates, reviewer metadata, separate findings by axis, and resolution status. anchors: candidates-and-reviewers, standards-findings-at-2c0f1e1, specification-findings-at-2c0f1e1, third-candidate-findings, standards, specification, evidence-limits
- `docs/reports/VALIDATION.md` — Public-candidate validation status, test evidence, review gates, and physical commissioning limits. anchors: current-status, automated-evidence, required-release-checks, limits
- `docs/reports/browser-focused-63da80f.md` — Fresh OpenAI review of the immutable browser/package slice and the cached-freshness finding.

## docs/spec/
- `docs/spec/o3-mvp.md` — Browser and Home Assistant implementation contract. anchors: architecture-and-privacy, room, home-assistant, research-and-verification

## home-assistant/
- `home-assistant/README.md` — Standalone Home Assistant bundle and commissioning instructions.

## skills/situareness-sources/
- `skills/situareness-sources/SKILL.md` — Official-source research and supported configuration workflow. covers: skills/situareness-sources/scripts/**, tests/skill/**

## skills/situareness-sources/references/
- `skills/situareness-sources/references/catalog-format.md` — Research catalog schema and validation guidance.
