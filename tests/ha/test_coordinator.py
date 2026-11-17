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

    async def test_invalid_cap_suspends_retry_across_restart_and_allows_independent_alert(
        self,
    ):
        import copy
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
        original = d.normalize(feature())
        for field, minutes in [
            ("sent", -2),
            ("effective", -2),
            ("onset", 0),
            ("expires", 30),
            ("ends", 30),
        ]:
            original[field] = (now + timedelta(minutes=minutes)).isoformat()
        cohere(original)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        class Flaky(Services):
            fail = True

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if self.fail:
                    raise OSError("offline")

        events = [original]

        async def fetch(*args):
            return events

        services, store = Flaky(), Store()
        hass = types.SimpleNamespace(services=services)
        coordinator = mod.SituarenessCoordinator(hass, cfg, store, {})
        with patch.object(mod, "fetch", fetch):
            first = await coordinator._async_update_data()
        self.assertEqual((first["pending_count"], first["delivery_failures"]), (1, 1))

        invalid = copy.deepcopy(original)
        invalid["cap_identity"][1] = "conflicting-identifier"
        independent = copy.deepcopy(original)
        independent["id"] += "-independent"
        cohere(independent)
        events = [invalid, independent]
        services.fail = False
        restarted = mod.SituarenessCoordinator(hass, cfg, Store(), store.saved[-1])
        with patch.object(mod, "fetch", fetch):
            health = await restarted._async_update_data()
        self.assertTrue(health["partial"])
        self.assertEqual((health["pending_count"], health["suspended_count"]), (1, 1))
        self.assertEqual(restarted.outbox[0]["incident_id"], original["id"])
        self.assertEqual(len(services.calls), 2)
        self.assertEqual(services.calls[-1][2]["data"]["url"], independent["id"])
        self.assertEqual(restarted.records[invalid["id"]]["state"], "quarantined")
        self.assertEqual(restarted.records[independent["id"]]["state"], "active")

        # A second restart preserves the suspended target; no invalid call is made.
        resumed = mod.SituarenessCoordinator(
            hass, cfg, Store(), restarted.store.saved[-1]
        )
        with patch.object(mod, "fetch", fetch):
            again = await resumed._async_update_data()
        self.assertEqual((again["pending_count"], again["suspended_count"]), (1, 1))
        self.assertEqual(len(services.calls), 2)

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
        for bad_store in (
            ["corrupt"],
            {"initialized": True},
            {"records": {"id": {"actions": {"fp": [123]}}}},
            {"records": {"id": {"updated": 123}}},
            {"records": {"id": {"inactive_since": 123}}},
            {"records": {"id": {"cancel_message": "yes"}}},
            {"records": {"id": {"cancellation_expired": "no"}}},
            {"records": {"id": {"action_identity": ["unhashable"]}}},
            {"records": {"id": {"fingerprint": 123}}},
            {"records": {"id": {"prior_state": 123}}},
            {"records": {"id": {"action_affected": [123]}}},
            {"initialized": 1},
            {"was_live": "true"},
            {"acknowledged_degraded_at": "not-a-timestamp"},
            {"last_degraded_poll": "not-a-timestamp"},
            {
                "outbox": [
                    {
                        "key": "k",
                        "incident_id": "i",
                        "fingerprint": "f",
                        "kind": "phone",
                        "target": "t",
                        "created": "2026-11-17T00:00:00+00:00",
                        "event": "Tornado Warning",
                        "instruction": "Take shelter.",
                        "source_url": "https://api.weather.gov/alerts/1",
                        "affected_names": ["New York"],
                        "location": None,
                        "attempts": True,
                    }
                ]
            },
            {
                "outbox": [
                    {
                        "key": "k",
                        "incident_id": "i",
                        "fingerprint": "f",
                        "kind": "phone",
                        "target": "t",
                        "created": "2026-11-17T00:00:00+00:00",
                        "event": "Tornado Warning",
                        "instruction": "Take shelter.",
                        "source_url": "https://api.weather.gov/alerts/1",
                        "affected_names": ["New York"],
                        "attempts": 0,
                    }
                ]
            },
            {
                "outbox": [
                    {
                        "key": "k",
                        "incident_id": "i",
                        "fingerprint": "f",
                        "kind": "phone",
                        "target": "t",
                        "created": "2026-11-17T00:00:00+00:00",
                        "location": None,
                        "attempts": 0,
                    }
                ]
            },
            {
                "outbox": [
                    {
                        "key": "k",
                        "incident_id": "i",
                        "fingerprint": "f",
                        "kind": "phone",
                        "target": "t",
                        "created": "not-an-iso-date",
                        "event": "Tornado Warning",
                        "instruction": "Take shelter.",
                        "source_url": "https://api.weather.gov/alerts/1",
                        "affected_names": ["New York"],
                        "location": None,
                        "attempts": 0,
                    }
                ]
            },
        ):
            with self.subTest(bad_store=bad_store):
                coordinator = mod.SituarenessCoordinator(
                    types.SimpleNamespace(services=services), cfg, Store(), bad_store
                )
                with patch.object(
                    mod,
                    "fetch",
                    side_effect=AssertionError("must not fetch while malformed_store"),
                ):
                    health = await coordinator._async_update_data()
                self.assertTrue(health["evidence_degraded"])
                self.assertTrue(health["output_blocked"])
                self.assertEqual(health["degraded_reason"], "malformed_store")
                self.assertIsNotNone(health["degraded_at"])
                self.assertIsNone(health["degraded_until"])
                self.assertFalse(health["quarantine_ambiguous"])
                self.assertFalse(health["cancellation_uncertain"])
                self.assertFalse(health["partial"])
                self.assertIsNone(health["active_count"])
                self.assertFalse(services.calls)

        # acknowledge_degraded_at must NEVER clear malformed_store or reset corrupt storage.
        ack_cfg = {
            **cfg,
            "acknowledge_degraded_at": "2026-11-17T00:00:00+00:00",
        }
        malformed_with_ack = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), ack_cfg, Store(), ["corrupt"]
        )
        self.assertTrue(malformed_with_ack.degraded)
        self.assertEqual(malformed_with_ack.degraded_reason, "malformed_store")
        with patch.object(
            mod,
            "fetch",
            side_effect=AssertionError("must not fetch while malformed_store"),
        ):
            health_ack = await malformed_with_ack._async_update_data()
        self.assertTrue(health_ack["evidence_degraded"])
        self.assertEqual(health_ack["degraded_reason"], "malformed_store")

        # Malformed store persists a stable malformed_store_at in entry.data
        # across reloads when persisted store itself lacks degraded_at.
        class FakeEntries:
            def __init__(self, entry):
                self.entry = entry

            def async_update_entry(self, entry, *, data):
                entry.data = data

        bad_entry = types.SimpleNamespace(data={})
        hass_bad = types.SimpleNamespace(
            services=services, config_entries=FakeEntries(bad_entry)
        )
        c_bad1 = mod.SituarenessCoordinator(
            hass_bad, cfg, Store(), ["corrupt"], entry=bad_entry
        )
        c_bad2 = mod.SituarenessCoordinator(
            hass_bad, cfg, Store(), ["corrupt"], entry=bad_entry
        )
        self.assertEqual(c_bad1.degraded_at, c_bad2.degraded_at)
        self.assertIsNone(c_bad1.degraded_until)

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
        self.assertIn(
            sibling["id"], [call[2]["data"].get("url") for call in services.calls]
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
        cohere(e)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        expected_reasons = {
            "oversized": "malformed_cancellation",
            "overflow": "cancellation_evidence_overflow",
            "conflict": "conflicting_cancellation",
        }
        for mode, expected_reason in expected_reasons.items():
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
                    mode == "oversized",
                    uncertain_cancellation=(mode == "oversized"),
                )

                async def fetch(*args):
                    return source

                store, services = Store(), Services()
                coordinator = mod.SituarenessCoordinator(
                    types.SimpleNamespace(services=services), cfg, store, persisted
                )
                with patch.object(mod, "fetch", fetch):
                    health = await coordinator._async_update_data()
                self.assertTrue(health["evidence_degraded"])
                self.assertTrue(health["output_blocked"])
                self.assertEqual(health["degraded_reason"], expected_reason)
                self.assertIsNotNone(health["degraded_at"])
                self.assertIsNotNone(health["degraded_until"])
                self.assertEqual(health["quarantine_ambiguous"], mode == "oversized")
                self.assertTrue(health["cancellation_uncertain"])
                self.assertEqual(health["event_count"], 1)
                self.assertEqual(len(health["events"]), 1)
                self.assertIsNone(health["active_count"])
                self.assertEqual(services.calls, [])
                self.assertTrue(store.saved[-1]["degraded"])
                self.assertLessEqual(len(store.saved[-1]["records"]), 1000)

                # Restart continues collecting read-only while output remains blocked;
                # per-poll quarantine_ambiguous / cancellation_uncertain clear on a clean poll.
                restarted = mod.SituarenessCoordinator(
                    types.SimpleNamespace(services=services),
                    cfg,
                    Store(),
                    store.saved[-1],
                )
                collected = []

                clean_e = d.normalize(feature())
                clean_e["id"] = e["id"] + "-clean"
                for key, minutes in [
                    ("sent", -1),
                    ("effective", -1),
                    ("onset", 0),
                    ("expires", 30),
                    ("ends", 30),
                ]:
                    clean_e[key] = (now + timedelta(minutes=minutes)).isoformat()
                cohere(clean_e)

                async def clean_fetch(*args):
                    collected.append(True)
                    return collector.CollectedEvents([clean_e], 0, [], False)

                with patch.object(mod, "fetch", clean_fetch):
                    restarted_health = await restarted._async_update_data()
                self.assertTrue(collected)
                self.assertTrue(restarted_health["evidence_degraded"])
                self.assertTrue(restarted_health["output_blocked"])
                self.assertFalse(restarted_health["quarantine_ambiguous"])
                self.assertFalse(restarted_health["cancellation_uncertain"])
                self.assertFalse(restarted_health["partial"])
                self.assertEqual(restarted_health["event_count"], 1)
                self.assertEqual(services.calls, [])

        # Transient fetch failure does NOT latch degraded state.
        store, services = Store(), Services()
        transient = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, store, {}
        )

        async def failed_fetch(*args):
            raise ValueError("incomplete pagination after cancel")

        with patch.object(mod, "fetch", failed_fetch):
            with self.assertRaises(UpdateFailed):
                await transient._async_update_data()
        self.assertFalse(transient.degraded)

    async def test_degraded_recovery_via_ack_and_seven_day_horizon(self):
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
        cohere(e)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        persisted = {
            "initialized": True,
            "was_live": True,
            "records": {},
            "outbox": [],
            "degraded": True,
            "degraded_reason": "conflicting_cancellation",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=6)).isoformat(),
        }
        # Stale acknowledgment before degraded_at does not clear degradation.
        old_ack_cfg = {
            **cfg,
            "acknowledge_degraded_at": (now - timedelta(hours=2)).isoformat(),
        }
        services = Services()
        c_old_ack = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), old_ack_cfg, Store(), persisted
        )
        self.assertTrue(c_old_ack.degraded)

        # Current acknowledgment >= degraded_at clears degradation immediately.
        new_ack_cfg = {
            **cfg,
            "acknowledge_degraded_at": (now - timedelta(minutes=30)).isoformat(),
        }
        c_new_ack = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), new_ack_cfg, Store(), persisted
        )
        self.assertFalse(c_new_ack.degraded)

        async def fetch_alert(*args):
            return collector.CollectedEvents([e], 0, [], False)

        with patch.object(mod, "fetch", fetch_alert):
            health = await c_new_ack._async_update_data()
        self.assertFalse(health["evidence_degraded"])
        self.assertFalse(health["output_blocked"])
        self.assertIsNone(health["degraded_reason"])
        self.assertEqual(len(services.calls), 1)

        # Automatic horizon expiry clears degradation when degraded_until < now and poll is clean.
        expired_persisted = {
            **persisted,
            "degraded_at": (now - timedelta(days=8)).isoformat(),
            "degraded_until": (now - timedelta(seconds=1)).isoformat(),
        }
        services2 = Services()
        store2 = Store()
        c_expired = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services2), cfg, store2, expired_persisted
        )
        with patch.object(mod, "fetch", fetch_alert):
            health2 = await c_expired._async_update_data()
        self.assertFalse(health2["evidence_degraded"])
        self.assertFalse(health2["output_blocked"])
        self.assertIsNone(health2["degraded_reason"])
        self.assertFalse(store2.saved[-1]["degraded"])
        self.assertEqual(len(services2.calls), 1)

        # Legacy degraded=True without degraded_at backfills degraded_at=now
        # and does not auto-clear via a prior acknowledgment.
        legacy_degraded = {
            "initialized": True,
            "was_live": True,
            "records": {},
            "outbox": [],
            "degraded": True,
        }
        store3 = Store()
        c_legacy = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            {**cfg, "acknowledge_degraded_at": (now - timedelta(hours=1)).isoformat()},
            store3,
            legacy_degraded,
        )
        self.assertTrue(c_legacy.degraded)
        with patch.object(mod, "fetch", fetch_alert):
            health3 = await c_legacy._async_update_data()
        self.assertTrue(health3["evidence_degraded"])
        self.assertIsNotNone(store3.saved[-1]["degraded_at"])
        self.assertIsNotNone(store3.saved[-1]["degraded_until"])

        # Future-dated acknowledge_degraded_at is rejected at load and does NOT
        # auto-clear on subsequent polls even after clock advances past it.
        class AckClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        AckClock.current = now
        future_ack_cfg = {
            **cfg,
            "acknowledge_degraded_at": (now + timedelta(hours=1)).isoformat(),
        }
        c_future = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            future_ack_cfg,
            Store(),
            persisted,
        )
        self.assertTrue(c_future.degraded)
        AckClock.current = now + timedelta(hours=2)
        with (
            patch.object(mod, "datetime", AckClock),
            patch.object(mod, "fetch", fetch_alert),
        ):
            still_deg = await c_future._async_update_data()
        self.assertTrue(still_deg["evidence_degraded"])
        self.assertTrue(still_deg["output_blocked"])

        # One-shot acknowledgment: once consumed, the same timestamp cannot clear a new degradation.
        ack_once = (now - timedelta(minutes=30)).isoformat()
        store_once = Store()
        c_once = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            {**cfg, "acknowledge_degraded_at": ack_once},
            store_once,
            persisted,
        )
        self.assertFalse(c_once.degraded)
        self.assertEqual(c_once.acknowledged_degraded_at, ack_once)
        with patch.object(mod, "fetch", fetch_alert):
            await c_once._async_update_data()
        self.assertEqual(store_once.saved[-1]["acknowledged_degraded_at"], ack_once)

        # Exact replay of an expired Cancel does not false-trigger conflicting_cancellation.
        target = d.normalize(feature())
        target["id"] += "-exp-target"
        target_sent = (now - timedelta(days=9, minutes=1)).isoformat()
        target.update(
            sent=target_sent,
            effective=target_sent,
            onset=target_sent,
            expires=target_sent,
            ends=target_sent,
            cap_identity=["nws@example.test", "exp-target", target_sent],
        )
        old_sent = (now - timedelta(days=9)).isoformat()
        expired_cancel = d.normalize(feature())
        expired_cancel.update(
            id="https://api.weather.gov/alerts/exp-cancel",
            message_type="Cancel",
            sent=old_sent,
            expires=old_sent,
            ends=old_sent,
            cap_identity=["nws@example.test", "exp-cancel", old_sent],
            references=[target["id"]],
            reference_identities=[target["cap_identity"]],
            cap_references_valid=True,
        )
        rec_with_cancel, _ = d.reconcile(
            {}, [expired_cancel], cfg, now - timedelta(days=8)
        )
        rec_expired, _ = d.reconcile(rec_with_cancel, [], cfg, now)
        self.assertFalse(rec_expired[expired_cancel["id"]]["cancel_message"])
        self.assertTrue(rec_expired[expired_cancel["id"]]["cancellation_expired"])
        services4 = Services()
        c_replay = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services4),
            cfg,
            Store(),
            {
                "initialized": True,
                "was_live": True,
                "records": rec_expired,
                "outbox": [],
            },
        )
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents([expired_cancel, e], 0, [], False),
        ):
            health4 = await c_replay._async_update_data()
        self.assertFalse(health4["evidence_degraded"])
        self.assertFalse(health4["output_blocked"])
        self.assertEqual(len(services4.calls), 1)

    async def test_withheld_degraded_plans_deliver_after_recovery_and_cancel_edge_cases(
        self,
    ):
        import copy
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

        def make_alert(name):
            ev = d.normalize(feature())
            ev["id"] = "https://api.weather.gov/alerts/" + name
            for key, delta in [
                ("sent", -2),
                ("effective", -2),
                ("onset", 0),
                ("expires", 60),
                ("ends", 60),
            ]:
                ev[key] = (now + timedelta(minutes=delta)).isoformat()
            cohere(ev)
            return ev

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        # Alert delivered before degradation does not duplicate,
        # while alert first qualifying DURING degradation delivers once recovery occurs.
        pre_alert = make_alert("pre-degraded")
        during_alert = make_alert("during-degraded")
        services = Services()
        store = Store()
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, store, {}
        )
        with patch.object(mod, "fetch", return_value=[pre_alert]):
            await coord._async_update_data()
        self.assertEqual(len(services.calls), 1)

        # Enter degraded mode via an Actual Cancel with empty references.
        empty_cancel = make_alert("empty-cancel")
        empty_cancel["message_type"] = "Cancel"
        empty_cancel["references"] = []
        empty_cancel["reference_identities"] = []
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents(
                [pre_alert, during_alert, empty_cancel],
                0,
                [],
                False,
                uncertain_cancellation=False,
            ),
        ):
            deg_health = await coord._async_update_data()
        self.assertTrue(deg_health["evidence_degraded"])
        self.assertEqual(deg_health["degraded_reason"], "malformed_cancellation")
        self.assertEqual(len(services.calls), 1)
        # Withheld plan's fingerprint was popped from `during_alert`'s actions.
        self.assertEqual(store.saved[-1]["records"][during_alert["id"]]["actions"], {})
        self.assertTrue(store.saved[-1]["records"][pre_alert["id"]]["actions"])

        # Acknowledge and recover with both alerts still active: only `during_alert` delivers.
        ack_cfg = {**cfg, "acknowledge_degraded_at": deg_health["degraded_at"]}
        recovered = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services),
            ack_cfg,
            Store(),
            store.saved[-1],
        )
        with patch.object(mod, "fetch", return_value=[pre_alert, during_alert]):
            rec_health = await recovered._async_update_data()
        self.assertFalse(rec_health["evidence_degraded"])
        self.assertIsNone(rec_health["degraded_until"])
        self.assertEqual(len(services.calls), 2)
        self.assertEqual(services.calls[-1][2]["data"]["url"], during_alert["id"])

        # Legacy record without `cancel_message` does not false-trigger conflict.
        legacy_cancel = copy.deepcopy(empty_cancel)
        legacy_cancel["id"] = "https://api.weather.gov/alerts/legacy-cancel"
        legacy_cancel["references"] = [pre_alert["id"]]
        legacy_cancel["reference_identities"] = [pre_alert["cap_identity"]]
        cohere(legacy_cancel, pre_alert)
        legacy_store = {
            "initialized": True,
            "was_live": True,
            "records": {
                legacy_cancel["id"]: {
                    "state": "ineligible",
                    "actions": {},
                    "updated": (now - timedelta(minutes=5)).isoformat(),
                }
            },
            "outbox": [],
        }
        c_leg = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, Store(), legacy_store
        )
        with patch.object(mod, "fetch", return_value=[legacy_cancel]):
            h_leg = await c_leg._async_update_data()
        self.assertFalse(h_leg["evidence_degraded"])

        # Incomplete-reference Cancel replay matches on lineage; differing lineage conflicts.
        inc_cancel = make_alert("inc-cancel")
        inc_cancel["message_type"] = "Cancel"
        inc_cancel["references"] = ["https://api.weather.gov/alerts/ref-1"]
        inc_cancel["reference_identities"] = [None]
        inc_cancel["cap_references_valid"] = False
        inc_store = {
            "initialized": True,
            "was_live": True,
            "records": {
                inc_cancel["id"]: {
                    "state": "cancelled",
                    "cancel_message": True,
                    "cap_identity": inc_cancel["cap_identity"],
                    "cap_references": None,
                    "lineage": sorted([inc_cancel["id"], inc_cancel["references"][0]]),
                    "updated": now.isoformat(),
                }
            },
            "outbox": [],
        }
        c_inc_same = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, Store(), inc_store
        )
        with patch.object(mod, "fetch", return_value=[inc_cancel]):
            h_same = await c_inc_same._async_update_data()
        self.assertFalse(h_same["evidence_degraded"])
        diff_cancel = copy.deepcopy(inc_cancel)
        diff_cancel["references"] = ["https://api.weather.gov/alerts/ref-2"]
        c_inc_diff = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, Store(), inc_store
        )
        with patch.object(mod, "fetch", return_value=[diff_cancel]):
            h_diff = await c_inc_diff._async_update_data()
        # Recoverable lineage conflict surfaces cancellation_uncertain without global degradation;
        # unrecoverable empty-reference conflict latches conflicting_cancellation.
        self.assertFalse(h_diff["evidence_degraded"])
        self.assertTrue(h_diff["cancellation_uncertain"])
        self.assertTrue(h_diff["partial"])

        diff_cancel_empty = copy.deepcopy(inc_cancel)
        diff_cancel_empty["references"] = []
        diff_cancel_empty["reference_identities"] = []
        c_inc_unrec = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, Store(), inc_store
        )
        with patch.object(mod, "fetch", return_value=[diff_cancel_empty]):
            h_unrec = await c_inc_unrec._async_update_data()
        self.assertTrue(h_unrec["evidence_degraded"])
        self.assertEqual(h_unrec["degraded_reason"], "conflicting_cancellation")

    async def test_sibling_withheld_release_overflow_release_conflict_preserve_and_outbox_age(
        self,
    ):
        import copy
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

        def make_alert(name):
            ev = d.normalize(feature())
            ev["id"] = "https://api.weather.gov/alerts/" + name
            for key, delta in [
                ("sent", -2),
                ("effective", -2),
                ("onset", 0),
                ("expires", 120),
                ("ends", 120),
            ]:
                ev[key] = (now + timedelta(minutes=delta)).isoformat()
            cohere(ev)
            return ev

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        # Two equivalent siblings S1, S2 qualify during degradation;
        # after recovery (even if S1 leaves), S2 delivers.
        root = make_alert("srh1-root")
        s1 = make_alert("srh1-s1")
        s2 = make_alert("srh1-s2")
        cohere(s1, root)
        cohere(s2, root)
        services = Services()
        store = Store()
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, store, {}
        )
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents(
                [s1, s2], 0, [], False, uncertain_cancellation=True
            ),
        ):
            h_deg = await coord._async_update_data()
        self.assertTrue(h_deg["evidence_degraded"])
        self.assertEqual(store.saved[-1]["records"][s1["id"]]["actions"], {})
        self.assertEqual(store.saved[-1]["records"][s2["id"]]["actions"], {})
        recovered = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services),
            {**cfg, "acknowledge_degraded_at": h_deg["degraded_at"]},
            Store(),
            store.saved[-1],
        )
        with patch.object(mod, "fetch", return_value=[s2]):
            await recovered._async_update_data()
        self.assertEqual(len(services.calls), 1)
        self.assertEqual(services.calls[0][2]["data"]["url"], s2["id"])

        # Overflow strips newly planned action on bounded records.
        overflow_records = {
            f"old-cancel-{i}": {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [],
                "updated": now.isoformat(),
            }
            for i in range(1000)
        }
        ov_alert = make_alert("sit-m1-alert")
        store_ov = Store()
        c_ov = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            cfg,
            store_ov,
            {
                "initialized": True,
                "was_live": True,
                "records": overflow_records,
                "outbox": [],
            },
        )
        with patch.object(mod, "fetch", return_value=[ov_alert]):
            h_ov = await c_ov._async_update_data()
        self.assertEqual(h_ov["degraded_reason"], "cancellation_evidence_overflow")
        self.assertEqual(store_ov.saved[-1]["records"][ov_alert["id"]]["actions"], {})

        # Conflicting Cancel C' with recoverable target refs preserves C -> t1,
        # preserves C -> t1, quarantines t2, reports cancellation_uncertain without global
        # degradation, and allows unrelated valid alerts to deliver; unrecoverable conflict
        # (empty references) latches conflicting_cancellation while still protecting t1.
        t1 = make_alert("sit-h2-t1")
        t2 = make_alert("sit-h2-t2")
        unrelated_r1 = make_alert("sit-r1-unrelated")
        c_orig = make_alert("sit-h2-c")
        c_orig["message_type"] = "Cancel"
        cohere(c_orig, t1)
        services_h2 = Services()
        store_h2 = Store()
        c_h2 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services_h2), cfg, store_h2, {}
        )
        with patch.object(mod, "fetch", return_value=[t1, t2, c_orig]):
            await c_h2._async_update_data()
        self.assertEqual(len(services_h2.calls), 1)
        self.assertEqual(services_h2.calls[0][2]["data"]["url"], t2["id"])

        c_conf = copy.deepcopy(c_orig)
        c_conf["references"] = [t2["id"]]
        c_conf["reference_identities"] = [t2["cap_identity"]]
        with patch.object(mod, "fetch", return_value=[c_conf, t2, unrelated_r1]):
            h_conf1 = await c_h2._async_update_data()
        self.assertFalse(h_conf1["evidence_degraded"])
        self.assertTrue(h_conf1["cancellation_uncertain"])
        self.assertTrue(h_conf1["partial"])
        self.assertEqual(store_h2.saved[-1]["records"][t1["id"]]["state"], "cancelled")
        self.assertEqual(
            store_h2.saved[-1]["records"][t2["id"]]["state"], "quarantined"
        )
        self.assertEqual(len(services_h2.calls), 2)
        self.assertEqual(services_h2.calls[-1][2]["data"]["url"], unrelated_r1["id"])

        c_conf_unrec = copy.deepcopy(c_orig)
        c_conf_unrec["references"] = []
        c_conf_unrec["reference_identities"] = []
        with patch.object(mod, "fetch", return_value=[c_conf_unrec]):
            h_conf2 = await c_h2._async_update_data()
        self.assertEqual(h_conf2["degraded_reason"], "conflicting_cancellation")

        c_h2_rec = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services_h2),
            {**cfg, "acknowledge_degraded_at": h_conf2["degraded_at"]},
            Store(),
            store_h2.saved[-1],
        )
        with patch.object(mod, "fetch", return_value=[t1]):
            h_replay = await c_h2_rec._async_update_data()
        self.assertFalse(h_replay["evidence_degraded"])
        self.assertEqual(len(services_h2.calls), 2)

        # Scoped oversized Actual Cancel (quarantined_cancel_lineages) quarantines
        # target without global degradation while delivering unrelated valid alert.
        target_r1 = make_alert("r1-scoped-target")
        indep_r1 = make_alert("r1-scoped-indep")
        srv_r1 = Services()
        c_r1 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=srv_r1), cfg, Store(), {}
        )
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents(
                [target_r1, indep_r1],
                1,
                [["https://api.weather.gov/alerts/big-cancel", target_r1["id"]]],
                False,
                uncertain_cancellation=False,
                quarantined_cancel_lineages=[
                    ["https://api.weather.gov/alerts/big-cancel", target_r1["id"]]
                ],
            ),
        ):
            h_r1 = await c_r1._async_update_data()
        self.assertFalse(h_r1["evidence_degraded"])
        self.assertTrue(h_r1["cancellation_uncertain"])
        self.assertEqual(len(srv_r1.calls), 1)
        self.assertEqual(srv_r1.calls[0][2]["data"]["url"], indep_r1["id"])

        # Stopping cancels an in-flight slow fetch immediately without saving.
        import asyncio

        started, never = asyncio.Event(), asyncio.Event()

        async def slow_fetch(*args):
            started.set()
            await never.wait()
            return []

        store_stop = Store()
        c_stop = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, store_stop, {}
        )
        with patch.object(mod, "fetch", slow_fetch):
            task = asyncio.create_task(c_stop._async_update_data())
            await asyncio.wait_for(started.wait(), 2)
            await asyncio.wait_for(c_stop.async_stop(), 2)
            await asyncio.wait_for(task, 2)
        self.assertEqual(store_stop.saved, [])

        # Pre-degradation undelivered target survives >15m degradation
        # without duplicating already-accepted target.
        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now

        class PartialFailServices(Services):
            fail_two = True

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if self.fail_two and args[1] == "mobile_app_two":
                    raise OSError("phone 2 offline")

        cfg_two = {**cfg, "phones": ["mobile_app_one", "mobile_app_two"]}
        m2_alert = make_alert("sit-m2-alert")
        srv_m2 = PartialFailServices()
        store_m2 = Store()
        c_m2 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=srv_m2), cfg_two, store_m2, {}
        )
        with patch.object(mod, "datetime", Clock):
            with patch.object(mod, "fetch", return_value=[m2_alert]):
                await c_m2._async_update_data()
            self.assertEqual(len(srv_m2.calls), 2)
            self.assertEqual(len(store_m2.saved[-1]["outbox"]), 1)

            # T + 1m: enter degraded mode.
            Clock.current = now + timedelta(minutes=1)
            with patch.object(
                mod,
                "fetch",
                return_value=collector.CollectedEvents(
                    [m2_alert], 0, [], False, uncertain_cancellation=True
                ),
            ):
                h_m2_deg = await c_m2._async_update_data()
            self.assertTrue(h_m2_deg["evidence_degraded"])

            # T + 20m: still degraded, >15m since initial queue, and m2_alert is
            # superseded by an equivalent update m2_update; retry migrates and survives.
            Clock.current = now + timedelta(minutes=20)
            m2_update = make_alert("sit-m2-update")
            cohere(m2_update, m2_alert)
            with patch.object(mod, "fetch", return_value=[m2_update]):
                await c_m2._async_update_data()
            self.assertEqual(len(store_m2.saved[-1]["outbox"]), 1)
            self.assertEqual(
                store_m2.saved[-1]["outbox"][0]["incident_id"], m2_update["id"]
            )

            # T + 21m: recover via ack; phone 2 delivers once for m2_update,
            # and phone 1 is not duplicated.
            Clock.current = now + timedelta(minutes=21)
            srv_m2.fail_two = False
            c_m2_rec = mod.SituarenessCoordinator(
                types.SimpleNamespace(services=srv_m2),
                {
                    **cfg_two,
                    "acknowledge_degraded_at": (now + timedelta(minutes=2)).isoformat(),
                },
                Store(),
                store_m2.saved[-1],
            )
            with patch.object(mod, "fetch", return_value=[m2_update]):
                h_m2_rec = await c_m2_rec._async_update_data()
            self.assertFalse(h_m2_rec["evidence_degraded"])
            self.assertEqual(len(srv_m2.calls), 3)
            self.assertEqual(srv_m2.calls[-1][1], "mobile_app_two")
            self.assertEqual(srv_m2.calls[-1][2]["data"]["url"], m2_update["id"])

        # Conflicting duplicate Cancel in collector latches conflicting_cancellation.
        c_dup_cancel = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()), cfg, Store(), {}
        )
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents(
                [t1], 2, [], False, conflicting_cancellation=True
            ),
        ):
            h_dup = await c_dup_cancel._async_update_data()
        self.assertEqual(h_dup["degraded_reason"], "conflicting_cancellation")

        # Missing persisted store after journal_initialized=True latches journal_lost.
        # latches journal_lost, withholds output while collecting, and preserves state.
        class FakeConfigEntries:
            def __init__(self, entry):
                self.entry = entry

            def async_update_entry(self, entry, *, data):
                entry.data = data

        entry = types.SimpleNamespace(data={})
        hass_entry = types.SimpleNamespace(
            services=Services(), config_entries=FakeConfigEntries(entry)
        )
        store_jl = Store()
        c_init = mod.SituarenessCoordinator(
            hass_entry, cfg, store_jl, None, entry=entry
        )
        with patch.object(mod, "fetch", return_value=[]):
            await c_init._async_update_data()
        self.assertTrue(entry.data.get("journal_initialized"))

        # Restart with lost store (None or {}) latches journal_lost and blocks output.
        for lost_payload in (None, {}):
            with self.subTest(lost_payload=lost_payload):
                srv_jl = Services()
                store_lost = Store()
                hass_lost = types.SimpleNamespace(
                    services=srv_jl, config_entries=FakeConfigEntries(entry)
                )
                c_lost = mod.SituarenessCoordinator(
                    hass_lost, cfg, store_lost, lost_payload, entry=entry
                )
                self.assertTrue(c_lost.degraded)
                self.assertEqual(c_lost.degraded_reason, "journal_lost")
                alert_jl = make_alert("spec01-alert")
                with patch.object(mod, "fetch", return_value=[alert_jl]):
                    h_jl = await c_lost._async_update_data()
                self.assertTrue(h_jl["evidence_degraded"])
                self.assertTrue(h_jl["output_blocked"])
                self.assertEqual(h_jl["degraded_reason"], "journal_lost")
                self.assertEqual(srv_jl.calls, [])
                self.assertEqual(
                    store_lost.saved[-1]["degraded_reason"], "journal_lost"
                )

        # Overflow propagates dropped_horizon to degraded_until and a
        # subsequent shorter trigger never shrinks an earlier longer degraded_until.
        long_exp = (now + timedelta(days=4)).isoformat()
        ov_long_records = {
            f"ov-long-{i}": {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [f"ov-long-{i}"],
                "expires": long_exp if i == 0 else now.isoformat(),
                "updated": (now - timedelta(minutes=1)).isoformat()
                if i == 0
                else now.isoformat(),
            }
            for i in range(1001)
        }
        store_horizon = Store()
        c_horizon = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            cfg,
            store_horizon,
            {
                "initialized": True,
                "was_live": True,
                "records": ov_long_records,
                "outbox": [],
            },
        )
        with patch.object(mod, "fetch", return_value=[make_alert("ov-h-ev")]):
            h_ov_long = await c_horizon._async_update_data()
        expected_long_until = d.timestamp(long_exp) + d.MAX_ACCEPTANCE_AGE
        self.assertGreaterEqual(
            d.timestamp(h_ov_long["degraded_until"]), expected_long_until
        )
        with patch.object(
            mod,
            "fetch",
            return_value=collector.CollectedEvents(
                [make_alert("ov-h-ev2")], 0, [], False, uncertain_cancellation=True
            ),
        ):
            h_ov_next = await c_horizon._async_update_data()
        self.assertEqual(h_ov_next["degraded_until"], h_ov_long["degraded_until"])

        # Reloading with acknowledge_degraded_at after >15m degraded preserves
        # last_degraded_poll until post-ack outbox migration credits the final interval.
        class AckOutboxClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        AckOutboxClock.current = now
        srv_s3 = PartialFailServices()
        srv_s3.fail_two = True
        store_s3 = Store()
        s3_alert = make_alert("spec03-alert")
        c_s3 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=srv_s3), cfg_two, store_s3, {}
        )
        with patch.object(mod, "datetime", AckOutboxClock):
            with patch.object(mod, "fetch", return_value=[s3_alert]):
                await c_s3._async_update_data()
            AckOutboxClock.current = now + timedelta(minutes=1)
            with patch.object(
                mod,
                "fetch",
                return_value=collector.CollectedEvents(
                    [s3_alert], 0, [], False, uncertain_cancellation=True
                ),
            ):
                await c_s3._async_update_data()
        # Reload at T + 20m with ack at T + 2m (evaluated at load time -> acknowledged),
        # then poll at T + 20m: last_degraded_poll (T + 1m) credits 19m and delivers phone_2.
        AckOutboxClock.current = now + timedelta(minutes=20)
        srv_s3.fail_two = False
        store_s3_rec = Store()
        with patch.object(mod, "datetime", AckOutboxClock):
            c_s3_rec = mod.SituarenessCoordinator(
                types.SimpleNamespace(services=srv_s3),
                {
                    **cfg_two,
                    "acknowledge_degraded_at": (now + timedelta(minutes=2)).isoformat(),
                },
                store_s3_rec,
                store_s3.saved[-1],
            )
            self.assertFalse(c_s3_rec.degraded)
            self.assertIsNotNone(c_s3_rec.last_degraded_poll)
            with patch.object(mod, "fetch", return_value=[s3_alert]):
                h_s3 = await c_s3_rec._async_update_data()
        self.assertFalse(h_s3["evidence_degraded"])
        self.assertIsNone(store_s3_rec.saved[-1]["last_degraded_poll"])
        self.assertEqual(len(srv_s3.calls), 3)
        self.assertEqual(srv_s3.calls[-1][1], "mobile_app_two")

    async def test_invalid_cap_cancel_quarantines_locally_and_independent_sibling_retries(
        self,
    ):
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

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        # Invalid-CAP Cancel (future sent) does not latch global degradation;
        # unrelated valid alert delivers normally.
        target = make("m1-target", -100, kind="Alert")
        bad_cancel = make("m1-bad-cancel", 600, [target], kind="Cancel")
        independent = make("m1-independent", -50, kind="Alert")
        services = Services()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, Store(), {}
        )
        with patch.object(mod, "fetch", return_value=[target, bad_cancel, independent]):
            health = await coordinator._async_update_data()
        self.assertFalse(health["evidence_degraded"])
        self.assertFalse(health["output_blocked"])
        self.assertEqual(len(services.calls), 1)
        self.assertEqual(services.calls[0][2]["data"]["url"], independent["id"])

        # Independent sibling branch retry moves to its valid update when
        # a different branch in the same component is cancelled.
        root = make("m3-root", -100, kind="Alert")
        branch_a = make("m3-a", -90, [root])
        branch_b = make("m3-b", -80, [root])
        branch_b2 = make("m3-b2", -70, [root, branch_b])
        cancel_a = make("m3-cancel-a", -60, [branch_a], kind="Cancel")
        records = {}
        for ev in (root, branch_a, branch_b):
            records, _ = d.reconcile(records, [ev], cfg, now)
        decision = d.qualify(branch_b, cfg, now)
        plan = {
            "id": branch_b["id"],
            "fingerprint": d.fingerprint(branch_b, decision),
            "event": branch_b["event"],
            "instruction": branch_b["instruction"],
            "affected": decision["affected"],
            "phones": cfg["phones"],
        }
        item = delivery.targets(plan, cfg, now)[0]
        services2 = Services()
        coord2 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services2),
            cfg,
            Store(),
            {
                "initialized": True,
                "was_live": True,
                "records": copy.deepcopy(records),
                "outbox": [item],
            },
        )
        with patch.object(mod, "fetch", return_value=[cancel_a, branch_b2]):
            health2 = await coord2._async_update_data()
        self.assertEqual(health2["pending_count"], 0)
        self.assertEqual(len(services2.calls), 1)
        self.assertEqual(services2.calls[0][2]["data"]["url"], branch_b2["id"])

        # Historic cancellation uncertainty clears once absent and outbox empty.
        records3 = {}
        child = make("h1-child", -80, [branch_a])
        for ev in (root, branch_a, child):
            records3, _ = d.reconcile(records3, [ev], cfg, now)
        coord3 = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            cfg,
            Store(),
            {
                "initialized": True,
                "was_live": True,
                "records": copy.deepcopy(records3),
                "outbox": [],
            },
        )
        with patch.object(mod, "fetch", return_value=[cancel_a]):
            h_uncertain = await coord3._async_update_data()
        self.assertTrue(h_uncertain["cancellation_uncertain"])
        self.assertTrue(h_uncertain["partial"])
        with patch.object(mod, "fetch", return_value=[]):
            h_cleared = await coord3._async_update_data()
        self.assertFalse(h_cleared["cancellation_uncertain"])
        self.assertFalse(h_cleared["partial"])

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

    async def test_stop_during_first_fetch_returns_non_degraded_health(self):
        import asyncio

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

        started = asyncio.Event()

        async def blocking_fetch(*args):
            started.set()
            await asyncio.sleep(60)
            return []

        hass = types.SimpleNamespace(services=Services())
        created = "2026-11-17T12:00:00+00:00"
        persisted_outbox = [
            {
                "key": "k-1",
                "incident_id": "https://api.weather.gov/alerts/pending-1",
                "fingerprint": "fp-1",
                "kind": "phone",
                "target": "mobile_app_one",
                "location": "new_york_ny",
                "affected_names": ["New York"],
                "event": "Tornado Warning",
                "instruction": "Take shelter",
                "source_url": "https://api.weather.gov/alerts/pending-1",
                "attempts": 0,
                "created": created,
            }
        ]
        coordinator = mod.SituarenessCoordinator(
            hass,
            config(),
            Store(),
            {"records": {}, "outbox": persisted_outbox, "initialized": True},
        )
        with patch.object(mod, "fetch", blocking_fetch):
            task = asyncio.create_task(coordinator._async_update_data())
            await asyncio.wait_for(started.wait(), 2)
            await asyncio.wait_for(coordinator.async_stop(), 2)
            result = await asyncio.wait_for(task, 2)
        self.assertFalse(result["evidence_degraded"])
        self.assertFalse(result["output_blocked"])
        self.assertIsNone(result["degraded_reason"])
        self.assertIsNone(result["active_count"])
        self.assertEqual(result["pending_count"], 1)
        self.assertEqual(result["suspended_count"], 1)

        # Stopping a degraded coordinator with no prior data still reports degraded health.
        started2 = asyncio.Event()

        async def blocking_fetch2(*args):
            started2.set()
            await asyncio.sleep(60)
            return []

        entry = types.SimpleNamespace(entry_id="e1", data={"journal_initialized": True})
        hass2 = types.SimpleNamespace(
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        deg_coord = mod.SituarenessCoordinator(
            hass2, config(), Store(), None, entry=entry
        )
        with patch.object(mod, "fetch", blocking_fetch2):
            task2 = asyncio.create_task(deg_coord._async_update_data())
            await asyncio.wait_for(started2.wait(), 2)
            await asyncio.wait_for(deg_coord.async_stop(), 2)
            result2 = await asyncio.wait_for(task2, 2)
        self.assertTrue(result2["evidence_degraded"])
        self.assertTrue(result2["output_blocked"])
        self.assertEqual(result2["degraded_reason"], "journal_lost")

    async def test_journal_lost_persists_before_first_fetch_and_stabilizes_horizon(
        self,
    ):
        from datetime import datetime, timedelta, timezone

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        notifications = {}
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                notifications.__setitem__(
                    notification_id, {"message": msg, "title": title}
                )
            ),
            async_dismiss=lambda hass, notification_id: notifications.pop(
                notification_id, None
            ),
        )
        with patch.dict(
            sys.modules,
            {
                **HA_MODULES,
                "homeassistant.components": module(
                    "homeassistant.components", persistent_notification=fake_pn
                ),
                "homeassistant.components.persistent_notification": fake_pn,
            },
        ):
            spec.loader.exec_module(mod)

        entry = types.SimpleNamespace(
            entry_id="lost-entry", data={"journal_initialized": True}
        )
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        store = Store()
        coordinator = mod.SituarenessCoordinator(
            hass, config(), store, None, entry=entry
        )
        self.assertTrue(coordinator.degraded)
        self.assertEqual(coordinator.degraded_reason, "journal_lost")
        self.assertIn("situareness_degraded", notifications)
        lost_at = entry.data.get("journal_lost_at")
        self.assertIsNotNone(lost_at)
        expected_until = coordinator.degraded_until

        async def failing_fetch(*args):
            raise RuntimeError("NWS outage")

        with patch.object(mod, "fetch", failing_fetch):
            with self.assertRaises(UpdateFailed):
                await coordinator._async_update_data()
        # Even though the first fetch failed, journal_lost was already persisted.
        self.assertEqual(len(store.saved), 1)
        self.assertTrue(store.saved[0]["degraded"])
        self.assertEqual(store.saved[0]["degraded_reason"], "journal_lost")
        self.assertEqual(store.saved[0]["degraded_at"], lost_at)

        # Reload with missing persisted store preserves original journal_lost_at / degraded_until.
        reloaded = mod.SituarenessCoordinator(
            hass, config(), Store(), None, entry=entry
        )
        self.assertEqual(reloaded.degraded_at, lost_at)
        self.assertEqual(reloaded.degraded_until, expected_until)

        await reloaded.async_stop()
        self.assertNotIn("situareness_degraded", notifications)

        # Valid acknowledgement on reload clears degraded state and journal_lost_at.
        ack_cfg = config()
        ack_cfg["acknowledge_degraded_at"] = (
            datetime.now(timezone.utc) + timedelta(seconds=1)
        ).isoformat()
        with patch.object(mod, "datetime") as mock_dt:
            mock_dt.now.return_value = datetime.now(timezone.utc) + timedelta(seconds=2)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            acked = mod.SituarenessCoordinator(
                hass, ack_cfg, Store(), None, entry=entry
            )
        self.assertFalse(acked.degraded)
        self.assertNotIn("journal_lost_at", entry.data)
        self.assertNotIn("situareness_degraded", notifications)

    async def test_invalid_cap_cancel_replay_quarantines_targets_and_delivers_sibling(
        self,
    ):
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

        def make_alert(name, delta_min=-2):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/{name}"
            for key, sec in [
                ("sent", delta_min * 60),
                ("effective", delta_min * 60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=sec)).isoformat()
            return cohere(ev)

        target_id = "https://api.weather.gov/alerts/bad-cancel-target"
        bad_cancel = make_alert("bad-cancel-replay", delta_min=-1)
        bad_cancel["message_type"] = "Cancel"
        bad_cancel["references"] = [target_id]
        bad_cancel["reference_identities"] = []
        bad_cancel["cap_references_valid"] = False

        sibling1 = make_alert("unrelated-sibling-1", delta_min=-2)
        sibling2 = make_alert("unrelated-sibling-2", delta_min=-1)

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        services = Services()
        store = Store()
        coordinator = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, store, {}
        )

        # Poll 1: invalid-CAP Actual Cancel + sibling1.
        with patch.object(mod, "fetch", return_value=[bad_cancel, sibling1]):
            h1 = await coordinator._async_update_data()
        self.assertFalse(h1["evidence_degraded"])
        self.assertFalse(h1["output_blocked"])
        self.assertEqual(len(services.calls), 1)
        self.assertEqual(services.calls[0][2]["data"]["url"], sibling1["id"])

        # Poll 2: exact same invalid-CAP Actual Cancel replays alongside sibling2.
        with patch.object(mod, "fetch", return_value=[bad_cancel, sibling2]):
            h2 = await coordinator._async_update_data()
        self.assertFalse(h2["evidence_degraded"])
        self.assertFalse(h2["output_blocked"])
        self.assertIsNone(h2["degraded_reason"])
        self.assertEqual(len(services.calls), 2)
        self.assertEqual(services.calls[1][2]["data"]["url"], sibling2["id"])
        # Target remains blocked if it later appears.
        target_ev = make_alert("bad-cancel-target", delta_min=-3)
        with patch.object(mod, "fetch", return_value=[target_ev, sibling2]):
            h3 = await coordinator._async_update_data()
        self.assertFalse(h3["evidence_degraded"])
        self.assertEqual(coordinator.records[target_id]["state"], "quarantined")
        self.assertEqual(len(services.calls), 2)

    async def test_malformed_upgrade_marks_journal_initialized_and_remove_dismisses_first(
        self,
    ):
        import tempfile

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        events = []
        notifications = {}
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                notifications.__setitem__(notification_id, msg)
            ),
            async_dismiss=lambda hass, notification_id: (
                events.append("dismiss"),
                notifications.pop(notification_id, None),
            )[1],
        )

        class RecordingStore(Store):
            def __init__(self, *args, **kwargs):
                super().__init__()

            async def async_load(self):
                raise RuntimeError("unreadable disk store")

            async def async_remove(self):
                events.append("remove")

        with patch.dict(
            sys.modules,
            {
                **HA_MODULES,
                "homeassistant.components": module(
                    "homeassistant.components", persistent_notification=fake_pn
                ),
                "homeassistant.components.persistent_notification": fake_pn,
                "homeassistant.helpers.storage": module(
                    "homeassistant.helpers.storage", Store=RecordingStore
                ),
            },
        ):
            spec.loader.exec_module(mod)

        # Upgraded entry with empty data and malformed persisted store marks journal_initialized.
        entry = types.SimpleNamespace(entry_id="up1", data={})
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        coord = mod.SituarenessCoordinator(
            hass, config(), Store(), {"records": "corrupt"}, entry=entry
        )
        self.assertTrue(coord.degraded)
        self.assertEqual(coord.degraded_reason, "malformed_store")
        self.assertTrue(entry.data.get("journal_initialized"))

        # Subsequent reload with missing store transitions cleanly to journal_lost.
        lost = mod.SituarenessCoordinator(hass, config(), Store(), None, entry=entry)
        self.assertTrue(lost.degraded)
        self.assertEqual(lost.degraded_reason, "journal_lost")
        self.assertIn("situareness_degraded", notifications)

        # async_remove_entry dismisses notification BEFORE calling async_remove().
        await mod.async_remove_entry(hass, entry)
        self.assertEqual(events, ["dismiss", "remove"])
        self.assertNotIn("situareness_degraded", notifications)

        # async_setup_entry treats store.async_load() exceptions as malformed_store.
        with tempfile.TemporaryDirectory() as tmp:
            cfg_file = Path(tmp) / "situareness.json"
            cfg_file.write_text("{}", encoding="utf-8")

            async def run_exec(fn, *args):
                return fn(*args)

            setup_entry = types.SimpleNamespace(entry_id="bad-load", data={})
            setup_hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                async_add_executor_job=run_exec,
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(
                        ent, "data", data
                    ),
                    async_forward_entry_setups=lambda *a: asyncio.sleep(0),
                ),
            )
            setup_coord = None

            class CapturingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    self.data = await self._update_once()

            with patch.object(mod, "SituarenessCoordinator", CapturingCoordinator):
                import asyncio

                await mod.async_setup_entry(setup_hass, setup_entry)
            setup_coord = setup_hass.data[mod.DOMAIN][setup_entry.entry_id]
            self.assertEqual(setup_coord.degraded_reason, "malformed_store")
            self.assertTrue(setup_entry.data.get("journal_initialized"))

    async def test_outbox_overflow_latches_degraded_and_recovers_after_prune(self):
        from datetime import datetime, timedelta, timezone

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        notifications = {}
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                notifications.__setitem__(notification_id, msg)
            ),
            async_dismiss=lambda hass, notification_id: notifications.pop(
                notification_id, None
            ),
        )
        with patch.dict(
            sys.modules,
            {
                **HA_MODULES,
                "homeassistant.components": module(
                    "homeassistant.components", persistent_notification=fake_pn
                ),
                "homeassistant.components.persistent_notification": fake_pn,
            },
        ):
            spec.loader.exec_module(mod)

        now = datetime.now(timezone.utc)
        ev = d.normalize(feature())
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        cohere(ev)

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(5001)],
            tts_entity=None,
        )
        services = Services()
        store = Store()
        hass = types.SimpleNamespace(data={}, services=services)
        coordinator = mod.SituarenessCoordinator(hass, cfg, store, {})
        with patch.object(mod, "fetch", return_value=[ev]):
            h1 = await coordinator._async_update_data()
        self.assertTrue(h1["evidence_degraded"])
        self.assertTrue(h1["output_blocked"])
        self.assertEqual(h1["degraded_reason"], "outbox_overflow")
        self.assertEqual(len(store.saved[-1]["outbox"]), 5000)
        self.assertEqual(services.calls, [])
        self.assertIn("situareness_degraded", notifications)

        # Once outbox items expire past 15m and user reloads with valid acknowledge_degraded_at,
        # normal delivery recovers cleanly.
        later_cfg = config()
        later_cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_ok"],
            tts_entity=None,
            acknowledge_degraded_at=(now + timedelta(minutes=16)).isoformat(),
        )
        later = now + timedelta(minutes=17)
        ev2 = d.normalize(feature())
        ev2["id"] += "-after-overflow"
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev2[key] = (later + timedelta(seconds=delta)).isoformat()
        cohere(ev2)

        class Clock:
            current = later

            @classmethod
            def now(cls, tz):
                return cls.current

        with patch.object(mod, "datetime", Clock):
            recovered = mod.SituarenessCoordinator(
                hass, later_cfg, Store(), store.saved[-1]
            )
            self.assertFalse(recovered.degraded)
            self.assertNotIn("situareness_degraded", notifications)
            with patch.object(mod, "fetch", return_value=[ev2]):
                h2 = await recovered._async_update_data()
        self.assertFalse(h2["evidence_degraded"])
        self.assertFalse(h2["output_blocked"])
        self.assertEqual(len(services.calls), 1)
