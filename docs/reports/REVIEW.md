# Independent review record

The release gate is open until the current candidate has zero supported unresolved findings on standards, specification, and fresh adversarial review. Interrupted attempts are not approvals. Public records omit private paths and local raw logs.

## Candidates and reviewers

| Candidate | Scope | Reviewer | Result |
| --- | --- | --- | --- |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Public privacy and clean history | Claude Opus 5.5, medium effort | PASS, zero findings |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Standards | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `6f55e0aa9699a2fd2a8ccf6b11a74421b6bb5d83` | Specification | Claude Opus 5.5, medium effort | Seven findings; repaired in next checkpoint |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Standards | Claude Opus 5.5, medium effort | Ten findings; repaired in the next checkpoint |
| `2c0f1e1864d1738e5c5488d3c0e423c0f0a7ebee` | Specification | Claude Opus 5.5, medium effort | Twelve findings; repaired in the next checkpoint |
| `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` | Standards | Claude Opus 5.5, medium effort | Ten findings; repaired on WIP branch |
| `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` | Specification | Claude Opus 5.5, medium effort | Nine findings; repaired on WIP branch |
| `63da80f6660667a529a3c4e0d1a0b7bc368760b5` | Focused browser/package | OpenAI `gpt-6-astra`, ultra | One P2 finding (`BROWSE-01`); repaired in `5ec38ac` |
| `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` | Standards | Claude Opus 5.5, medium effort | Seven findings (`run_id`: `20261117T164428Z-8b628a`, 260.4s); repaired in `e38a7fd` |
| `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` | Specification | Claude Opus 5.5, medium effort | Twelve findings (`run_id`: `20261117T164428Z-8b628a`, 225.2s); repaired in `e38a7fd` |
| `e38a7fdd88ff4877bf2969bad2658c5025ed583d` | Standards | Claude Opus 5.5, medium effort | Ten findings (`run_id`: `20261117T171412Z-dfb683`, 214.2s; zero browser/packaging defects); repaired in `83f328c` |
| `e38a7fdd88ff4877bf2969bad2658c5025ed583d` | Specification | Claude Opus 5.5, medium effort | Eight findings (`run_id`: `20261117T171412Z-dfb683`, 204.1s; zero browser/packaging defects); repaired in `83f328c` |
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Standards | Claude Opus 5.5, medium effort | Six findings (`run_id`: `20261117T173308Z-a2a286`, 260.9s; zero browser/packaging defects); repaired in `64b6fa0` |
| `83f328c518f4f9c5b87903b5ef56317127a94ae8` | Specification | Claude Opus 5.5, medium effort | Five findings (`run_id`: `20261117T173308Z-a2a286`, 267.0s; zero browser/packaging defects); repaired in `64b6fa0` |
| `64b6fa03ae148cd5964e23e7c1d1420c020175b2` | Standards | Claude Opus 5.5, medium effort | Three findings (0 High, 1 Medium, 2 Low; `run_id`: `20261117T174809Z-251d8a`, 384.8s; zero browser/packaging/catalog defects); repaired in `9308033` |
| `64b6fa03ae148cd5964e23e7c1d1420c020175b2` | Specification | Claude Opus 5.5, medium effort | Four findings (0 High, 1 Medium, 3 Low; `run_id`: `20261117T174809Z-251d8a`, 308.0s; zero HA-01/packaging defects); repaired in `9308033` |
| `930803369829a761cfd4593d4db3f153b8c13d64` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 4 Low, 2 Nit; `run_id`: `20261117T180834Z-0e141a`, 348.0s); repaired in `120c3c4` |
| `930803369829a761cfd4593d4db3f153b8c13d64` | Specification | Claude Opus 5.5, medium effort | Six findings (0 High, 1 Medium, 2 Low, 3 Nit; `run_id`: `20261117T180834Z-0e141a`, 394.4s); repaired in `120c3c4` |
| `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` | Standards | Claude Opus 5.5, medium effort | Four actionable findings + one non-blocking nit (0 Critical, 0 High, 1 Medium, 2 Low, 1+1 Nit; `run_id`: `20261117T184436Z-6d91c1`, 260.7s; zero browser/packaging/catalog defects); repaired in `f0e8a08` |
| `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` | Specification | Claude Opus 5.5, medium effort | Three findings (0 High, 0 Medium, 3 Low; `run_id`: `20261117T184436Z-6d91c1`, 244.0s; zero browser/packaging/catalog defects); repaired in `f0e8a08` |
| `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 1 High, 0 Medium, 1 Low, 2 Nit; `run_id`: `20261117T190130Z-35fadb`, 311.6s; zero browser/packaging/catalog defects); repaired in `a146710` |
| `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` | Specification | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 2 Low, 4 Nit; `run_id`: `20261117T190130Z-35fadb`, 283.6s; zero browser/packaging/catalog defects); repaired in `a146710` |
| `a1467104017f1efad31661370dbd19a4f37189ee` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 2 Low, 2 Nit; `run_id`: `20261117T192723Z-402b20`, 307.7s; zero browser/packaging/catalog/CAP/gate defects); repaired in `c0a909c` |
| `a1467104017f1efad31661370dbd19a4f37189ee` | Specification | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 1 Medium, 2 Low, 3 Nit; `run_id`: `20261117T192723Z-402b20`, 340.1s; zero browser/packaging/catalog/room defects); repaired in `c0a909c` |
| `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 2 Low, 4 Nit; `run_id`: `20261117T194649Z-7a1803`, 329.5s; zero browser/packaging/catalog/output-gate defects); repaired in `221ed9b` |
| `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 2 Medium, 1 Low, 0 Nit; `run_id`: `20261117T194649Z-7a1803`, 390.8s; zero browser/UI/packaging/catalog defects); repaired in `221ed9b` |
| `221ed9b037ea72e826f88716e14826c28e95a3df` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 4 Low, 2 Nit; `run_id`: `20261117T203507Z-d741fd`, 316.3s; zero CAP/browser/packaging/catalog/gate defects); repaired in `ad93ead` |
| `221ed9b037ea72e826f88716e14826c28e95a3df` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261117T203507Z-d741fd`, 287.4s; zero CAP/browser/UI/packaging/catalog defects); repaired in `ad93ead` |
| `ad93eada5a9222fe3120707180b24c2704dc5e7c` | Standards | Claude Opus 5.5, medium effort | Five findings (0 Critical, 0 High, 1 Medium, 2 Low, 2 Nit; `run_id`: `20261117T214931Z-ca8e85`, 318.6s; zero CAP/browser/packaging/catalog/quarantine defects); repaired in `3d18093` |
| `ad93eada5a9222fe3120707180b24c2704dc5e7c` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low-Medium, 1 Low; `run_id`: `20261117T214931Z-ca8e85`, 291.6s; zero CAP/qualification/quarantine/lifecycle/room/catalog defects); repaired in `3d18093` |
| `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` | Standards | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 0 Medium, 3 Low, 3 Nit; `run_id`: `20261117T221552Z-4d6117`, 309.4s; zero browser/packaging/catalog/gate defects); repaired in `6236ea8` |
| `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` | Specification | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 2 Low, 0 Nit + 1 capacity advisory; `run_id`: `20261117T221552Z-4d6117`, 308.7s; zero room/CAP/quarantine/outbox/lifecycle defects); repaired in `6236ea8` |
| `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` | Standards | Claude Opus 5.5, medium effort | Five findings (0 Critical, 0 High, 1 Medium, 3 Low, 1 Nit; `run_id`: `20261117T223104Z-7fe723`, 215.8s; zero browser/packaging/catalog/gate/overflow defects); repaired in `c81fb7f` |
| `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low, 1 Nit; `run_id`: `20261117T223104Z-7fe723`, 202.2s; zero room/gate/quarantine/store/overflow defects); repaired in `c81fb7f` |
| `c81fb7f5221b54a88453627dd5376216db0051b9` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 1 Medium, 1 Low, 0 Nit; `run_id`: `20261117T224454Z-a299b9`, 217.6s; zero core-safety/store/persistence/concurrency/gate/extension/attribute-list defects); repaired in `1078764` |
| `c81fb7f5221b54a88453627dd5376216db0051b9` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261117T224454Z-a299b9`, 373.9s; zero room/catalog/quarantine/overflow/store/lifecycle defects); repaired in `1078764` |
| `1078764e6e08da5560fdc95fbee6ea04021cd651` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 1 Medium, 1 Low, 2 Nit; `run_id`: `20261117T230054Z-57bc4c`, 286.1s; zero gate/routing/privacy/persistence/overflow/concurrency/browser/packaging defects); repaired in `3b35e7c` |
| `1078764e6e08da5560fdc95fbee6ea04021cd651` | Specification | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 1 Low, 1 Nit; `run_id`: `20261117T230054Z-57bc4c`, 394.5s; zero room/catalog/CAP/overflow/notification/gate defects); repaired in `3b35e7c` |
| `3b35e7c6edfc66cd9509771112307a3428ef0692` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 1 Medium, 2 Low, 1 Nit; `run_id`: `20261117T232125Z-6894d0`, 359.6s; zero gate/routing/privacy/shadow/room defects); repaired in `05a979e` |
| `3b35e7c6edfc66cd9509771112307a3428ef0692` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 2 Low, 1 Nit; `run_id`: `20261117T232125Z-6894d0`, 349.8s; zero room/gate/routing/overflow/store/lifecycle/packaging defects); repaired in `05a979e` |
| `05a979eb7695862aafd63b74c156dc72961d7bab` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 2 Medium, 2 Low, 0 Nit; `run_id`: `20261117T234711Z-2fcb85`, 408.5s; zero gate/store-roundtrip/journal/lifecycle/recorder/packaging/room/index defects); repaired in `c132758` |
| `05a979eb7695862aafd63b74c156dc72961d7bab` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 2 Low, 1 Nit; `run_id`: `20261117T234711Z-2fcb85`, 339.1s; zero CAP/quarantine/overflow/room/catalog/packaging defects); repaired in `c132758` |
| `c132758459e5ea4ff5c4573448a6af2192deee9c` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 2 Low, 2 Nit; `run_id`: `20261118T001451Z-588b6e`, 323.9s; zero gate/routing/privacy/persistence/lifecycle/browser/packaging defects); repaired in `6bd9bc9` |
| `c132758459e5ea4ff5c4573448a6af2192deee9c` | Specification | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 1 Low, 3 Nit; `run_id`: `20261118T001451Z-588b6e`, 386.0s; zero qualification/supersession/quarantine/cancellation/bounds/overflow/ack/room/packaging defects); repaired in `6bd9bc9` |
| `6bd9bc928f02ccce5d1b1b005419e2fbf8bdeeed` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 2 Low, 0 Nit; `run_id`: `20261118T002932Z-5e3623`, 361.5s; zero gate/routing/privacy/store-integrity/room/index defects); repaired in `698fe14` |
| `6bd9bc928f02ccce5d1b1b005419e2fbf8bdeeed` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 0 Low, 2 Nit; `run_id`: `20261118T002932Z-5e3623`, 230.3s; zero gate/CAP/quarantine/horizon/store/ack/offload/room/packaging defects); repaired in `698fe14` |
| `698fe14ee6dbd1b77518170893b2f835dbfc87bd` | Standards | Claude Opus 5.5, medium effort | Three findings (0 Critical, 1 High, 1 Medium, 1 Low, 0 Nit; `run_id`: `20261118T004922Z-f1724a`, 248.1s); repaired in `e13efc8` |
| `698fe14ee6dbd1b77518170893b2f835dbfc87bd` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261118T004922Z-f1724a`, 294.2s); repaired in `e13efc8` |
| `e13efc870a6dd0dc50e44175bcb8e10912c9750f` | Standards | Claude Opus 5.5, medium effort | Seven findings (0 Critical, 0 High, 1 Medium, 5 Low, 1 Nit; `run_id`: `20261118T011756Z-942760`, 335.6s); repaired in `039ea07` |
| `e13efc870a6dd0dc50e44175bcb8e10912c9750f` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261118T011756Z-942760`, 324.1s); repaired in `039ea07` |
| `039ea0726ec2bbe63462fd3283b56c532589b5c2` | Standards | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 1 Medium, 3 Low, 2 Nit; `run_id`: `20261118T014754Z-e43694`, 272.7s); repaired in `8637f5e` |
| `039ea0726ec2bbe63462fd3283b56c532589b5c2` | Specification | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 1 Medium, 1 Low, 0 Nit; `run_id`: `20261118T014754Z-e43694`, 182.6s); repaired in `8637f5e` |
| `8637f5e67bc6c5a28a3d2137f590e0a60da8c738` | Standards | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 2 Low, 1 Nit/Low; `run_id`: `20261118T020354Z-a2c113`, 297.6s; zero gate/routing/privacy/persistence/CAP/browser/packaging/index defects); repaired in `bd617e2` |
| `8637f5e67bc6c5a28a3d2137f590e0a60da8c738` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 1 High, 0 Medium, 1 Low, 1 Nit; `run_id`: `20261118T020354Z-a2c113`, 304.0s; zero gate/routing/CAP/store/ack-reuse/lifecycle/room/catalog defects); repaired in `bd617e2` |
| `bd617e2cf6786a29d510c7a16a5d933dafd48bed` | Standards | Claude Opus 5.5, medium effort | Nine findings (0 Critical, 0 High, 0 Medium, 6 Low, 3 Nit; `run_id`: `20261118T022802Z-e54306`, 392.1s; zero gate/routing/privacy/persistence/compatibility/index/packaging defects); repaired in `18342bc` |
| `bd617e2cf6786a29d510c7a16a5d933dafd48bed` | Specification | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 2 Low, 2 Nit; `run_id`: `20261118T022802Z-e54306`, 441.5s; zero qualification/CAP/bounds/degraded/outbox-overflow/ack/room/catalog defects); repaired in `18342bc` |
| `18342bc3648d0515a0c0307353e4cdf8c0a6954e` | Standards | Claude Opus 5.5, medium effort | Six findings (0 Critical, 0 High, 1 Medium, 4 Low, 1 Nit; `run_id`: `20261118T025653Z-90db5a`, 240.5s; zero gate/routing/privacy/recorder/stop-cancellation/store-validation/room defects); repaired in `4ea74ca` |
| `18342bc3648d0515a0c0307353e4cdf8c0a6954e` | Specification | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 1 Medium, 2 Low, 1 Nit; `run_id`: `20261118T025653Z-90db5a`, 276.3s; zero gate/routing/CAP/quarantine/overflow/ack/stop-unload/room/INDEX defects); repaired in `4ea74ca` |
| `4ea74ca4a136f95815777a3d71035ce4c1136a7b` | Standards | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 1 Low, 2 Nit; `run_id`: `20261118T031956Z-d2125a`, 312.2s; zero live-gate/routing/privacy/persistence-compat/concurrency/CAP-timestamp/index defects); repaired in `0cb3656` |
| `4ea74ca4a136f95815777a3d71035ce4c1136a7b` | Specification | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 0 Medium, 2 Low, 2 Nit; `run_id`: `20261118T031956Z-d2125a`, 316.6s; zero qualification/quarantine/cancellation/outbox-overflow/ack/lifecycle/packaging/catalog defects); repaired in `0cb3656` |
| `0cb365603be3c7935e3a549a4b01b9ec8fe2e026` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 0 Low, 2 Nit; `run_id`: `20261118T155112Z-c46492`, 275.5s; zero persistence/lifecycle/delivery/concurrency/safety-gate/privacy/browser-room defects); repaired in `62337c2` |
| `0cb365603be3c7935e3a549a4b01b9ec8fe2e026` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low, 1 Nit; `run_id`: `20261118T155112Z-c46492`, 251.4s); repaired in `62337c2` |
| `62337c2d56ec9ed0eb7851e9fea92445af0331b4` | Standards | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 1 Medium, 2 Low, 1 Low/Nit; `run_id`: `20261118T160611Z-e864d7`, 313.6s; zero shadow-default/live-gate/routing/horn/privacy/stop-unload/browser-room defects); repaired in next candidate |
| `62337c2d56ec9ed0eb7851e9fea92445af0331b4` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 1 Low, 2 Nit; `run_id`: `20261118T160611Z-e864d7`, 346.7s; zero qualification/CAP/quarantine/delivery/overflow/ack/lifecycle/room defects); repaired in next candidate |
| `0cb365603be3c7935e3a549a4b01b9ec8fe2e026` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 0 Medium, 0 Low, 2 Nit; `run_id`: `20261118T155112Z-c46492`, 275.5s; zero persistence/lifecycle/delivery/concurrency/safety-gate/privacy/browser-room defects); repaired in next candidate |
| `0cb365603be3c7935e3a549a4b01b9ec8fe2e026` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 1 Medium, 1 Low, 1 Nit; `run_id`: `20261118T155112Z-c46492`, 251.4s); repaired in next candidate |

| `30e7149dd9d7a3a71be6efca535c5ef6515878ae` | Standards | Claude Opus 5.5, medium effort | Three findings (0 Critical, 1 High, 0 Medium, 1 Low, 1 Nit; `run_id`: `20261118T180246Z-dd8694`, 216.4s); repaired in `aab5fb1` |
| `30e7149dd9d7a3a71be6efca535c5ef6515878ae` | Specification | Claude Opus 5.5, medium effort | Three findings (0 Critical, 0 High, 0 Medium, 2 Low, 1 Nit; `run_id`: `20261118T180246Z-dd8694`); repaired in `aab5fb1` |
| `aab5fb1c0afc86d0e782a0a6a622a97b36ac0c33` | Standards | Claude Opus 5.5, medium effort | Two findings (0 Critical, 0 High, 1 Medium, 1 Low, 0 Nit; `run_id`: `20261118T182230Z-b16dc5`, 381.8s; zero gate/privacy/persistence/upgrade defects); repaired in `14b5b04` |
| `aab5fb1c0afc86d0e782a0a6a622a97b36ac0c33` | Specification | Claude Opus 5.5, medium effort | Four findings (0 Critical, 0 High, 1 Medium, 2 Low, 1 Nit; `run_id`: `20261118T182230Z-b16dc5`, 297.0s; zero gate/routing/malformed-store/journal-lost/ack/stop-unload/room defects); repaired in `14b5b04` |
| `14b5b04b2a5a0f4a6b2a4e63dd128832eb8952c6` | Standards | Claude Opus 5.5, medium effort | Three doc/notice findings (0 Critical, 0 High, 1 Medium, 1 Low, 1 Nit; `run_id`: `20261118T183557Z-2cfe8f`, 202.9s; zero safety-gate/privacy/persistence/concurrency defects); repaired in next candidate |
| `14b5b04b2a5a0f4a6b2a4e63dd128832eb8952c6` | Specification | Claude Opus 5.5, medium effort | Three doc findings (0 Critical, 0 High, 1 Medium, 2 Low, 0 Nit; `run_id`: `20261118T183557Z-2cfe8f`; zero code/packaging/room/CAP/lifecycle defects); repaired in next candidate |

The exact model reported by completed CLI result metadata was `claude-opus-5-5`. The second standards/specification passes took 204.4 and 205.3 seconds respectively. They independently read an immutable full-source snapshot, complete change diff from the public root, documented contract/standards, and raw local test evidence. They executed no code or physical output.

## Standards findings at 2c0f1e1

Codes preserve the standards reviewer's separate axis. Repairs are implemented and locally tested; all remain open pending independent re-review.

| Code | Severity | Finding |
| --- | --- | --- |
| STD-HA-01 | Medium | Inactive equivalent-action history can suppress renewed exposure indefinitely. |
| STD-HA-02 | Low | Ancestor cancellation can leave a descendant retry suspended. |
| STD-HA-03 | Low | Entry removal can race an in-flight save and recreate the private store. |
| STD-HA-04 | Low | One oversized feature or lineage can stop unrelated warning decisions. |
| STD-BR-01 | Medium | The storage-cap warning becomes permanent during ordinary use. |
| STD-BR-02 | Low | A bundled-default load failure leaves the room connecting indefinitely. |
| STD-BR-03 | Low | Explicit context-dashboard null loses to a legacy key. |
| STD-BR-04 | Nit | A configurable dashboard URL retains a fixed World Monitor label. |
| STD-BR-05 | Nit | Startup no longer immediately collects overdue sources. |
| STD-HA-05 | Nit | Pending health does not distinguish suspended work. |

## Specification findings at 2c0f1e1

Codes preserve the specification reviewer's separate axis. Repairs are implemented and locally tested; all remain open pending independent re-review.

| Code | Severity | Finding |
| --- | --- | --- |
| SPEC-HA-01 | Medium | Root-only references can cause duplicate critical plans and retries. |
| SPEC-HA-02 | Medium | A cancellation can miss work migrated to a successor. |
| SPEC-HA-03 | Low | A changed unapproved action retains an old pending action. |
| SPEC-HA-04 | Low | One oversized alert stops all monitoring in the configured states. |
| SPEC-HA-05 | Low | A migrated retry keeps the predecessor's source link. |
| SPEC-HA-06 | Nit | Repeated outbox/event scans can block the event loop at documented bounds. |
| SPEC-HA-07 | Nit | The deduplication description no longer matches inactive-history handling. |
| SPEC-RM-01 | Medium | Global retention loss is permanently mixed into the freshness banner. |
| SPEC-RM-02 | Low | Context-link labeling and explicit-null precedence are misleading. |
| SPEC-RM-03 | Low | Disabled or failed NWS cached items can appear current indefinitely. |
| SPEC-RM-04 | Low | An all-disabled room appears healthy and busy. |
| SPEC-RM-05 | Nit | Manual/install refreshes do not reset collection cadence. |

## Third candidate findings

Candidate `847d0e56853f4d9bfdf4cdf3d1812f836bf58eba` passed 93 local automated tests, but independent Opus 5.5 medium-effort reviews found the following. Workers were interrupted by account usage limits; partial repairs and preliminary primary-source captures are preserved in the WIP handoff, with supported findings still open. This is not release approval. Previous narratives were deliberately omitted from the review packets, while executable code, contracts, tests and standards were included.

### Standards

| Code | Severity | Finding |
| --- | --- | --- |
| SR-01 | Medium-high | Long quarantine can erase delivered-action history and cause duplicate alarms. |
| SR-02 | Low | Quarantined/unconfirmed states fail to resolve and can revive legacy history. |
| SR-03 | Low-medium | Reload can discard acceptance records for in-flight delivery. |
| SR-04 | Low | Carried retry items are not deduplicated against each other after a merge. |
| SR-05 | Low | The journal cap can evict a current record and cause persistent refresh failure. |
| SR-06 | Low | Backward clock correction can stall Chrome alarm collection. |
| SR-07 | Low | Whole-component cancellation may stop a continuing sibling segment; source semantics need verification. |
| SR-08 | Low | The HA guide contradicts itself about partial collections. |
| SR-09 | Nit | Retention priority ignores source freshness. |
| SR-10 | Nit | Dashboard setting instructions and UI label drift. |

### Specification

| Code | Severity | Finding |
| --- | --- | --- |
| SPEC-01 | Medium | Quarantine can discard a cancellation tombstone. |
| SPEC-02 | Low | Legacy journal migration can lose or misapply action history. |
| SPEC-03 | Low | The journal cap can evict current records and cancellation evidence. |
| SPEC-04 | Low | Reload can duplicate in-flight deliveries. |
| SPEC-05 | Low | Room retention priority ignores freshness. |
| SPEC-06 | Low | Worker-side bundled-configuration failure is not identified clearly. |
| SPEC-07 | Nit | New neutral/disabled/cached classes lack distinct visual styles. |
| SPEC-08 | Nit | Dashboard documentation label differs from the UI. |
| SPEC-09 | Nit | A helper assumes an array without validating it. |

## Evidence limits

Candidate `2c0f1e1` passed 79 automated tests and `847d0e5` passed 93, plus live anonymous browser reads and deterministic packaging, before their respective findings were discovered. These results do not describe the newer failing WIP. Those successes did not cover the reported triggers. Home Assistant source and delivery targets were simulated. The live smoke returned no NWS alerts, so it cannot validate real CAP lineage. Physical commissioning, broader primary-source adapters, automatic health escalation and the browser-to-HA health bridge remain separate work.

## Supervisor continuation findings

Candidate `fcc9072c9d221a353d2a0483f22d3a0c3e74f89a` passed 128 local tests, but independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T164428Z-8b628a`; 260.4s standards, 225.2s specification) failed with seven standards and twelve specification findings. Prior focused browser review at `63da80f6660667a529a3c4e0d1a0b7bc368760b5` ([BROWSE-01](browser-focused-63da80f.md)) and earlier internal checks (`CAP-SCOPE-01`, `CAP-RENEW-01`, `CAP-STORE-01`, `CAP-ID-01`) are preserved in history.

### Standards findings at fcc9072

| Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- |
| HA-01 | High | Unbounded cancellation protection eventually triggers permanent `CancellationEvidenceOverflow` shutdown. | Enforced 7-day `MAX_ACCEPTANCE_AGE` and anchored `cancellation_horizon`; re-review pending. |
| HA-02 | Medium | `seen_cancel` turns unrelated or transient fetch errors into permanent `CancellationEvidenceLost`. | Removed `seen_cancel` / `CancellationEvidenceLost` and kept malformed-cancel scoping bounded; re-review pending. |
| HA-03 | Medium | Coordinator retry filter restricts the entire component instead of uncertain records. | Removed component-wide filter while keeping `"cancelled"` drop and `"quarantined"` retry suspension; re-review pending. |
| HA-04 | Low | `CancelledError` is swallowed after seeing a Cancel and latches degraded mode on unload/shutdown. | Let `asyncio.CancelledError` propagate untouched; re-review pending. |
| HA-05 | Low | Degraded health misreports `quarantine_ambiguous` and `cancellation_uncertain` regardless of cause. | Added `degraded_reason`/`degraded_at` and accurate diagnostic flags; re-review pending. |
| HA-06 | Low | Superseded cancellation-group records force `prior_state: "active"`, and long non-Cancel features fail the whole poll. | Removed forged `prior_state`; quarantined oversized/malformed non-Cancel features per feature/lineage; re-review pending. |
| DOC-01 | Nit | `tests/fixtures/cap/**` omitted from `docs/INDEX.md` coverage. | Added `covers: tests/fixtures/cap/**` on the `cap-cancellation.md` entry. |

### Specification findings at fcc9072

| Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- |
| SIT-H1 | High | Historic cancellation uncertainty sets poll-wide `quarantined = True` and stalls resolution indefinitely. | Scoped unconfirmed/quarantined resolution per group and active/current-cancel presence; re-review pending. |
| SIT-H2 | High | Cancellation evidence has no retention horizon and deterministically hits the 1,000-record cap. | Added 7-day `MAX_ACCEPTANCE_AGE` and source-anchored `cancellation_horizon` expiry; re-review pending. |
| SIT-H3 | High | Transient or unrelated fetch errors after observing a Cancel permanently latch degraded state. | Removed `CancellationEvidenceLost` fetch-error latching; re-review pending. |
| SIT-M1 | Medium | `CancelledError` is swallowed and writes a degraded latch during unload/shutdown. | Propagates `asyncio.CancelledError` untouched; re-review pending. |
| SIT-M2 | Medium | Degraded mode stops collection and lacks an authorized recovery path. | Continues collection while output-blocked for uncorrupted degradation; recovers via 7-day `degraded_until` or `acknowledge_degraded_at`; re-review pending. |
| SIT-M3 | Medium | Continuing descendant retry is blocked by an unrelated Cancel in the same component. | Removed component-wide outbox filter so uncancelled siblings/descendants migrate cleanly; re-review pending. |
| SIT-M4 | Medium | Single malformed non-Cancel feature fails the entire poll. | Quarantines malformed/oversized non-Cancel features per feature/lineage in `collector.py`; re-review pending. |
| SIT-M5 | Medium | Nested malformed persisted journal entries crash every poll instead of latching `malformed_store`. | Added `_valid_persisted_store` deep schema validation; re-review pending. |
| SIT-M6 | Medium | `_degraded_health()` reports invented `partial`/`quarantine_ambiguous`/`cancellation_uncertain` values. | Reports actual collected counts/events and cause-accurate flags; re-review pending. |
| SIT-L1 | Low | Worker bundled-config errors render as collector disconnect and `runAction` regex omits them. | Added `isBundledConfigError`, schema bootstrap check, and `runAction` regex fix; re-review pending. |
| SIT-L2 | Low | Disabled/failed/overdue USGS and BBC items lack visible cached badges, drifting from `o3-mvp.md`. | Extended `"cached"` badge to non-weather items when `sourceStates` is unavailable/overdue and updated `docs/setup.md`; re-review pending. |
| SIT-N1 | Nit | Superseded records in cancellation groups hardcode `prior_state: "active"`. | Removed the hardcode and guarded `referenced` updates; re-review pending. |

### Candidate e38a7fd Opus review findings

Candidate `e38a7fdd88ff4877bf2969bad2658c5025ed583d` passed 141 local tests and had zero supported defects in the browser room, UI, packaging, and source skill. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T171412Z-dfb683`; 214.2s standards, 204.1s specification) reported ten standards and eight specification findings in Home Assistant and HA documentation:

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Alerts first qualifying while degraded mark `actions` and fail to deliver after recovery. | Strip withheld plan fingerprints from `actions` while degraded; re-review pending. |
| Standards / Spec | SIT-M2, SIT-M3 / SIT-R1 | High / Medium | `acknowledge_degraded_at` accepts future timestamps, can be reused, and clears `malformed_store` or `degraded_at=None` legacies. | Enforced one-shot `degraded_at <= ack <= now`, backfilled `degraded_at` for legacy degraded stores, and kept `malformed_store` unacknowledged until store repair/replacement; re-review pending. |
| Spec | SIT-R2 | High | Normalized `Actual Cancel` with no recoverable references avoids `malformed_cancellation`. | Trigger `malformed_cancellation` for normalized `Actual Cancel` with empty `references`; re-review pending. |
| Spec | SIT-R3 | High | Update valid in collector but rejected against journal in `reconcile` still hides predecessor `P`. | Added `resolve_candidates` in `domain.py` and coordinator so rejected Updates restore valid predecessors; re-review pending. |
| Standards / Spec | SIT-M1 / SIT-R4 | Medium | Upgrading legacy Cancel records or replaying Cancel with `cap_references_valid=False` latches false `conflicting_cancellation`. | Normalized incoming `cap_references` and lineage matching, and treated pre-upgrade records lacking `cancel_message` as legacy uncertainty; re-review pending. |
| Standards / Spec | SIT-L1 / SIT-R5 | Low | `degraded_at` keeps only the earliest trigger timestamp when re-triggered. | Always update `degraded_at` and `degraded_until` on each active trigger; re-review pending. |
| Standards / Spec | SIT-L4 / SIT-R6 | Low | Deep store validation omits outbox `location`/`created` and record `updated`/`inactive_since`/`cancel_message` checks. | Completed `_valid_persisted_store` validation across all dereferenced fields; re-review pending. |
| Standards / Spec | SIT-L2, SIT-L3 / SIT-R7 | Low | `cancellation_uncertain` persists on resolved outbox items, `_degraded_health()` keeps `quarantine_ambiguous=True` across clean polls, and docs misstate `malformed_cancellation` triggers. | Scoped `cancellation_uncertain` and `quarantine_ambiguous` to active/current-poll evidence and synchronized docs; re-review pending. |
| Standards / Spec | SIT-N1 / SIT-R8 | Nit | Dead `_store_recovered` attribute. | Removed `_store_recovered`; re-review pending. |
| Standards | SIT-N2 | Nit | Documented `degraded_until` missing from sensor attributes. | Exposed `degraded_until` on normal and degraded sensor health; re-review pending. |

### Candidate 83f328c Opus review findings

Candidate `83f328c518f4f9c5b87903b5ef56317127a94ae8` passed 143 local tests and had zero supported defects in the browser room, UI, packaging, and catalog validator. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T173308Z-a2a286`; 260.9s standards, 267.0s specification) reported six standards and five specification findings in Home Assistant and HA documentation:

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Suspended quarantined retry collides in `_outbox_signature` with an independent sibling in the same group. | Key quarantined outbox items separately by `incident_id` in `_outbox_signature`; re-review pending. |
| Standards / Spec | SIT-H2 / SR-M1 | High / Medium | Conflicting `Cancel` overwrites prior `C -> T1` evidence, allowing `T1` replay after recovery. | Preserved prior `cap_identity`/`cap_references`/`cancel_message`/`lineage` on `conflicting_prior_cancel` while quarantining conflicting references; re-review pending. |
| Standards / Spec | SIT-M1 / SR-H1 | Medium / High | Newly qualifying sibling alerts and `CancellationEvidenceOverflow` polls fail to clear withheld `actions`. | Pop `(group, fp)` from `records` on `now` across all siblings and before raising `CancellationEvidenceOverflow`; re-review pending. |
| Standards | SIT-M2 | Medium | Undelivered pre-degradation outbox items expire past `MAX_AGE` during >15m degradation. | Preserved active retry budget across degradation via `last_degraded_poll` and `degraded_delta` migration without duplicating sent targets; re-review pending. |
| Spec | SR-M2 | Medium | Conflicting duplicate feature in `collector.py` fails the entire poll via `ValueError`. | Quarantined conflicting duplicate features per feature/lineage (and set `conflicting_cancellation` for duplicate Cancels); re-review pending. |
| Standards | SIT-L1 | Low | Docs overstate what `acknowledge_degraded_at` clears while an active trigger persists. | Clarified in `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md` that ongoing triggers refresh `degraded_at`/`degraded_until`; re-review pending. |
| Standards / Spec | SIT-L2 / SR-L1 | Low | Deep store validation misses unhashable `prior_state`/`action_identity`/`fingerprint`/`action_fingerprint`/`action_affected` and outbox payload fields. | Completed `_valid_persisted_store` validation across all record and outbox fields; re-review pending. |
| Spec | SR-L2 | Low | `malformed_store` reports `degraded_at: null` and `degraded_until: null`. | Populated `degraded_at` and `degraded_until` from detection time while keeping `malformed_store` latched until store repair/replacement; re-review pending. |

All findings from `fcc9072`, `e38a7fd`, and `83f328c` were repaired in `64b6fa0`.

### Candidate 64b6fa0 Opus review findings

Candidate `64b6fa03ae148cd5964e23e7c1d1420c020175b2` passed 146 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 High findings** and zero packaging or catalog defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T174809Z-251d8a`; 384.8s standards, 308.0s specification) reported 1 Medium + 2 Low standards findings and 1 Medium + 3 Low specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | SPEC-01 | Medium | Missing/empty persisted store on an already-initialized config entry silently resets history without latching `journal_lost`. | Added `entry.data["journal_initialized"]` detection latching `journal_lost` with output withheld and read-only collection preserved; re-review pending. |
| Standards | SIT-REV-M1 | Medium | Overflow drops `state == "cancelled"` records before non-cancel protected items and computes `degraded_until` without dropped-component horizons. | Seeded `state == "cancelled"` protection and expiry in `domain.py`, prioritized `Cancel`/`cancelled` records under overflow, and propagated `dropped_horizon` into `degraded_until` without shrinking earlier horizons; re-review pending. |
| Spec / Standards | SPEC-02 / SIT-REV-L1 | Low | Poll-time `_try_acknowledge(now)` lets future-dated `acknowledge_degraded_at` auto-clear on later polls without reload. | Evaluated `_try_acknowledge` solely at coordinator construction against load time; re-review pending. |
| Spec | SPEC-03 | Low | `_try_acknowledge()` clears `last_degraded_poll`, losing retry-budget credit for the final interval before recovery poll. | Preserved `last_degraded_poll` until after `_migrate_and_prune_outbox()` runs on recovery; re-review pending. |
| Spec | SPEC-04 | Low | `"Cached · source unavailable"` badge suppressed on cached `not_in_latest_fetch` (and missing-lifecycle) NWS items when source is unavailable. | Appended `"cached"` pill alongside `"not_in_latest_fetch"` when `isEventSourceUnavailable(...)` is true and defaulted missing/unknown NWS lifecycle on unavailable sources to `"cached"` (keeping `"expired"` exclusive); re-review pending. |
| Standards | SIT-REV-L2 | Low | Operational history-loss/re-alert caveats for missing stores, store replacement, and early overflow acknowledgement missing from docs alongside `journal_lost`. | Documented `journal_lost`, load-time-only acknowledgement, overflow `dropped_horizon`, and tombstone-loss re-alert risks across `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |

All findings from `fcc9072`, `e38a7fd`, `83f328c`, and `64b6fa0` were verified fixed at `9308033`.

### Candidate 9308033 Opus review findings

Candidate `930803369829a761cfd4593d4db3f153b8c13d64` passed 150 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical and 0 High findings** and zero regressions in prior fixes. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T180834Z-0e141a`; 348.0s standards, 394.4s specification) reported 1 Medium + 4 Low + 2 Nit standards findings and 1 Medium + 2 Low + 3 Nit specification findings (11 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-R1 | Medium | Recoverable oversized/conflicting `Actual Cancel` anywhere in monitored states triggers global 7-day degraded lockdown without operator notification. | Scoped recoverable oversized/conflicting `Actual Cancel`s (non-empty NWS target refs within 5,000-ID cap) per targeted lineage/descendants (`quarantined_cancel_lineages`), delineated Policy 4 vs Policy 6, and added `situareness_degraded` HA persistent notification; re-review pending. |
| Spec | SIT-SPEC-01 | Medium | Raw `quarantined_lineages` references enter `lineage_index()`, tainting independent sibling alerts sharing a root. | Excluded `quarantine_events` from `lineage_index()`, stripped raw refs for all `invalid_ids` in `grouping_events`, and replaced group-level quarantine with per-ID `quarantined_event_ids`/`quarantined_record_ids`; re-review pending. |
| Standards | SIT-R2 | Low | `async_stop()` waits on multi-page fetches during unload/reload. | Tracked `_fetch_task`, cancelled in-flight `fetch()` in `async_stop()`, and aborted before post-stop saves; re-review pending. |
| Standards | SIT-R3 | Low | Poll-refreshed `degraded_at` and `degraded_until` churn recorder history every minute. | Excluded `degraded_at` and `degraded_until` alongside `events` and `last_success` in `SituarenessSensor._unrecorded_attributes`; re-review pending. |
| Standards | SIT-R4 | Low | `malformed_store` reports a moving `degraded_until` timestamp it never honors. | Set `malformed_store` `degraded_until: None` and persisted stable `malformed_store_at` on the config entry until store repair; re-review pending. |
| Standards | SIT-R5 | Low | `runAction` regex routes `"Bundled configuration..."` errors to toast instead of `showDisconnected`. | Removed `Bundled configuration` from `runAction` toast regex so action failures show `"Room could not start"` and disable controls; re-review pending. |
| Spec | SIT-SPEC-02 | Low | `_valid_persisted_store` skips `bool` checks for `initialized` and `was_live`. | Required `bool` for `degraded`, `initialized`, and `was_live` in `_valid_persisted_store`; re-review pending. |
| Spec | SIT-SPEC-03 | Low | `quarantined_count` undercounts earlier identical copies of a conflicting duplicate (`[A, A, A_conflict]`). | Tracked per-ID `id_counts` in `collector.py` and added `id_counts[eid] + 1` on first conflict; re-review pending. |
| Standards / Spec | SIT-R6 / SIT-DOC-04 | Nit | 5,000-identifier quarantine cap skips feature IDs and conflicting-duplicate IDs. | Unified accounting via `add_quarantined_lineage` across all retained unique IDs (feature IDs + ref URLs + conflicting duplicates); re-review pending. |
| Spec | SIT-UI-05 | Nit | `isEventSourceUnavailable` overwrites `state.interval_minutes` when `sources` omits the entry. | Fell back to `config?.interval_minutes ?? state.interval_minutes`; re-review pending. |
| Standards / Spec | SIT-R7 / SIT-DOC-06 | Nit | `docs/reference/cap-cancellation.md` line 3 disclaimer contradicts line 19 assertions. | Reworded line 3 and Policy 6 so `cap-cancellation.md` clearly states required policy while test/review evidence verifies conformance separately; re-review pending. |

All findings from candidate `9308033` (and earlier `fcc9072`, `e38a7fd`, `83f328c`, and `64b6fa0`) were verified fixed at `120c3c4`.

### Candidate 120c3c4 Opus review findings

Candidate `120c3c4362ff529a62f3e43e59ff10a8b3c02ec2` passed 154 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T184436Z-6d91c1`; 244.0s specification, 260.7s standards) reported 3 Low specification findings and 1 Medium + 2 Low + 1+1 Nit standards findings (5 unique actionable findings + 1 non-blocking doc nit):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-HA-01 | Medium | Invalid `Actual Cancel` persists raw `refs` in `lineage`, unioning root-sharing siblings on Poll 2 into `ambiguous_groups`. | Isolated invalid `Cancel` target references in `uncertain_targets` (validated in `_valid_persisted_store`) without persisting raw `lineage` edges and isolated `nodes` `is_cancel` checks; re-review pending. |
| Spec / Standards | SIT-SPEC-01 / SIT-HA-02 | Low | `journal_lost` and persisted degraded states delay persistence/notification until after a successful fetch, and unload/remove leaves `situareness_degraded` active. | Stabilized `journal_lost_at` on config entry, persisted `journal_lost` before first fetch, synced `situareness_degraded` at init and pre-fetch, and dismissed it in `async_stop`/`async_unload_entry`/`async_remove_entry`; re-review pending. |
| Standards | SIT-HA-03 | Nit | Stopping during the first fetch while healthy returns `_degraded_health()` (`evidence_degraded: True`). | Added `_stopped_health()` returning non-degraded empty health when `not self.degraded`; re-review pending. |
| Spec | SIT-DOC-03 | Low | Docs lack concrete recovery steps for `malformed_store` when deleting the corrupt disk file triggers `journal_lost`. | Documented exact `malformed_store` repair/replacement options (repair disk JSON + reload, delete/empty disk store + reload -> `journal_lost`, or remove & re-add config entry) across `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |
| Standards / Spec | SIT-DOC-01 / SIT-DOC-02 | Low | `docs/ha/README.md:45` states seven real-HA tests and omits `journal_lost` scenarios. | Updated `docs/ha/README.md:45` to report the exact passing real-HA test count and list both `journal_lost` scenarios; re-review pending. |
| Standards (note) | SIT-DOC-02 | Nit | `docs/ha/README.md:27` overstates clearing condition for historic uncertainty (`and any suspended outbox retry expires`). | Clarified that `ended_or_absent` clears once absent while suspended outbox retries prune/expire separately under the 15-minute limit; re-review pending. |

All findings from candidate `120c3c4` were verified fixed at `f0e8a08`.

### Candidate f0e8a08 Opus review findings

Candidate `f0e8a08eb8f09585666b3ba5b2f966e57cc65a25` passed 158 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 browser/UI/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T190130Z-35fadb`; 283.6s specification, 311.6s standards) reported 1 High + 1 Low + 2 Nit standards findings and 1 Medium + 2 Low + 4 Nit specification findings (9 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-H1 | High | Replaying an identical invalid-CAP Cancel on Poll 2 triggers `conflicting_prior_cancel` -> global `conflicting_cancellation` because Poll 1 persisted `cap_identity=None`/`cap_references=None`/`lineage=[eid]`. | Persisted incoming Cancel's `cap_identity`/`cap_references` + `uncertain_targets` on first save, matched `uncertain_targets` in `conflicting_prior_cancel`, routed invalid-Cancel `records` cleanly in `cancellation_evidence()`, and verified across Poll 2 replays; re-review pending. |
| Spec | SIT-HA-01 | Medium | Unparseable JSON store file raises during `store.async_load()` or renames to `.corrupt.*` (`None`) instead of latching `malformed_store`. | Caught `store.async_load()` exceptions (`["unreadable"]`) and detected `.corrupt.*` backup files (`["corrupt_json"]`) in `async_setup_entry`, clearing backups on clean save or removal; re-review pending. |
| Spec | SIT-HA-02 | Low | Upgrading a base entry whose existing store triggers `malformed_store` never sets `journal_initialized`, so deleting the store fails to latch `journal_lost`. | Set `journal_initialized: True` when loading any non-empty valid store or entering `malformed_store`; re-review pending. |
| Spec | SIT-HA-03 | Low | Outbox exceeding 5,000 targets raises `ValueError` before `_save()`, failing every poll without durable save or notification. | Bounded outbox at 5,000 targets, saved reconciled records/outbox under durable `outbox_overflow` degraded state, and raised `situareness_degraded`; re-review pending. |
| Standards | SIT-L1 | Low | Duplicated quarantined/cancelled record builder blocks in `reconcile()` and degraded save blocks in `_update_once()`. | Extracted `_cancel_record_identity`, `_quarantined_record`, `_expire_cancellation_horizons`, `_bound_records`, `_latch_degraded`, and `_persist_degraded_poll`; re-review pending. |
| Spec | SIT-HA-04 | Nit | `_stopped_health()` reports `suspended_count: 0` even when `outbox` is non-empty. | Set `suspended_count: len(self.outbox)` in `_stopped_health()`; re-review pending. |
| Spec / Standards | SIT-HA-05 / SIT-N1 | Nit | `async_remove_entry()` deletes the store before dismissing `situareness_degraded`, contrary to spec ordering. | Dismissed `situareness_degraded` before `Store.async_remove()` and aligned `o3-mvp.md`; re-review pending. |
| Spec | SIT-DOC-01 | Nit | `collector.py` counts unique quarantined identifiers per lineage rather than per poll. | Tracked `seen_quarantine_ids` across the entire poll in `fetch()` against the 5,000-ID bound; re-review pending. |
| Spec / Standards | SIT-TEST-01 / SIT-N2 | Nit | Tests contain a leftover drafting comment and inline external review IDs. | Removed the drafting comment and replaced all review-code tags in `tests/ha/**` with behavioral comments; re-review pending. |

All findings from candidate `f0e8a08` were verified fixed at `a146710`.

### Candidate a146710 Opus review findings

Candidate `a1467104017f1efad31661370dbd19a4f37189ee` passed 162 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog/CAP-core/gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T192723Z-402b20`; 307.7s standards, 340.1s specification) reported 2 Low + 2 Nit standards findings and 1 Medium + 2 Low + 3 Nit specification findings (8 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | HA-ACK-01 | Medium | `_try_acknowledge()` deletes `journal_lost_at` before `_save()` runs; if the first poll after reload fails, retries regenerate `degraded_at = now` and lose the acknowledgement. | Retained `journal_lost_at` in `entry.data` inside `_try_acknowledge()` so it clears only when `_save()` persists non-degraded state; re-review pending. |
| Spec | HA-STORE-01 | Low | `except Exception:` around `store.async_load()` treats transient `OSError`/permission errors as `malformed_store`. | Caught only JSON/value/type/key/unsupported-version errors as `malformed_store` and raised `ConfigEntryNotReady` on `OSError`/unexpected load errors; re-review pending. |
| Standards / Spec | SIT-R2 / HA-NOTIF-01 | Low | `_sync_degraded_notification` keys on `(reason, degraded_at, degraded_until)`, re-creating `situareness_degraded` every minute while triggers persist. | Keyed notification on `degraded_reason` alone with stable message text free of moving timestamps; re-review pending. |
| Standards | SIT-R1 | Low | Docs state `outbox_overflow` refreshes `degraded_at`/`degraded_until` while outbox remains above capacity, whereas degraded polls cap outbox at 5,000 before re-evaluating. | Synchronized `docs/ha/README.md`, `home-assistant/README.md`, and `o3-mvp.md` with actual `outbox_overflow` behavior; re-review pending. |
| Spec | DOC-HA-01 | Low | `docs/ha/README.md:29` states ambiguous quarantine suspends all *absent* lineages instead of *all* lineages (current and absent). | Corrected `docs/ha/README.md:29` to state `all lineages (both current and absent) are suspended for that poll`; re-review pending. |
| Spec | DOC-HA-02 | Nit | Docs say "deleting/emptying" the store file transitions to `journal_lost`, whereas a 0-byte file triggers `.corrupt.*`/`malformed_store`. | Clarified docs to say deleting the store file and any `.corrupt.*` backups (or replacing its data with empty JSON `{}`); re-review pending. |
| Standards / Spec | SIT-R3 / PERF-01 | Nit | `_save()` runs `.storage` `.corrupt.*` glob cleanup on every save, including delivery-loop saves. | Added `has_corrupt_backup` and `_needs_corrupt_cleanup` so cleanup runs once when needed; re-review pending. |
| Standards | SIT-R4 | Nit | Test lambda at `tests/ha/test_coordinator.py` references `asyncio` before `import asyncio` and leaves unused `setup_coord = None`. | Moved `import asyncio` above the lambda and removed `setup_coord = None`; re-review pending. |

All findings from candidate `a146710` were verified fixed at `c0a909c`.

### Candidate c0a909c Opus review findings

Candidate `c0a909c3309f1fc9f88ec967d6765df977ed8ca2` passed 163 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 browser/UI/packaging/catalog/output-gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T194649Z-7a1803`; 329.5s standards, 390.8s specification) reported 1 Medium + 2 Low + 4 Nit standards findings and 2 Medium + 1 Low specification findings (10 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SAF-01 | Medium | Non-Cancel feature failing `normalize` with valid `feature_id` and one invalid/oversized `@id` sets `quarantine_ambiguous = True` without raising `situareness_degraded`. | Scoped quarantine to `[feature_id, *valid_refs]` when `feature_id` is valid, raised `situareness_degraded` for `quarantine_ambiguous`, and aligned `o3-mvp.md`/`cap-cancellation.md`/READMEs; re-review pending. |
| Spec | SPEC-HA-01 | Medium | `outbox_overflow` strips fingerprints for already-queued overflow targets, causing acknowledgement recovery to re-latch immediately while the alert stays active. | Preserved fingerprints for already-queued targets during initial `outbox_overflow` latching so acknowledged recovery delivers cleanly; re-review pending. |
| Spec | SPEC-HA-02 | Medium | Partial-CAN unreferenced continuing updates (`U -> P`) are quarantined by root cancellation propagation (`C -> P`), blocking new actions. | Distinguished continuing unreferenced segments (`sent >= cancelled_at`) for new qualifying actions while keeping pre-cancellation retries suspended; re-review pending. |
| Spec | SPEC-HA-03 | Low | Future-dated `Actual Cancel` (`sent > now + 5m`) passes `cap_event_valid`, writing raw `lineage` edges and flipping to cancelled once the clock catches up. | Enforced `sent <= now + 5m` in `cap_event_valid(event, now)` and graph/evidence validation so future-dated `Cancel` targets stay isolated in `uncertain_targets`; re-review pending. |
| Standards | HLT-01 | Low | `_degraded_health` omits `quarantined_cancel_lineages`/`recoverable_prior_conflict` checks and couples triggered status to timestamp string equality. | Passed `triggered_now` and `recoverable_prior_conflict` flags and checked `quarantined_cancel_lineages` in `_degraded_health`; re-review pending. |
| Standards | PRV-01 | Low | `Store(hass, 1, prefix)` omits `private=True` for private journal/outbox storage. | Passed `private=True` to `Store` on load and removal; re-review pending. |
| Standards | DOC-01 | Nit | Docs list `malformed_cancellation` for all over-cap `Actual Cancel`s, omitting `conflicting_cancellation` for conflicting duplicates over the 5,000-ID cap. | Synchronized `o3-mvp.md`, `cap-cancellation.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |
| Standards | DOC-02 | Nit | `docs/ha/README.md:27` says suspended retries clear when leaving `quarantined`, whereas `ended_or_absent` retries stay suspended up to the 15-minute limit. | Updated `docs/ha/README.md:27` to document retained suspended retries until equivalent recovery, invalidation, or 15-minute expiry; re-review pending. |
| Standards | MNT-01 | Nit | Supersession logic duplicated in `collector.py` and `domain.py`; `_update_once` and `o3-mvp.md` §Home Assistant are overly monolithic. | Reused `resolve_candidates` in `collector.py`, extracted coordinator helpers, and split `o3-mvp.md` §Home Assistant into readable paragraphs; re-review pending. |
| Standards | CMP-01 | Nit | `DataUpdateCoordinator` does not explicitly pass `config_entry=entry`. | Passed `config_entry=entry` in `SituarenessCoordinator.__init__`; re-review pending. |

All findings from candidate `c0a909c` were verified fixed at `221ed9b`.

### Candidate 221ed9b Opus review findings

Candidate `221ed9b037ea72e826f88716e14826c28e95a3df` passed 166 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 CAP/cancellation, browser/UI, packaging, catalog, or live/shadow gate findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T203507Z-d741fd`; 316.3s standards, 287.4s specification) reported 1 Medium + 4 Low + 2 Nit standards findings and 1 Medium + 2 Low specification findings (8 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-01 / SPEC-HA-01 | Medium | `outbox[:5000]` drops targets mid-plan while passing `plans=[]` keeps unqueued plans' fingerprints in `records`. | Queued whole plans atomically (draining 1 deliverable batch before overflow if space frees), kept fingerprints only for queued plans, stripped dropped overflow plans, and documented the ~1,500-target/15m delivery bound; re-review pending. |
| Spec | SPEC-HA-02 | Low | Valid `feature_id` with non-dict/null `properties` triggers `quarantine_ambiguous = True`. | Scoped `[feature_id]` whenever `feature_id` is extractable regardless of `properties` type; re-review pending. |
| Spec / Standards | STD-HA-03 / SIT-07 | Low / Nit | `degraded_reason` restore has an operator-precedence bug and `_valid_persisted_store` accepts unknown/`malformed_store` strings. | Parenthesized fallback expression and validated `degraded_reason` against `PERSISTED_DEGRADED_REASONS`; re-review pending. |
| Standards | SIT-02 | Low | `_degraded_health` hardcodes `planned_count: 0` without showing withheld plans. | Exposed `withheld_count` (and queued `planned_count` on initial `outbox_overflow`) across coordinator health snapshots; re-review pending. |
| Standards | SIT-03 | Low | Double `deepcopy` in `reconcile` and unvalidated 5,001-phone test caused slow-callback warnings; 1,000-record cost was unmeasured. | Replaced double `deepcopy` with single `deepcopy` + shallow dict copies, used `islice(..., 100)` in delivery scan, replaced the 5,001-phone test with a valid 50-phone multi-plan test, and added a 1,000-record `reconcile` benchmark; re-review pending. |
| Standards | SIT-04 | Low | `docs/CONTEXT.md` and `docs/plans/primary-source-roadmap.md` omit degraded mode, `acknowledge_degraded_at`, and `situareness_degraded` notifications. | Synchronized both documents with degraded mode and existing local persistent notifications; re-review pending. |
| Standards | SIT-05 | Low | Normative degraded/cancellation rules are duplicated in long paragraphs across four documents. | Made `docs/spec/o3-mvp.md` (`#home-assistant`) the single canonical normative contract with concise operator summaries and cross-links in `docs/ha/README.md`, `home-assistant/README.md`, and `cap-cancellation.md`; re-review pending. |
| Standards | SIT-06 | Nit | Production `__init__.py` includes test-compatibility `ImportError`/`hasattr`/`isinstance` shims that could hide HA breakage. | Moved test shims into `tests/ha/test_coordinator.py` `HA_MODULES` and fake `hass` fixtures; re-review pending. |

All findings from candidate `221ed9b` were verified fixed at `ad93ead`.

### Candidate ad93ead Opus review findings

Candidate `ad93eada5a9222fe3120707180b24c2704dc5e7c` passed 168 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 CAP/qualification/quarantine/lifecycle/browser/packaging/catalog findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T214931Z-ca8e85`; 318.6s standards, 291.6s specification) reported 1 Medium + 2 Low + 2 Nit standards findings and 1 Medium + 1 Low-Medium + 1 Low specification findings (7 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-R1 / HA-OVF-01 | Medium | `outbox_overflow` latches a 7-day `degraded_until`, halts queued delivery, and freezes item ages via `degraded_delta`, preventing automatic overflow recovery. | Updated `outbox_overflow` to use the 15-minute `MAX_AGE` horizon, keep bounded 100-target/poll queued delivery active without aging freeze (`evidence_degraded: false`, `output_blocked: false`, accurate `deliverable_count`/`suspended_count`/`withheld_count`), and auto-clear once plans fit within `5,000`; re-review pending. |
| Spec | HA-STORE-01 | Low-Medium | Store major/minor version mismatches (`NotImplementedError` or silent `_async_migrate_func` fallback) can retry indefinitely or overwrite instead of entering `malformed_store`. | Added a rejecting `_async_migrate_func` on `Store` and caught `NotImplementedError` alongside `ValueError`/`UnsupportedStorageVersionError` as `malformed_store` with real-HA wrong-version tests; re-review pending. |
| Standards | SIT-R2 | Low | `CancellationEvidenceOverflow` strips planned fingerprints inside `domain.py`, causing coordinator `withheld_count` to report `0`. | Carried stripped `plans` on `CancellationEvidenceOverflow` and passed `len(plans)` into `_persist_degraded_poll` `withheld_count`; re-review pending. |
| Standards | SIT-R3 | Low | `config.validate()` accepts future `acknowledge_degraded_at`, and non-matching load-time acknowledgements remain unconsumed until the clock passes them. | Enforced `ack_ts <= now` in `config.validate(raw, now=None)` and consumed non-matching/premature `acknowledge_degraded_at` values on load so they cannot clear unseen later degradations; re-review pending. |
| Spec | HA-IO-01 | Low | `_deliver_outbox_batch` rewrites the full journal and outbox after every single delivery item (up to ~100 full rewrites per poll). | Batched expired-item pruning and post-group delivery persistence once per completed 10-target delivery group while keeping at-least-once semantics; re-review pending. |
| Standards | SIT-R4 | Nit | `situareness_degraded` notification text hardcodes a "seven-day horizon" and omits `acknowledge_degraded_at` recovery instructions. | Differentiated `outbox_overflow`, horizon-extended evidence/journal degradations (`degraded_until` + `acknowledge_degraded_at` + reload), and `malformed_store` manual repair guidance; re-review pending. |
| Standards | SIT-R5 | Nit | `test_reconcile_thousand_record_bounded_latency` uses a tight `< 0.5s` wall-clock assertion. | Asserted `d.deepcopy` `call_count == 1` deterministically and relaxed the wall-clock sanity bound to `< 5.0s`; re-review pending. |

All findings from candidate `ad93ead` were verified fixed at `3d18093`.

### Candidate 3d18093 Opus review findings

Candidate `3d1809327eafc2bb09c88ef104622e9eacb4b7cc` passed 169 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium findings**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T221552Z-4d6117`; 309.4s standards, 308.7s specification) reported 3 Low + 3 Nit standards findings and 2 Low specification findings (7 unique findings total, plus 1 capacity advisory):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-HA-01 / HA-JLOST-01 | Low | Reusing a stale `journal_lost_at` across repeat store loss or `malformed_store` deletion shortens the 7-day `journal_lost` hold. | Extended `degraded_until` from `max(lost_ts, detect_now) + MAX_ACCEPTANCE_AGE`, rotated stale timestamps older than 7 days, and cleared `journal_lost_at` on post-fetch saves, non-empty store loads, and `malformed_store` entry; re-review pending. |
| Spec | HA-NOTIFY-01 | Low | `_sync_degraded_notification` picks `.storage` manual-repair text whenever `degraded_until` is null even for non-`malformed_store` reasons. | Selected notification copy by `degraded_reason` (`malformed_store` vs `outbox_overflow` vs `degraded_until`/`acknowledge_degraded_at`); re-review pending. |
| Standards | SIT-HA-02 | Low | Persisted outboxes over 5,000 items pass validation and are truncated silently in `_queue_outbox_plans`. | Rejected `len(outbox) > 5000` in `_valid_persisted_store` as `malformed_store` and removed silent truncation; re-review pending. |
| Standards | SIT-TOOL-01 | Low | `tools/live-browser-smoke.mjs` polling promise can reject unhandled after a timeout before `live-browser-smoke.json` writes. | Added a `stopped` flag checked in the polling loop and `smokePromise.catch(() => {})` before `Promise.race`; re-review pending. |
| Standards | SIT-HA-03 | Nit | `async_setup_entry` assigns private `store._async_migrate_func`. | Removed the private attribute assignment; HA's default `NotImplementedError` and `UnsupportedStorageVersionError` continue mapping version mismatches to `malformed_store`; re-review pending. |
| Standards | SIT-DOC-01 | Nit | `docs/spec/o3-mvp.md` §Home Assistant uses dense single-paragraph blocks restated across READMEs and `docs/CONTEXT.md`. | Reformatted `docs/spec/o3-mvp.md#home-assistant` as structured bulleted subsections and slimmed `docs/ha/README.md`, `home-assistant/README.md`, and `docs/CONTEXT.md` to concise links/summaries; re-review pending. |
| Standards | SIT-HA-04 | Nit | Degraded notifications say "output is blocked" even in shadow mode. | Qualified degraded notification text when `live(self.config)` is false; re-review pending. |

Advisory note `HA-CAP-01` (multi-state feeds near 1,000 features plus retained tombstones reaching the 1,000-record `cancellation_evidence_overflow` bound) is documented in `docs/spec/o3-mvp.md#home-assistant` and `docs/ha/README.md`.

All findings from candidate `3d18093` were verified fixed at `6236ea8`.

### Candidate 6236ea8 Opus review findings

Candidate `6236ea8f7e47aed3a8d8be0966f77baf8af1b2e7` passed 170 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and zero room/live-gate/routing/quarantine/overflow defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T223104Z-7fe723`; 215.8s standards, 202.2s specification) reported 1 Medium + 3 Low + 1 Nit standards findings and 1 Medium + 1 Low + 1 Nit specification findings (7 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-HA-ACK-01 / SIT-HA-02 | Medium / Low | `_latch_degraded` resets `degraded_at` every poll on recurring triggers, racing `acknowledge_degraded_at`; consumed/rejected acks lack operator visibility; notification/docs omit active-trigger clearing prerequisites. | Kept initial `degraded_at` stable across unchanged reasons while extending `degraded_until`, exposed `acknowledge_rejected` in snapshots + notifications (including immediate Poll 1 re-latch), and documented trigger-clear + `>= degraded_at` prerequisites; re-review pending. |
| Spec | SIT-DOC-01 | Medium | Standalone bundle `home-assistant/README.md` links to `../docs/spec/o3-mvp.md` and `../docs/reference/cap-cancellation.md` which are absent from the HA ZIP archive. | Replaced external links with a self-contained recovery, bounds, attribute, retry-freeze, and tombstone-warning section inside `home-assistant/README.md`; re-review pending. |
| Standards | SIT-HA-CANCEL-02 | Low | `_update_once` converts external outer-task `asyncio.CancelledError` into a normal return whenever `self._stopping` is True. | Gated stopped-health fallback on `current_task is None or current_task.cancelling() == 0` so outer task cancellations propagate cleanly; re-review pending. |
| Standards | SIT-HA-STORE-03 | Low | `async_setup_entry` catches broad `(TypeError, KeyError)` on `store.async_load()`, turning internal store errors into `malformed_store`. | Narrowed handler to `(json.JSONDecodeError, ValueError, NotImplementedError)` + `UnsupportedStorageVersionError` so unexpected errors raise `ConfigEntryNotReady`; re-review pending. |
| Standards | SIT-DOC-RETRY-04 | Low | Operator guides promise a 15-minute retry window without explaining the degraded-mode `last_degraded_poll` retry-age freeze across multi-day holds. | Documented degraded-mode retry age preservation and up to 7+ day delayed resumption across `home-assistant/README.md`, `docs/ha/README.md`, and `docs/spec/o3-mvp.md`; re-review pending. |
| Standards | SIT-NIT-05 | Nit | `_deliver_outbox_batch` comment still states per-item persistence and docs omit the expired-key prune save. | Updated comment and docs to describe expired-item pruning saves plus per-10-target-group delivery saves; re-review pending. |
| Spec | SIT-DOC-03 | Nit | `docs/ha/README.md` sensor attribute list omits `event_count` and `source_feature_count`. | Added `event_count`, `source_feature_count`, and `acknowledge_rejected` to `docs/ha/README.md` and `home-assistant/README.md`; re-review pending. |

All findings from candidate `6236ea8` were verified fixed at `c81fb7f`.

### Candidate c81fb7f Opus review findings

Candidate `c81fb7f5221b54a88453627dd5376216db0051b9` passed 171 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and zero room/catalog/quarantine/overflow/lifecycle defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T224454Z-a299b9`; 217.6s standards, 373.9s specification) reported 1 Medium + 1 Low standards findings and 1 Medium + 2 Low specification findings (3 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | HA-ACK-01 / SPEC-HA-01 / DOC-HA-02 | Medium / Low | `config.validate` raises `ValueError` for future or unparseable/naive `acknowledge_degraded_at` strings, failing HA setup (`ConfigEntryNotReady`), hiding `situareness_degraded`/`acknowledge_rejected`, and letting automatic retries apply a future timestamp later; operator docs promise `acknowledge_rejected`. | Validated only non-string/empty/control-character values in `config.validate`, moved timestamp parsing/future checks into `SituarenessCoordinator._try_acknowledge` (setting `acknowledge_rejected: true`, updating `situareness_degraded`, and persisting valid ISO timestamp consumption in `entry.data` and store without blocking setup), and synced docs + real-HA reload coverage; re-review pending. |
| Standards | HA-DOC-02 | Low | `home-assistant/README.md` line 19 states `(unrecoverable Actual Cancel or >5,000 quarantined IDs; 7 days)`, whereas >5,000 non-Cancel IDs trigger `quarantine_ambiguous`. | Clarified `malformed_cancellation`/`conflicting_cancellation` vs poll-scoped `quarantine_ambiguous` in `home-assistant/README.md`; re-review pending. |
| Spec | SPEC-HA-03 | Low | `_bound_records` computes `dropped_horizon` over all dropped groups rather than only dropped protected/cancellation groups, allowing unprotected old records to extend overflow lockouts. | Restricted `dropped_groups` in `_bound_records` to `eid in protected` and verified unprotected 30-day records do not extend `dropped_horizon`; re-review pending. |

All findings from candidate `c81fb7f` were verified fixed at `1078764`.

### Candidate 1078764 Opus review findings

Candidate `1078764e6e08da5560fdc95fbee6ea04021cd651` passed 171 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, 0 Medium specification findings, and zero browser/packaging/catalog/gate/routing/overflow/store/lifecycle defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T230054Z-57bc4c`; 286.1s standards, 394.5s specification) reported 1 Medium + 1 Low + 2 Nit standards findings and 1 Low + 1 Nit specification findings (4 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | HA-01 | Medium | `timestamp()` accepts years up to `9999`, so persisted records or `cap_references` near `9999-12-31` cause `cancellation_horizon` / `_bound_records` (`+ MAX_ACCEPTANCE_AGE`) to raise `OverflowError` once the component leaves the feed. | Bounded `timestamp()` to UTC years `2–9998` and added `OverflowError` clamping inside `cancellation_horizon()` and `_bound_records()` plus domain/coordinator regression tests; re-review pending. |
| Standards | HA-02 | Low | `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` state expired-item pruning is saved once rather than once before each 10-target group that prunes expired items. | Updated `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` to match `_deliver_outbox_batch()` (`persisting once before a 10-target group when expired items are pruned and once after each completed 10-target group`); re-review pending. |
| Spec / Standards | SPEC-01 / HA-04 | Low / Nit | `config.validate` rejects `len(ack) > 100` with `ValueError` (`ConfigEntryNotReady`), conflicting with the contract requiring setup to accept string values and reject bad timestamps at runtime via `acknowledge_rejected`. | Removed the `len(ack) > 100` setup rejection in `config.validate` and treated over-length `acknowledge_degraded_at` strings as runtime-rejected in `_try_acknowledge` while keeping monitoring online; synced contract/READMEs; re-review pending. |
| Standards / Spec | HA-03 / NIT-01 | Nit | `config.validate(raw, now=None)` accepts and documents an unused `now` parameter. | Removed `now=None` from `config.validate(raw)`, updated `docs/spec/o3-mvp.md` and tests; re-review pending. |

All findings from candidate `1078764` were verified fixed at `3b35e7c`.

### Candidate 3b35e7c Opus review findings

Candidate `3b35e7c6edfc66cd9509771112307a3428ef0692` passed 172 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, 0 Medium specification findings, and zero live-gate/routing/privacy/shadow/room/packaging defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T232125Z-6894d0`; 359.6s standards, 349.8s specification) reported 1 Medium + 2 Low + 1 Nit standards findings and 2 Low + 1 Nit specification findings (7 findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SIT-R01 | Medium | Future-dated timestamps (`sent > now + 5m` or far-future `expires`/`ends`) in an invalid `Cancel` extend `cancellation_horizon` indefinitely, suppressing real alerts and occupying protected slots. | Bounded each record's retention timestamps in `cancellation_horizon()` at `min(ts, updated + 5m)` and clamped outputs at `MAX_TIMESTAMP`, with 8-day expiry regression tests; re-review pending. |
| Spec | SPEC-HA-01 | Low | Dates in late `9998` (`9998-12-25..31`) pass `timestamp()` (`<= 9998`), then `+ MAX_ACCEPTANCE_AGE` yields year `9999` in `degraded_until`, which `_valid_persisted_store()` rejects as `malformed_store` on reload. | Defined `MAX_TIMESTAMP` (`9998-12-31T23:59:59+00:00`) and clamped `cancellation_horizon()`, `_bound_records()`, and `_latch_degraded()` horizons at `MAX_TIMESTAMP` so reload validation always passes; re-review pending. |
| Standards | SIT-R02 | Low | Synchronous CPU work (`reconcile`, `_deliverable_count`, `_valid_persisted_store`) runs on HA's event loop, and the 1,000-record benchmark allows 5.0s. | Offloaded `reconcile` and `_valid_persisted_store` via `hass.async_add_executor_job`, scoped `_deliverable_count` and batched `_deliver_outbox_batch` `qualify()` calls to queued active IDs, and tightened the 1,000-record bound to `< 0.5s`; re-review pending. |
| Standards | SIT-R03 | Low | Outbox batching is strictly FIFO, allowing `attempts > 0` retries to delay or expire newly queued first-attempt (`attempts == 0`) alerts. | Sorted deliverable outbox selection with first-attempt (`attempts == 0`) targets ahead of retries while preserving FIFO within each tier; re-review pending. |
| Spec | SPEC-HA-02 | Low | Healthy coordinator load clears/ignores invalid, naive, or over-length `acknowledge_degraded_at` and silently consumes future timestamps without surfacing `acknowledge_rejected` or `situareness_degraded`. | Rejected invalid/naive/over-length (`ack_ts is None`) and future (`ack_ts > current_now`) `acknowledge_degraded_at` values with `acknowledge_rejected: true` and `situareness_degraded` even while healthy; re-review pending. |
| Standards | SIT-R04 | Nit | `docs/INDEX.md` lacks the new section anchors in `docs/spec/o3-mvp.md` and `home-assistant/README.md`. | Synchronized `docs/INDEX.md` anchors with all current headings in `docs/spec/o3-mvp.md` and `home-assistant/README.md`; re-review pending. |
| Spec | SPEC-HA-03 | Nit | `outbox_overflow` notification copy states it clears "when the 15-minute `degraded_until` horizon expires", though ongoing overflow re-latches `degraded_until`. | Removed the inaccurate 15-minute expiry auto-clear clause from live and shadow `outbox_overflow` notifications; re-review pending. |

All findings from candidate `3b35e7c` were verified fixed at `05a979e`.

### Candidate 05a979e Opus review findings

Candidate `05a979eb7695862aafd63b74c156dc72961d7bab` passed 173 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, 0 Medium specification findings, and zero live-gate/store-roundtrip/journal/lifecycle/recorder/packaging/room/index defects**. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261117T234711Z-2fcb85`; 408.5s standards, 339.1s specification) reported 2 Medium + 2 Low standards findings and 2 Low + 1 Nit specification findings (7 findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SR-01 | Medium | `resolve_candidates`, `grouping_events`, and `referenced` allow non-`Actual` (`Test`/`Exercise`/`System`) or `Alert` messages with valid CAP tuples to supersede referenced `Actual` alerts and migrate pending outbox items. | Restricted supersession and lineage-grouping authority strictly to `Actual` `Update` and `Cancel` messages (`_actual_superseding`) across `resolve_candidates()` and `reconcile()`; re-review pending. |
| Standards | SR-02 | Medium | For malformed/oversized non-`Cancel` features, `reconcile` skips quarantining referenced predecessors present in the same poll while docs state `[feature_id, *valid_refs]`. | Clarified in `docs/spec/o3-mvp.md`, `docs/reference/cap-cancellation.md`, and `home-assistant/README.md` that malformed/oversized non-`Cancel` features quarantine `feature_id` and absent, unreferenced prior records in `valid_refs` (`[feature_id, *absent_unreferenced_valid_refs]`) so raw references on a non-`Cancel` feature cannot suppress valid current candidates; re-review pending. |
| Standards | SR-03 | Low | Only one consumed acknowledgement slot is stored and `_save()` can overwrite a newer `entry.data` acknowledgement with an older store value if a load failure prevented store write. | Added bounded `consumed_acknowledgements` history (`<= 100` ISO timestamps merged across `entry.data` and store without downgrade on reload or save); re-review pending. |
| Standards | SR-04 | Low | Post-fetch `resolve_candidates`, `lineage_index`, `_migrate_and_prune_outbox`, target planning, `_deliverable_count`, and async JSON normalization still ran on HA's loop while docs summarized reconciliation as off-loop. | Offloaded post-fetch candidate/conflict resolution, `lineage_index`/outbox migration, target planning, and deliverable-count qualification checks alongside `reconcile` and `_valid_persisted_store` via `async_add_executor_job`, and synced docs; re-review pending. |
| Spec | SR-ACK-01 | Low | `acknowledge_rejected` is unconditionally cleared to `False` when `degraded_until` expires or `outbox_overflow` auto-clears mid-session even if an invalid/future `acknowledge_degraded_at` remains configured. | Preserved `_config_ack_rejected` across mid-session `degraded_until` and `outbox_overflow` auto-clears so invalid/naive/over-length/future settings stay flagged; re-review pending. |
| Spec | SR-ACK-02 | Low | When healthy `acknowledge_rejected` and `quarantine_ambiguous` occur together, `quarantine_ambiguous` masks the acknowledgement-rejection notice on `situareness_degraded`. | Merged acknowledgement-rejection warning into the `quarantine_ambiguous` notification and keyed its state on `self.acknowledge_rejected`; re-review pending. |
| Spec | SR-CFG-01 | Nit | `config.validate()` rejects `ord(ch) < 32`, missing DEL (`U+007F`) and C1 (`U+0080–U+009F`) control characters. | Extended control-character check to `ord(ch) < 32 or 127 <= ord(ch) <= 159` on `acknowledge_degraded_at` and location names; re-review pending. |

All findings from candidate `05a979e` were verified fixed at `c132758`.

### Candidate c132758 Opus review findings

Candidate `c132758459e5ea4ff5c4573448a6af2192deee9c` passed 175 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium findings across both standards and specification**, and zero live-gate/routing/privacy/CAP/quarantine/overflow/store/ack/room/packaging defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T001451Z-588b6e`; 323.9s standards, 386.0s specification) reported 2 Low + 2 Nit standards findings and 1 Low + 3 Nit specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | SR-DOC-01 | Low | `docs/CONTEXT.md` says evidence integrity failure "withholds new or affected outputs", understating that evidence/storage degradations block all output while only `outbox_overflow` withholds overflowing plans. | Updated `docs/CONTEXT.md` to distinguish all-output blocks (`cancellation_evidence_overflow`, `malformed_cancellation`, `conflicting_cancellation`, `journal_lost`, `malformed_store`) from `outbox_overflow`; re-review pending. |
| Standards | SR-DOC-02 | Low | `_sync_degraded_notification()` uses feed-trigger recovery wording even for `journal_lost` (which has no feed trigger) and `cancellation_evidence_overflow` (protected journal history). | Differentiated `_sync_degraded_notification()` recovery copy for `journal_lost`, `cancellation_evidence_overflow`, and feed-triggered cancellation degradations, and synced `docs/spec/o3-mvp.md`; re-review pending. |
| Spec / Standards | SPEC-01 / SR-DOC-03 | Low / Nit | `collector.fetch()` still invokes `resolve_candidates()` on HA's loop despite the off-loop candidate-resolution contract and duplicated work in `_resolve_and_scan_candidates()`. | Removed `resolve_candidates()` from `collector.fetch()` so `fetch()` runs only async HTTP/JSON normalization and candidate resolution runs solely off-loop via `async_add_executor_job`; re-review pending. |
| Standards / Spec | SR-MAINT-01 / STD-01 | Nit | Dead `_migrate_and_prune_outbox` method and unused `planned_count`/`delivery_attempts`/`delivery_failures` parameters on `_persist_degraded_poll`. | Removed `_migrate_and_prune_outbox` and the unused parameters on `_persist_degraded_poll`; re-review pending. |
| Spec | STD-02 | Nit | Unreachable `if len(events) > 1000:` check at `collector.py:234-235` after `feature_count > 1000` already raised at lines 121-123. | Removed unreachable check in `collector.py`; re-review pending. |
| Spec | DOC-01 | Nit | `docs/ha/README.md` and `home-assistant/README.md` say bare `"acknowledgement"` rather than `"recipient alert acknowledgement"` near operator `acknowledge_degraded_at` docs. | Updated both READMEs to specify `"recipient alert acknowledgement"`; re-review pending. |

All findings from candidate `c132758` were verified fixed at `6bd9bc9`.

### Candidate 6bd9bc9 Opus review findings

Candidate `6bd9bc928f02ccce5d1b1b005419e2fbf8bdeeed` passed 175 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium standards findings**, and zero live-gate/routing/privacy/CAP/quarantine/store/ack/offload/room/packaging defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T002932Z-5e3623`; 361.5s standards, 230.3s specification) reported 2 Low standards findings and 1 Medium + 2 Nit specification findings (5 findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | SPEC-HA-01 | Medium | Queued active targets (including `attempts == 0` first attempts) beyond ~1,500 attempts/15m (or ~300 under slow 15s timeouts) can expire silently without an `expired_unsent` metric/notification, while docs say only overflow retries expire. | Added `expired_by_age()` in `delivery.py`, surfaced `expired_unsent` (`partial: True`), `"expired": True` outcomes, and `situareness_degraded` notifications on expired active targets, and corrected docs/notifications; re-review pending. |
| Standards | SIT-PERF-01 | Low | `_deliver_outbox_batch` can save twice per 10-target group when items expire, and 5,000 outbox items with 10KB instructions serialize large rewrites per poll. | Coalesced expired-item pruning + post-delivery persistence into at most one save per 10-target group and documented the per-item instruction serialization bound across ~12 writes/poll; re-review pending. |
| Standards | SIT-AVAIL-01 | Low | `_bound_records()` counts current `ineligible` non-cancellation feed items as `protected`, leaving zero headroom over the 1,000-feature fetch cap when retained tombstones exist. | Excluded ordinary `ineligible` items (without action history or cancellation evidence) from `protected` in `_bound_records()` and synchronized docs; re-review pending. |
| Spec | SPEC-HA-02 | Nit | First successful post-recovery save after `malformed_store` deletes `.corrupt.*` backups automatically, which was undocumented. | Documented post-recovery automatic `.corrupt.*` backup cleanup across `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md`; re-review pending. |
| Spec | DOC-01 | Nit | `home-assistant/README.md` says `quarantine_ambiguous` exceeds `5,000` "non-Cancel IDs", narrower than `collector.py`. | Removed the `"non-Cancel"` qualifier in `home-assistant/README.md` (`>5,000 quarantined IDs` in a poll); re-review pending. |

All findings from candidate `6bd9bc9` were verified fixed at `698fe14`.

### Candidate 698fe14 Opus review findings

Candidate `698fe14ee6dbd1b77518170893b2f835dbfc87bd` passed 177 local tests, Ruff, deterministic packaging, and live anonymous smoke, with zero Critical findings across both standards and specification and zero live-gate/routing/privacy/CAP/quarantine/overflow/store/offload/room/packaging defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T004922Z-f1724a`; 248.1s standards, 294.2s specification) reported 1 High + 1 Medium + 1 Low standards findings and 1 Medium + 2 Low specification findings (5 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | F1 / HA-SNAP-01 | High / Medium | `_healthy_snapshot()` indexes `records[e["id"]]` directly outside `_update_once()`'s `try:` block, raising raw `KeyError` when `_bound_records()` evicts unprotected current `ineligible` items above 1,000 records. | Switched `_healthy_snapshot()` to safe `.get()` / membership fallbacks (`"ineligible"` + `qualify()` reasons) and moved `_healthy_snapshot()` inside `_update_once()`'s `try:` block; re-review pending. |
| Standards | F2 | Medium | Per-poll `expired_unsent` auto-dismisses `situareness_degraded` (~60s) and resets `partial: false` on the next clean poll. | Persisted validated `expired_unsent`, `expired_unsent_at`, and `expired_unsent_until` in store (`7`-day `MAX_ACCEPTANCE_AGE` latch or cleared on reload via valid `acknowledge_degraded_at`), surfaced across healthy, degraded, and `_stopped_health()` snapshots; re-review pending. |
| Standards | F3 | Low | Pre-fetch `_sync_degraded_notification()` defaults `expired_unsent=0`, rewriting notifications twice per degraded poll, while `bool(expired_unsent)` keys leave count text stale. | Defaulted `_sync_degraded_notification()` `expired_unsent` to `self.expired_unsent`, keyed active state tuples on exact integer `expired_count`, and synchronized pre-fetch/post-poll state; re-review pending. |
| Spec | HA-ACK-02 | Low | `_ack_cleared_on_load` omits the cleared reason, falsely setting `acknowledge_rejected: true` if Poll 1 latches an unrelated degradation reason. | Tracked `_ack_cleared_reason` on load clear and set `acknowledge_rejected = True` in `_latch_degraded()` only when `reason == self._ack_cleared_reason`; re-review pending. |
| Spec | HA-DEG-03 | Low | `CancellationEvidenceOverflow` overwrites concurrent `malformed_cancellation`/`conflicting_cancellation` triggers, oscillating `degraded_reason` and resetting `degraded_at`. | Preserved feed cancellation trigger precedence over concurrent `CancellationEvidenceOverflow` while enforcing `max(until, fallback_until)` and documenting concurrent history overflow guidance; re-review pending. |

All findings from candidate `698fe14` were verified fixed at `e13efc8`.

### Candidate e13efc8 Opus review findings

Candidate `e13efc870a6dd0dc50e44175bcb8e10912c9750f` passed 181 local tests, Ruff, deterministic packaging, and live anonymous smoke, with zero Critical findings and zero live-gate/routing/privacy/CAP-quarantine/outbox-overflow/async-offload/room/packaging defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T011756Z-942760`; 335.6s standards, 324.1s specification) reported 1 Medium + 5 Low + 1 Nit standards findings and 1 Medium + 2 Low specification findings (9 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | HA-BOUND-01 | Medium | `_bound_records()` excludes absent `quarantined`/`unconfirmed`/15m-bridge `ended_or_absent` actionable records from `protected`, allowing >1,000 `ineligible` items to evict them and cause duplicate alarms. | Extracted `_is_actionable_record()` in `_bound_records()` (`domain.py`) so all `active`/`quarantined`/`unconfirmed`/`cancelled`, `cancel_message`/`uncertain_targets`, and `<=15m` bridge-window `actions` records are protected and prioritized regardless of presence; re-review pending. |
| Standards | HA-BOUND-02 | Low | Hidden `superseded` placeholders in `current_graph_ids` enter `protected` even when their group has no action or cancellation evidence. | Required `_is_actionable_record()` or actionable/cancellation-group membership to protect feed records, excluding non-actionable hidden `superseded` placeholders from `protected`; re-review pending. |
| Spec | SPEC-HA-01 | Medium | Raw 1,000-feature abort in `collector.py` causes persistent `UpdateFailed` on >1,000-feature bursts (including duplicate copies) and prevents `_bound_records()`/`_healthy_snapshot()` burst handling. | Removed the 1,000-feature abort in `collector.py` while keeping `feature_count` for `source_count` and preserving `MAX_PAGES`/`MAX_BYTES`/`MAX_QUARANTINE_IDS` bounds; updated docs and tests; re-review pending. |
| Standards / Spec | HA-NOTE-01 / SPEC-HA-02 | Low | Healthy `expired_unsent > 0` acknowledgement-rejection notice mentions only invalid/naive/over-length/future causes instead of premature (`< expired_unsent_at`), missing `expired_unsent_at`, or already-consumed rejections and clear rules. | Updated `_sync_degraded_notification()` for both standalone `acknowledge_rejected` (when `expired_count > 0`) and concurrent `quarantine_ambiguous` to surface all rejection causes and `expired_unsent_at <= acknowledge_degraded_at <= reload time`; re-review pending. |
| Spec | SPEC-HA-03 | Low | `_valid_persisted_store()` accepts records missing `"state"` or holding unknown `"state"` strings. | Added `VALID_RECORD_STATES` and required every persisted record `"state"` (and non-`None` `"prior_state"`) to belong to it; re-review pending. |
| Standards | HA-OUT-01 | Low | `created > now` (backward clock step) or non-age active-alert invalidation discards queued targets silently without `expired_unsent` or outcomes. | Updated `delivery.expired_by_age()` to return `True` for any unexhausted queued target of a still-`active` or `prior_state == "active"` suspended record that fails `pending_valid(..., allow_suspended=True)`; re-review pending. |
| Standards | DOC-HA-01 | Low | `docs/ha/README.md` rewrite dropped explicit 3-attempt retry cap, crash-between-acceptance-and-save duplication caveat, non-cancellation semantics of `ended_or_absent`, later-poll cancellation delay, and retry-vs-reminder disclosures. | Restored all five disclosures into `docs/ha/README.md`, `docs/spec/o3-mvp.md`, and `home-assistant/README.md`; re-review pending. |
| Standards | HA-STORE-01 | Low | `_clear_corrupt_store_backups()` swallows `OSError`, `_save()` unconditionally disarms cleanup, and a stale `.corrupt.*` backup can later misclassify `journal_lost` as `malformed_store`. | Logged warnings and returned `bool` from `_clear_corrupt_store_backups()`, kept `_needs_corrupt_cleanup` armed until unlink succeeds, and ensured `async_setup_entry()` enters `journal_lost` on an already-recovered initialized entry whose main store vanishes without `malformed_store_at`; re-review pending. |
| Standards | HA-JL-01 | Nit | `journal_lost` accepts future `journal_lost_at > detect_now`, does not clamp `degraded_until` at `MAX_TIMESTAMP`, duplicates degraded-clear blocks, and leaves unused `batch_expired` variables. | Rejected future `journal_lost_at > detect_now`, clamped `degraded_until` via `min(..., MAX_TIMESTAMP)` with `OverflowError` handling, extracted `_clear_degraded_state()`, and replaced unused `batch_expired` unpacking with `_`; re-review pending. |

All findings from candidate `e13efc8` were verified fixed at `039ea07`.

### Candidate 039ea07 Opus review findings

Candidate `039ea0726ec2bbe63462fd3283b56c532589b5c2` passed 187 local tests, Ruff, deterministic packaging, and live anonymous smoke, with zero Critical/High findings and zero safety-gate/CAP-quarantine/cancellation/ack-rejection/offload/room/packaging defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T014754Z-e43694`; 272.7s standards, 182.6s specification) reported 1 Medium + 3 Low + 2 Nit standards findings and 1 Medium + 1 Low specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec / Standards | SPEC-HA-01 / HA-DOC-PAGES | Medium | `collector.py:13` caps `MAX_PAGES` at `10`, conflicting with the documented `50`-page NWS pagination contract. | Raised `MAX_PAGES = 50` in `collector.py` and added 12-page / 51-page pagination tests in `tests/ha/test_domain.py`; re-review pending. |
| Spec / Standards | DOC-HA-02 / HA-DOC-RETRY | Low | `docs/ha/README.md` and `home-assistant/README.md` describe `"three retries"` / `"up to three times"`, overstating `MAX_ATTEMPTS = 3` (1 initial attempt + up to 2 retries). | Reworded `docs/ha/README.md`, `home-assistant/README.md`, and `docs/spec/o3-mvp.md` to specify three total attempts (`MAX_ATTEMPTS = 3`: one initial call plus up to two retries); re-review pending. |
| Standards | HA-CORRUPT-CLEANUP | Low | `{}` replacement recovery after `malformed_store` clears `malformed_store_at` before computing `_needs_corrupt_cleanup`, leaving `.corrupt.*` backups behind on disk. | Captured `had_malformed_entry` before clearing `malformed_store_at` and scanned `_has_corrupt_store_backup` at startup for `persisted is None or persisted == {}` so `{}` recovery deletes `.corrupt.*` on first save; re-review pending. |
| Standards | HA-PREDRAIN-LATENCY | Low | Pre-drain sets `already_delivered = True` even when `<100` items drained, delaying newly queued first-attempt plans by an extra poll without disclosure. | Parameterized `_deliver_outbox_batch(..., max_attempts, deadline, attempted_keys, exclude_keys)`, added `_finish_poll_delivery()` to deliver new plans in remaining poll budget without re-attempting failed pre-drain items, and documented the `100`-target pre-drain cap delay; re-review pending. |
| Standards | HA-NOTIFY-RECOVERY | Nit | `malformed_store` notification omits deleting `.corrupt.*` backup files alongside store file repair/replacement. | Updated `malformed_store` notification text to name deleting the store file and any `.corrupt.*` backups; re-review pending. |
| Standards | HA-DUP-DISMISS | Nit | `async_unload_entry()` calls `_dismiss_degraded_notification(hass)` redundantly after `async_stop()` already dismissed it. | Removed duplicate `_dismiss_degraded_notification(hass)` from `async_unload_entry()` and added single-dismiss unit test coverage; re-review pending. |

All findings from candidate `039ea07` were verified fixed at `8637f5e`.

### Candidate 8637f5e Opus review findings

Candidate `8637f5e67bc6c5a28a3d2137f590e0a60da8c738` passed 191 local tests, Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical findings**, **0 Medium findings**, and zero safety-gate/routing/privacy/CAP-cancellation/store-schema/ack-reuse/lifecycle/room/packaging/catalog/index defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T020354Z-a2c113`; 297.6s standards, 304.0s specification) reported 2 Low + 1 Nit/Low standards findings and 1 High + 1 Low + 1 Nit specification findings (5 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | HA-QA-01 | High | Poll-wide `quarantine_all` over >1,000 current `ineligible` events turns all `quarantined` items into `protected`, raising `CancellationEvidenceOverflow` and latching a `>=7`-day output block for a per-poll condition. | Passed `quarantine_all` into `_bound_records()`, limited `_is_actionable_record()` protection of `quarantined`/`unconfirmed` records to `prior_state == "active"`, `<=15m` `actions`, or (`not quarantine_all and state == "quarantined"`), and added >1,000-feature ambiguous-poll recovery tests; re-review pending. |
| Spec | HA-COL-02 | Low | Per-page `asyncio.timeout(25)` across `MAX_PAGES = 50` allows a slow multi-page poll to run up to ~21 minutes without total poll deadline. | Added `MAX_FETCH_SECONDS = 50` overall loop timeout in `collector.fetch()` while preserving the 25s per-page timeout and added deadline tests; re-review pending. |
| Standards | SIT-R1 | Low | `_strip_withheld_actions()` and `_deliver_outbox_batch()` prefiltering/sorting iterate up to 1,000–5,000 items synchronously on HA's event loop contrary to off-loop docs. | Extracted and offloaded `_strip_withheld_actions` (all 3 sites) and `_select_deliverable_batch` via `hass.async_add_executor_job`, explicitly documented loop vs executor work (including `collector.fetch()` HTTP/JSON and per-group `<=10`-item delivery rechecks), and added offload tests; re-review pending. |
| Standards | SIT-R2 | Low | Documented `"up to ~12 saves/poll"` understates the two-pass near-capacity pre-drain path (`~21` saves/poll). | Updated `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` to state `up to 11 saves/poll normally, or up to 22 saves/poll when a near-capacity pre-drain runs a second delivery pass`; re-review pending. |
| Standards / Spec | SIT-R3 / HA-ACK-03 | Nit/Low | Degraded acknowledgement clears unanchored `expired_unsent` when `expired_unsent_at` is `None`, whereas the healthy path requires a valid `expired_unsent_at`. | Unified `_try_acknowledge()`'s degraded branch (`exp_at_ts is not None and exp_at_ts <= ack_ts <= current_now`) with the healthy branch, synchronized docs, and added regression tests; re-review pending. |

All findings from candidate `8637f5e` were verified fixed at `bd617e2`.

### Candidate bd617e2 Opus review findings

Candidate `bd617e2cf6786a29d510c7a16a5d933dafd48bed` passed 196 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium findings** and zero gate/routing/privacy/CAP-cancellation/bounds/store-schema/ack/room-UI/catalog/index defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T022802Z-e54306`; 392.1s standards, 441.5s specification) reported 6 Low + 3 Nit standards findings and 2 Low + 2 Nit specification findings (12 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-L01 / SPEC-01 | Low | `expired_unsent` notifications always state `"aged past the 15-minute delivery window"` even for clock rollbacks (`created > now`) or removed targets in `situareness.json`. | Added `delivery.expiry_reason()`, persisted/validated `expired_unsent_reasons` and outcome `"reason"`, keyed notifications on `reasons`, and tailored notice wording per active cause; re-review pending. |
| Standards | SIT-L02 | Low | `_stopping` is checked only right after fetch, allowing post-stop saves when unload begins during executor work, and `async_unload_platforms()` runs before `async_stop()`. | Added `_stopped_poll_result()` and `_stopping` guards across `_update_once`, `_persist_degraded_poll`, and `_queue_outbox_plans`, and stopped the coordinator before `async_unload_platforms()`; re-review pending. |
| Standards | SIT-L03 | Low | Persistent overflow + intermittent feed cancellation trigger alternates `degraded_reason`, resetting `degraded_at` and re-creating `situareness_degraded`. | Enforced `_EVIDENCE_REASON_RANK` retention across active non-overflow reasons and preserved non-`outbox_overflow` `degraded_at` across evidence-reason updates; re-review pending. |
| Standards | SIT-L04 | Low | `_queue_outbox_plans()` drops and strips all trailing plans after `outbox_overflow` latches, including already-queued plans with empty `new_items`. | Skipped empty-`new_items` plans in `_queue_outbox_plans()` so already-queued plans are never counted in `dropped_plans` or stripped; re-review pending. |
| Standards | SIT-L05 | Low | Dismissing `situareness_degraded` only in `async_unload_entry()` leaves notifications behind when `SETUP_RETRY` fails Poll 1 and is disabled/abandoned (`NOT_LOADED`). | Attached a one-shot iteration-safe (`call_soon`) `entry.async_on_state_change` listener on failed first refresh to dismiss `situareness_degraded` on `not_loaded`/`setup_error`/`migration_error`, verified in real HA 2026.11.1; re-review pending. |
| Standards | SIT-L06 | Low | `docs/CONTEXT.md:15` claims persistence failures raise `situareness_degraded`, whereas Store save errors raise `UpdateFailed`. | Updated `docs/CONTEXT.md:15` to distinguish persisted-store validation/evidence degradations from poll-time Store save `UpdateFailed` errors; re-review pending. |
| Spec | STD-01 | Low | `collector.py` runs `json.loads` and per-feature `normalize`/lineage bookkeeping synchronously on HA's event loop across up to 50 pages × 8 MiB. | Extracted `_parse_and_collect_page()` in `collector.py`, offloaded per-page parsing/normalization via `asyncio.to_thread`, and updated contract/README docs; re-review pending. |
| Standards | SIT-N01 | Nit | Several HA/spec/reference bullets are 1–2 kB run-on parentheticals, and `docs/ha/README.md:23` has `"latched;re-latching"`. | Fixed typo and reorganized dense bullets across `docs/spec/o3-mvp.md`, `docs/ha/README.md`, `home-assistant/README.md`, and `docs/reference/cap-cancellation.md`; re-review pending. |
| Standards | SIT-N02 | Nit | Dead/redundant code in `__init__.py` (`_strip_withheld_actions = staticmethod`, `_deliverable_count`, discarded `pre_drain_expired`, ignored 3rd `_deliver_outbox_batch` return). | Removed dead wrappers/returns cleanly; re-review pending. |
| Standards | SIT-N03 | Nit | `extension/room.js` overwrites `interval_minutes` with `undefined` (30m fallback) when a source state lacks a matching config entry, diverging from `helpers.mjs`. | Added `freshnessFor()` in `extension/room.js` falling back via `configured?.interval_minutes ?? source.interval_minutes` with unit tests; re-review pending. |
| Spec | NIT-01 | Nit | `delivery.py:102` `expired_by_age` docstring states `"for an active alert fails delivery"`, omitting suspended-from-active and invalidation cases. | Updated docstring to `"active or suspended-from-active alert is invalid or expired"`; re-review pending. |
| Spec | NIT-02 | Nit | `extension/background.js:97-101` reads dead `stored.collector.storage_truncated` key that nothing writes. | Removed the dead `storage_truncated` fallback and added a startup regression test in `tests/runtime/worker.test.js`; re-review pending. |

All findings from candidate `bd617e2` were verified fixed at `18342bc`.

### Candidate 18342bc Opus review findings

Candidate `18342bc3648d0515a0c0307353e4cdf8c0a6954e` passed 205 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical and 0 High findings** and zero gate/routing/privacy/CAP-cancellation/bounds/store-schema/stop-cancellation/room/INDEX defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T025653Z-90db5a`; 240.5s standards, 276.3s specification) reported 1 Medium + 4 Low + 1 Nit standards findings and 1 Medium + 2 Low + 1 Nit specification findings (8 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | HA-UNLOAD-01 | Medium | `async_unload_entry()` calls `async_stop()` before `async_unload_platforms()`; if platform unload returns `False` or raises, `_stopping` remains `True` and `situareness_degraded` stays dismissed permanently. | Added `SituarenessCoordinator.resume_after_failed_unload()` and called it on failed/raising `async_unload_platforms()`, restoring polling and notifications; re-review pending. |
| Spec | SR-01 | Medium | Home Assistant `Store.async_save` logs and swallows `WriteError`/`SerializationError` (`OSError`), so read-only/full `.storage` would otherwise appear to succeed without failing `UpdateFailed` or halting delivery. | Added tail `save_id` verification (`_verify_store_save` via `async_add_executor_job`, validated in `_valid_persisted_store`) and proved against real HA 2026.11.1 `0o500` `.storage` that swallowed `WriteError` fails the poll cleanly before notify calls; re-review pending. |
| Standards / Spec | HA-SETUP-02 / SR-03 | Low | Repeated `async_config_entry_first_refresh()` failures register duplicate `async_on_state_change` listeners on each `SETUP_RETRY`. | Deduplicated retry listeners per `(id(hass), entry.entry_id)` via `_SETUP_RETRY_UNSUBS` and `_clear_retry_listener()`, cleaned up on reload and removal; re-review pending. |
| Standards | HA-PERSIST-03 | Low | `_update_expired_unsent()` and `self.last_degraded_poll = ...` mutate `self` before `_save()`, causing double counting and lost freeze credit if `_save()` fails. | Replaced with pure `_compute_expired_unsent()` and transactional post-save commits in `_save()` (`last_degraded_poll`, `expired_unsent*`, `acknowledge_rejected`); re-review pending. |
| Standards | HA-RETRY-04 | Low | Targets failing all 3 delivery attempts (`attempts >= MAX_ATTEMPTS`) are dropped with no persistent `expired_unsent` / `situareness_degraded` disclosure. | Added `"exhausted"` to `VALID_EXPIRY_REASONS` / `delivery.expiry_reason(..., check_exhausted=True)` so 3-attempt failures latch `expired_unsent` (`expired_unsent_reasons`) and cause-accurate notifications; re-review pending. |
| Standards / Spec | DOC-CTX-05 / SR-02 | Low | `docs/CONTEXT.md:15` states every store save failure occurs before any service call, overstating post-10-target delivery group saves. | Updated `docs/CONTEXT.md:15`, `docs/ha/README.md`, and `home-assistant/README.md` to distinguish pre-delivery save failures (`UpdateFailed` before first service call) from post-group save failures; re-review pending. |
| Spec | SR-04 | Nit | `_merge_consumed_acks` moves `entry.data` entries last rather than sorting chronologically, so `acknowledged_degraded_at` could regress despite `"without downgrade"` wording. | Sorted deduplicated `consumed_acknowledgements` chronologically by parsed timestamp in `_merge_consumed_acks` and updated docs (`ordered chronologically without loss`); re-review pending. |
| Standards | TEST-NIT-06 | Nit | Drafting comment in `tests/ha/test_coordinator.py` and no-op `undefined ?? ...` in `tests/ui/helpers.test.js`. | Cleaned up comment/expression and switched `BaseCoordinator._exec` to `asyncio.to_thread` for zero slow-callback warnings; re-review pending. |

All findings from candidate `18342bc` were verified fixed at `4ea74ca`.

### Candidate 4ea74ca Opus review findings

Candidate `4ea74ca4a136f95815777a3d71035ce4c1136a7b` passed 211 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical, 0 High, and 0 Medium findings**, and zero gate/routing/privacy/persistence-compat/CAP-cancellation/bounds/overflow/ack/packaging/catalog/index defects. Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T031956Z-d2125a`; 312.2s standards, 316.6s specification) reported 1 Low + 2 Nit standards findings and 2 Low + 2 Nit specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards / Spec | SIT-R1 / SPEC-HA-02 | Low | `_verify_store_save` runs unconditionally after `await self.store.async_save`, falsely raising `OSError` -> `UpdateFailed` when HA is stopping (`CoreState.stopping` defers writes to final-write listener), and coupling to HA `Store` internals lacks documentation. | Added `_is_hass_stopping(hass)` guard skipping disk tail verification during `stopping`/`final_write`/`stopped` states, added docstring documenting `Store.path`/tail coupling, and added unit test coverage; re-review pending. |
| Spec | SPEC-HA-01 | Low | If `async_config_entry_first_refresh()` succeeds (having created `situareness_degraded`) and `async_forward_entry_setups()` raises, coordinator remains in `hass.data` and `situareness_degraded` stays raised in `setup_error`. | Moved `hass.data` registration and `async_forward_entry_setups()` under cleanup protection that pops `hass.data`, dismisses `situareness_degraded`, and calls `await coordinator.async_stop()` on failure, with unit test coverage; re-review pending. |
| Standards | SIT-R2 | Nit | `_compute_expired_unsent` when `poll_expired > 0` retains stale `expired_unsent`, `expired_unsent_at`, and `expired_unsent_reasons` even when `now > existing_until` after a >7-day outage. | Updated `_compute_expired_unsent` to reset base count, anchor timestamp, reasons, and horizon when `now > existing_until` before adding new expirations, with unit test coverage; re-review pending. |
| Standards | SIT-R3 | Nit | `docs/ha/README.md`, `home-assistant/README.md`, and `docs/spec/o3-mvp.md` reference private leading-underscore symbols and implementation save counts inside dense bullets. | Rewrote contract and operator READMEs around observable behaviors and limits without private symbol names or implementation save counts, split long bullets into scannable points, and moved `Store` internals to code docstrings; re-review pending. |
| Spec | SPEC-ROOM-01 | Nit | `extension/room.js` checks `paused` before `!enabled.length` in `renderStatus()`, rendering a gold `"Collection paused"` dot when paused with all sources disabled while `renderFeed()` displays `"No sources enabled"`. | Prioritized `!enabled.length` ahead of `paused` in `renderStatus()` so an all-disabled collector is always neutral, and added Playwright paused/all-disabled assertion; re-review pending. |
| Spec | SPEC-HA-03 | Nit | `resume_after_failed_unload()` calls `_sync_degraded_notification()` with default `quarantine_ambiguous=False`, dropping an active healthy-path `"Situareness alert scope ambiguous"` notice if platform unload fails. | Tracked `self._last_quarantine_ambiguous` across polls and defaulted `_sync_degraded_notification(quarantine_ambiguous=None)` to it so `resume_after_failed_unload()` restores active ambiguity notices, with unit test coverage; re-review pending. |

All findings from candidate `4ea74ca` were verified fixed at `0cb3656`.

### Candidate 0cb3656 Opus review findings

Candidate `0cb365603be3c7935e3a549a4b01b9ec8fe2e026` passed 215 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical and 0 High findings** and zero Standards findings above Nit (zero persistence/lifecycle/delivery/concurrency/safety-gate/privacy/browser-room defects). Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T155112Z-c46492`; 275.5s standards, 251.4s specification) reported 0 Medium/Low + 2 Nit standards findings and 1 Medium + 1 Low + 1 Nit specification findings (4 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Spec | SIT-EXP-ACK-01 | Medium | `_compute_expired_unsent` preserves earliest `expired_unsent_at` (`T1`) across subsequent expirations (`T3`) during the active 7-day window, letting an acknowledgement at `T2` (`T1 <= T2 < T3`) clear unseen `T3` expirations on reload. | Updated `_compute_expired_unsent` to advance `expired_unsent_at = max(existing_at, now).isoformat()` whenever new expirations occur (`poll_expired > 0`), updated `docs/spec/o3-mvp.md` / operator READMEs, and verified intermediate-timestamp rejection in unit tests; re-review pending. |
| Spec | SIT-ACK-COMMIT-02 | Low | `docs/spec/o3-mvp.md` includes `entry acknowledgement state` under post-verification commit, whereas load-time `_try_acknowledge` records rejected or no-op ISO-8601 acknowledgements immediately via `_record_consumed_ack`. | Narrowed `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` to distinguish poll-time post-verification commits from load-time rejected/no-op ack and initial store-error markers; re-review pending. |
| Standards | TRUTH-01 | Nit | `output_blocked` reads `false` during polls with `quarantine_ambiguous: true`, even though `quarantine_all=True` suspends every lineage and blocks all deliveries for that poll. | Updated `_degraded_health` and `_healthy_snapshot` so `output_blocked` is `True` whenever `quarantine_ambiguous` holds (while keeping `evidence_degraded` `False` unless in an evidence degraded mode), synchronized contract/READMEs, and added assertions in unit tests; re-review pending. |
| Standards / Spec | DOC-01 / SIT-LOOP-03 | Nit | `docs/spec/o3-mvp.md`, `docs/ha/README.md`, and `home-assistant/README.md` claim `"only per-group <=10-item qualification rechecks run on the event loop"`, understating bounded `O(n)` in-memory setup, outbox, and snapshot bookkeeping on the loop. | Reworded all three docs to state `bounded per-group <=10-item qualification/pending rechecks and O(n) in-memory setup, outbox, and snapshot bookkeeping` run on the event loop; re-review pending. |

All findings from candidate `0cb3656` were verified fixed at `62337c2`.

### Candidate 62337c2 Opus review findings

Candidate `62337c2d56ec9ed0eb7851e9fea92445af0331b4` passed 215 local tests (with zero asyncio slow-callback warnings), Ruff, deterministic packaging, and live anonymous smoke, with **0 Critical and 0 High findings** and zero Specification findings above Low (zero qualification/CAP/quarantine/delivery/overflow/ack/lifecycle/room/privacy/live-gate defects). Independent Claude Opus 5.5 medium-effort reviews (`run_id`: `20261118T160611Z-e864d7`; 313.6s standards, 346.7s specification) reported 1 Medium + 2 Low + 1 Low/Nit standards findings and 0 Medium + 1 Low + 2 Nit specification findings (6 unique findings total):

| Axis | Code | Severity | Finding | Current disposition |
| --- | --- | --- | --- | --- |
| Standards | HA-01 | Medium | `Store(hass, 1, prefix, private=True)` uses HA's default `serialize_in_event_loop=True`, serializing large outboxes on the event loop contrary to off-loop claims. | Configured `Store(..., private=True, atomic_writes=True, serialize_in_event_loop=False)` with isolated top-level collection copies in `_save` and verified constructor args in `RecordingStore`; re-review pending. |
| Standards | HA-02 | Low | `Store` omitted `atomic_writes=True`, and docs overstated non-atomic immediate reads as disk-durable against power loss. | Enabled `atomic_writes=True`, clarified `_verify_store_save` docstring on filesystem write verification + OS/fsync boundaries, and widened at-least-once caveats in contract, READMEs, and `docs/CONTEXT.md` to cover crash, power loss, or save failure; re-review pending. |
| Standards | HA-03 | Low (nit) | Fallback `records = err.records if err.records is not None else self.records` in `_update_once()` could mutate committed `self.records` in place on the executor if `records=None`. | Changed fallback to `deepcopy(self.records)` with regression test coverage; re-review pending. |
| Spec | SPEC-L1 | Low | `_valid_persisted_store` checked only `isinstance(record["updated"], str)` without parsing it, and `cancellation_horizon` fell back to `MAX_TIMESTAMP` when `"updated"` was absent. | Required parseable `timestamp(record["updated"])` in `_valid_persisted_store` and bounded missing-`"updated"` records by poll observation time `now + 5m` in `cancellation_horizon(..., now=now)` with updated domain/coordinator tests; re-review pending. |
| Spec | SPEC-N1 | Nit | `_sync_degraded_notification` did not qualify `quarantine_ambiguous`, `acknowledge_rejected`, or `expired_unsent` notices when running in shadow mode. | Added explicit `" (Shadow mode: live output is disabled.)"` qualification across all three notification branches with live vs shadow unit assertions; re-review pending. |
| Standards / Spec | DOC-01 / DOC-N1 | Low / Nit | Operator READMEs and `docs/reference/cap-cancellation.md` duplicated full normative state details instead of linking to `docs/spec/o3-mvp.md`, and docs mislabeled setup-time store validation as `"post-fetch"`. | Consolidated normative details in `docs/spec/o3-mvp.md` (with accurate `"setup-time store validation"` wording) and distilled `docs/ha/README.md`, `home-assistant/README.md`, and `docs/reference/cap-cancellation.md` into concise summaries linking to the spec; re-review pending. |

All findings from candidate `62337c2` are repaired on `wip/supervisor-handoff-20261117` (verified across 216 automated tests, including 13 real HA 2026.11.1 tests, with zero asyncio slow-callback warnings). Independent Claude Opus 5.5 (`standards`, `spec`, and fresh `adversarial`) reviews on the new immutable candidate remain required before release approval.
All findings from candidate `0cb3656` are repaired on `wip/supervisor-handoff-20261117` (verified across 215 automated tests, including 13 real HA 2026.11.1 tests, with zero asyncio slow-callback warnings). Independent Claude Opus 5.5 (`standards`, `spec`, and fresh `adversarial`) reviews on the new immutable candidate remain required before release approval.
