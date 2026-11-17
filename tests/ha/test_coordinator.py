"""Mocked HA boundary tests, not an installed Home Assistant run."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_domain import PACKAGE, config, feature, d, cohere


def module(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


class BaseCoordinator:
    def __init__(self, hass, *args, **kwargs):
        self.hass = hass


class UpdateFailed(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


class Store:
    def __init__(self):
        self.saved = []
        self.fail = False

    async def async_save(self, value):
        if self.fail:
            raise OSError("disk full")
        self.saved.append(value)


class Services:
    def __init__(self):
        self.calls = []

    async def async_call(self, *args, **kwargs):
        self.calls.append(args)


HA_MODULES = {
    "homeassistant": module("homeassistant"),
    "homeassistant.const": module(
        "homeassistant.const", Platform=types.SimpleNamespace(SENSOR="sensor")
    ),
    "homeassistant.exceptions": module(
        "homeassistant.exceptions", ConfigEntryNotReady=ConfigEntryNotReady
    ),
    "homeassistant.helpers": module("homeassistant.helpers"),
    "homeassistant.helpers.aiohttp_client": module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: None,
    ),
    "homeassistant.helpers.storage": module(
        "homeassistant.helpers.storage", Store=Store
    ),
    "homeassistant.helpers.update_coordinator": module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=BaseCoordinator,
        UpdateFailed=UpdateFailed,
    ),
}


class CoordinatorBoundary(unittest.IsolatedAsyncioTestCase):
    async def test_baseline_shadow_failure_and_persistence(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        store = Store()
        hass = types.SimpleNamespace(services=Services())
        coordinator = mod.SituarenessCoordinator(hass, config(), store, {})
        # Use current times because the coordinator supplies its own clock.
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)
        e = d.normalize(feature())
        for key, delta in [
            ("sent", -1),
            ("effective", -1),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            e[key] = (now + timedelta(minutes=delta)).isoformat()
        cohere(e)

        async def fetch(*args):
            return [e]

        with patch.object(mod, "fetch", fetch):
            data = await coordinator._async_update_data()
            self.assertEqual(data["planned_count"], 0)
            self.assertTrue(data["shadow"])
            self.assertEqual(hass.services.calls, [])
            e["instruction"] = "Take shelter immediately inside."
            data = await coordinator._async_update_data()
            self.assertEqual(data["planned_count"], 1)
            self.assertEqual(hass.services.calls, [])
            before = coordinator.records.copy()
            store.fail = True
            e["instruction"] = "Take shelter in a basement."
            with self.assertRaises(UpdateFailed):
                await coordinator._async_update_data()
            self.assertEqual(coordinator.records, before)

        async def failed(*args):
            raise OSError("offline")

        with patch.object(mod, "fetch", failed), self.assertRaises(UpdateFailed):
            await coordinator._async_update_data()
        self.assertEqual(coordinator.records, before)

    async def test_retry_restart_cancellation_and_crash_windows(self):
        import copy
        from datetime import datetime, timezone, timedelta

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        e = d.normalize(feature())
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            e[key] = (now + timedelta(minutes=delta)).isoformat()
        cohere(e)

        def mark_cap(event, seconds, refs=()):
            sent = (now + timedelta(seconds=seconds)).isoformat()
            event["sent"] = sent
            event["cap_identity"] = [
                "nws@example.test",
                event["id"].split("/alerts/", 1)[1],
                sent,
            ]
            event["references"] = [ref["id"] for ref in refs]
            event["reference_identities"] = [ref["cap_identity"] for ref in refs]
            event["cap_references_valid"] = True

        async def fetch(*args):
            return [e]

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        class DurableStore(Store):
            def __init__(self):
                super().__init__()
                self.snapshot = None
                self.fail_at = 0
                self.count = 0

            async def async_save(self, value):
                self.count += 1
                if self.count == self.fail_at:
                    raise OSError("disk failed")
                self.snapshot = copy.deepcopy(value)

        class Flaky(Services):
            def __init__(self):
                super().__init__()
                self.fail = True

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if self.fail:
                    raise OSError("offline")

        store = DurableStore()
        services = Flaky()
        hass = types.SimpleNamespace(services=services)
        with patch.object(mod, "fetch", fetch):
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            data = await first._async_update_data()
            self.assertEqual((data["pending_count"], data["delivery_failures"]), (1, 1))
            services.fail = False
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            data = await restarted._async_update_data()
            self.assertEqual((data["pending_count"], len(services.calls)), (0, 2))
            await restarted._async_update_data()
            self.assertEqual(len(services.calls), 2)

            # Pending work survives equivalent successors and a restart even
            # when the latest update references both the original and prior ID.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            original = copy.deepcopy(e)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            e["id"] = original["id"] + "-b"
            e["references"] = [original["id"]]
            cohere(e, original)
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 1))
            self.assertEqual(store.snapshot["outbox"][0]["incident_id"], e["id"])
            predecessor = copy.deepcopy(e)
            e["id"] = original["id"] + "-c"
            e["references"] = [original["id"], original["id"] + "-b"]
            cohere(e, original, predecessor)
            e["expires"] = (now + timedelta(minutes=40)).isoformat()
            e["ends"] = e["expires"]
            services.fail = False
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 3)
            e.clear()
            e.update(original)

            # Failure after the service accepted leaves durable pending work; a restart may duplicate it.
            store = DurableStore()
            store.fail_at = 2
            services = Flaky()
            services.fail = False
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            with self.assertRaises(UpdateFailed):
                await first._async_update_data()
            self.assertEqual(len(store.snapshot["outbox"]), 1)
            store.fail_at = 0
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            await restarted._async_update_data()
            self.assertEqual(len(services.calls), 2)
            self.assertEqual(store.snapshot["outbox"], [])

            # A transient absence suspends, rather than sends or discards, a retry.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            self.assertEqual(len(store.snapshot["outbox"]), 1)

            async def empty(*args):
                return []

            with patch.object(mod, "fetch", empty):
                services.fail = False
                restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
                await restarted._async_update_data()
            self.assertEqual(len(services.calls), 1)
            self.assertEqual(len(store.snapshot["outbox"]), 1)
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 2)

            # Partial collection suspends an unconfirmed prior item while an
            # unrelated current alert can still be processed and reported.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            unrelated = copy.deepcopy(e)
            unrelated["id"] += "-unrelated"
            cohere(unrelated)

            async def partial(*args):
                from test_domain import collector

                return collector.CollectedEvents(
                    [unrelated], 1, [[e["id"] + "-oversize", e["id"]]], False
                )

            services.fail = False
            with patch.object(mod, "fetch", partial):
                data = await first._async_update_data()
            self.assertTrue(data["partial"])
            self.assertEqual((data["quarantined_count"], data["active_count"]), (1, 1))
            self.assertEqual(
                (
                    data["pending_count"],
                    data["deliverable_count"],
                    data["suspended_count"],
                ),
                (1, 0, 1),
            )
            self.assertEqual(len(services.calls), 2)

            # Root-only references find the current descendant and carry a
            # retry exactly once, linking the current message.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            b = copy.deepcopy(e)
            b.update(id=e["id"] + "-b", references=[e["id"]])
            cohere(b, e)

            async def current(*args):
                return [b]

            with patch.object(mod, "fetch", current):
                await first._async_update_data()
                b["id"] = e["id"] + "-c"
                cohere(b, e)
                services.fail = False
                data = await first._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 3)
            self.assertEqual(services.calls[-1][2]["data"]["url"], b["id"])

            # Root-only cancellation leaves a descendant retry uncertain, never sent.
            original_event = copy.deepcopy(e)
            mark_cap(e, -5)
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            b = copy.deepcopy(e)
            b["id"] += "-b"
            mark_cap(b, -4, [e])
            with patch.object(mod, "fetch", current):
                await first._async_update_data()
                cancelled = copy.deepcopy(e)
                cancelled.update(id=e["id"] + "-cancel", message_type="Cancel")
                mark_cap(cancelled, -3, [e])
                saved_b = b
                b = cancelled
                services.fail = False
                data = await first._async_update_data()
                self.assertEqual(data["pending_count"], 1)
                self.assertTrue(data["partial"])
                b = saved_b
                data = await first._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 1))
            self.assertEqual(len(services.calls), 2)
            e.clear()
            e.update(original_event)

            # A failed target follows the eligible sibling, regardless of order.
            for reverse in (False, True):
                store = DurableStore()
                services = Flaky()
                hass = types.SimpleNamespace(services=services)
                first = mod.SituarenessCoordinator(hass, cfg, store, {})
                await first._async_update_data()
                b = copy.deepcopy(e)
                b.update(id=e["id"] + "-b", references=[e["id"]])
                cohere(b, e)
                c = copy.deepcopy(b)
                c.update(id=e["id"] + "-c", geometry=None)
                cohere(c, e)

                async def siblings(*args):
                    return [b, c][:: -1 if reverse else 1]

                services.fail = False
                restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
                with patch.object(mod, "fetch", siblings):
                    data = await restarted._async_update_data()
                self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
                self.assertEqual(len(services.calls), 2)

            # If two equivalent siblings are first seen together, a retry can
            # follow the remaining sibling even though neither references the other.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            b = copy.deepcopy(e)
            b.update(id=e["id"] + "-b", references=[e["id"]])
            cohere(b, e)
            c = copy.deepcopy(b)
            c["id"] = e["id"] + "-c"
            cohere(c, e)

            async def both(*args):
                return [b, c]

            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            with patch.object(mod, "fetch", both):
                data = await first._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (1, 1))

            async def just_c(*args):
                return [c]

            services.fail = False
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            with patch.object(mod, "fetch", just_c):
                data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 2)

            # A temporarily ineligible merge discards the changed action and
            # retains the matching one, in either reference order.
            for reverse in (False, True):
                store = DurableStore()
                services = Flaky()
                hass = types.SimpleNamespace(services=services)
                b = copy.deepcopy(e)
                b.update(id=e["id"] + "-b", references=[e["id"]])
                cohere(b, e)
                c = copy.deepcopy(b)
                c.update(id=e["id"] + "-c", instruction="Take shelter in the basement.")
                cohere(c, e)
                first = mod.SituarenessCoordinator(hass, cfg, store, {})
                with patch.object(mod, "fetch", both):
                    data = await first._async_update_data()
                self.assertEqual((data["planned_count"], data["pending_count"]), (2, 2))
                merged = copy.deepcopy(b)
                refs = [b["id"], c["id"]]
                merged.update(
                    id=e["id"] + "-merge",
                    references=refs[::-1] if reverse else refs,
                    expires=(now - timedelta(minutes=1)).isoformat(),
                )
                cohere(merged, *(c, b) if reverse else (b, c))

                async def merge(*args):
                    return [merged]

                services.fail = False
                restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
                with patch.object(mod, "fetch", merge):
                    data = await restarted._async_update_data()
                    self.assertEqual(
                        (data["planned_count"], data["pending_count"]), (0, 1)
                    )
                    merged["expires"] = (now + timedelta(minutes=30)).isoformat()
                    data = await restarted._async_update_data()
                self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
                self.assertEqual(len(services.calls), 3)

            # An ineligible update suspends the target until a current update qualifies.
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            b = copy.deepcopy(e)
            b.update(
                id=e["id"] + "-b",
                references=[e["id"]],
                expires=(now - timedelta(minutes=1)).isoformat(),
            )
            cohere(b, e)

            async def update(*args):
                return [b]

            services.fail = False
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            with patch.object(mod, "fetch", update):
                data = await restarted._async_update_data()
                self.assertEqual((data["planned_count"], data["pending_count"]), (0, 1))
                self.assertEqual(len(services.calls), 1)
                b["expires"] = (now + timedelta(minutes=30)).isoformat()
                data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 2)

            # An explicitly referenced message loses its pending retry.
            original_event = copy.deepcopy(e)
            mark_cap(e, -5)
            store = DurableStore()
            services = Flaky()
            hass = types.SimpleNamespace(services=services)
            first = mod.SituarenessCoordinator(hass, cfg, store, {})
            await first._async_update_data()
            b = copy.deepcopy(e)
            b.update(id=e["id"] + "-cancel", message_type="Cancel")
            mark_cap(b, -3, [e])
            services.fail = False
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            with patch.object(mod, "fetch", update):
                data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 0))
            self.assertEqual(len(services.calls), 1)

    async def test_legacy_journal_without_gate_marker_does_not_force_live_realert(self):
        from datetime import datetime, timedelta, timezone

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        event = d.normalize(feature())
        for field, delta in [
            ("sent", -1),
            ("effective", -1),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            event[field] = (now + timedelta(minutes=delta)).isoformat()
        cohere(event)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        records, _ = d.reconcile({}, [event], cfg, now)
        services = Services()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, Store(), {"records": records}
        )

        async def fetch(*args):
            return [event]

        with patch.object(mod, "fetch", fetch):
            result = await coordinator._async_update_data()
        self.assertEqual(result["planned_count"], 0)
        self.assertFalse(services.calls)

    async def test_malformed_existing_store_is_degraded_not_fresh_install(self):
        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        cfg = config()
        cfg.update(live_enabled=True, commissioning_passed=True)
        services = Services()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, Store(), ["corrupt"]
        )
        with patch.object(
            mod, "fetch", side_effect=AssertionError("must not fetch while degraded")
        ):
            health = await coordinator._async_update_data()
        self.assertTrue(health["evidence_degraded"])
        self.assertTrue(health["output_blocked"])
        self.assertIsNone(health["active_count"])
        self.assertFalse(services.calls)
        fresh = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, Store(), None
        )
        self.assertFalse(fresh.degraded)

    async def test_uncertain_retry_cannot_move_to_independent_sibling(self):
        import copy
        from datetime import datetime, timedelta, timezone
        from test_domain import delivery

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)

        def make(name, seconds, refs=(), kind="Update"):
            event = d.normalize(feature())
            event.update(id="https://api.weather.gov/alerts/" + name, message_type=kind)
            for field, delta in [
                ("sent", seconds),
                ("effective", -120),
                ("onset", -60),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                event[field] = (now + timedelta(seconds=delta)).isoformat()
            event["cap_identity"] = ["nws@example.test", name, event["sent"]]
            event["references"] = [ref["id"] for ref in refs]
            event["reference_identities"] = [ref["cap_identity"] for ref in refs]
            event["cap_references_valid"] = True
            return event

        root = make("root", -100, kind="Alert")
        branch = make("branch", -90, [root])
        child = make("child", -80, [branch])
        sibling = make("sibling", -70, [root])
        cancel = make("cancel", -60, [branch], "Cancel")
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        records = {}
        for event in (root, branch, child):
            records, _ = d.reconcile(records, [event], cfg, now)
        decision = d.qualify(child, cfg, now)
        plan = {
            "id": child["id"],
            "fingerprint": d.fingerprint(child, decision),
            "event": child["event"],
            "instruction": child["instruction"],
            "affected": decision["affected"],
            "phones": cfg["phones"],
        }
        item = delivery.targets(plan, cfg, now)[0]
        services, store = Services(), Store()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services),
            cfg,
            store,
            {
                "initialized": True,
                "was_live": True,
                "records": copy.deepcopy(records),
                "outbox": [item],
            },
        )

        async def fetch(*args):
            return [cancel, sibling]

        with patch.object(mod, "fetch", fetch):
            health = await coordinator._async_update_data()
        self.assertTrue(health["cancellation_uncertain"])
        self.assertEqual(health["suspended_count"], 1)
        self.assertEqual(coordinator.outbox[0]["incident_id"], child["id"])
        self.assertNotIn(
            child["id"], [call[2]["data"].get("url") for call in services.calls]
        )

    async def test_cancellation_evidence_loss_latches_before_delivery_and_survives_restart(
        self,
    ):
        from datetime import datetime, timedelta, timezone
        from test_domain import collector

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        e = d.normalize(feature())
        for key, minutes in [
            ("sent", -1),
            ("effective", -1),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            e[key] = (now + timedelta(minutes=minutes)).isoformat()
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        for mode in ("oversized", "overflow", "failed_after_cancel", "conflict"):
            with self.subTest(mode=mode):
                records = (
                    {
                        f"old-{i}": {
                            "state": "cancelled",
                            "cancel_message": True,
                            "lineage": [],
                            "updated": now.isoformat(),
                        }
                        for i in range(1000)
                    }
                    if mode == "overflow"
                    else {}
                )
                if mode == "conflict":
                    records[e["id"]] = {
                        "state": "cancelled",
                        "cancel_message": True,
                        "cap_identity": ["sender", "id", e["sent"]],
                        "cap_references": [],
                        "lineage": [e["id"]],
                    }
                persisted = {
                    "initialized": True,
                    "was_live": True,
                    "records": records,
                    "outbox": [],
                }
                source = collector.CollectedEvents(
                    [e],
                    1 if mode == "oversized" else 0,
                    [],
                    False,
                    uncertain_cancellation=(mode == "oversized"),
                )

                async def fetch(*args):
                    if mode == "failed_after_cancel":
                        raise collector.CancellationEvidenceLost("partial fetch")
                    return source

                store, services = Store(), Services()
                coordinator = mod.SituarenessCoordinator(
                    types.SimpleNamespace(services=services), cfg, store, persisted
                )
                with patch.object(mod, "fetch", fetch):
                    health = await coordinator._async_update_data()
                self.assertTrue(health["evidence_degraded"])
                self.assertTrue(health["output_blocked"])
                self.assertIsNone(health["active_count"])
                self.assertEqual(services.calls, [])
                self.assertTrue(store.saved[-1]["degraded"])
                restarted = mod.SituarenessCoordinator(
                    types.SimpleNamespace(services=services),
                    cfg,
                    Store(),
                    store.saved[-1],
                )
                with patch.object(
                    mod,
                    "fetch",
                    side_effect=AssertionError("must not collect while latched"),
                ):
                    self.assertTrue(
                        (await restarted._async_update_data())["evidence_degraded"]
                    )
                self.assertEqual(services.calls, [])

    async def test_merged_retries_are_deduplicated_and_reload_waits_for_acceptance(
        self,
    ):
        import asyncio
        import copy
        from datetime import datetime, timedelta, timezone
        from test_domain import delivery

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        a = d.normalize(feature())
        for key, delta in [
            ("sent", -1),
            ("effective", -1),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            a[key] = (now + timedelta(minutes=delta)).isoformat()
        cohere(a)
        b = copy.deepcopy(a)
        b["id"] += "-sibling"
        cohere(b)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        ra, pa = d.reconcile({}, [a], cfg, now)
        rb, pb = d.reconcile({}, [b], cfg, now)
        items = delivery.targets(pa[0], cfg, now) + delivery.targets(pb[0], cfg, now)
        merged = copy.deepcopy(a)
        merged.update(id=a["id"] + "-merged", references=[a["id"], b["id"]])
        cohere(merged, a, b)
        started, finish = asyncio.Event(), asyncio.Event()

        class WaitingServices(Services):
            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                started.set()
                await finish.wait()

        async def fetch(*args):
            return [merged]

        store = Store()
        services = WaitingServices()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services),
            cfg,
            store,
            {
                "initialized": True,
                "was_live": True,
                "records": {**ra, **rb},
                "outbox": items,
            },
        )
        with patch.object(mod, "fetch", fetch):
            update = asyncio.create_task(coordinator._async_update_data())
            await asyncio.wait_for(started.wait(), 2)
            stop = asyncio.create_task(coordinator.async_stop())
            await asyncio.sleep(0)
            self.assertFalse(stop.done())
            finish.set()
            await asyncio.wait_for(update, 2)
            await asyncio.wait_for(stop, 2)
        self.assertEqual(len(services.calls), 1)
        self.assertEqual(store.saved[-1]["outbox"], [])
        self.assertTrue(store.saved[-1]["outcomes"][-1]["accepted"])
        restarted = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, Store(), store.saved[-1]
        )
        with patch.object(mod, "fetch", fetch):
            await restarted._async_update_data()
        self.assertEqual(len(services.calls), 1)

    async def test_new_hazard_after_restart_is_not_baselined(self):
        from datetime import datetime, timezone, timedelta

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        e = d.normalize(feature())
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            e[key] = (now + timedelta(minutes=delta)).isoformat()
        cohere(e)

        async def fetch(*args):
            return [e]

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        services = Services()
        store = Store()
        hass = types.SimpleNamespace(services=services)
        restarted = mod.SituarenessCoordinator(
            hass, cfg, store, {"initialized": True, "records": {}, "outbox": []}
        )
        with patch.object(mod, "fetch", fetch):
            await restarted._async_update_data()
        self.assertEqual(len(services.calls), 1)

    async def test_clock_advance_suspends_expired_before_next_group(self):
        from datetime import datetime, timedelta, timezone

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, HA_MODULES):
            spec.loader.exec_module(mod)
        now = datetime.now(timezone.utc)
        e = d.normalize(feature())
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 5),
            ("ends", 5),
        ]:
            e[key] = (now + timedelta(seconds=delta)).isoformat()
        cohere(e)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now

        class Advancing(Services):
            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if len(self.calls) == 10:
                    Clock.current = now + timedelta(seconds=6)

        async def fetch(*args):
            return [e]

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(11)],
            tts_entity=None,
        )
        services = Advancing()
        hass = types.SimpleNamespace(services=services)
        coordinator = mod.SituarenessCoordinator(hass, cfg, Store(), {})
        with patch.object(mod, "fetch", fetch), patch.object(mod, "datetime", Clock):
            result = await coordinator._async_update_data()
        self.assertEqual(len(services.calls), 10)
        self.assertEqual(result["pending_count"], 1)
