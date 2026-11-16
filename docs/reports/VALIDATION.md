# Validation status

## Current status

Public-release preparation, November 16, 2026. This is a locally tested prototype with household outputs disabled by default. Production installation and audible commissioning have not been performed. A complete independent release review is still pending; interrupted or timed-out review attempts are not approvals.

## Automated evidence

The staged public tree passed static checks, 25 Node tests, 26 standard-library Home Assistant policy/boundary/packaging tests, six companion-catalog tests, and ten isolated Chromium browser tests during development. Three additional tests passed against the actual Home Assistant 2026.11.1 loader, entity registry, disk-backed storage and service registry, with source events and output targets simulated locally.

The real Home Assistant test dependency stack emitted five upstream deprecation warnings from Home Assistant HTTP and `backoff`. They were not suppressed or patched in the project. The standard-library suite passes with warnings treated as errors. Reproduction commands are in [setup](../setup.md) and [HA setup](../ha/README.md).

## Required release checks

Before publication, verify the complete staged public tree and fresh Git history contain only generic examples and approved public material. Check local-data exclusions and installation archives, run the complete current test commands, and perform a live anonymous read-only source smoke test. Record the exact public candidate SHA and independent reviewer evidence here when those checks finish.

## Limits

No actual household Home Assistant, private location footprint, enrolled phone, physical speaker or horn was tested. No alert was delivered to a real recipient. API acceptance and a quiet shadow period do not establish reliable receipt. Browser collection depends on Chrome execution and an awake computer; independent operation requires an installed and healthy Home Assistant monitor. Broader primary-source adapters and a room-to-HA health bridge remain planned in the [roadmap](../plans/primary-source-roadmap.md).
