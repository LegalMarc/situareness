# Supervisor continuation plan

Started November 16, 2026 US Eastern time, from clean `67d829e` on `wip/supervisor-handoff-20261117`. Preserve the interrupted patches. This is development with household outputs disabled; passing tests is separate from release review and physical commissioning.

## Initial repair and evidence gate

Three bounded implementation/research streams use `gpt-6.1-terra`, high effort, in the shared checkout. Only the supervisor stages, commits, integrates, and pushes. Browser/package ownership is extension, browser/runtime/UI tests, package builder and package tests, and browser setup guides. HA ownership is custom components, remaining HA tests and HA guides. Research owns the CAP reference note and public provenance fixtures. Shared contract, index, reports and handoff remain supervisor-owned.

Initial estimates are 15–25 minutes per stream, with progress expected within eight minutes. Stop and seek guidance at twice a job's estimate if it remains stuck; do not silently retry indefinitely. Independent Opus review is estimated at four to eight minutes per bounded pass, with a sixteen-minute stop bound.

1. Verify CAP/NWS primary evidence, distinguish directed cancellation from grouping, and agree the evidence-supported policy before rewriting cancellation.
2. Resolve the failing bounded-history test against the intended contract, formatting, archive dependency omission, and supported third-review findings. Add realistic regression coverage without weakening safety gates or assertions.
3. Integrate and run static, Node, stdlib HA, source-skill, browser, actual-HA, lint/format, live anonymous smoke, deterministic archive and extracted-bundle checks. Audit tracked tree, complete reachable publication history and archives using private local criteria without disclosing the criteria.
4. Freeze a clean immutable candidate. Run independent verified Opus standards and specification reviews. Fix supported findings through nits and repeat gates/review as appropriate. Then run a fresh adversarial pass on the immutable candidate, excluding prior narratives from both source and diff. Preserve exact model, candidate, base, raw results and limitations.
5. Publish accurately labeled checkpoints after staged/history privacy inspection, maintain the handoff, and keep `main` unchanged until release gates pass. No physical household action is authorized here.
6. After release gates, continue roadmap S0 public CI/privacy/build checks, then S1 versioned registry and measured freshness. Resolve material product decisions before implementation; continue reversible evidence work independently.

## Completion evidence

Each repair needs its regression or source evidence. Reviews must report zero unresolved supported findings before release approval. Archive builds must be reproducible and executable after extraction. Five upstream actual-HA dependency deprecations are an environment limitation, not permission to suppress warnings or patch vendor code.
