# Validation status

## Current status

Public-release preparation, November 16, 2026. This is a locally tested prototype with household outputs disabled by default. Production installation and audible commissioning have not been performed. Independent standards and specification reviews identified issues in two candidates. The further repair pass is locally tested; fresh review and the final adversarial pass remain pending; see the [separate review record](REVIEW.md). A complete independent release review is still pending; interrupted or timed-out review attempts are not approvals.

## Automated evidence

The new repair checkpoint passed static checks, 34 Node tests, 33 standard-library Home Assistant policy/boundary/packaging tests, seven companion-catalog tests, and 14 isolated Chromium browser tests. Five additional tests passed against Home Assistant 2026.11.1, including the actual loader, entity/service registries, disk-backed private storage, recorder SQLite exclusions, and removal during an in-flight refresh. Source events and output targets were simulated locally. This is 93 automated tests total, with no household device delivery.

Ruff lint and formatting passed, and the standard-library HA suite passed with warnings treated as errors. A read-only live browser smoke test on November 16 received HTTP 200 from NWS, USGS and both BBC endpoints; NWS returned no current items in the sample NY/DC query. Two installation archive builds produced identical manifests and SHA-256 hashes. These checks cannot validate real CAP lineage or source availability beyond that observation.

The real Home Assistant test dependency stack emitted five upstream deprecation warnings from Home Assistant HTTP and `backoff`. They were not suppressed or patched in the project. The standard-library suite passes with warnings treated as errors. Reproduction commands are in [setup](../setup.md) and [HA setup](../ha/README.md).

## Required release checks

The initial public root was published after a verified privacy review with zero findings. Its clean history contains generic examples and approved public material. Review-driven changes are being checkpointed publicly with release review still pending; this is not a commissioned release. Before a release, recheck the complete tree and Git history. Check local-data exclusions and installation archives, run the complete current test commands, and perform a live anonymous read-only source smoke test. Record the exact public candidate SHA and independent reviewer evidence here when those checks finish.

## Limits

No actual household Home Assistant, private location footprint, enrolled phone, physical speaker or horn was tested. No alert was delivered to a real recipient. API acceptance and a quiet shadow period do not establish reliable receipt. Browser collection depends on Chrome execution and an awake computer; independent operation requires an installed and healthy Home Assistant monitor. Broader primary-source adapters and a room-to-HA health bridge remain planned in the [roadmap](../plans/primary-source-roadmap.md).
