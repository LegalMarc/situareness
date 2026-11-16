"""Mocked HA boundary tests, not an installed Home Assistant run."""

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from test_domain import PACKAGE, config, feature, d


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
            restarted = mod.SituarenessCoordinator(hass, cfg, store, store.snapshot)
            data = await restarted._async_update_data()
            self.assertEqual((data["planned_count"], data["pending_count"]), (0, 1))
            self.assertEqual(store.snapshot["outbox"][0]["incident_id"], e["id"])
            e["id"] = original["id"] + "-c"
            e["references"] = [original["id"], original["id"] + "-b"]
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

            # A failed delivery is discarded if a subsequent complete poll no longer includes the alert.
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
            self.assertEqual(store.snapshot["outbox"], [])

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

    async def test_clock_advance_drops_expired_before_next_group(self):
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
        self.assertEqual(result["pending_count"], 0)
