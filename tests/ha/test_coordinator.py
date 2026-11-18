"""Mocked HA boundary tests, not an installed Home Assistant run."""

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_domain import PACKAGE, config, feature, d, cohere, collector


def module(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


class BaseCoordinator:
    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.config_entry = kwargs.get("config_entry")
        if hass is not None and not hasattr(hass, "async_add_executor_job"):

            async def _exec(fn, *args):
                return await asyncio.to_thread(fn, *args)

            hass.async_add_executor_job = _exec


class UpdateFailed(Exception):
    pass


class ConfigEntryNotReady(Exception):
    pass


class Store:
    def __init__(self, *args, **kwargs):
        self.saved = []
        self.fail = False
        self.private = kwargs.get("private")

    async def async_save(self, value):
        if self.fail:
            raise OSError("disk full")
        self.saved.append(value)


class Services:
    def __init__(self):
        self.calls = []

    async def async_call(self, *args, **kwargs):
        self.calls.append(args)


_DEFAULT_PN = module(
    "homeassistant.components.persistent_notification",
    async_create=lambda *args, **kwargs: None,
    async_dismiss=lambda *args, **kwargs: None,
)

HA_MODULES = {
    "homeassistant": module("homeassistant"),
    "homeassistant.components": module(
        "homeassistant.components", persistent_notification=_DEFAULT_PN
    ),
    "homeassistant.components.persistent_notification": _DEFAULT_PN,
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
            if refs and event.get("message_type") == "Alert":
                event["message_type"] = "Update"
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
        store_future = Store()
        c_future = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            future_ack_cfg,
            store_future,
            persisted,
        )
        self.assertTrue(c_future.degraded)
        self.assertEqual(
            c_future.acknowledged_degraded_at,
            future_ack_cfg["acknowledge_degraded_at"],
        )
        AckClock.current = now + timedelta(hours=2)
        with (
            patch.object(mod, "datetime", AckClock),
            patch.object(mod, "fetch", fetch_alert),
        ):
            still_deg = await c_future._async_update_data()
            self.assertTrue(still_deg["evidence_degraded"])
            self.assertTrue(still_deg["output_blocked"])
            reloaded_after_future = mod.SituarenessCoordinator(
                types.SimpleNamespace(services=Services()),
                future_ack_cfg,
                Store(),
                store_future.saved[-1],
            )
            self.assertTrue(reloaded_after_future.degraded)

        # Pre-degradation ack consumed while healthy cannot clear a later degradation.
        pre_ack_cfg = {**cfg, "acknowledge_degraded_at": now.isoformat()}
        healthy_store = Store()
        c_healthy = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=Services()),
            pre_ack_cfg,
            healthy_store,
            {},
        )
        self.assertEqual(c_healthy.acknowledged_degraded_at, now.isoformat())
        with patch.object(mod, "fetch", return_value=[]):
            await c_healthy._async_update_data()
        later_persisted = {
            **healthy_store.saved[-1],
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now + timedelta(minutes=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        with patch.object(mod, "datetime") as mock_dt:
            mock_dt.now.return_value = now + timedelta(minutes=2)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            not_cleared = mod.SituarenessCoordinator(
                types.SimpleNamespace(services=Services()),
                pre_ack_cfg,
                Store(),
                later_persisted,
            )
        self.assertTrue(not_cleared.degraded)

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
        self.assertEqual(h_ov["planned_count"], 0)
        self.assertEqual(h_ov["withheld_count"], 1)
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
        expected_long_until = (
            (now - timedelta(minutes=1)) + timedelta(minutes=5) + d.MAX_ACCEPTANCE_AGE
        )
        self.assertEqual(d.timestamp(h_ov_long["degraded_until"]), expected_long_until)
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
        self.assertEqual(result["withheld_count"], 0)

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
        self.assertFalse(result2["acknowledge_rejected"])

        # External cancellation of _async_update_data raises CancelledError even if _stopping is True.
        started3 = asyncio.Event()

        async def blocking_fetch3(*args):
            started3.set()
            await asyncio.sleep(60)
            return []

        ext_coord = mod.SituarenessCoordinator(hass, config(), Store(), {})
        with patch.object(mod, "fetch", blocking_fetch3):
            task3 = asyncio.create_task(ext_coord._async_update_data())
            await asyncio.wait_for(started3.wait(), 2)
            ext_coord._stopping = True
            task3.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task3, 2)

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
        t0 = datetime.now(timezone.utc)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = t0
        store = Store()
        with patch.object(mod, "datetime", Clock):
            coordinator = mod.SituarenessCoordinator(
                hass, config(), store, None, entry=entry
            )
            self.assertTrue(coordinator.degraded)
            self.assertEqual(coordinator.degraded_reason, "journal_lost")
            self.assertIn("situareness_degraded", notifications)
            lost_at = entry.data.get("journal_lost_at")
            self.assertEqual(lost_at, t0.isoformat())
            expected_until = coordinator.degraded_until

            async def failing_fetch(*args):
                raise RuntimeError("NWS outage")

            with patch.object(mod, "fetch", failing_fetch):
                with self.assertRaises(UpdateFailed):
                    await coordinator._async_update_data()
            # Pre-fetch save preserves journal_lost_at on entry.data so failed poll 1 stays anchored.
            self.assertEqual(len(store.saved), 1)
            self.assertTrue(store.saved[0]["degraded"])
            self.assertEqual(store.saved[0]["degraded_reason"], "journal_lost")
            self.assertEqual(store.saved[0]["degraded_at"], lost_at)
            self.assertEqual(entry.data.get("journal_lost_at"), lost_at)

            # Same-instant reload preserves exact journal_lost_at and degraded_until.
            reloaded = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=entry
            )
            self.assertEqual(reloaded.degraded_at, lost_at)
            self.assertEqual(reloaded.degraded_until, expected_until)

            await reloaded.async_stop()
            self.assertNotIn("situareness_degraded", notifications)

            # Without a poll-1 post-fetch save, Day-6 repeat loss retains lost_at but gives
            # a full 7-day horizon from Day 6, while Day-8 rotates stale journal_lost_at.
            day6 = t0 + timedelta(days=6)
            Clock.current = day6
            reloaded_day6 = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=entry
            )
            self.assertEqual(reloaded_day6.degraded_at, lost_at)
            self.assertEqual(
                reloaded_day6.degraded_until, (day6 + timedelta(days=7)).isoformat()
            )
            self.assertEqual(entry.data.get("journal_lost_at"), lost_at)

            day8 = t0 + timedelta(days=8)
            Clock.current = day8
            reloaded_day8 = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=entry
            )
            self.assertEqual(reloaded_day8.degraded_at, day8.isoformat())
            self.assertEqual(entry.data.get("journal_lost_at"), day8.isoformat())
            self.assertEqual(
                reloaded_day8.degraded_until, (day8 + timedelta(days=7)).isoformat()
            )

            # Post-fetch degraded save clears journal_lost_at so a subsequent Day-6 loss starts fresh.
            Clock.current = t0
            repeat_entry = types.SimpleNamespace(
                entry_id="lost-repeat", data={"journal_initialized": True}
            )
            repeat_store = Store()
            repeat_coord = mod.SituarenessCoordinator(
                hass, config(), repeat_store, None, entry=repeat_entry
            )
            with patch.object(mod, "fetch", return_value=[]):
                await repeat_coord._async_update_data()
            self.assertNotIn("journal_lost_at", repeat_entry.data)
            Clock.current = day6
            repeat_day6 = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=repeat_entry
            )
            self.assertEqual(repeat_day6.degraded_at, day6.isoformat())
            self.assertEqual(
                repeat_day6.degraded_until, (day6 + timedelta(days=7)).isoformat()
            )

            # journal_lost -> malformed_store clears stale journal_lost_at; subsequent store
            # deletion latches a fresh 7-day journal_lost horizon.
            transition_entry = types.SimpleNamespace(
                entry_id="lost-mal-lost", data={"journal_initialized": True}
            )
            Clock.current = t0
            mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=transition_entry
            )
            self.assertIn("journal_lost_at", transition_entry.data)
            Clock.current = day6
            mal_transition = mod.SituarenessCoordinator(
                hass, config(), Store(), ["corrupt"], entry=transition_entry
            )
            self.assertEqual(mal_transition.degraded_reason, "malformed_store")
            self.assertNotIn("journal_lost_at", transition_entry.data)
            day7 = t0 + timedelta(days=7)
            Clock.current = day7
            fresh_after_mal = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=transition_entry
            )
            self.assertEqual(fresh_after_mal.degraded_reason, "journal_lost")
            self.assertEqual(fresh_after_mal.degraded_at, day7.isoformat())
            self.assertEqual(
                fresh_after_mal.degraded_until, (day7 + timedelta(days=7)).isoformat()
            )

        # Valid acknowledgement on reload clears degraded state, preserves journal_lost_at
        # until a clean save succeeds, and clears journal_lost_at once saved.
        ack_cfg = config()
        ack_cfg["acknowledge_degraded_at"] = (day8 + timedelta(seconds=1)).isoformat()
        store_ack = Store()
        with patch.object(mod, "datetime", Clock):
            Clock.current = day8 + timedelta(seconds=2)
            acked = mod.SituarenessCoordinator(
                hass, ack_cfg, store_ack, None, entry=entry
            )
            self.assertFalse(acked.degraded)
            self.assertIn("journal_lost_at", entry.data)
            self.assertNotIn("situareness_degraded", notifications)

            # Failing first poll keeps journal_lost_at preserved for subsequent retries.
            with patch.object(mod, "fetch", failing_fetch):
                with self.assertRaises(UpdateFailed):
                    await acked._async_update_data()
            self.assertEqual(store_ack.saved, [])
            self.assertIn("journal_lost_at", entry.data)

            # Retry with persisted=None still acknowledges, and clean poll removes journal_lost_at.
            acked_retry = mod.SituarenessCoordinator(
                hass, ack_cfg, store_ack, None, entry=entry
            )
            self.assertFalse(acked_retry.degraded)
            with patch.object(mod, "fetch", return_value=[]):
                await acked_retry._async_update_data()
        self.assertNotIn("journal_lost_at", entry.data)
        self.assertEqual(
            store_ack.saved[-1]["acknowledged_degraded_at"],
            ack_cfg["acknowledge_degraded_at"],
        )
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

        class UnsupportedStorageVersionError(Exception):
            pass

        load_error = ValueError("corrupt json")
        load_result = None

        seen_private = []
        seen_store_kwargs = []

        class RecordingStore(Store):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                seen_private.append(kwargs.get("private"))
                seen_store_kwargs.append(kwargs)

            async def async_load(self):
                if load_error is not None:
                    raise load_error
                return load_result

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
        with tempfile.TemporaryDirectory() as tmp:
            import asyncio

            async def run_exec(fn, *args):
                return fn(*args)

            entry = types.SimpleNamespace(entry_id="up1", data={})
            hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                async_add_executor_job=run_exec,
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
            lost = mod.SituarenessCoordinator(
                hass, config(), Store(), None, entry=entry
            )
            self.assertTrue(lost.degraded)
            self.assertEqual(lost.degraded_reason, "journal_lost")
            self.assertIn("situareness_degraded", notifications)

            # async_remove_entry dismisses notification BEFORE calling async_remove() and uses private=True.
            await mod.async_remove_entry(hass, entry)
            self.assertEqual(events, ["dismiss", "remove"])
            self.assertEqual(seen_private, [True])
            seen_store_kwargs.clear()
            self.assertNotIn("situareness_degraded", notifications)

            # Invalid or disallowed degraded_reason values fail store validation, and
            # degraded=False normalizes any stale degraded_reason to None.
            for bad_reason in ("malformed_store", "unknown_reason", 123):
                bad_coord = mod.SituarenessCoordinator(
                    hass,
                    config(),
                    Store(),
                    {"degraded": True, "degraded_reason": bad_reason, "records": {}},
                )
                self.assertEqual(bad_coord.degraded_reason, "malformed_store")
                self.assertIsNone(bad_coord.degraded_until)

            clean_stale = mod.SituarenessCoordinator(
                hass,
                config(),
                Store(),
                {
                    "degraded": False,
                    "degraded_reason": "outbox_overflow",
                    "records": {},
                },
            )
            self.assertFalse(clean_stale.degraded)
            self.assertIsNone(clean_stale.degraded_reason)

            # async_setup_entry treats decode/version errors as malformed_store and I/O errors
            # as ConfigEntryNotReady without marking malformed_store_at or journal_initialized.
            cfg_file = Path(tmp) / "situareness.json"
            cfg_file.write_text("{}", encoding="utf-8")

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

            class CapturingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    self.data = await self._update_once()

            for err in (
                ValueError("corrupt"),
                UnsupportedStorageVersionError("future version"),
                NotImplementedError("unsupported migration"),
            ):
                load_error = err
                err_entry = types.SimpleNamespace(entry_id="bad-load", data={})
                with patch.object(mod, "SituarenessCoordinator", CapturingCoordinator):
                    await mod.async_setup_entry(setup_hass, err_entry)
                setup_coord = setup_hass.data[mod.DOMAIN][err_entry.entry_id]
                self.assertEqual(setup_coord.degraded_reason, "malformed_store")
                self.assertIs(setup_coord.config_entry, err_entry)
                self.assertTrue(err_entry.data.get("journal_initialized"))
                self.assertTrue(all(seen_private))
                self.assertTrue(
                    seen_store_kwargs
                    and all(
                        kw.get("atomic_writes") is True
                        and kw.get("serialize_in_event_loop") is False
                        for kw in seen_store_kwargs
                    )
                )

            perm_err = RuntimeError("storage error")
            perm_err.__cause__ = PermissionError("denied")
            for non_corrupt_err in (
                OSError("read failure"),
                perm_err,
                TypeError("unexpected type"),
                KeyError("unexpected key"),
            ):
                load_error = non_corrupt_err
                io_entry = types.SimpleNamespace(entry_id="io-load", data={})
                with self.assertRaises(ConfigEntryNotReady):
                    await mod.async_setup_entry(setup_hass, io_entry)
                self.assertEqual(io_entry.data, {})

            # Non-empty invalid-schema persisted dict validates once off-loop and keeps degraded_at.
            load_error = None
            load_result = {
                "records": "corrupt",
                "degraded_at": "2026-11-17T01:02:03+00:00",
            }
            schema_entry = types.SimpleNamespace(entry_id="bad-schema", data={})
            with (
                patch.object(mod, "SituarenessCoordinator", CapturingCoordinator),
                patch.object(
                    mod, "_valid_persisted_store", wraps=mod._valid_persisted_store
                ) as mock_valid,
            ):
                await mod.async_setup_entry(setup_hass, schema_entry)
            mock_valid.assert_called_once_with(load_result)
            schema_coord = setup_hass.data[mod.DOMAIN][schema_entry.entry_id]
            self.assertEqual(schema_coord.degraded_reason, "malformed_store")
            self.assertEqual(schema_coord.degraded_at, "2026-11-17T01:02:03+00:00")

    async def test_outbox_overflow_latches_degraded_and_recovers_after_prune(self):
        from datetime import datetime, timedelta, timezone
        from test_domain import c

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

        def make_alerts(base_time):
            items = []
            for i in range(105):
                ev = d.normalize(feature())
                ev["id"] = f"https://api.weather.gov/alerts/ov-multi-{i}"
                ev["instruction"] = f"Take shelter immediately zone {i}."
                for key, delta in [
                    ("sent", -120),
                    ("effective", -120),
                    ("onset", 0),
                    ("expires", 1800),
                    ("ends", 1800),
                ]:
                    ev[key] = (base_time + timedelta(seconds=delta)).isoformat()
                items.append(cohere(ev))
            return items

        alerts = make_alerts(now)
        raw_cfg = config()
        raw_cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(50)],
            tts_entity=None,
        )
        cfg = c.validate(raw_cfg)
        services = Services()
        store = Store()
        hass = types.SimpleNamespace(data={}, services=services)
        coordinator = mod.SituarenessCoordinator(hass, cfg, store, {})

        # Poll 1: 100 plans fit (5,000 targets); 5 overflow atomically and are stripped,
        # while bounded delivery drains 100 targets from the outbox without blocking output.
        with patch.object(mod, "fetch", return_value=alerts):
            h1 = await coordinator._async_update_data()
        self.assertFalse(h1["evidence_degraded"])
        self.assertFalse(h1["output_blocked"])
        self.assertTrue(h1["partial"])
        self.assertEqual(h1["degraded_reason"], "outbox_overflow")
        self.assertEqual(h1["active_count"], 105)
        self.assertEqual(h1["deliverable_count"], 4900)
        self.assertEqual(h1["suspended_count"], 0)
        self.assertEqual(len(coordinator.outbox), 4900)
        self.assertEqual(len(store.saved[-1]["outbox"]), 4900)
        self.assertEqual(h1["planned_count"], 100)
        self.assertEqual(h1["withheld_count"], 5)
        self.assertEqual(h1["delivery_attempts"], 100)
        self.assertTrue(bool(coordinator.records[alerts[0]["id"]]["actions"]))
        self.assertTrue(bool(coordinator.records[alerts[99]["id"]]["actions"]))
        for overflow_alert in alerts[100:]:
            self.assertEqual(coordinator.records[overflow_alert["id"]]["actions"], {})
        self.assertEqual(len(services.calls), 100)
        self.assertIn("situareness_degraded", notifications)
        self.assertIn(
            "5,000-target limit", notifications["situareness_degraded"].lower()
        )
        self.assertNotIn(
            "live output blocked", notifications["situareness_degraded"].lower()
        )
        self.assertNotIn(
            "15-minute degraded_until horizon expires",
            notifications["situareness_degraded"].lower(),
        )
        self.assertIn(
            "fit within the 5,000-target limit",
            notifications["situareness_degraded"].lower(),
        )
        degraded_at = datetime.fromisoformat(store.saved[-1]["degraded_at"])
        degraded_until = datetime.fromisoformat(store.saved[-1]["degraded_until"])
        self.assertEqual(degraded_until - degraded_at, timedelta(minutes=15))

        # Poll 2: Pre-drain delivers 100 items (4900 -> 4800), queues 4 more plans (5000),
        # and withholds the final 105th alert.
        with patch.object(mod, "fetch", return_value=alerts):
            h2 = await coordinator._async_update_data()
        self.assertFalse(h2["evidence_degraded"])
        self.assertFalse(h2["output_blocked"])
        self.assertTrue(h2["partial"])
        self.assertEqual(h2["degraded_reason"], "outbox_overflow")
        self.assertEqual(h2["active_count"], 105)
        self.assertEqual(h2["deliverable_count"], 5000)
        self.assertEqual(h2["suspended_count"], 0)
        self.assertEqual(h2["planned_count"], 4)
        self.assertEqual(h2["withheld_count"], 1)
        self.assertEqual(h2["delivery_attempts"], 100)
        self.assertEqual(len(services.calls), 200)
        self.assertEqual(len(coordinator.outbox), 5000)
        self.assertIn("situareness_degraded", notifications)

        # Poll 3 (same coordinator, no reload or ack): Pre-drain frees 100 slots (5000 -> 4900),
        # queues the remaining withheld alert (4950 total), and auto-clears outbox_overflow.
        with patch.object(mod, "fetch", return_value=alerts):
            h3 = await coordinator._async_update_data()
        self.assertFalse(h3["evidence_degraded"])
        self.assertFalse(h3["output_blocked"])
        self.assertIsNone(h3["degraded_reason"])
        self.assertEqual(h3["active_count"], 105)
        self.assertEqual(h3["deliverable_count"], 4950)
        self.assertEqual(h3["suspended_count"], 0)
        self.assertEqual(h3["delivery_attempts"], 100)
        self.assertEqual(len(services.calls), 300)
        self.assertEqual(len(coordinator.outbox), 4950)
        self.assertEqual(h3["planned_count"], 1)
        self.assertEqual(h3["withheld_count"], 0)
        self.assertTrue(bool(coordinator.records[alerts[104]["id"]]["actions"]))
        self.assertNotIn("situareness_degraded", notifications)

        # Partial pre-drain failures that leave insufficient headroom re-latch outbox_overflow
        # and surface exact pre-drain delivery_attempts / delivery_failures.
        class PartialFlakyServices:
            def __init__(self):
                self.calls = []

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if len(self.calls) <= 60:
                    raise OSError("transient delivery error")

        extra_alert = make_alerts(now + timedelta(minutes=3))[0]
        extra_alert["id"] = "https://api.weather.gov/alerts/ov-extra-101"
        extra_alert["instruction"] = "Take shelter immediately zone extra."
        cohere(extra_alert)
        fail_services = PartialFlakyServices()
        fail_hass = types.SimpleNamespace(data={}, services=fail_services)
        # Outbox currently has 4950 items; draining 100 with 60 failures leaves 4910,
        # which cannot fit two 50-target plans (4910 + 100 > 5000).
        extra_alert2 = make_alerts(now + timedelta(minutes=3))[1]
        extra_alert2["id"] = "https://api.weather.gov/alerts/ov-extra-102"
        extra_alert2["instruction"] = "Take shelter immediately zone extra 2."
        cohere(extra_alert2)

        class SameWindowClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        retry_store = Store()
        SameWindowClock.current = now + timedelta(minutes=4)
        with patch.object(mod, "datetime", SameWindowClock):
            partial_coord = mod.SituarenessCoordinator(
                fail_hass,
                cfg,
                retry_store,
                {
                    "records": coordinator.records,
                    "outbox": coordinator.outbox,
                    "initialized": True,
                    "was_live": True,
                },
            )
            with patch.object(
                mod, "fetch", return_value=[*alerts, extra_alert, extra_alert2]
            ):
                h_partial = await partial_coord._async_update_data()
        self.assertFalse(h_partial["evidence_degraded"])
        self.assertFalse(h_partial["output_blocked"])
        self.assertTrue(h_partial["partial"])
        self.assertEqual(h_partial["degraded_reason"], "outbox_overflow")
        self.assertEqual(h_partial["delivery_attempts"], 100)
        self.assertEqual(h_partial["delivery_failures"], 60)
        self.assertEqual(h_partial["planned_count"], 1)
        self.assertEqual(h_partial["withheld_count"], 1)
        self.assertEqual(len(partial_coord.outbox), 4960)
        self.assertEqual(h_partial["deliverable_count"], 4960)

        # Once outbox items and the 15-minute outbox_overflow horizon expire, reload clears cleanly
        # without requiring acknowledge_degraded_at.
        later = now + timedelta(minutes=21)
        later_cfg = c.validate(
            {
                **config(),
                "live_enabled": True,
                "commissioning_passed": True,
                "phones": ["mobile_app_ok"],
                "tts_entity": None,
            }
        )
        ev_later = d.normalize(feature())
        ev_later["id"] += "-after-overflow"
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev_later[key] = (later + timedelta(seconds=delta)).isoformat()
        cohere(ev_later)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = later
        services.calls.clear()
        with patch.object(mod, "datetime", Clock):
            after_prune = mod.SituarenessCoordinator(
                hass, later_cfg, Store(), retry_store.saved[-1]
            )
            self.assertTrue(after_prune.degraded)
            with patch.object(mod, "fetch", return_value=[ev_later]):
                h_final = await after_prune._async_update_data()
        self.assertFalse(after_prune.degraded)
        self.assertNotIn("situareness_degraded", notifications)
        self.assertFalse(h_final["evidence_degraded"])
        self.assertFalse(h_final["output_blocked"])
        self.assertIsNone(h_final["degraded_reason"])
        self.assertEqual(h_final["withheld_count"], 0)
        self.assertEqual(len(services.calls), 1)

    async def test_degraded_notification_fires_once_and_clean_save_skips_corrupt_cleanup(
        self,
    ):
        from datetime import datetime, timedelta, timezone
        import tempfile

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        create_calls = []
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                create_calls.append((notification_id, msg, title))
            ),
            async_dismiss=lambda hass, notification_id: None,
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
        bad_cancel = d.normalize(feature())
        bad_cancel["message_type"] = "Cancel"
        bad_cancel["references"] = []
        bad_cancel["reference_identities"] = []
        bad_cancel["cap_references_valid"] = True
        cohere(bad_cancel)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now

        with tempfile.TemporaryDirectory() as tmp:
            exec_calls = []

            async def track_exec(fn, *args):
                exec_calls.append(getattr(getattr(fn, "func", fn), "__name__", str(fn)))
                return fn(*args)

            clean_entry = types.SimpleNamespace(entry_id="clean-entry", data={})
            hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                async_add_executor_job=track_exec,
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            )
            coord = mod.SituarenessCoordinator(
                hass, config(), Store(), {}, entry=clean_entry
            )
            with patch.object(mod, "datetime", Clock):
                # Clean save must not schedule directory scans for corrupt backups.
                with patch.object(mod, "fetch", return_value=[]):
                    await coord._async_update_data()
                self.assertNotIn("_clear_corrupt_store_backups", exec_calls)
                self.assertIn("_resolve_and_scan_candidates", exec_calls)
                self.assertIn("reconcile", exec_calls)
                self.assertIn("_migrate_outbox_with_index", exec_calls)
                self.assertIn("_count_deliverable", exec_calls)

                # Two consecutive degraded polls with advancing timestamps emit notification once.
                with patch.object(mod, "fetch", return_value=[bad_cancel]):
                    await coord._async_update_data()
                    Clock.current = now + timedelta(minutes=2)
                    await coord._async_update_data()
            self.assertEqual(len(create_calls), 1)
            self.assertEqual(create_calls[0][0], "situareness_degraded")
            self.assertIn("acknowledge_degraded_at", create_calls[0][1])
            self.assertIn("degraded_until", create_calls[0][1])
            self.assertNotIn("Until:", create_calls[0][1])

            # malformed_store notification explicitly instructs .storage repair or entry removal.
            mal_coord = mod.SituarenessCoordinator(hass, config(), Store(), ["corrupt"])
            self.assertTrue(mal_coord.degraded)
            self.assertEqual(len(create_calls), 2)
            self.assertIn(".storage", create_calls[1][1])
            self.assertNotIn("acknowledge_degraded_at", create_calls[1][1])

            # Per-10-target-group delivery executes ONE post-group _save instead of 10 per-item saves.
            batch_cfg = config()
            batch_cfg.update(
                live_enabled=True,
                commissioning_passed=True,
                phones=[f"mobile_app_{i}" for i in range(10)],
                tts_entity=None,
            )
            batch_ev = d.normalize(feature())
            batch_ev["id"] += "-batch-10"
            for key, delta in [
                ("sent", -120),
                ("effective", -120),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                batch_ev[key] = (now + timedelta(seconds=delta)).isoformat()
            cohere(batch_ev)
            batch_store = Store()
            batch_services = Services()
            batch_hass = types.SimpleNamespace(data={}, services=batch_services)
            batch_coord = mod.SituarenessCoordinator(
                batch_hass, batch_cfg, batch_store, {}
            )
            with (
                patch.object(mod, "datetime", Clock),
                patch.object(mod, "fetch", return_value=[batch_ev]),
            ):
                await batch_coord._async_update_data()
            self.assertEqual(len(batch_services.calls), 10)
            # Save 0 = pre-delivery outbox persist; Save 1 = single post-group delivery persist.
            self.assertEqual(len(batch_store.saved), 2)
            self.assertEqual(batch_store.saved[1]["outbox"], [])
            self.assertEqual(len(batch_store.saved[1]["outcomes"]), 10)

    async def test_quarantine_ambiguous_notification_and_degraded_cancel_uncertainty(
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
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        services = Services()
        store = Store()
        hass = types.SimpleNamespace(data={}, services=services)
        coord = mod.SituarenessCoordinator(hass, cfg, store, {})

        # Scoped quarantine with valid feature_id does not trigger quarantine_ambiguous or notify.
        scoped = collector.CollectedEvents(
            [ev],
            1,
            [["https://api.weather.gov/alerts/bad-ref"]],
            False,
            source_count=2,
            all_events=[ev],
        )
        with patch.object(mod, "fetch", return_value=scoped):
            h1 = await coord._async_update_data()
        self.assertTrue(h1["partial"])
        self.assertFalse(h1["quarantine_ambiguous"])
        self.assertEqual(len(services.calls), 1)
        self.assertNotIn("situareness_degraded", notifications)

        # Unextractable feature_id sets quarantine_ambiguous and raises situareness_degraded;
        # next clean poll clears the notification.
        ambig = collector.CollectedEvents(
            [ev], 1, [], True, source_count=2, all_events=[ev]
        )
        with patch.object(mod, "fetch", return_value=ambig):
            h2 = await coord._async_update_data()
        self.assertTrue(h2["quarantine_ambiguous"])
        self.assertFalse(h2["evidence_degraded"])
        self.assertTrue(h2["output_blocked"])
        self.assertIn("situareness_degraded", notifications)
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness alert scope ambiguous",
        )
        with patch.object(mod, "fetch", return_value=[ev]):
            h3 = await coord._async_update_data()
        self.assertFalse(h3["quarantine_ambiguous"])
        self.assertFalse(h3["output_blocked"])
        self.assertNotIn("situareness_degraded", notifications)

        # Degraded journal_lost poll carrying quarantined_cancel_lineages reports
        # cancellation_uncertain=True and partial=True even when target is absent from records.
        lost_entry = types.SimpleNamespace(
            entry_id="lost-q", data={"journal_initialized": True}
        )
        lost_hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        lost_coord = mod.SituarenessCoordinator(
            lost_hass, cfg, Store(), None, entry=lost_entry
        )
        q_cancel = collector.CollectedEvents(
            [],
            1,
            [
                [
                    "https://api.weather.gov/alerts/c1",
                    "https://api.weather.gov/alerts/t1",
                ]
            ],
            False,
            source_count=1,
            all_events=[],
            quarantined_cancel_lineages=[
                [
                    "https://api.weather.gov/alerts/c1",
                    "https://api.weather.gov/alerts/t1",
                ]
            ],
        )
        with patch.object(mod, "fetch", return_value=q_cancel):
            h_deg = await lost_coord._async_update_data()
        self.assertTrue(h_deg["evidence_degraded"])
        self.assertTrue(h_deg["cancellation_uncertain"])
        self.assertTrue(h_deg["partial"])

    async def test_partial_cancellation_continuing_segment_delivery(self):
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

        def make_ev(name, offset_min, refs=(), message_type="Update"):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/{name}"
            ev["message_type"] = message_type
            for key, sec in [
                ("sent", offset_min * 60),
                ("effective", offset_min * 60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=sec)).isoformat()
            return cohere(ev, *refs)

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        p = make_ev("part-p", -10, message_type="Alert")
        cancel_c = make_ev("part-c", -5, [p], message_type="Cancel")
        u_new = make_ev("part-u-new", -4, [p])
        u_new["instruction"] = "Take shelter in a basement immediately."
        u2 = make_ev("part-u2", -3, [p, u_new])
        u2["instruction"] = u_new["instruction"]

        services = Services()
        store = Store()
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(services=services), cfg, store, {}
        )
        with patch.object(mod, "fetch", return_value=[p]):
            await coord._async_update_data()
        self.assertEqual(len(services.calls), 1)

        with patch.object(mod, "fetch", return_value=[cancel_c, u_new]):
            h2 = await coord._async_update_data()
        self.assertEqual(h2["active_count"], 1)
        self.assertEqual(len(services.calls), 2)
        self.assertEqual(services.calls[1][2]["data"]["url"], u_new["id"])

        # After Cancel leaves the feed, continuing update with same instruction stays active without duplicate output.
        with patch.object(mod, "fetch", return_value=[u2]):
            h3 = await coord._async_update_data()
        self.assertEqual(h3["active_count"], 1)
        self.assertEqual(len(services.calls), 2)

    async def test_notification_reason_selection_shadow_qualification_and_oversized_outbox(
        self,
    ):
        from datetime import datetime, timezone

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

        hass = types.SimpleNamespace(data={}, services=Services())
        shadow_cfg = config()

        # Legacy store with degraded_reason="cancellation_evidence_overflow" and degraded_until=None
        # uses degraded_until / acknowledge_degraded_at guidance rather than .storage repair,
        # and qualifies shadow mode truthfully.
        legacy_coord = mod.SituarenessCoordinator(
            hass,
            shadow_cfg,
            Store(),
            {
                "degraded": True,
                "degraded_reason": "cancellation_evidence_overflow",
                "degraded_until": None,
            },
        )
        self.assertTrue(legacy_coord.degraded)
        legacy_msg = notifications["situareness_degraded"]["message"]
        self.assertIn("shadow mode", legacy_msg.lower())
        self.assertIn("live output disabled", legacy_msg.lower())
        self.assertNotIn("output is blocked", legacy_msg.lower())
        self.assertIn("degraded_until", legacy_msg)
        self.assertIn("acknowledge_degraded_at", legacy_msg)
        self.assertIn("1,000", legacy_msg)
        self.assertIn("evicted tombstones", legacy_msg)
        self.assertNotIn(".storage", legacy_msg)

        # journal_lost guidance omits feed-trigger phrasing and warns about missing tombstones.
        lost_entry = types.SimpleNamespace(
            entry_id="lost-note", data={"journal_initialized": True}
        )
        lost_hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        mod.SituarenessCoordinator(
            lost_hass, shadow_cfg, Store(), None, entry=lost_entry
        )
        lost_msg = notifications["situareness_degraded"]["message"]
        self.assertNotIn("triggering feed condition", lost_msg)
        self.assertIn("missing historical tombstones", lost_msg)
        self.assertIn("acknowledge_degraded_at", lost_msg)

        # Shadow-mode outbox_overflow and malformed_store also qualify shadow mode truthfully.
        mod.SituarenessCoordinator(
            hass,
            shadow_cfg,
            Store(),
            {
                "degraded": True,
                "degraded_reason": "outbox_overflow",
                "degraded_until": datetime.now(timezone.utc).isoformat(),
            },
        )
        ov_note = notifications["situareness_degraded"]
        self.assertEqual(ov_note["title"], "Situareness delivery outbox full")
        self.assertIn("shadow mode", ov_note["message"].lower())
        self.assertNotIn("continue bounded delivery", ov_note["message"].lower())

        mod.SituarenessCoordinator(hass, shadow_cfg, Store(), ["corrupt"])
        mal_msg = notifications["situareness_degraded"]["message"]
        self.assertIn("shadow mode", mal_msg.lower())
        self.assertNotIn("output is blocked", mal_msg.lower())
        self.assertIn(".storage", mal_msg)

        # Persisted outbox longer than 5,000 items is rejected as malformed_store without truncation.
        now_iso = datetime.now(timezone.utc).isoformat()
        oversized_outbox = [
            {
                "key": f"k-{i}",
                "incident_id": f"https://api.weather.gov/alerts/ov-{i}",
                "fingerprint": f"fp-{i}",
                "kind": "notify",
                "target": "mobile_app_one",
                "created": now_iso,
                "event": "Tornado Warning",
                "instruction": "Take shelter immediately",
                "source_url": f"https://api.weather.gov/alerts/ov-{i}",
                "affected_names": ["New York"],
                "location": "New York",
                "attempts": 0,
            }
            for i in range(5001)
        ]
        oversized_store = {"records": {}, "outbox": oversized_outbox}
        self.assertFalse(mod._valid_persisted_store(oversized_store))
        ov_store = Store()
        ov_coord = mod.SituarenessCoordinator(
            hass, shadow_cfg, ov_store, oversized_store
        )
        self.assertTrue(ov_coord.degraded)
        self.assertEqual(ov_coord.degraded_reason, "malformed_store")
        h_ov = await ov_coord._async_update_data()
        self.assertEqual(h_ov["degraded_reason"], "malformed_store")
        self.assertTrue(h_ov["output_blocked"])
        self.assertEqual(ov_store.saved, [])
        self.assertEqual(len(oversized_outbox), 5001)

    async def test_acknowledge_stability_relatch_and_rejection_visibility(self):
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

        t0 = datetime.now(timezone.utc) - timedelta(minutes=20)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        def make_bad_cancel(ts):
            ev = d.normalize(feature())
            ev["id"] = "https://api.weather.gov/alerts/bad-cancel-ack"
            ev["message_type"] = "Cancel"
            ev["references"] = []
            for key, sec in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (ts + timedelta(seconds=sec)).isoformat()
            return ev

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        services = Services()
        store = Store()
        hass = types.SimpleNamespace(data={}, services=services)

        Clock.current = t0
        bad_cancel = make_bad_cancel(t0)
        with patch.object(mod, "datetime", Clock):
            coord = mod.SituarenessCoordinator(hass, cfg, store, {})
            with patch.object(mod, "fetch", return_value=[bad_cancel]):
                h1 = await coord._async_update_data()
            Clock.current = t0 + timedelta(minutes=2)
            with patch.object(mod, "fetch", return_value=[bad_cancel]):
                h2 = await coord._async_update_data()

        # degraded_at stays pinned to initial latch t0 while degraded_until advances.
        self.assertEqual(h1["degraded_reason"], "malformed_cancellation")
        self.assertEqual(h1["degraded_at"], t0.isoformat())
        self.assertEqual(h2["degraded_at"], t0.isoformat())
        self.assertGreater(
            d.timestamp(h2["degraded_until"]), d.timestamp(h1["degraded_until"])
        )
        self.assertFalse(h2["acknowledge_rejected"])

        # Setting acknowledge_degraded_at to initial degraded_at recovers cleanly after trigger leaves feed.
        cfg_pin_ack = {**cfg, "acknowledge_degraded_at": t0.isoformat()}
        Clock.current = t0 + timedelta(minutes=3)
        with patch.object(mod, "datetime", Clock):
            recovered = mod.SituarenessCoordinator(
                hass, cfg_pin_ack, Store(), store.saved[-1]
            )
            self.assertFalse(recovered.degraded)
            self.assertFalse(recovered.acknowledge_rejected)
            with patch.object(mod, "fetch", return_value=[]):
                h_rec = await recovered._async_update_data()
        self.assertFalse(h_rec["degraded_reason"] is not None)
        self.assertFalse(h_rec["acknowledge_rejected"])

        # Reloading with valid ack while trigger STILL persists re-latches on Poll 1
        # with new degraded_at == Poll1_now and acknowledge_rejected == True.
        cfg_active_ack = {
            **cfg,
            "acknowledge_degraded_at": (t0 + timedelta(minutes=3)).isoformat(),
        }
        Clock.current = t0 + timedelta(minutes=4)
        with patch.object(mod, "datetime", Clock):
            re_coord = mod.SituarenessCoordinator(
                hass, cfg_active_ack, Store(), store.saved[-1]
            )
            self.assertFalse(re_coord.degraded)
            Clock.current = t0 + timedelta(minutes=5)
            with patch.object(mod, "fetch", return_value=[bad_cancel]):
                h_relatch = await re_coord._async_update_data()
        self.assertTrue(re_coord.degraded)
        self.assertEqual(
            h_relatch["degraded_at"], (t0 + timedelta(minutes=5)).isoformat()
        )
        self.assertTrue(h_relatch["acknowledge_rejected"])
        relatch_msg = notifications["situareness_degraded"]["message"]
        self.assertIn("re-latched", relatch_msg.lower())
        self.assertIn("degraded_at", relatch_msg)

        # Rejected acks (pre-degraded_at, already consumed, or malformed_store) expose acknowledge_rejected=True.
        persisted_deg = {
            "records": {},
            "outbox": [],
            "degraded": True,
            "degraded_reason": "cancellation_evidence_overflow",
            "degraded_at": (t0 + timedelta(minutes=5)).isoformat(),
            "degraded_until": (t0 + timedelta(days=7)).isoformat(),
            "acknowledged_degraded_at": (t0 + timedelta(minutes=6)).isoformat(),
        }
        Clock.current = t0 + timedelta(minutes=7)
        with patch.object(mod, "datetime", Clock):
            # Pre-degradation ack
            early_coord = mod.SituarenessCoordinator(
                hass,
                {
                    **cfg,
                    "acknowledge_degraded_at": (t0 + timedelta(minutes=4)).isoformat(),
                },
                Store(),
                persisted_deg,
            )
            self.assertTrue(early_coord.acknowledge_rejected)
            self.assertIn(
                "did not clear", notifications["situareness_degraded"]["message"]
            )
            with patch.object(mod, "fetch", return_value=[]):
                h_early = await early_coord._async_update_data()
            self.assertTrue(h_early["acknowledge_rejected"])

            # Already-consumed ack
            same_coord = mod.SituarenessCoordinator(
                hass,
                {
                    **cfg,
                    "acknowledge_degraded_at": (t0 + timedelta(minutes=6)).isoformat(),
                },
                Store(),
                persisted_deg,
            )
            self.assertTrue(same_coord.acknowledge_rejected)
            with patch.object(mod, "fetch", return_value=[]):
                h_same = await same_coord._async_update_data()
            self.assertTrue(h_same["acknowledge_rejected"])

            # malformed_store with configured ack
            mal_coord = mod.SituarenessCoordinator(
                hass,
                {
                    **cfg,
                    "acknowledge_degraded_at": (t0 + timedelta(minutes=6)).isoformat(),
                },
                Store(),
                ["corrupt"],
            )
            self.assertTrue(mal_coord.acknowledge_rejected)
            mal_msg = notifications["situareness_degraded"]["message"]
            self.assertIn("did not clear", mal_msg)
            self.assertIn(".storage", mal_msg)
            h_mal = await mal_coord._async_update_data()
            self.assertTrue(h_mal["acknowledge_rejected"])

            # Validating and loading naive/future acknowledge_degraded_at does not fail setup;
            # naive strings keep stored ISO state valid, and future timestamps are consumed immediately
            # on entry.data even when no store save occurs before a later restart.
            from test_domain import c

            naive_cfg = c.validate(
                {**cfg, "acknowledge_degraded_at": "2026-11-17T10:00:00"}
            )
            naive_entry = types.SimpleNamespace(entry_id="ack-naive", data={})
            naive_hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            )
            naive_store = Store()
            naive_coord = mod.SituarenessCoordinator(
                naive_hass, naive_cfg, naive_store, persisted_deg, entry=naive_entry
            )
            self.assertTrue(naive_coord.degraded)
            self.assertTrue(naive_coord.acknowledge_rejected)
            self.assertNotIn("acknowledged_degraded_at", naive_entry.data)
            self.assertEqual(
                naive_coord.acknowledged_degraded_at,
                persisted_deg["acknowledged_degraded_at"],
            )
            naive_msg = notifications["situareness_degraded"]["message"]
            self.assertIn("missing timezone offset", naive_msg)
            with patch.object(mod, "fetch", return_value=[]):
                await naive_coord._async_update_data()
            self.assertTrue(mod._valid_persisted_store(naive_store.saved[-1]))

            future_ack = (t0 + timedelta(minutes=10)).isoformat()
            future_cfg = c.validate({**cfg, "acknowledge_degraded_at": future_ack})
            fut_entry = types.SimpleNamespace(entry_id="ack-future", data={})
            fut_hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            )
            fut_coord = mod.SituarenessCoordinator(
                fut_hass, future_cfg, Store(), persisted_deg, entry=fut_entry
            )
            self.assertTrue(fut_coord.degraded)
            self.assertTrue(fut_coord.acknowledge_rejected)
            self.assertEqual(fut_entry.data.get("acknowledged_degraded_at"), future_ack)
            # No _save() occurred; advance clock past future_ack and reload with original persisted_deg.
            Clock.current = t0 + timedelta(minutes=15)
            fut_reload = mod.SituarenessCoordinator(
                fut_hass, future_cfg, Store(), persisted_deg, entry=fut_entry
            )
            self.assertTrue(fut_reload.degraded)
            self.assertTrue(fut_reload.acknowledge_rejected)

            # Over-length acknowledge_degraded_at passes c.validate(), rejects cleanly at runtime,
            # keeps monitoring online, and persists valid store state.
            over_len_ack = "2026-11-17T10:00:00Z-" + "x" * 100
            over_len_cfg = c.validate({**cfg, "acknowledge_degraded_at": over_len_ack})
            self.assertEqual(
                over_len_cfg["acknowledge_degraded_at"], over_len_ack[:101]
            )
            over_entry = types.SimpleNamespace(entry_id="ack-overlen", data={})
            over_hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            )
            over_store = Store()
            over_coord = mod.SituarenessCoordinator(
                over_hass, over_len_cfg, over_store, persisted_deg, entry=over_entry
            )
            self.assertTrue(over_coord.degraded)
            self.assertTrue(over_coord.acknowledge_rejected)
            self.assertNotIn("acknowledged_degraded_at", over_entry.data)
            self.assertEqual(
                over_coord.acknowledged_degraded_at,
                persisted_deg["acknowledged_degraded_at"],
            )
            over_msg = notifications["situareness_degraded"]["message"]
            self.assertIn("did not clear", over_msg)
            with patch.object(mod, "fetch", return_value=[]):
                h_over = await over_coord._async_update_data()
            self.assertTrue(h_over["acknowledge_rejected"])
            self.assertTrue(mod._valid_persisted_store(over_store.saved[-1]))

        # Far-future year-9999 timestamps in expires/ends/sent/Cancel leave the feed without
        # OverflowError or UpdateFailed while valid alerts stay active and deliver cleanly.
        now_live = datetime.now(timezone.utc)
        valid_ev = d.normalize(feature())
        valid_ev["id"] = "https://api.weather.gov/alerts/coord-valid-9999"
        for key, sec in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            valid_ev[key] = (now_live + timedelta(seconds=sec)).isoformat()
        cohere(valid_ev)

        y9999_exp = d.normalize(feature())
        y9999_exp["id"] = "https://api.weather.gov/alerts/coord-9999-exp"
        cohere(y9999_exp)
        y9999_exp["expires"] = "9999-12-31T23:59:59Z"
        y9999_exp["ends"] = "9999-12-31T23:59:59Z"

        y9999_cancel = d.normalize(feature())
        y9999_cancel["id"] = "https://api.weather.gov/alerts/coord-9999-cancel"
        y9999_cancel["message_type"] = "Cancel"
        y9999_cancel["sent"] = "9999-12-31T23:59:59Z"
        y9999_cancel["references"] = [
            "https://api.weather.gov/alerts/coord-9999-target"
        ]

        live_services = Services()
        live_store = Store()
        live_coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=live_services), cfg, live_store, {}
        )
        with patch.object(
            mod, "fetch", return_value=[valid_ev, y9999_exp, y9999_cancel]
        ):
            h_y1 = await live_coord._async_update_data()
        self.assertFalse(h_y1["evidence_degraded"])
        self.assertEqual(h_y1["active_count"], 1)
        self.assertEqual(len(live_services.calls), 1)
        self.assertEqual(live_services.calls[0][2]["data"]["url"], valid_ev["id"])

        # After year-9999 features leave the feed, subsequent polls remain clean without UpdateFailed.
        with patch.object(mod, "fetch", return_value=[valid_ev]):
            h_y2 = await live_coord._async_update_data()
        self.assertFalse(h_y2["evidence_degraded"])
        self.assertEqual(h_y2["active_count"], 1)
        self.assertEqual(len(live_services.calls), 1)

    async def test_max_timestamp_overflow_retry_priority_and_healthy_ack_rejection(
        self,
    ):
        from datetime import datetime, timedelta, timezone
        from test_domain import c

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

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )

        # Near-MAX_TIMESTAMP CancellationEvidenceOverflow stores MAX_TIMESTAMP.isoformat(),
        # passes _valid_persisted_store(), and reloads into cancellation_evidence_overflow.
        class MaxClock:
            current = datetime(9998, 12, 30, 0, 0, tzinfo=timezone.utc)

            @classmethod
            def now(cls, tz):
                return cls.current

        max_now = MaxClock.current
        ov_records = {
            f"https://api.weather.gov/alerts/max-ov-{i}": {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [f"https://api.weather.gov/alerts/max-ov-{i}"],
                "sent": max_now.isoformat(),
                "expires": max_now.isoformat(),
                "updated": max_now.isoformat(),
            }
            for i in range(1001)
        }
        ov_store = Store()
        with patch.object(mod, "datetime", MaxClock):
            ov_coord = mod.SituarenessCoordinator(
                hass,
                cfg,
                ov_store,
                {
                    "records": ov_records,
                    "outbox": [],
                    "initialized": True,
                    "was_live": True,
                },
            )
            with patch.object(mod, "fetch", return_value=[]):
                h_max = await ov_coord._async_update_data()
        expected_max_iso = d.MAX_TIMESTAMP.isoformat()
        self.assertEqual(expected_max_iso, "9998-12-31T23:59:59+00:00")
        self.assertEqual(h_max["degraded_reason"], "cancellation_evidence_overflow")
        self.assertEqual(h_max["degraded_until"], expected_max_iso)
        self.assertTrue(mod._valid_persisted_store(ov_store.saved[-1]))
        reloaded_max = mod.SituarenessCoordinator(
            hass, cfg, Store(), ov_store.saved[-1]
        )
        self.assertEqual(reloaded_max.degraded_reason, "cancellation_evidence_overflow")
        self.assertEqual(reloaded_max.degraded_until, expected_max_iso)

        # Outbox delivery prioritizes first-attempt items (attempts == 0) before retries (attempts > 0)
        # while maintaining FIFO within each tier and caching qualify() per incident per 10-target group.
        now = datetime.now(timezone.utc)

        def make_live_event(suffix, offset_sec=-60):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/prio-{suffix}"
            for key, delta in [
                ("sent", offset_sec),
                ("effective", offset_sec),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        retry_ev = make_live_event("retry", -120)
        fresh_ev = make_live_event("fresh", -30)
        batch_cfg = {**cfg, "phones": [f"mobile_app_{i}" for i in range(10)]}
        retry_outbox = [
            {
                "key": f"retry-{i}",
                "incident_id": retry_ev["id"],
                "fingerprint": "fp-retry",
                "kind": "phone",
                "target": f"mobile_app_{i % 10}",
                "location": "new_york_ny",
                "affected_names": ["New York"],
                "event": "Tornado Warning",
                "instruction": "Take shelter immediately.",
                "source_url": retry_ev["id"],
                "attempts": 1,
                "created": now.isoformat(),
            }
            for i in range(100)
        ]
        fresh_item = {
            "key": "fresh-0",
            "incident_id": fresh_ev["id"],
            "fingerprint": "fp-fresh",
            "kind": "phone",
            "target": "mobile_app_0",
            "location": "new_york_ny",
            "affected_names": ["New York"],
            "event": "Tornado Warning",
            "instruction": "Take shelter immediately.",
            "source_url": fresh_ev["id"],
            "attempts": 0,
            "created": now.isoformat(),
        }
        prio_services = Services()
        prio_hass = types.SimpleNamespace(data={}, services=prio_services)
        prio_records = {
            retry_ev["id"]: {
                "state": "active",
                "fingerprint": "fp-retry",
                "lineage": [retry_ev["id"]],
                "actions": {"fp-retry": ["new_york_ny"]},
                "updated": now.isoformat(),
            },
            fresh_ev["id"]: {
                "state": "active",
                "fingerprint": "fp-fresh",
                "lineage": [fresh_ev["id"]],
                "actions": {"fp-fresh": ["new_york_ny"]},
                "updated": now.isoformat(),
            },
        }
        prio_coord = mod.SituarenessCoordinator(
            prio_hass,
            batch_cfg,
            Store(),
            {
                "records": prio_records,
                "outbox": [*retry_outbox, fresh_item],
                "initialized": True,
                "was_live": True,
            },
        )
        with patch.object(mod, "qualify", wraps=d.qualify) as mock_qualify:
            attempts, failures = await prio_coord._deliver_outbox_batch(
                [retry_ev, fresh_ev], now
            )
        self.assertEqual(attempts, 100)
        self.assertEqual(failures, 0)
        self.assertEqual(prio_services.calls[0][2]["data"]["url"], fresh_ev["id"])
        # Remaining 99 slots go to FIFO retries; 1 retry remains queued.
        self.assertEqual(len(prio_coord.outbox), 1)
        self.assertEqual(prio_coord.outbox[0]["key"], "retry-99")
        # Group 0 had fresh_ev + 9 retry_ev items => at most 2 qualify() calls for Group 0
        # plus 1 per subsequent 10-target group (9 remaining groups) = 11 instead of 100.
        self.assertLessEqual(mock_qualify.call_count, 11)

        # Loading naive, over-length, or future acknowledge_degraded_at while healthy sets
        # acknowledge_rejected=True on coordinator + snapshot and raises situareness_degraded;
        # valid consumed future ISO still cannot clear a later degradation.
        healthy_store = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
        }
        for bad_ack in (
            "2026-11-17T10:00:00",
            "2026-11-17T10:00:00Z-" + "x" * 100,
        ):
            notifications.clear()
            bad_cfg = c.validate({**cfg, "acknowledge_degraded_at": bad_ack})
            hc = mod.SituarenessCoordinator(hass, bad_cfg, Store(), healthy_store)
            self.assertFalse(hc.degraded)
            self.assertTrue(hc.acknowledge_rejected)
            self.assertIn("situareness_degraded", notifications)
            self.assertEqual(
                notifications["situareness_degraded"]["title"],
                "Situareness acknowledgement rejected",
            )
            with patch.object(mod, "fetch", return_value=[]):
                hh = await hc._async_update_data()
            self.assertTrue(hh["acknowledge_rejected"])
            self.assertFalse(hh["evidence_degraded"])

        notifications.clear()
        fut_healthy_ack = (now + timedelta(hours=1)).isoformat()
        fut_healthy_entry = types.SimpleNamespace(entry_id="healthy-fut", data={})
        fut_hc = mod.SituarenessCoordinator(
            hass,
            c.validate({**cfg, "acknowledge_degraded_at": fut_healthy_ack}),
            Store(),
            healthy_store,
            entry=fut_healthy_entry,
        )
        self.assertFalse(fut_hc.degraded)
        self.assertTrue(fut_hc.acknowledge_rejected)
        self.assertEqual(
            fut_healthy_entry.data.get("acknowledged_degraded_at"), fut_healthy_ack
        )
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness acknowledgement rejected",
        )
        with patch.object(mod, "fetch", return_value=[]):
            hh_fut = await fut_hc._async_update_data()
        self.assertTrue(hh_fut["acknowledge_rejected"])

        # Subsequent degradation after clock passes fut_healthy_ack still cannot be cleared by it.
        later_deg = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now + timedelta(minutes=10)).isoformat(),
            "degraded_until": (now + timedelta(days=8)).isoformat(),
            "acknowledged_degraded_at": fut_healthy_ack,
        }

        class FutureAckClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        FutureAckClock.current = now + timedelta(hours=2)

        with patch.object(mod, "datetime", FutureAckClock):
            deg_after = mod.SituarenessCoordinator(
                hass,
                c.validate({**cfg, "acknowledge_degraded_at": fut_healthy_ack}),
                Store(),
                later_deg,
                entry=fut_healthy_entry,
            )
        self.assertTrue(deg_after.degraded)
        self.assertTrue(deg_after.acknowledge_rejected)

        # Removing acknowledge_degraded_at clears acknowledgement rejection notification.
        clean_hc = mod.SituarenessCoordinator(hass, cfg, Store(), healthy_store)
        self.assertFalse(clean_hc.acknowledge_rejected)
        self.assertNotIn("situareness_degraded", notifications)

    async def test_supersession_outbox_isolation_multi_ack_and_rejection_transitions(
        self,
    ):
        from datetime import datetime, timedelta, timezone
        from test_domain import c

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

        now = datetime.now(timezone.utc)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_one"],
            tts_entity=None,
        )

        # Non-Actual Test Update/Cancel and Actual Alert messages referencing P
        # do not steal or suspend P's pending outbox items.
        class FlakyServices:
            def __init__(self):
                self.calls = []
                self.fail = True

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                if self.fail:
                    raise OSError("transient")

        p_ev = d.normalize(feature())
        p_ev["id"] = "https://api.weather.gov/alerts/outbox-p"
        for key, delta in [
            ("sent", -120),
            ("effective", -120),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            p_ev[key] = (now + timedelta(seconds=delta)).isoformat()
        cohere(p_ev)

        test_upd = d.normalize(feature())
        test_upd["id"] = "https://api.weather.gov/alerts/test-ref-p"
        test_upd["status"] = "Test"
        test_upd["message_type"] = "Update"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            test_upd[key] = (now + timedelta(seconds=delta)).isoformat()
        cohere(test_upd, p_ev)
        test_upd["message_type"] = "Update"

        spurious_alert = d.normalize(feature())
        spurious_alert["id"] = "https://api.weather.gov/alerts/alert-ref-p"
        spurious_alert["instruction"] = "Ignore."
        for key, delta in [
            ("sent", -30),
            ("effective", -30),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            spurious_alert[key] = (now + timedelta(seconds=delta)).isoformat()
        cohere(spurious_alert, p_ev)
        spurious_alert["message_type"] = "Alert"

        flaky = FlakyServices()
        outbox_store = Store()
        outbox_hass = types.SimpleNamespace(data={}, services=flaky)
        coord_p = mod.SituarenessCoordinator(outbox_hass, cfg, outbox_store, {})
        with patch.object(mod, "fetch", return_value=[p_ev]):
            await coord_p._async_update_data()
        self.assertEqual(len(coord_p.outbox), 1)
        self.assertEqual(coord_p.outbox[0]["incident_id"], p_ev["id"])

        with patch.object(mod, "fetch", return_value=[p_ev, test_upd, spurious_alert]):
            h_mig = await coord_p._async_update_data()
        self.assertEqual(h_mig["pending_count"], 1)
        self.assertEqual(coord_p.outbox[0]["incident_id"], p_ev["id"])
        self.assertEqual(coord_p.records[p_ev["id"]]["state"], "active")

        # Multi-slot consumed_acknowledgements:
        # Trigger 1: future B recorded in entry.data over store A without store save
        # survives reload with ack removed, and next _save() preserves [A, B].
        ack_a = (now - timedelta(hours=2)).isoformat()
        ack_b = (now + timedelta(hours=1)).isoformat()
        store_with_a = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "acknowledged_degraded_at": ack_a,
        }
        entry_m = types.SimpleNamespace(entry_id="multi-ack", data={})
        hass_m = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        c_b_rej = mod.SituarenessCoordinator(
            hass_m,
            c.validate({**cfg, "acknowledge_degraded_at": ack_b}),
            Store(),
            store_with_a,
            entry=entry_m,
        )
        self.assertTrue(c_b_rej.acknowledge_rejected)
        self.assertEqual(entry_m.data.get("consumed_acknowledgements"), [ack_a, ack_b])
        self.assertEqual(entry_m.data.get("acknowledged_degraded_at"), ack_b)

        save_store_m = Store()
        c_no_ack = mod.SituarenessCoordinator(
            hass_m, cfg, save_store_m, store_with_a, entry=entry_m
        )
        self.assertEqual(c_no_ack.consumed_acknowledgements, [ack_a, ack_b])
        self.assertEqual(c_no_ack.acknowledged_degraded_at, ack_b)
        with patch.object(mod, "fetch", return_value=[]):
            await c_no_ack._async_update_data()
        self.assertEqual(
            save_store_m.saved[-1]["consumed_acknowledgements"], [ack_a, ack_b]
        )
        self.assertEqual(save_store_m.saved[-1]["acknowledged_degraded_at"], ack_b)

        # Trigger 2: consuming ack_1 then ack_2 remembers both and rejects replaying ack_1.
        ack_1 = (now - timedelta(minutes=20)).isoformat()
        ack_2 = (now - timedelta(minutes=5)).isoformat()
        entry_t2 = types.SimpleNamespace(entry_id="multi-t2", data={})
        store_t2 = Store()
        deg1 = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now - timedelta(minutes=30)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        c_rec1 = mod.SituarenessCoordinator(
            hass_m,
            {**cfg, "acknowledge_degraded_at": ack_1},
            store_t2,
            deg1,
            entry=entry_t2,
        )
        self.assertFalse(c_rec1.degraded)
        with patch.object(mod, "fetch", return_value=[]):
            await c_rec1._async_update_data()

        deg2 = {
            **store_t2.saved[-1],
            "degraded": True,
            "degraded_reason": "cancellation_evidence_overflow",
            "degraded_at": (now - timedelta(minutes=10)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        c_rec2 = mod.SituarenessCoordinator(
            hass_m,
            {**cfg, "acknowledge_degraded_at": ack_2},
            store_t2,
            deg2,
            entry=entry_t2,
        )
        self.assertFalse(c_rec2.degraded)
        with patch.object(mod, "fetch", return_value=[]):
            await c_rec2._async_update_data()
        self.assertEqual(
            store_t2.saved[-1]["consumed_acknowledgements"], [ack_1, ack_2]
        )

        deg3 = {
            **store_t2.saved[-1],
            "degraded": True,
            "degraded_reason": "malformed_cancellation",
            "degraded_at": (now - timedelta(minutes=2)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        c_replay1 = mod.SituarenessCoordinator(
            hass_m,
            {**cfg, "acknowledge_degraded_at": ack_1},
            Store(),
            deg3,
            entry=entry_t2,
        )
        self.assertTrue(c_replay1.degraded)
        self.assertTrue(c_replay1.acknowledge_rejected)

        # acknowledge_rejected remains True and notifies after degraded_until expiry AND
        # after outbox_overflow auto-clear while naive/future acknowledge_degraded_at stays set.
        class ExpiryClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        ExpiryClock.current = now + timedelta(minutes=1)
        notifications.clear()
        with patch.object(mod, "datetime", ExpiryClock):
            exp_coord = mod.SituarenessCoordinator(
                hass_m,
                c.validate({**cfg, "acknowledge_degraded_at": "2026-11-17T10:00:00"}),
                Store(),
                {
                    "records": {},
                    "outbox": [],
                    "initialized": True,
                    "was_live": True,
                    "degraded": True,
                    "degraded_reason": "cancellation_evidence_overflow",
                    "degraded_at": (now - timedelta(days=8)).isoformat(),
                    "degraded_until": (now - timedelta(minutes=1)).isoformat(),
                },
            )
            with patch.object(mod, "fetch", return_value=[]):
                h_exp = await exp_coord._async_update_data()
        self.assertFalse(exp_coord.degraded)
        self.assertFalse(h_exp["evidence_degraded"])
        self.assertTrue(h_exp["acknowledge_rejected"])
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness acknowledgement rejected",
        )

        # Same persistence across outbox_overflow auto-clear.
        notifications.clear()
        ov_auto_coord = mod.SituarenessCoordinator(
            hass_m,
            c.validate({**cfg, "acknowledge_degraded_at": "2026-11-17T10:00:00"}),
            Store(),
            {
                "records": {},
                "outbox": [],
                "initialized": True,
                "was_live": True,
                "degraded": True,
                "degraded_reason": "outbox_overflow",
                "degraded_at": (now - timedelta(minutes=1)).isoformat(),
                "degraded_until": (now + timedelta(minutes=14)).isoformat(),
            },
        )
        with patch.object(mod, "fetch", return_value=[]):
            h_ov_clear = await ov_auto_coord._async_update_data()
        self.assertFalse(ov_auto_coord.degraded)
        self.assertIsNone(h_ov_clear["degraded_reason"])
        self.assertTrue(h_ov_clear["acknowledge_rejected"])
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness acknowledgement rejected",
        )

        # Merged quarantine_ambiguous + acknowledge_rejected notification copy preserves both notices.
        notifications.clear()
        ambig_coord = mod.SituarenessCoordinator(
            hass_m,
            c.validate({**cfg, "acknowledge_degraded_at": "2026-11-17T10:00:00"}),
            Store(),
            {"records": {}, "outbox": [], "initialized": True, "was_live": True},
        )
        ambig_events = collector.CollectedEvents([], 1, [], True)
        with patch.object(mod, "fetch", return_value=ambig_events):
            h_ambig = await ambig_coord._async_update_data()
        self.assertTrue(h_ambig["quarantine_ambiguous"])
        self.assertTrue(h_ambig["acknowledge_rejected"])
        merged_note = notifications["situareness_degraded"]
        self.assertEqual(merged_note["title"], "Situareness alert scope ambiguous")
        self.assertIn("acknowledge_degraded_at", merged_note["message"])
        self.assertIn("rejected", merged_note["message"])

    async def test_expired_unsent_surfacing_and_coalesced_group_save(self):
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

        now = datetime.now(timezone.utc)
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(50)],
            tts_entity=None,
        )

        def make_ev(name, offset_sec=-60):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/exp-{name}"
            for key, delta in [
                ("sent", offset_sec),
                ("effective", offset_sec),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        # Below outbox_overflow: active aged first-attempt item surfaces expired_unsent,
        # partial=True, expired outcome, and notification; ended alert does not.
        act_ev = make_ev("active-aged")
        act_decision = d.qualify(act_ev, cfg, now)
        act_fp = d.fingerprint(act_ev, act_decision)
        ended_ev = make_ev("ended-aged")
        ended_fp = d.fingerprint(ended_ev, d.qualify(ended_ev, cfg, now))
        aged_created = (now - timedelta(minutes=16)).isoformat()
        persisted_below = {
            "records": {
                act_ev["id"]: {
                    "state": "active",
                    "fingerprint": act_fp,
                    "actions": {act_fp: ["new_york_ny"]},
                    "lineage": [act_ev["id"]],
                    "cap_identity": act_ev["cap_identity"],
                    "cap_references": [],
                    "sent": act_ev["sent"],
                    "expires": act_ev["expires"],
                    "ends": act_ev["ends"],
                    "updated": now.isoformat(),
                },
                ended_ev["id"]: {
                    "state": "active",
                    "fingerprint": ended_fp,
                    "actions": {ended_fp: ["new_york_ny"]},
                    "lineage": [ended_ev["id"]],
                    "cap_identity": ended_ev["cap_identity"],
                    "cap_references": [],
                    "sent": ended_ev["sent"],
                    "expires": ended_ev["expires"],
                    "ends": ended_ev["ends"],
                    "updated": now.isoformat(),
                },
            },
            "outbox": [
                {
                    "key": "exp-active-0",
                    "incident_id": act_ev["id"],
                    "fingerprint": act_fp,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": act_ev["instruction"],
                    "source_url": act_ev["id"],
                    "attempts": 0,
                    "created": aged_created,
                },
                {
                    "key": "exp-ended-0",
                    "incident_id": ended_ev["id"],
                    "fingerprint": ended_fp,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ended_ev["instruction"],
                    "source_url": ended_ev["id"],
                    "attempts": 0,
                    "created": aged_created,
                },
            ],
            "initialized": True,
            "was_live": True,
        }
        hass = types.SimpleNamespace(data={}, services=Services())
        store_below = Store()
        coord_below = mod.SituarenessCoordinator(
            hass, cfg, store_below, persisted_below
        )
        with patch.object(mod, "fetch", return_value=[act_ev]):
            h_below = await coord_below._async_update_data()
        self.assertEqual(h_below["expired_unsent"], 1)
        self.assertTrue(h_below["partial"])
        self.assertFalse(h_below["evidence_degraded"])
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness alert targets expired unsent",
        )
        expired_outs = [
            o for o in store_below.saved[-1]["outcomes"] if o.get("expired")
        ]
        self.assertEqual(len(expired_outs), 1)
        self.assertEqual(expired_outs[0]["key"], "exp-active-0")
        self.assertFalse(expired_outs[0]["accepted"])

        # During outbox_overflow: aged target adds expired_unsent > 0 alongside capacity note.
        notifications.clear()
        ov_alerts = []
        for i in range(101):
            ev = make_ev(f"ov-{i}")
            ev["instruction"] = f"Take shelter immediately overflow zone {i}."
            ov_alerts.append(ev)
        store_ov = Store()
        coord_ov = mod.SituarenessCoordinator(
            hass,
            cfg,
            store_ov,
            {
                **persisted_below,
                "outbox": [persisted_below["outbox"][0]],
            },
        )
        with patch.object(mod, "fetch", return_value=[act_ev, *ov_alerts]):
            h_ov = await coord_ov._async_update_data()
        self.assertEqual(h_ov["degraded_reason"], "outbox_overflow")
        self.assertEqual(h_ov["expired_unsent"], 1)
        self.assertTrue(h_ov["partial"])
        ov_note = notifications["situareness_degraded"]["message"]
        self.assertIn("~1,500 attempts", ov_note)
        self.assertIn("1 queued target(s) expired unsent", ov_note)
        self.assertTrue(
            any(
                o.get("key") == "exp-active-0" and o.get("expired")
                for o in store_ov.saved[0]["outcomes"]
            )
        )

        # Coalesced per-group save: a 10-target slice with 1 expired + 9 deliverable items
        # issues ONE pre-batch save + ONE coalesced post-group save (2 total, not 3).
        class PollExpiryClock:
            calls = 0

            @classmethod
            def now(cls, tz):
                cls.calls += 1
                # First call is initial poll `now`; subsequent calls advance 20s (<30s deadline)
                # so the 14m50s item crosses 15m MAX_AGE while the 5m items stay deliverable.
                if cls.calls <= 1:
                    return now
                return now + timedelta(seconds=20)

        batch_ev = make_ev("coalesce")
        batch_fp = d.fingerprint(batch_ev, d.qualify(batch_ev, cfg, now))
        fresh_created = (now - timedelta(minutes=5)).isoformat()
        about_to_expire = (now - timedelta(minutes=14, seconds=50)).isoformat()
        slice_outbox = [
            {
                "key": "slice-exp",
                "incident_id": batch_ev["id"],
                "fingerprint": batch_fp,
                "kind": "phone",
                "target": "mobile_app_0",
                "location": None,
                "affected_names": ["New York"],
                "event": "Tornado Warning",
                "instruction": batch_ev["instruction"],
                "source_url": batch_ev["id"],
                "attempts": 0,
                "created": about_to_expire,
            }
        ] + [
            {
                "key": f"slice-ok-{i}",
                "incident_id": batch_ev["id"],
                "fingerprint": batch_fp,
                "kind": "phone",
                "target": f"mobile_app_{i}",
                "location": None,
                "affected_names": ["New York"],
                "event": "Tornado Warning",
                "instruction": batch_ev["instruction"],
                "source_url": batch_ev["id"],
                "attempts": 0,
                "created": fresh_created,
            }
            for i in range(1, 10)
        ]
        batch_store = Store()
        batch_services = Services()
        batch_coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=batch_services),
            {**cfg, "phones": [f"mobile_app_{i}" for i in range(10)]},
            batch_store,
            {
                "records": {
                    batch_ev["id"]: {
                        "state": "active",
                        "fingerprint": batch_fp,
                        "actions": {batch_fp: ["new_york_ny"]},
                        "lineage": [batch_ev["id"]],
                        "cap_identity": batch_ev["cap_identity"],
                        "cap_references": [],
                        "sent": batch_ev["sent"],
                        "expires": batch_ev["expires"],
                        "ends": batch_ev["ends"],
                        "updated": now.isoformat(),
                    }
                },
                "outbox": slice_outbox,
                "initialized": True,
                "was_live": True,
            },
        )
        PollExpiryClock.calls = 0
        with (
            patch.object(mod, "datetime", PollExpiryClock),
            patch.object(mod, "fetch", return_value=[batch_ev]),
        ):
            h_coal = await batch_coord._async_update_data()
        self.assertEqual(len(batch_store.saved), 2)
        self.assertEqual(h_coal["delivery_attempts"], 9)
        self.assertEqual(h_coal["expired_unsent"], 1)
        self.assertTrue(h_coal["partial"])
        self.assertEqual(len(batch_services.calls), 9)
        self.assertEqual(batch_coord.outbox, [])
        last_outcomes = batch_store.saved[-1]["outcomes"]
        self.assertEqual(len(last_outcomes), 10)
        self.assertTrue(
            any(o["key"] == "slice-exp" and o.get("expired") for o in last_outcomes)
        )

    async def test_healthy_snapshot_handles_evicted_ineligible_records_and_wraps_errors(
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
        cfg = config()
        cfg.update(live_enabled=False, commissioning_passed=False, tts_entity=None)

        def make_ineligible(i):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/inelig-{i:04d}"
            ev["event"] = "Flood Watch"
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        events = [make_ineligible(i) for i in range(1005)]
        hass = types.SimpleNamespace(data={}, services=Services())
        store = Store()
        coord = mod.SituarenessCoordinator(hass, cfg, store, None)
        with patch.object(mod, "fetch", return_value=events):
            health = await coord._async_update_data()

        self.assertEqual(health["event_count"], 1005)
        self.assertEqual(health["active_count"], 0)
        self.assertFalse(health["evidence_degraded"])
        self.assertLessEqual(len(store.saved[-1]["records"]), 1000)

        # Direct snapshot call where leading candidate events are absent from records.
        snap = coord._healthy_snapshot(
            events[:5],
            events[:5],
            {},
            [],
            now,
            0,
            0,
            False,
            deliverable=0,
        )
        self.assertEqual(snap["events"][0]["state"], "ineligible")
        self.assertTrue(snap["events"][0]["reasons"])

        # Unexpected exception inside _healthy_snapshot is wrapped as UpdateFailed.
        with (
            patch.object(mod, "fetch", return_value=events[:1]),
            patch.object(
                coord, "_healthy_snapshot", side_effect=RuntimeError("snapshot boom")
            ),
        ):
            with self.assertRaises(UpdateFailed):
                await coord._async_update_data()

        # End-to-end collector.fetch -> _async_update_data() with >1,000 distinct ineligible features.
        import json
        from test_domain import Response, Session

        raw_features = []
        for i in range(1005):
            raw = feature()
            cap_id = f"urn:oid:e2e-inelig-{i:04d}"
            raw["id"] = f"https://api.weather.gov/alerts/{cap_id}"
            raw["properties"] = {
                **raw["properties"],
                "id": cap_id,
                "event": "Flood Watch",
            }
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                raw["properties"][key] = (now + timedelta(seconds=delta)).isoformat()
            raw_features.append(raw)
        raw_payload = json.dumps(
            {"type": "FeatureCollection", "features": raw_features}
        ).encode()
        e2e_cfg = {**cfg, "states": ["NY"]}
        e2e_store = Store()
        e2e_coord = mod.SituarenessCoordinator(hass, e2e_cfg, e2e_store, None)
        e2e_coord.session = Session(Response(raw_payload))
        e2e_health = await e2e_coord._async_update_data()
        self.assertEqual(e2e_health["event_count"], 1005)
        self.assertEqual(e2e_health["source_feature_count"], 1005)
        self.assertEqual(e2e_health["active_count"], 0)
        self.assertFalse(e2e_health["evidence_degraded"])
        self.assertLessEqual(len(e2e_store.saved[-1]["records"]), 1000)

    async def test_expired_unsent_persisted_latch_notification_and_acknowledgement(
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
        create_calls = []

        def fake_create(hass, msg, title=None, notification_id=None):
            create_calls.append({"message": msg, "title": title})
            notifications[notification_id] = {"message": msg, "title": title}

        fake_pn = types.SimpleNamespace(
            async_create=fake_create,
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

        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)

        class MutableClock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        MutableClock.current = now

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_0"],
            tts_entity=None,
        )

        def make_ev(name):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/pers-{name}"
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 8 * 86400),
                ("ends", 8 * 86400),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        ev1 = make_ev("one")
        fp1 = d.fingerprint(ev1, d.qualify(ev1, cfg, now))
        aged_created = (now - timedelta(minutes=16)).isoformat()
        persisted_initial = {
            "records": {
                ev1["id"]: {
                    "state": "active",
                    "fingerprint": fp1,
                    "actions": {fp1: ["new_york_ny"]},
                    "lineage": [ev1["id"]],
                    "cap_identity": ev1["cap_identity"],
                    "cap_references": [],
                    "sent": ev1["sent"],
                    "expires": ev1["expires"],
                    "ends": ev1["ends"],
                    "updated": now.isoformat(),
                }
            },
            "outbox": [
                {
                    "key": "exp-persist-1",
                    "incident_id": ev1["id"],
                    "fingerprint": fp1,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev1["instruction"],
                    "source_url": ev1["id"],
                    "attempts": 0,
                    "created": aged_created,
                }
            ],
            "initialized": True,
            "was_live": True,
        }
        hass = types.SimpleNamespace(data={}, services=Services())
        store1 = Store()

        with patch.object(mod, "datetime", MutableClock):
            coord1 = mod.SituarenessCoordinator(hass, cfg, store1, persisted_initial)
            with patch.object(mod, "fetch", return_value=[ev1]):
                h1 = await coord1._async_update_data()
            self.assertEqual(h1["expired_unsent"], 1)
            self.assertTrue(h1["partial"])
            saved1 = store1.saved[-1]
            self.assertEqual(saved1["expired_unsent"], 1)
            self.assertEqual(saved1["expired_unsent_at"], now.isoformat())
            self.assertEqual(
                saved1["expired_unsent_until"], (now + timedelta(days=7)).isoformat()
            )
            self.assertEqual(len(create_calls), 1)
            self.assertIn(
                "1 queued qualifying alert target(s) aged past",
                notifications["situareness_degraded"]["message"],
            )

            # Subsequent clean poll keeps latch without churning async_create.
            MutableClock.current = now + timedelta(minutes=5)
            with patch.object(mod, "fetch", return_value=[ev1]):
                h2 = await coord1._async_update_data()
            self.assertEqual(h2["expired_unsent"], 1)
            self.assertTrue(h2["partial"])
            self.assertEqual(len(create_calls), 1)

            # Reload preserves latch; another expiration increments to 2 and updates notification.
            MutableClock.current = now + timedelta(hours=1)
            saved_with_second_exp = {
                **store1.saved[-1],
                "outbox": [
                    {
                        "key": "exp-persist-2",
                        "incident_id": ev1["id"],
                        "fingerprint": fp1,
                        "kind": "phone",
                        "target": "mobile_app_0",
                        "location": None,
                        "affected_names": ["New York"],
                        "event": "Tornado Warning",
                        "instruction": ev1["instruction"],
                        "source_url": ev1["id"],
                        "attempts": 0,
                        "created": (
                            MutableClock.current - timedelta(minutes=16)
                        ).isoformat(),
                    }
                ],
            }
            store2 = Store()
            create_calls.clear()
            coord2 = mod.SituarenessCoordinator(
                hass, cfg, store2, saved_with_second_exp
            )
            self.assertEqual(coord2.expired_unsent, 1)
            self.assertEqual(coord2._stopped_health()["expired_unsent"], 1)
            self.assertTrue(coord2._stopped_health()["partial"])
            self.assertEqual(len(create_calls), 1)

            with patch.object(mod, "fetch", return_value=[ev1]):
                h3 = await coord2._async_update_data()
            self.assertEqual(h3["expired_unsent"], 2)
            self.assertEqual(store2.saved[-1]["expired_unsent"], 2)
            self.assertEqual(
                store2.saved[-1]["expired_unsent_at"],
                (now + timedelta(hours=1)).isoformat(),
            )
            self.assertEqual(len(create_calls), 2)
            self.assertIn(
                "2 queued qualifying alert target(s) aged past",
                notifications["situareness_degraded"]["message"],
            )

            # Another clean poll at count=2 does not churn or alter expired_unsent_at.
            MutableClock.current = now + timedelta(hours=2)
            with patch.object(mod, "fetch", return_value=[ev1]):
                h4 = await coord2._async_update_data()
            self.assertEqual(h4["expired_unsent"], 2)
            self.assertEqual(
                store2.saved[-1]["expired_unsent_at"],
                (now + timedelta(hours=1)).isoformat(),
            )
            self.assertEqual(len(create_calls), 2)

            # Early/invalid acknowledge_degraded_at (including between 1st and 2nd expiration) is rejected.
            persisted_two = store2.saved[-1]
            entry_updates = []
            entry_cfg = {
                **cfg,
                "acknowledge_degraded_at": (now + timedelta(minutes=30)).isoformat(),
            }
            entry_obj = types.SimpleNamespace(entry_id="e-exp", data={})
            hass_with_entries = types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda entry, data: (
                        setattr(entry, "data", data),
                        entry_updates.append(data),
                    )
                ),
            )
            coord_rej = mod.SituarenessCoordinator(
                hass_with_entries, entry_cfg, Store(), persisted_two, entry=entry_obj
            )
            self.assertTrue(coord_rej.acknowledge_rejected)
            self.assertEqual(coord_rej.expired_unsent, 2)
            rej_msg = notifications["situareness_degraded"]["message"]
            self.assertIn("2 queued target(s) expired unsent", rej_msg)
            self.assertIn(
                "earlier than expired_unsent_at, missing expired_unsent_at, or already consumed",
                rej_msg,
            )
            self.assertIn(
                "expired_unsent_at <= acknowledge_degraded_at <= reload time", rej_msg
            )
            coord_rej._sync_degraded_notification(quarantine_ambiguous=True)
            self.assertIn(
                "earlier than expired_unsent_at, or already consumed",
                notifications["situareness_degraded"]["message"],
            )

            # Valid acknowledge_degraded_at >= latest expired_unsent_at while healthy clears latch
            # and commits consumption together on Poll 1 save.
            ack_valid = (now + timedelta(minutes=90)).isoformat()
            entry_ok = types.SimpleNamespace(entry_id="e-exp-ok", data={})
            store_ok = Store()
            coord_ok = mod.SituarenessCoordinator(
                hass_with_entries,
                {**cfg, "acknowledge_degraded_at": ack_valid},
                store_ok,
                persisted_two,
                entry=entry_ok,
            )
            self.assertFalse(coord_ok.acknowledge_rejected)
            self.assertEqual(coord_ok.expired_unsent, 0)
            self.assertIsNone(coord_ok.expired_unsent_at)
            self.assertIsNone(coord_ok.expired_unsent_until)
            self.assertFalse(coord_ok._stopped_health()["partial"])
            self.assertNotIn("situareness_degraded", notifications)
            with patch.object(mod, "fetch", return_value=[ev1]):
                h_ok = await coord_ok._async_update_data()
            self.assertEqual(h_ok["expired_unsent"], 0)
            self.assertFalse(h_ok["partial"])
            self.assertEqual(store_ok.saved[-1]["expired_unsent"], 0)
            self.assertIn(ack_valid, entry_ok.data["consumed_acknowledgements"])

            # 7-day auto-clear on poll and on reload.
            MutableClock.current = now + timedelta(days=7, hours=2)
            coord_expire_poll = mod.SituarenessCoordinator(
                hass, cfg, Store(), persisted_two
            )
            # Load at +7d 2h already clears because expired_unsent_until was +7d 1h.
            self.assertEqual(coord_expire_poll.expired_unsent, 0)

            MutableClock.current = now + timedelta(days=7, minutes=30)
            store_poll_exp = Store()
            coord_expire_during_poll = mod.SituarenessCoordinator(
                hass, cfg, store_poll_exp, persisted_two
            )
            self.assertEqual(coord_expire_during_poll.expired_unsent, 2)
            MutableClock.current = now + timedelta(days=7, hours=2)
            with patch.object(mod, "fetch", return_value=[ev1]):
                h_after_horizon = await coord_expire_during_poll._async_update_data()
            self.assertEqual(h_after_horizon["expired_unsent"], 0)
            self.assertFalse(h_after_horizon["partial"])
            self.assertEqual(store_poll_exp.saved[-1]["expired_unsent"], 0)

        # Invalid persisted expired_unsent types and unparseable record.updated fail store validation.
        for bad_payload in (
            {"records": {}, "expired_unsent": True},
            {"records": {}, "expired_unsent": -1},
            {"records": {}, "expired_unsent_at": "not-a-date"},
            {"records": {}, "expired_unsent_until": "2026-11-17T12:00:00"},
            {"records": {"id-1": {"state": "active", "updated": "not-a-timestamp"}}},
        ):
            self.assertFalse(mod._valid_persisted_store(bad_payload))
            bad_coord = mod.SituarenessCoordinator(hass, cfg, Store(), bad_payload)
            self.assertEqual(bad_coord.degraded_reason, "malformed_store")
            self.assertEqual(bad_coord.expired_unsent, 0)

    async def test_ack_cleared_reason_tracks_cleared_reason_only(self):
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
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_0"],
            tts_entity=None,
            acknowledge_degraded_at=(now - timedelta(minutes=5)).isoformat(),
        )
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda entry, data: setattr(entry, "data", data)
            ),
        )
        persisted_jl = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        coord = mod.SituarenessCoordinator(
            hass,
            cfg,
            Store(),
            persisted_jl,
            entry=types.SimpleNamespace(entry_id="ack-reason", data={}),
        )
        self.assertFalse(coord.degraded)
        self.assertFalse(coord.acknowledge_rejected)
        self.assertEqual(coord._ack_cleared_reason, "journal_lost")

        # Next poll triggers a DIFFERENT degraded reason -> must NOT set acknowledge_rejected=True.
        base_ev = d.normalize(feature())
        base_ev["id"] = "https://api.weather.gov/alerts/ack-diff-base"
        for key, delta in [
            ("sent", -300),
            ("effective", -300),
            ("onset", -60),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            base_ev[key] = (now + timedelta(seconds=delta)).isoformat()
        base_ev = cohere(base_ev)
        conflict_feed = collector.CollectedEvents(
            [base_ev], 2, [], False, conflicting_cancellation=True
        )
        with patch.object(mod, "fetch", return_value=conflict_feed):
            h_diff = await coord._async_update_data()
        self.assertEqual(h_diff["degraded_reason"], "conflicting_cancellation")
        self.assertFalse(h_diff["acknowledge_rejected"])

        # Same-reason re-latch DOES set acknowledge_rejected=True.
        persisted_same = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "conflicting_cancellation",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        coord_same = mod.SituarenessCoordinator(
            hass,
            {
                **cfg,
                "acknowledge_degraded_at": (now - timedelta(minutes=4)).isoformat(),
            },
            Store(),
            persisted_same,
            entry=types.SimpleNamespace(entry_id="ack-same", data={}),
        )
        with patch.object(mod, "fetch", return_value=conflict_feed):
            h_same = await coord_same._async_update_data()
        self.assertEqual(h_same["degraded_reason"], "conflicting_cancellation")
        self.assertTrue(h_same["acknowledge_rejected"])

    async def test_feed_cancellation_priority_over_concurrent_overflow(self):
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

        now = datetime(2026, 11, 17, 15, 0, tzinfo=timezone.utc)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now

        cfg = config()
        cfg.update(live_enabled=False, commissioning_passed=False, tts_entity=None)
        hass = types.SimpleNamespace(data={}, services=Services())

        base_ev = d.normalize(feature())
        base_ev["id"] = "https://api.weather.gov/alerts/prio-base"
        for key, delta in [
            ("sent", -300),
            ("effective", -300),
            ("onset", -60),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            base_ev[key] = (now + timedelta(seconds=delta)).isoformat()
        base_ev = cohere(base_ev)
        conflict_feed = collector.CollectedEvents(
            [base_ev], 2, [], False, conflicting_cancellation=True
        )

        long_horizon = now + timedelta(days=10)
        long_overflow = d.CancellationEvidenceOverflow(
            "protected overflow",
            dropped_horizon=long_horizon,
            records={},
            plans=[],
        )
        store = Store()
        coord = mod.SituarenessCoordinator(hass, cfg, store, None)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=conflict_feed),
            patch.object(mod, "reconcile", side_effect=long_overflow),
        ):
            h1 = await coord._async_update_data()

        self.assertEqual(h1["degraded_reason"], "conflicting_cancellation")
        self.assertEqual(h1["degraded_until"], long_horizon.isoformat())
        self.assertEqual(h1["degraded_at"], now.isoformat())
        self.assertIn(
            "or the latest evicted component horizon if history also overflowed",
            notifications["situareness_degraded"]["message"],
        )

        # Second concurrent poll preserves degraded_reason and degraded_at cleanly.
        Clock.current = now + timedelta(minutes=10)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=conflict_feed),
            patch.object(mod, "reconcile", side_effect=long_overflow),
        ):
            h2 = await coord._async_update_data()
        self.assertEqual(h2["degraded_reason"], "conflicting_cancellation")
        self.assertEqual(h2["degraded_at"], now.isoformat())

        # Third poll where conflicting_cancellation continues WITHOUT overflow still retains
        # degraded_reason, stable degraded_at, and the overflow-extended degraded_until.
        Clock.current = now + timedelta(minutes=20)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=conflict_feed),
        ):
            h3 = await coord._async_update_data()
        self.assertEqual(h3["degraded_reason"], "conflicting_cancellation")
        self.assertEqual(h3["degraded_at"], now.isoformat())
        self.assertEqual(h3["degraded_until"], long_horizon.isoformat())

        # Short overflow horizon (< 7 days) with malformed_cancellation keeps 7-day floor.
        mal_cancel = d.normalize(feature())
        mal_cancel["id"] = "https://api.weather.gov/alerts/prio-mal-cancel"
        mal_cancel["message_type"] = "Cancel"
        mal_cancel["references"] = []
        mal_cancel["reference_identities"] = []
        mal_cancel["sent"] = (now - timedelta(seconds=10)).isoformat()
        mal_cancel["effective"] = (now - timedelta(seconds=10)).isoformat()
        mal_cancel["onset"] = (now - timedelta(seconds=10)).isoformat()
        mal_cancel["expires"] = (now + timedelta(seconds=1800)).isoformat()
        mal_cancel["ends"] = (now + timedelta(seconds=1800)).isoformat()

        short_overflow = d.CancellationEvidenceOverflow(
            "short overflow",
            dropped_horizon=now + timedelta(hours=1),
            records={},
            plans=[],
        )
        Clock.current = now
        coord_short = mod.SituarenessCoordinator(hass, cfg, Store(), None)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[mal_cancel]),
            patch.object(mod, "reconcile", side_effect=short_overflow),
        ):
            h_short = await coord_short._async_update_data()
        self.assertEqual(h_short["degraded_reason"], "malformed_cancellation")
        self.assertEqual(
            h_short["degraded_until"], (now + timedelta(days=7)).isoformat()
        )

    async def test_valid_persisted_store_rejects_missing_or_unknown_record_states(self):
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

        for bad_record in (
            {"updated": "2026-11-17T00:00:00+00:00"},
            {"state": "unknown_state"},
            {"state": 123},
            {"state": "active", "prior_state": "bad_prior"},
            {"state": "active", "prior_state": 42},
        ):
            self.assertFalse(
                mod._valid_persisted_store({"records": {"id-1": bad_record}})
            )

        self.assertTrue(
            mod._valid_persisted_store(
                {
                    "records": {
                        "id-1": {
                            "state": "active",
                            "prior_state": None,
                            "updated": "2026-11-17T00:00:00+00:00",
                        },
                        "id-2": {
                            "state": "unconfirmed",
                            "prior_state": "active",
                        },
                    }
                }
            )
        )

    async def test_expired_unsent_captures_clock_rollback_and_deconfigured_active_targets(
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

        now = datetime(2026, 11, 17, 14, 0, tzinfo=timezone.utc)

        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_current"],
            tts_entity=None,
        )
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/inv-active"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        ev = cohere(ev)
        fp = d.fingerprint(ev, d.qualify(ev, cfg, now))

        persisted = {
            "records": {
                ev["id"]: {
                    "state": "active",
                    "fingerprint": fp,
                    "actions": {fp: ["new_york_ny"]},
                    "lineage": [ev["id"]],
                    "cap_identity": ev["cap_identity"],
                    "cap_references": [],
                    "sent": ev["sent"],
                    "expires": ev["expires"],
                    "ends": ev["ends"],
                    "updated": now.isoformat(),
                }
            },
            "outbox": [
                {
                    "key": "future-created-key",
                    "incident_id": ev["id"],
                    "fingerprint": fp,
                    "kind": "phone",
                    "target": "mobile_app_current",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev["instruction"],
                    "source_url": ev["id"],
                    "attempts": 0,
                    "created": (now + timedelta(minutes=2)).isoformat(),
                },
                {
                    "key": "removed-target-key",
                    "incident_id": ev["id"],
                    "fingerprint": fp,
                    "kind": "phone",
                    "target": "mobile_app_removed",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev["instruction"],
                    "source_url": ev["id"],
                    "attempts": 0,
                    "created": (now - timedelta(minutes=1)).isoformat(),
                },
            ],
            "initialized": True,
            "was_live": True,
        }
        hass = types.SimpleNamespace(data={}, services=Services())
        store = Store()
        coord = mod.SituarenessCoordinator(hass, cfg, store, persisted)
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            health = await coord._async_update_data()

        self.assertEqual(health["expired_unsent"], 2)
        self.assertTrue(health["partial"])
        self.assertEqual(
            store.saved[-1]["expired_unsent_reasons"],
            ["clock_rollback", "target_removed"],
        )
        expired_outcomes = [o for o in store.saved[-1]["outcomes"] if o.get("expired")]
        self.assertEqual(
            {o["key"]: o["reason"] for o in expired_outcomes},
            {
                "future-created-key": "clock_rollback",
                "removed-target-key": "target_removed",
            },
        )
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness alert targets expired unsent",
        )
        msg = notifications["situareness_degraded"]["message"]
        self.assertIn("2 queued qualifying alert target(s)", msg)
        self.assertIn(
            "invalidated by backward clock rollback (created > now); dropped after target removal from situareness.json",
            msg,
        )

    async def test_corrupt_backup_cleanup_retries_and_missing_store_enters_journal_lost(
        self,
    ):
        import asyncio
        import tempfile

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

        with tempfile.TemporaryDirectory() as tmp:
            storage_dir = Path(tmp) / ".storage"
            storage_dir.mkdir()
            prefix = f"{mod.DOMAIN}.entry-corrupt"
            corrupt_path = storage_dir / f"{prefix}.corrupt.20261117"
            corrupt_path.write_text("{broken", encoding="utf-8")

            # unlink OSError logs warning and returns False so coordinator retries cleanup.
            with (
                patch.object(Path, "unlink", side_effect=OSError("permission denied")),
                self.assertLogs(mod._LOGGER, level="WARNING") as cm,
            ):
                ok = mod._clear_corrupt_store_backups(storage_dir, prefix)
            self.assertFalse(ok)
            self.assertTrue(corrupt_path.exists())
            self.assertIn("Could not remove corrupt store backup", cm.output[0])

            async def run_exec(fn, *args):
                return fn(*args)

            entry = types.SimpleNamespace(
                entry_id="entry-corrupt",
                data={"journal_initialized": True},
            )
            hass = types.SimpleNamespace(
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
            cfg = config()
            store = Store()
            coord = mod.SituarenessCoordinator(
                hass, cfg, store, {}, entry=entry, has_corrupt_backup=True
            )
            self.assertTrue(coord._needs_corrupt_cleanup)
            with patch.object(mod, "_clear_corrupt_store_backups", return_value=False):
                await coord._save({}, [], [])
            self.assertTrue(coord._needs_corrupt_cleanup)
            await coord._save({}, [], [])
            self.assertFalse(coord._needs_corrupt_cleanup)
            self.assertFalse(corrupt_path.exists())

            # Missing main store on already-recovered initialized entry + stale .corrupt.* backup
            # enters journal_lost (not malformed_store) while keeping _needs_corrupt_cleanup=True.
            stale_corrupt = storage_dir / f"{mod.DOMAIN}.recovered-lost.corrupt.1"
            stale_corrupt.write_text("{stale", encoding="utf-8")
            (Path(tmp) / "situareness.json").write_text("{}", encoding="utf-8")
            recovered_entry = types.SimpleNamespace(
                entry_id="recovered-lost",
                data={"journal_initialized": True},
            )

            class NoneStore(Store):
                async def async_load(self):
                    return None

            class CapturingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    self.data = await self._update_once()

            with (
                patch.object(mod, "Store", NoneStore),
                patch.object(mod, "SituarenessCoordinator", CapturingCoordinator),
                patch.object(mod, "fetch", return_value=[]),
            ):
                await mod.async_setup_entry(hass, recovered_entry)
            lost_coord = hass.data[mod.DOMAIN][recovered_entry.entry_id]
            self.assertEqual(lost_coord.degraded_reason, "journal_lost")
            self.assertFalse(stale_corrupt.exists())

    async def test_journal_lost_at_future_reset_and_near_max_timestamp_clamped(self):
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

        now = datetime(2026, 11, 17, 16, 0, tzinfo=timezone.utc)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now
        cfg = config()
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        future_entry = types.SimpleNamespace(
            entry_id="jl-future",
            data={
                "journal_initialized": True,
                "journal_lost_at": (now + timedelta(days=2)).isoformat(),
                "malformed_store_at": "2026-11-10T00:00:00+00:00",
            },
        )
        with patch.object(mod, "datetime", Clock):
            coord_future = mod.SituarenessCoordinator(
                hass, cfg, Store(), None, entry=future_entry
            )
        self.assertEqual(coord_future.degraded_reason, "journal_lost")
        self.assertEqual(coord_future.degraded_at, now.isoformat())
        self.assertEqual(
            coord_future.degraded_until, (now + timedelta(days=7)).isoformat()
        )
        self.assertEqual(future_entry.data["journal_lost_at"], now.isoformat())
        self.assertNotIn("malformed_store_at", future_entry.data)

        # Near MAX_TIMESTAMP detect_now clamps degraded_until to MAX_TIMESTAMP without OverflowError.
        Clock.current = mod.MAX_TIMESTAMP - timedelta(days=2)
        near_max_entry = types.SimpleNamespace(
            entry_id="jl-max",
            data={"journal_initialized": True},
        )
        with patch.object(mod, "datetime", Clock):
            coord_max = mod.SituarenessCoordinator(
                hass, cfg, Store(), None, entry=near_max_entry
            )
        self.assertEqual(coord_max.degraded_reason, "journal_lost")
        self.assertEqual(coord_max.degraded_until, mod.MAX_TIMESTAMP.isoformat())

    async def test_empty_store_replacement_clears_corrupt_backups_and_notification_mentions_corrupt_backups(
        self,
    ):
        import asyncio
        import tempfile

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

        cfg = config()
        mal_coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()), cfg, Store(), ["bad"]
        )
        self.assertEqual(mal_coord.degraded_reason, "malformed_store")
        self.assertIn(
            ".corrupt.* backups",
            notifications["situareness_degraded"]["message"],
        )

        async def run_exec(fn, *args):
            return fn(*args)

        with tempfile.TemporaryDirectory() as tmp:
            storage_dir = Path(tmp) / ".storage"
            storage_dir.mkdir()
            (Path(tmp) / "situareness.json").write_text("{}", encoding="utf-8")

            # Case A: "{}" replacement after malformed_store_at in entry.data deletes stale .corrupt.* on Poll 1.
            backup_a = storage_dir / f"{mod.DOMAIN}.rep-entry-a.corrupt.1"
            backup_a.write_text("{corrupt", encoding="utf-8")
            entry_a = types.SimpleNamespace(
                entry_id="rep-entry-a",
                data={
                    "journal_initialized": True,
                    "malformed_store_at": "2026-11-17T10:00:00+00:00",
                },
            )
            hass = types.SimpleNamespace(
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
            store_a = Store()
            coord_a = mod.SituarenessCoordinator(hass, cfg, store_a, {}, entry=entry_a)
            self.assertEqual(coord_a.degraded_reason, "journal_lost")
            self.assertTrue(coord_a._needs_corrupt_cleanup)
            with patch.object(mod, "fetch", return_value=[]):
                await coord_a._async_update_data()
            self.assertFalse(coord_a._needs_corrupt_cleanup)
            self.assertFalse(backup_a.exists())
            self.assertNotIn("malformed_store_at", entry_a.data)

            # Case B: async_setup_entry with persisted == {} and .corrupt.* backup (without malformed_store_at)
            # preserves journal_lost and deletes stale .corrupt.* backup on first refresh.
            backup_b = storage_dir / f"{mod.DOMAIN}.rep-entry-b.corrupt.2"
            backup_b.write_text("{corrupt", encoding="utf-8")
            entry_b = types.SimpleNamespace(
                entry_id="rep-entry-b",
                data={"journal_initialized": True},
            )

            class EmptyDictStore(Store):
                async def async_load(self):
                    return {}

            class CapturingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    self.data = await self._update_once()

            with (
                patch.object(mod, "Store", EmptyDictStore),
                patch.object(mod, "SituarenessCoordinator", CapturingCoordinator),
                patch.object(mod, "fetch", return_value=[]),
            ):
                await mod.async_setup_entry(hass, entry_b)
            coord_b = hass.data[mod.DOMAIN][entry_b.entry_id]
            self.assertEqual(coord_b.degraded_reason, "journal_lost")
            self.assertFalse(coord_b._needs_corrupt_cleanup)
            self.assertFalse(backup_b.exists())

    async def test_near_capacity_pre_drain_uses_remaining_budget_for_new_targets(self):
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

        now = datetime(2026, 11, 17, 17, 0, tzinfo=timezone.utc)

        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        cfg = config()
        cfg["locations"] = {
            "new_york_ny": {"point": [0.5, 0.5], "speakers": []},
            "washington_dc": {
                "point": [3.0, 3.0],
                "speakers": [f"media_player.dc_{i}" for i in range(4980)],
            },
            "retry_zone": {
                "point": [2.5, 2.5],
                "speakers": [f"media_player.retry_{i}" for i in range(10)],
            },
        }
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(10)],
            tts_entity="tts.home",
        )

        def make_ev(name, geometry=None):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/cap-{name}"
            if geometry is not None:
                ev["geometry"] = geometry
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        dc_poly = {
            "type": "Polygon",
            "coordinates": [
                [[2.9, 2.9], [3.1, 2.9], [3.1, 3.1], [2.9, 3.1], [2.9, 2.9]]
            ],
        }
        retry_poly = {
            "type": "Polygon",
            "coordinates": [
                [[2.2, 2.2], [2.8, 2.2], [2.8, 2.8], [2.2, 2.8], [2.2, 2.2]]
            ],
        }
        susp_ev = make_ev("susp", geometry=dc_poly)
        susp_fp = d.fingerprint(susp_ev, d.qualify(susp_ev, cfg, now))
        retry_ev = make_ev("retry", geometry=retry_poly)
        retry_fp = d.fingerprint(retry_ev, d.qualify(retry_ev, cfg, now))
        new_ev = make_ev("new")

        fresh = (now - timedelta(minutes=2)).isoformat()
        suspended_items = [
            {
                "key": f"susp-{i}",
                "incident_id": susp_ev["id"],
                "fingerprint": susp_fp,
                "kind": "speaker",
                "target": f"media_player.dc_{i}",
                "location": "washington_dc",
                "affected_names": ["washington_dc"],
                "event": "Tornado Warning",
                "instruction": susp_ev["instruction"],
                "source_url": susp_ev["id"],
                "attempts": 0,
                "created": fresh,
            }
            for i in range(4980)
        ]
        retry_items = [
            {
                "key": f"retry-p-{i}",
                "incident_id": retry_ev["id"],
                "fingerprint": retry_fp,
                "kind": "phone",
                "target": f"mobile_app_{i}",
                "location": None,
                "affected_names": ["retry_zone"],
                "event": "Tornado Warning",
                "instruction": retry_ev["instruction"],
                "source_url": retry_ev["id"],
                "attempts": 1,
                "created": fresh,
            }
            for i in range(10)
        ] + [
            {
                "key": f"retry-s-{i}",
                "incident_id": retry_ev["id"],
                "fingerprint": retry_fp,
                "kind": "speaker",
                "target": f"media_player.retry_{i}",
                "location": "retry_zone",
                "affected_names": ["retry_zone"],
                "event": "Tornado Warning",
                "instruction": retry_ev["instruction"],
                "source_url": retry_ev["id"],
                "attempts": 1,
                "created": fresh,
            }
            for i in range(10)
        ]
        persisted = {
            "records": {
                susp_ev["id"]: {
                    "state": "ended_or_absent",
                    "prior_state": "active",
                    "fingerprint": susp_fp,
                    "actions": {susp_fp: ["washington_dc"]},
                    "lineage": [susp_ev["id"]],
                    "cap_identity": susp_ev["cap_identity"],
                    "cap_references": [],
                    "sent": susp_ev["sent"],
                    "expires": susp_ev["expires"],
                    "ends": susp_ev["ends"],
                    "inactive_since": fresh,
                    "updated": fresh,
                },
                retry_ev["id"]: {
                    "state": "active",
                    "fingerprint": retry_fp,
                    "actions": {retry_fp: ["retry_zone"]},
                    "lineage": [retry_ev["id"]],
                    "cap_identity": retry_ev["cap_identity"],
                    "cap_references": [],
                    "sent": retry_ev["sent"],
                    "expires": retry_ev["expires"],
                    "ends": retry_ev["ends"],
                    "updated": fresh,
                },
            },
            "outbox": suspended_items + retry_items,
            "initialized": True,
            "was_live": True,
        }
        services = Services()
        hass = types.SimpleNamespace(data={}, services=services)
        store = Store()
        coord = mod.SituarenessCoordinator(hass, cfg, store, persisted)
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[retry_ev, new_ev]),
        ):
            health = await coord._async_update_data()

        self.assertIsNone(health["degraded_reason"])
        self.assertEqual(health["delivery_attempts"], 30)
        self.assertEqual(health["delivery_failures"], 0)
        self.assertEqual(len(coord.outbox), 4980)
        self.assertEqual(len(services.calls), 30)
        self.assertTrue(
            any(
                e["id"] == new_ev["id"] and e["state"] == "active"
                for e in health["events"]
            )
        )

        # Failed pre-drain retries are NOT re-attempted a second time in the same poll.
        class FailRetryServices:
            def __init__(self):
                self.calls = []

            async def async_call(self, *args, **kwargs):
                self.calls.append(args)
                data = args[2]
                if data.get("data", {}).get("url") == retry_ev["id"] or data.get(
                    "media_player_entity_id", ""
                ).startswith("media_player.retry_"):
                    raise OSError("retry channel offline")

        fail_services = FailRetryServices()
        fail_coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=fail_services),
            cfg,
            Store(),
            persisted,
        )
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[retry_ev, new_ev]),
        ):
            fail_health = await fail_coord._async_update_data()
        # Each of the 20 retry items is attempted ONCE (20 attempts, 20 failures -> attempts == 2),
        # never retried a second time in the same poll even though attempts < 100 and plans was non-empty.
        self.assertEqual(fail_health["degraded_reason"], "outbox_overflow")
        self.assertEqual(fail_health["delivery_attempts"], 20)
        self.assertEqual(fail_health["delivery_failures"], 20)
        self.assertEqual(fail_health["withheld_count"], 1)
        self.assertEqual(len(fail_services.calls), 20)
        self.assertEqual(
            [
                item["attempts"]
                for item in fail_coord.outbox
                if item["incident_id"] == retry_ev["id"]
            ],
            [2] * 20,
        )

    async def test_async_unload_entry_dismisses_notification_once(self):
        import asyncio

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        dismiss_calls = []
        fake_pn = types.SimpleNamespace(
            async_create=lambda *args, **kwargs: None,
            async_dismiss=lambda hass, notification_id: dismiss_calls.append(
                notification_id
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

        entry = types.SimpleNamespace(entry_id="unload-once", data={})
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_unload_platforms=lambda ent, platforms: asyncio.sleep(
                    0, result=True
                )
            ),
        )
        coord = mod.SituarenessCoordinator(hass, config(), Store(), None, entry=entry)
        hass.data[mod.DOMAIN] = {entry.entry_id: coord}
        dismiss_calls.clear()

        unloaded = await mod.async_unload_entry(hass, entry)
        self.assertTrue(unloaded)
        self.assertEqual(dismiss_calls, ["situareness_degraded"])
        self.assertNotIn(entry.entry_id, hass.data[mod.DOMAIN])

    async def test_quarantine_ambiguous_over_1000_ineligible_recovers_without_overflow_latch(
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
        cfg = config()
        cfg.update(live_enabled=False, commissioning_passed=False, tts_entity=None)

        def make_ineligible(i):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/qall-inelig-{i:04d}"
            ev["event"] = "Flood Watch"
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        events = [make_ineligible(i) for i in range(1005)]
        ambig_feed = collector.CollectedEvents(
            events, 1, [["https://api.weather.gov/alerts/bad-feature"]], True
        )
        hass = types.SimpleNamespace(data={}, services=Services())
        store = Store()
        coord = mod.SituarenessCoordinator(hass, cfg, store, None)
        with patch.object(mod, "fetch", return_value=ambig_feed):
            h1 = await coord._async_update_data()

        self.assertFalse(h1["evidence_degraded"])
        self.assertIsNone(h1["degraded_reason"])
        self.assertTrue(h1["quarantine_ambiguous"])
        self.assertTrue(h1["output_blocked"])
        self.assertTrue(h1["partial"])
        self.assertLessEqual(len(store.saved[-1]["records"]), 1000)

        # Clean poll clears quarantine_ambiguous immediately without a 7-day latch.
        clean_feed = collector.CollectedEvents(events[:1], 0, [], False)
        with patch.object(mod, "fetch", return_value=clean_feed):
            h2 = await coord._async_update_data()
        self.assertFalse(h2["quarantine_ambiguous"])
        self.assertFalse(h2["output_blocked"])
        self.assertFalse(h2["evidence_degraded"])
        self.assertIsNone(h2["degraded_reason"])

    async def test_strip_withheld_actions_and_select_deliverable_batch_offloaded_to_executor(
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

        now = datetime(2026, 11, 17, 18, 0, tzinfo=timezone.utc)

        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_0"],
            tts_entity=None,
        )
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/exec-offload-1"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        ev = cohere(ev)
        fp = d.fingerprint(ev, d.qualify(ev, cfg, now))

        exec_calls = []

        async def recording_exec(fn, *args):
            exec_calls.append(fn)
            return fn(*args)

        hass = types.SimpleNamespace(
            data={}, services=Services(), async_add_executor_job=recording_exec
        )
        persisted_healthy = {
            "records": {
                ev["id"]: {
                    "state": "active",
                    "fingerprint": fp,
                    "actions": {fp: ["new_york_ny"]},
                    "lineage": [ev["id"]],
                    "cap_identity": ev["cap_identity"],
                    "cap_references": [],
                    "sent": ev["sent"],
                    "expires": ev["expires"],
                    "ends": ev["ends"],
                    "updated": now.isoformat(),
                }
            },
            "outbox": [
                {
                    "key": "exec-item-1",
                    "incident_id": ev["id"],
                    "fingerprint": fp,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev["instruction"],
                    "source_url": ev["id"],
                    "attempts": 0,
                    "created": (now - timedelta(minutes=1)).isoformat(),
                }
            ],
            "initialized": True,
            "was_live": True,
        }
        coord = mod.SituarenessCoordinator(hass, cfg, Store(), persisted_healthy)
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            await coord._async_update_data()
        self.assertIn(mod._select_deliverable_batch, exec_calls)

        exec_calls.clear()
        persisted_degraded = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
        }
        deg_coord = mod.SituarenessCoordinator(hass, cfg, Store(), persisted_degraded)
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            await deg_coord._async_update_data()
        self.assertIn(mod._strip_withheld_actions, exec_calls)

    async def test_degraded_ack_with_missing_expired_unsent_at_preserves_expired_unsent(
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

        now = datetime(2026, 11, 17, 19, 0, tzinfo=timezone.utc)
        ack_str = (now - timedelta(minutes=5)).isoformat()
        cfg = config()
        cfg.update(acknowledge_degraded_at=ack_str)
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
            ),
        )
        persisted = {
            "records": {},
            "outbox": [],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
            "expired_unsent": 2,
            "expired_unsent_at": None,
            "expired_unsent_until": (now + timedelta(days=6)).isoformat(),
        }
        coord = mod.SituarenessCoordinator(
            hass,
            cfg,
            Store(),
            persisted,
            entry=types.SimpleNamespace(entry_id="deg-exp-none", data={}),
        )
        self.assertFalse(coord.degraded)
        self.assertIsNone(coord.degraded_reason)
        self.assertFalse(coord.acknowledge_rejected)
        self.assertEqual(coord.expired_unsent, 2)

    async def test_valid_persisted_store_rejects_invalid_expiry_reasons(self):
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

        for bad_payload in (
            {"records": {}, "expired_unsent_reasons": ["unknown"]},
            {"records": {}, "expired_unsent_reasons": "age"},
            {"records": {}, "expired_unsent_reasons": ["age"] * 5},
            {"records": {}, "outcomes": [{"key": "k", "reason": "bad_reason"}]},
        ):
            self.assertFalse(mod._valid_persisted_store(bad_payload))

        self.assertTrue(
            mod._valid_persisted_store(
                {
                    "records": {},
                    "expired_unsent": 2,
                    "expired_unsent_reasons": ["clock_rollback", "target_removed"],
                    "outcomes": [{"key": "k", "reason": "clock_rollback"}],
                }
            )
        )

    async def test_stopping_skips_post_fetch_saves_and_unload_stops_before_platform_unload(
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

        now = datetime(2026, 11, 17, 20, 0, tzinfo=timezone.utc)
        cfg = config()
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/stop-ev"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        ev = cohere(ev)

        # 1) _stopping=True at start of _update_once skips journal_lost pre-fetch save and fetch.
        store_start = Store()
        coord_start = mod.SituarenessCoordinator(
            types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            ),
            cfg,
            store_start,
            None,
            entry=types.SimpleNamespace(
                entry_id="stop-start", data={"journal_initialized": True}
            ),
        )
        coord_start._stopping = True
        with patch.object(mod, "fetch") as mock_fetch:
            res_start = await coord_start._update_once()
        mock_fetch.assert_not_called()
        self.assertEqual(store_start.saved, [])
        self.assertIsNone(res_start["last_success"])

        # 2) _stopping set during _migrate_outbox_with_index skips post-fetch saves.
        store_mig = Store()
        coord_mig = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()), cfg, store_mig, None
        )
        orig_mig = mod._migrate_outbox_with_index

        def stop_during_migrate(*args, **kwargs):
            coord_mig._stopping = True
            return orig_mig(*args, **kwargs)

        with (
            patch.object(mod, "fetch", return_value=[ev]),
            patch.object(
                mod, "_migrate_outbox_with_index", side_effect=stop_during_migrate
            ),
        ):
            await coord_mig._update_once()
        self.assertEqual(store_mig.saved, [])

        # 3) _stopping set right before pre-drain save inside _queue_outbox_plans skips save.
        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        live_cfg = {**cfg, "live_enabled": True, "commissioning_passed": True}
        store_pre = Store()
        coord_pre = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()),
            live_cfg,
            store_pre,
            {
                "records": {},
                "outbox": [],
                "initialized": True,
                "was_live": True,
            },
        )
        orig_build = mod._build_planned_items

        def stop_during_build(*args, **kwargs):
            if kwargs.get("prepare_pre_drain"):
                coord_pre._stopping = True
            return orig_build(*args, **kwargs)

        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[ev]),
            patch.object(mod, "_build_planned_items", side_effect=stop_during_build),
        ):
            await coord_pre._update_once()
        self.assertEqual(store_pre.saved, [])

        # 4) _stopping set right before post-queue _save skips save.
        store_post = Store()
        coord_post = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()), cfg, store_post, None
        )

        async def stop_before_post_save(*args, **kwargs):
            coord_post._stopping = True
            return [], False, [], {}, 0, 0, False

        with (
            patch.object(mod, "fetch", return_value=[ev]),
            patch.object(
                coord_post, "_queue_outbox_plans", side_effect=stop_before_post_save
            ),
        ):
            await coord_post._update_once()
        self.assertEqual(store_post.saved, [])

        # 5) async_unload_entry calls async_stop() before async_unload_platforms().
        order = []

        async def fake_unload_platforms(ent, platforms):
            order.append("unload_platforms")
            return True

        entry = types.SimpleNamespace(entry_id="unload-order", data={})
        hass_unload = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_unload_platforms=fake_unload_platforms
            ),
        )
        coord_unload = mod.SituarenessCoordinator(
            hass_unload, cfg, Store(), None, entry=entry
        )

        async def tracked_stop():
            order.append("async_stop")
            coord_unload._stopping = True

        coord_unload.async_stop = tracked_stop
        hass_unload.data[mod.DOMAIN] = {entry.entry_id: coord_unload}
        self.assertTrue(await mod.async_unload_entry(hass_unload, entry))
        self.assertEqual(order, ["async_stop", "unload_platforms"])

    async def test_intermittent_malformed_cancellation_with_persistent_overflow_does_not_flip_flop(
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
        create_calls = []
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                create_calls.append({"title": title, "message": msg})
            ),
            async_dismiss=lambda *args, **kwargs: None,
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

        t0 = datetime(2026, 11, 17, 21, 0, tzinfo=timezone.utc)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = t0
        cfg = config()
        cfg.update(live_enabled=False, commissioning_passed=False, tts_entity=None)
        hass = types.SimpleNamespace(data={}, services=Services())

        mal_cancel = d.normalize(feature())
        mal_cancel["id"] = "https://api.weather.gov/alerts/flip-mal-cancel"
        mal_cancel["message_type"] = "Cancel"
        mal_cancel["references"] = []
        mal_cancel["reference_identities"] = []
        mal_cancel["sent"] = (t0 - timedelta(seconds=10)).isoformat()
        mal_cancel["effective"] = (t0 - timedelta(seconds=10)).isoformat()
        mal_cancel["onset"] = (t0 - timedelta(seconds=10)).isoformat()
        mal_cancel["expires"] = (t0 + timedelta(seconds=1800)).isoformat()
        mal_cancel["ends"] = (t0 + timedelta(seconds=1800)).isoformat()

        ov_err = d.CancellationEvidenceOverflow(
            "persistent overflow",
            dropped_horizon=t0 + timedelta(days=9),
            records={},
            plans=[],
        )
        coord = mod.SituarenessCoordinator(hass, cfg, Store(), None)

        # Poll 1: overflow only.
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[]),
            patch.object(mod, "reconcile", side_effect=ov_err),
        ):
            h1 = await coord._async_update_data()
        self.assertEqual(h1["degraded_reason"], "cancellation_evidence_overflow")
        self.assertEqual(h1["degraded_at"], t0.isoformat())
        self.assertEqual(len(create_calls), 1)

        # Poll 2: intermittent malformed_cancellation + overflow escalates without resetting degraded_at.
        Clock.current = t0 + timedelta(minutes=5)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[mal_cancel]),
            patch.object(mod, "reconcile", side_effect=ov_err),
        ):
            h2 = await coord._async_update_data()
        self.assertEqual(h2["degraded_reason"], "malformed_cancellation")
        self.assertEqual(h2["degraded_at"], t0.isoformat())
        self.assertEqual(len(create_calls), 2)

        # Poll 3: overflow-only again does NOT flip-flop back or re-create notification.
        Clock.current = t0 + timedelta(minutes=10)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[]),
            patch.object(mod, "reconcile", side_effect=ov_err),
        ):
            h3 = await coord._async_update_data()
        self.assertEqual(h3["degraded_reason"], "malformed_cancellation")
        self.assertEqual(h3["degraded_at"], t0.isoformat())
        self.assertEqual(len(create_calls), 2)

    async def test_outbox_overflow_preserves_already_queued_empty_new_items_plans(self):
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

        now = datetime(2026, 11, 17, 22, 0, tzinfo=timezone.utc)

        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        cfg = config()
        cfg["locations"] = {
            "new_york_ny": {"point": [0.5, 0.5], "speakers": []},
            "washington_dc": {
                "point": [3.0, 3.0],
                "speakers": [f"media_player.dc_{i}" for i in range(4995)],
            },
        }
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=[f"mobile_app_{i}" for i in range(6)],
            tts_entity="tts.home",
        )

        def make_ev(name):
            ev = d.normalize(feature())
            ev["id"] = f"https://api.weather.gov/alerts/empty-new-{name}"
            for key, delta in [
                ("sent", -60),
                ("effective", -60),
                ("onset", 0),
                ("expires", 1800),
                ("ends", 1800),
            ]:
                ev[key] = (now + timedelta(seconds=delta)).isoformat()
            return cohere(ev)

        susp_ev = make_ev("susp")
        susp_fp = d.fingerprint(susp_ev, d.qualify(susp_ev, cfg, now))
        queued_ev = make_ev("queued")
        queued_fp = d.fingerprint(queued_ev, d.qualify(queued_ev, cfg, now))
        overflow_ev = make_ev("overflow")
        overflow_ev["instruction"] = "Take shelter immediately second alert."

        fresh = (now - timedelta(minutes=1)).isoformat()
        susp_items = [
            {
                "key": f"susp-{i}",
                "incident_id": susp_ev["id"],
                "fingerprint": susp_fp,
                "kind": "speaker",
                "target": f"media_player.dc_{i}",
                "location": "washington_dc",
                "affected_names": ["washington_dc"],
                "event": "Tornado Warning",
                "instruction": susp_ev["instruction"],
                "source_url": susp_ev["id"],
                "attempts": 0,
                "created": fresh,
            }
            for i in range(4995)
        ]
        queued_plan = {
            "id": queued_ev["id"],
            "fingerprint": queued_fp,
            "affected": ["new_york_ny"],
            "phones": list(cfg["phones"]),
            "event": "Tornado Warning",
            "instruction": queued_ev["instruction"],
        }
        queued_items = mod.targets(queued_plan, cfg, now)
        outbox = susp_items[:4994] + queued_items
        records = {
            susp_ev["id"]: {
                "state": "ended_or_absent",
                "prior_state": "active",
                "fingerprint": susp_fp,
                "actions": {susp_fp: ["washington_dc"]},
                "lineage": [susp_ev["id"]],
                "cap_identity": susp_ev["cap_identity"],
                "cap_references": [],
                "sent": susp_ev["sent"],
                "expires": susp_ev["expires"],
                "ends": susp_ev["ends"],
                "inactive_since": fresh,
                "updated": fresh,
            },
            queued_ev["id"]: {
                "state": "active",
                "fingerprint": queued_fp,
                "actions": {queued_fp: ["new_york_ny"]},
                "lineage": [queued_ev["id"]],
                "cap_identity": queued_ev["cap_identity"],
                "cap_references": [],
                "sent": queued_ev["sent"],
                "expires": queued_ev["expires"],
                "ends": queued_ev["ends"],
                "updated": now.isoformat(),
            },
            overflow_ev["id"]: {
                "state": "active",
                "fingerprint": "fp-overflow",
                "actions": {"fp-overflow": ["new_york_ny"]},
                "lineage": [overflow_ev["id"]],
                "cap_identity": overflow_ev["cap_identity"],
                "cap_references": [],
                "sent": overflow_ev["sent"],
                "expires": overflow_ev["expires"],
                "ends": overflow_ev["ends"],
                "updated": now.isoformat(),
            },
        }
        overflow_plan = {
            "id": overflow_ev["id"],
            "fingerprint": "fp-overflow",
            "affected": ["new_york_ny"],
            "phones": list(cfg["phones"]),
            "event": "Tornado Warning",
            "instruction": overflow_ev["instruction"],
        }
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()), cfg, Store(), None
        )
        coord.records = records
        coord.outbox = outbox
        groups, _ = d.lineage_index(records, [])
        # Simulate pre-drain failing to shrink below overflow (already_delivered=False path or pre-drain skipped):
        with patch.object(mod, "_build_planned_items") as mock_build:
            mock_build.return_value = (
                set(),
                [(queued_plan, []), (overflow_plan, [("item", "sig")] * 6)],
                5006,
                None,
            )
            (
                _,
                overflowed,
                dropped,
                _,
                _,
                _,
                _,
            ) = await coord._queue_outbox_plans(
                records,
                [queued_plan, overflow_plan],
                list(outbox),
                [queued_ev, overflow_ev],
                groups,
                now,
            )
        self.assertTrue(overflowed)
        self.assertEqual(dropped, [overflow_plan])
        await coord.hass.async_add_executor_job(
            mod._strip_withheld_actions, records, dropped, groups, now
        )
        self.assertIn(queued_fp, records[queued_ev["id"]]["actions"])
        self.assertNotIn("fp-overflow", records[overflow_ev["id"]]["actions"])

    async def test_abandoned_setup_retry_listener_dismisses_degraded_notification(self):
        import tempfile

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        dismiss_calls = []
        fake_pn = types.SimpleNamespace(
            async_create=lambda *args, **kwargs: None,
            async_dismiss=lambda hass, nid: dismiss_calls.append(nid),
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

        async def run_exec(fn, *args):
            return fn(*args)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "situareness.json").write_text("{}", encoding="utf-8")
            listeners = []

            class FakeEntry:
                entry_id = "retry-abandon"
                data = {}
                state = "setup_retry"

                def async_on_state_change(self, cb):
                    listeners.append(cb)
                    return lambda: listeners.remove(cb)

            entry = FakeEntry()
            hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                async_add_executor_job=run_exec,
            )

            class EmptyStore(Store):
                async def async_load(self):
                    return None

            class FailingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    raise ConfigEntryNotReady("NWS down")

            with (
                patch.object(mod, "Store", EmptyStore),
                patch.object(mod, "SituarenessCoordinator", FailingCoordinator),
            ):
                with self.assertRaises(ConfigEntryNotReady):
                    await mod.async_setup_entry(hass, entry)
            peer_calls = []
            listeners.append(lambda: peer_calls.append("peer"))
            self.assertEqual(len(listeners), 2)
            dismiss_calls.clear()
            entry.state = "not_loaded"
            for cb in listeners:
                cb()
            await asyncio.sleep(0)
            self.assertEqual(dismiss_calls, ["situareness_degraded"])
            self.assertEqual(peer_calls, ["peer"])
            self.assertEqual(len(listeners), 1)

    async def test_failed_platform_unload_resumes_coordinator_and_next_poll_succeeds(
        self,
    ):
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
            async_dismiss=lambda hass, nid: notifications.pop(nid, None),
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

        unload_result = False

        async def fake_unload(ent, platforms):
            if isinstance(unload_result, Exception):
                raise unload_result
            return unload_result

        entry = types.SimpleNamespace(entry_id="resume-unload", data={})
        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(
                async_unload_platforms=fake_unload,
                async_update_entry=lambda ent, data=None: setattr(ent, "data", data),
            ),
        )
        coord = mod.SituarenessCoordinator(
            hass,
            config(),
            Store(),
            {
                "records": {},
                "outbox": [],
                "initialized": True,
                "was_live": True,
                "degraded": True,
                "degraded_reason": "journal_lost",
                "degraded_at": "2026-11-17T10:00:00+00:00",
                "degraded_until": "2026-11-24T10:00:00+00:00",
            },
            entry=entry,
        )
        hass.data[mod.DOMAIN] = {entry.entry_id: coord}
        self.assertIn("situareness_degraded", notifications)

        # Returning False from async_unload_platforms resumes coordinator and resyncs notification.
        self.assertFalse(await mod.async_unload_entry(hass, entry))
        self.assertFalse(coord._stopping)
        self.assertIn("situareness_degraded", notifications)
        self.assertIn(entry.entry_id, hass.data[mod.DOMAIN])

        with patch.object(mod, "fetch", return_value=[]):
            health = await coord._async_update_data()
        self.assertEqual(health["degraded_reason"], "journal_lost")

        # Raising from async_unload_platforms also resumes coordinator before re-raising.
        unload_result = RuntimeError("platform unload error")
        with self.assertRaises(RuntimeError):
            await mod.async_unload_entry(hass, entry)
        self.assertFalse(coord._stopping)
        self.assertIn("situareness_degraded", notifications)

    async def test_repeated_failed_setup_entry_deduplicates_retry_listener(self):
        import tempfile

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

        async def run_exec(fn, *args):
            return fn(*args)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "situareness.json").write_text("{}", encoding="utf-8")
            listeners = []

            class FakeEntry:
                entry_id = "dedup-retry"
                data = {}
                state = "setup_retry"

                def async_on_state_change(self, cb):
                    listeners.append(cb)
                    return lambda: listeners.remove(cb)

            entry = FakeEntry()
            hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                async_add_executor_job=run_exec,
            )

            class EmptyStore(Store):
                async def async_load(self):
                    return None

                async def async_remove(self):
                    pass

            class FailingCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    raise ConfigEntryNotReady("NWS down")

            with (
                patch.object(mod, "Store", EmptyStore),
                patch.object(mod, "SituarenessCoordinator", FailingCoordinator),
            ):
                for _ in range(3):
                    with self.assertRaises(ConfigEntryNotReady):
                        await mod.async_setup_entry(hass, entry)
                    self.assertEqual(len(listeners), 1)
                await mod.async_remove_entry(hass, entry)
            self.assertEqual(listeners, [])

    async def test_failed_save_preserves_expired_unsent_and_last_degraded_poll(self):
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

        now = datetime(2026, 11, 18, 1, 0, tzinfo=timezone.utc)

        class Clock:
            current = None

            @classmethod
            def now(cls, tz):
                return cls.current

        Clock.current = now
        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_0"],
            tts_entity=None,
        )
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/save-fail-1"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        ev = cohere(ev)
        fp = d.fingerprint(ev, d.qualify(ev, cfg, now))

        prev_poll = (now - timedelta(minutes=1)).isoformat()
        persisted = {
            "records": {
                ev["id"]: {
                    "state": "active",
                    "fingerprint": fp,
                    "actions": {fp: ["new_york_ny"]},
                    "lineage": [ev["id"]],
                    "cap_identity": ev["cap_identity"],
                    "cap_references": [],
                    "sent": ev["sent"],
                    "expires": ev["expires"],
                    "ends": ev["ends"],
                    "updated": (now - timedelta(minutes=20)).isoformat(),
                }
            },
            "outbox": [
                {
                    "key": "fail-save-item",
                    "incident_id": ev["id"],
                    "fingerprint": fp,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev["instruction"],
                    "source_url": ev["id"],
                    "attempts": 0,
                    "created": (now - timedelta(minutes=17)).isoformat(),
                }
            ],
            "initialized": True,
            "was_live": True,
            "degraded": True,
            "degraded_reason": "journal_lost",
            "degraded_at": (now - timedelta(hours=1)).isoformat(),
            "degraded_until": (now + timedelta(days=7)).isoformat(),
            "last_degraded_poll": prev_poll,
        }
        store = Store()
        store.fail = True
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()), cfg, store, persisted
        )
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            with self.assertRaises(UpdateFailed):
                await coord._async_update_data()
        # Neither expired_unsent nor last_degraded_poll changed when _save failed.
        self.assertEqual(coord.expired_unsent, 0)
        self.assertEqual(coord.last_degraded_poll, prev_poll)

        # Succeeding retry poll advances last_degraded_poll cleanly and counts item once.
        store.fail = False
        Clock.current = now + timedelta(minutes=1)
        with (
            patch.object(mod, "datetime", Clock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            health = await coord._async_update_data()
        self.assertEqual(health["expired_unsent"], 1)
        self.assertEqual(coord.expired_unsent, 1)
        self.assertEqual(coord.last_degraded_poll, Clock.current.isoformat())

    async def test_third_failed_delivery_attempt_latches_exhausted_expired_unsent(self):
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
            async_dismiss=lambda hass, nid: notifications.pop(nid, None),
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

        now = datetime(2026, 11, 18, 2, 0, tzinfo=timezone.utc)

        class FixedClock:
            @classmethod
            def now(cls, tz):
                return now

        cfg = config()
        cfg.update(
            live_enabled=True,
            commissioning_passed=True,
            phones=["mobile_app_0"],
            tts_entity=None,
        )
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/exhaust-3"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            ev[key] = (now + timedelta(seconds=delta)).isoformat()
        ev = cohere(ev)
        fp = d.fingerprint(ev, d.qualify(ev, cfg, now))

        class FailingServices:
            async def async_call(self, *args, **kwargs):
                raise OSError("channel down")

        persisted = {
            "records": {
                ev["id"]: {
                    "state": "active",
                    "fingerprint": fp,
                    "actions": {fp: ["new_york_ny"]},
                    "lineage": [ev["id"]],
                    "cap_identity": ev["cap_identity"],
                    "cap_references": [],
                    "sent": ev["sent"],
                    "expires": ev["expires"],
                    "ends": ev["ends"],
                    "updated": now.isoformat(),
                }
            },
            "outbox": [
                {
                    "key": "exhaust-item-1",
                    "incident_id": ev["id"],
                    "fingerprint": fp,
                    "kind": "phone",
                    "target": "mobile_app_0",
                    "location": None,
                    "affected_names": ["New York"],
                    "event": "Tornado Warning",
                    "instruction": ev["instruction"],
                    "source_url": ev["id"],
                    "attempts": 2,
                    "created": (now - timedelta(minutes=2)).isoformat(),
                }
            ],
            "initialized": True,
            "was_live": True,
        }
        store = Store()
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=FailingServices()),
            cfg,
            store,
            persisted,
        )
        with (
            patch.object(mod, "datetime", FixedClock),
            patch.object(mod, "fetch", return_value=[ev]),
        ):
            health = await coord._async_update_data()

        self.assertEqual(coord.outbox, [])
        self.assertEqual(health["delivery_attempts"], 1)
        self.assertEqual(health["delivery_failures"], 1)
        self.assertEqual(health["expired_unsent"], 1)
        self.assertTrue(health["partial"])
        self.assertEqual(store.saved[-1]["expired_unsent_reasons"], ["exhausted"])
        expired_outs = [o for o in store.saved[-1]["outcomes"] if o.get("expired")]
        self.assertEqual(len(expired_outs), 1)
        self.assertEqual(expired_outs[0]["reason"], "exhausted")
        self.assertEqual(expired_outs[0]["attempt"], 3)
        self.assertIn(
            "exhausted all 3 delivery attempts (MAX_ATTEMPTS = 3)",
            notifications["situareness_degraded"]["message"],
        )

    async def test_merge_consumed_acks_sorts_chronologically(self):
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

        t0 = "2026-11-17T08:00:00+00:00"
        t1 = "2026-11-17T09:00:00+00:00"
        t2 = "2026-11-17T10:00:00+00:00"
        self.assertEqual(mod._merge_consumed_acks([t2, t1], [t0]), [t0, t1, t2])

        entry = types.SimpleNamespace(
            entry_id="ack-order",
            data={"acknowledged_degraded_at": t0, "consumed_acknowledgements": [t0]},
        )
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(
                data={},
                services=Services(),
                config_entries=types.SimpleNamespace(
                    async_update_entry=lambda ent, data=None: setattr(ent, "data", data)
                ),
            ),
            config(),
            Store(),
            {"records": {}, "acknowledged_degraded_at": t2},
            entry=entry,
        )
        self.assertEqual(coord.acknowledged_degraded_at, t2)
        self.assertEqual(coord.consumed_acknowledgements, [t0, t2])

    async def test_save_skips_disk_verify_when_hass_stopping(self):
        import tempfile

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

        stopping_state = types.SimpleNamespace(name="stopping", value="STOPPING")

        with tempfile.TemporaryDirectory() as tmp:
            store_file = Path(tmp) / "situareness.deferred"

            class DeferredStore:
                path = store_file

                async def async_save(self, data):
                    # Emulates HA Store.async_save deferring writes to final_write during shutdown.
                    return None

            async def run_exec(fn, *args):
                return await asyncio.to_thread(fn, *args)

            hass = types.SimpleNamespace(
                state=stopping_state,
                data={},
                services=Services(),
                async_add_executor_job=run_exec,
            )
            coord = mod.SituarenessCoordinator(
                hass,
                config(),
                DeferredStore(),
                {},
            )
            await coord._save({"id-1": {"state": "ineligible"}}, [], [])
            self.assertIn("id-1", coord.records)

            hass.state = types.SimpleNamespace(name="running", value="RUNNING")
            with self.assertRaises(OSError):
                await coord._save({"id-2": {"state": "ineligible"}}, [], [])

    async def test_setup_entry_cleans_data_and_notification_when_forward_fails(self):
        import tempfile

        path = (
            Path(__file__).resolve().parents[2]
            / "custom_components/situareness/__init__.py"
        )
        spec = importlib.util.spec_from_file_location(
            PACKAGE, path, submodule_search_locations=[str(path.parent)]
        )
        mod = importlib.util.module_from_spec(spec)
        notifications = {}
        dismiss_calls = []
        fake_pn = types.SimpleNamespace(
            async_create=lambda hass, msg, title=None, notification_id=None: (
                notifications.__setitem__(
                    notification_id, {"message": msg, "title": title}
                )
            ),
            async_dismiss=lambda hass, nid: (
                dismiss_calls.append(nid),
                notifications.pop(nid, None),
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

        async def run_exec(fn, *args):
            return await asyncio.to_thread(fn, *args)

        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "situareness.json").write_text("{}", encoding="utf-8")

            class ForwardFailEntries:
                def async_update_entry(self, ent, data=None):
                    ent.data = data

                async def async_forward_entry_setups(self, ent, platforms):
                    raise RuntimeError("platform setup boom")

            class DegradedFirstRefreshCoordinator(mod.SituarenessCoordinator):
                async def async_config_entry_first_refresh(self):
                    self.data = await self._update_once()

            listeners = []
            entry = types.SimpleNamespace(
                entry_id="fwd-fail",
                data={"journal_initialized": True},
                state="setup_error",
                async_on_state_change=lambda cb: (
                    listeners.append(cb),
                    lambda: listeners.remove(cb),
                )[-1],
            )
            hass = types.SimpleNamespace(
                data={},
                services=Services(),
                config=types.SimpleNamespace(
                    path=lambda *p: str(Path(tmp).joinpath(*p))
                ),
                config_entries=ForwardFailEntries(),
                async_add_executor_job=run_exec,
            )

            class EmptyStore(Store):
                async def async_load(self):
                    return None

            with (
                patch.object(mod, "Store", EmptyStore),
                patch.object(
                    mod, "SituarenessCoordinator", DegradedFirstRefreshCoordinator
                ),
                patch.object(
                    mod,
                    "fetch",
                    return_value=collector.CollectedEvents([], 0, set(), False),
                ),
                self.assertRaisesRegex(RuntimeError, "platform setup boom"),
            ):
                await mod.async_setup_entry(hass, entry)

            self.assertNotIn(entry.entry_id, hass.data.get(mod.DOMAIN, {}))
            self.assertNotIn("situareness_degraded", notifications)
            self.assertGreaterEqual(len(dismiss_calls), 1)
            for cb in list(listeners):
                cb()
            await asyncio.sleep(0)
            self.assertEqual(listeners, [])

    async def test_compute_expired_unsent_resets_elapsed_prior_window(self):
        from datetime import datetime, timezone

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

        old_at = datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
        now = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)
        persisted = {
            "records": {},
            "outbox": [],
            "expired_unsent": 4,
            "expired_unsent_at": old_at.isoformat(),
            "expired_unsent_until": (old_at + mod.MAX_ACCEPTANCE_AGE).isoformat(),
            "expired_unsent_reasons": ["target_removed"],
        }
        coord = mod.SituarenessCoordinator(
            types.SimpleNamespace(data={}, services=Services()),
            config(),
            Store(),
            persisted,
        )
        # Preserve the elapsed window directly to test poll_expired > 0 right after outage recovery.
        coord.expired_unsent = 4
        coord.expired_unsent_at = old_at.isoformat()
        coord.expired_unsent_until = (old_at + mod.MAX_ACCEPTANCE_AGE).isoformat()
        coord.expired_unsent_reasons = ["target_removed"]

        count, new_at, new_until, reasons, ack_rej = coord._compute_expired_unsent(
            1, now, outcomes=[{"expired": True, "reason": "age"}]
        )
        self.assertEqual(count, 1)
        self.assertEqual(new_at, now.isoformat())
        self.assertEqual(new_until, (now + mod.MAX_ACCEPTANCE_AGE).isoformat())
        self.assertEqual(reasons, ["age"])
        self.assertFalse(ack_rej)

    async def test_failed_platform_unload_restores_quarantine_ambiguous_notice(self):
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
            async_dismiss=lambda hass, nid: notifications.pop(nid, None),
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

        async def run_exec(fn, *args):
            return await asyncio.to_thread(fn, *args)

        async def fail_unload(entry, platforms):
            return False

        hass = types.SimpleNamespace(
            data={},
            services=Services(),
            config_entries=types.SimpleNamespace(async_unload_platforms=fail_unload),
            async_add_executor_job=run_exec,
        )
        coord = mod.SituarenessCoordinator(hass, config(), Store(), {})
        entry = types.SimpleNamespace(entry_id="resume-qa")
        hass.data.setdefault(mod.DOMAIN, {})[entry.entry_id] = coord

        ambiguous_batch = collector.CollectedEvents([], 1, set(), True, source_count=1)
        with patch.object(mod, "fetch", return_value=ambiguous_batch):
            health = await coord._async_update_data()

        self.assertTrue(health["quarantine_ambiguous"])
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness alert scope ambiguous",
        )
        self.assertFalse(await mod.async_unload_entry(hass, entry))
        self.assertIn(entry.entry_id, hass.data[mod.DOMAIN])
        self.assertEqual(
            notifications["situareness_degraded"]["title"],
            "Situareness alert scope ambiguous",
        )

    async def test_shadow_notification_qualification_and_overflow_record_isolation(
        self,
    ):
        from datetime import datetime, timezone

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
            async_dismiss=lambda hass, nid: notifications.pop(nid, None),
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

        shadow_cfg = config()
        live_cfg = {**shadow_cfg, "live_enabled": True, "commissioning_passed": True}
        hass = types.SimpleNamespace(data={}, services=Services())

        now_iso = datetime.now(timezone.utc).isoformat()
        for cfg_variant, expect_shadow in ((shadow_cfg, True), (live_cfg, False)):
            notifications.clear()
            coord_qa = mod.SituarenessCoordinator(hass, cfg_variant, Store(), {})
            coord_qa._sync_degraded_notification(quarantine_ambiguous=True)
            qa_msg = notifications["situareness_degraded"]["message"]
            self.assertEqual(
                "Shadow mode: live output is disabled." in qa_msg, expect_shadow
            )

            notifications.clear()
            mod.SituarenessCoordinator(
                hass,
                cfg_variant,
                Store(),
                {"records": {}, "expired_unsent": 1, "expired_unsent_at": now_iso},
            )
            exp_msg = notifications["situareness_degraded"]["message"]
            self.assertEqual(
                "Shadow mode: live output is disabled." in exp_msg, expect_shadow
            )

            notifications.clear()
            mod.SituarenessCoordinator(
                hass,
                {**cfg_variant, "acknowledge_degraded_at": "invalid"},
                Store(),
                {"records": {}},
            )
            rej_msg = notifications["situareness_degraded"]["message"]
            self.assertEqual(
                "Shadow mode: live output is disabled." in rej_msg, expect_shadow
            )

        # Fallback records=None on CancellationEvidenceOverflow must not mutate self.records in place.
        class FailingStore(Store):
            async def async_save(self, value):
                raise OSError("disk full")

        async def run_exec(fn, *args):
            return await asyncio.to_thread(fn, *args)

        hass_fail = types.SimpleNamespace(
            data={}, services=Services(), async_add_executor_job=run_exec
        )
        initial_rec = {
            "https://api.weather.gov/alerts/a1": {
                "state": "active",
                "actions": {"fp1": ["new_york_ny"]},
                "updated": now_iso,
            }
        }
        coord_iso = mod.SituarenessCoordinator(
            hass_fail, live_cfg, FailingStore(), {"records": initial_rec}
        )
        original_actions = dict(
            coord_iso.records["https://api.weather.gov/alerts/a1"]["actions"]
        )
        overflow_plans = [
            {
                "id": "https://api.weather.gov/alerts/a1",
                "fingerprint": "fp1",
                "event": "Tornado Warning",
                "instruction": "Take shelter immediately",
                "affected_names": ["New York"],
                "new_items": [],
            }
        ]
        overflow_err = d.CancellationEvidenceOverflow(
            "overflow", records=None, plans=overflow_plans
        )
        with (
            patch.object(
                mod,
                "fetch",
                return_value=collector.CollectedEvents([], 0, set(), False),
            ),
            patch.object(mod, "reconcile", side_effect=overflow_err),
            self.assertRaises(UpdateFailed),
        ):
            await coord_iso._async_update_data()
        self.assertEqual(
            coord_iso.records["https://api.weather.gov/alerts/a1"]["actions"],
            original_actions,
        )
