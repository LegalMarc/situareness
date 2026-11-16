import copy
from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys
import types
import unittest

PACKAGE = "situareness_test"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [
    str(Path(__file__).resolve().parents[2] / "custom_components" / "situareness")
]
sys.modules[PACKAGE] = pkg
d = importlib.import_module(PACKAGE + ".domain")
c = importlib.import_module(PACKAGE + ".config")
delivery = importlib.import_module(PACKAGE + ".delivery")
collector = importlib.import_module(PACKAGE + ".collector")
NOW = datetime(2026, 11, 15, 20, tzinfo=timezone.utc)
# Deliberately fictional coordinates, unrelated to either named sample location.
POLY = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
}


def feature():
    return {
        "type": "Feature",
        "id": "https://api.weather.gov/alerts/urn:oid:123",
        "geometry": POLY,
        "properties": {
            "id": "urn:oid:123",
            "event": "Tornado Warning",
            "status": "Actual",
            "messageType": "Alert",
            "sent": "2026-11-15T19:55:00Z",
            "effective": "2026-11-15T19:55:00Z",
            "onset": "2026-11-15T20:00:00Z",
            "expires": "2026-11-15T21:00:00Z",
            "ends": "2026-11-15T21:00:00Z",
            "urgency": "Immediate",
            "certainty": "Observed",
            "instruction": "Take shelter now.",
            "references": [],
        },
    }


def config():
    return c.validate(
        {
            "approved_rules": {"Tornado Warning": ["Take shelter"]},
            "locations": {
                "new_york_ny": {
                    "point": [0.5, 0.5],
                    "speakers": ["media_player.new_york_ny"],
                },
                "washington_dc": {
                    "point": [3, 3],
                    "speakers": ["media_player.washington_dc"],
                },
            },
            "phones": ["mobile_app_one", "mobile_app_two"],
            "tts_entity": "tts.home",
        }
    )


class Policy(unittest.TestCase):
    def test_normalize_real_nws_id(self):
        self.assertEqual(d.normalize(feature())["id"], feature()["id"])
        bad = feature()
        bad["id"] = "https://evil.test/alerts/123"
        self.assertIsNone(d.normalize(bad))
        bad = feature()
        bad["properties"]["references"] = [{"@id": feature()["id"]}] * 101
        self.assertIsNone(d.normalize(bad))

    def test_positive_and_boundary(self):
        e = d.normalize(feature())
        self.assertEqual(
            d.qualify(e, config(), NOW),
            {"qualifies": True, "reasons": [], "affected": ["new_york_ny"]},
        )
        self.assertTrue(d.matches([0, 0.5], POLY))
        self.assertFalse(d.matches([-1, 0.5], POLY))

    def test_old_sent_but_current_actionable(self):
        e = d.normalize(feature())
        e["sent"] = "2026-11-14T10:00:00Z"
        self.assertTrue(d.qualify(e, config(), NOW)["qualifies"])
        e["expires"] = "2026-11-15T19:59:00Z"
        self.assertFalse(d.qualify(e, config(), NOW)["qualifies"])

    def test_holes_and_malformed_geometry(self):
        g = copy.deepcopy(POLY)
        g["coordinates"].append(
            [[0.3, 0.3], [0.7, 0.3], [0.7, 0.7], [0.3, 0.7], [0.3, 0.3]]
        )
        self.assertFalse(d.matches([0.5, 0.5], g))
        self.assertFalse(d.matches([0.3, 0.5], g))
        self.assertFalse(
            d.matches([0.5, 0.5], {"type": "Polygon", "coordinates": [[[0, 0]]]})
        )
        self.assertFalse(d.matches([0.5, 0.5], None))

    def test_fail_closed_scenarios(self):
        for change in (
            {"status": "Test"},
            {"status": "Exercise"},
            {"message_type": "Cancel"},
            {"expires": "2026-11-15T19:59:00Z"},
            {"instruction": ""},
            {"instruction": "No protective action is needed."},
            {"event": "Severe Thunderstorm Watch"},
            {"effective": "2026-11-16T00:00:00Z"},
            {"onset": "2026-11-16T10:00:00Z"},
            {"certainty": "Possible"},
            {"geometry": None},
        ):
            with self.subTest(change=change):
                e = d.normalize(feature())
                e.update(change)
                self.assertFalse(d.qualify(e, config(), NOW)["qualifies"])
        cfg = config()
        cfg["locations"] = {"new_york_ny": {}}
        self.assertFalse(d.qualify(d.normalize(feature()), cfg, NOW)["qualifies"])

    def test_reconcile_restart_dedup_updates_cancellation(self):
        e = d.normalize(feature())
        cfg = config()
        records, plans = d.reconcile({}, [e], cfg, NOW, baseline=True)
        self.assertEqual(plans, [])
        records, plans = d.reconcile(records, [e], cfg, NOW)
        self.assertEqual(plans, [])
        e["instruction"] = "Take shelter in basement now."
        records, plans = d.reconcile(records, [e], cfg, NOW)
        self.assertEqual(plans[0]["phones"], ["mobile_app_one", "mobile_app_two"])
        self.assertEqual(plans[0]["affected"], ["new_york_ny"])
        records, plans = d.reconcile(records, [], cfg, NOW)
        self.assertEqual(records[e["id"]]["state"], "ended_or_absent")
        self.assertFalse(plans)

    def test_referenced_update_does_not_repeat_unchanged(self):
        e = d.normalize(feature())
        records, _ = d.reconcile({}, [e], config(), NOW)
        update = copy.deepcopy(e)
        update["id"] += "-update"
        update["references"] = [e["id"]]
        records, plans = d.reconcile(records, [update], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(records[e["id"]]["state"], "superseded")

    def test_expiry_only_update_does_not_repeat(self):
        e = d.normalize(feature())
        records, _ = d.reconcile({}, [e], config(), NOW)
        update = copy.deepcopy(e)
        update["id"] += "-update"
        update["references"] = [e["id"]]
        update["expires"] = "2026-11-15T22:00:00Z"
        update["ends"] = "2026-11-15T22:00:00Z"
        records, plans = d.reconcile(records, [update], config(), NOW)
        self.assertEqual(plans, [])
        update["instruction"] = "Take shelter immediately in a basement."
        _, plans = d.reconcile(records, [update], config(), NOW)
        self.assertEqual(len(plans), 1)

    def test_multi_reference_lineage_uses_active_predecessor(self):
        for reverse in (False, True):
            with self.subTest(reverse=reverse):
                a = d.normalize(feature())
                records, plans = d.reconcile({}, [a], config(), NOW)
                self.assertEqual(len(plans), 1)
                b = copy.deepcopy(a)
                b.update(id=a["id"] + "-b", references=[a["id"]])
                records, plans = d.reconcile(records, [b], config(), NOW)
                self.assertFalse(plans)
                c = copy.deepcopy(b)
                refs = [a["id"], b["id"]]
                c.update(
                    id=a["id"] + "-c",
                    references=refs[::-1] if reverse else refs,
                    expires="2026-11-15T22:00:00Z",
                    ends="2026-11-15T22:00:00Z",
                )
                records, plans = d.reconcile(records, [c], config(), NOW)
                self.assertFalse(plans)
                self.assertEqual(records[b["id"]]["state"], "superseded")
                changed = copy.deepcopy(c)
                changed.update(
                    id=a["id"] + "-d",
                    references=[a["id"], c["id"]],
                    instruction="Take shelter in the basement.",
                )
                records, plans = d.reconcile(records, [changed], config(), NOW)
                self.assertEqual(len(plans), 1)
                # An old equivalent ancestor must not suppress a changed current action.
                reverted = copy.deepcopy(c)
                reverted.update(id=a["id"] + "-e", references=[a["id"], changed["id"]])
                _, plans = d.reconcile(records, [reverted], config(), NOW)
                self.assertEqual(len(plans), 1)

    def test_lineage_new_site_and_cancellation(self):
        cfg = config()
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], cfg, NOW)
        b = copy.deepcopy(a)
        b.update(id=a["id"] + "-b", references=[a["id"]])
        records, _ = d.reconcile(records, [b], cfg, NOW)
        cfg["locations"]["second"] = {"point": [0.6, 0.4], "speakers": []}
        c = copy.deepcopy(b)
        c.update(id=a["id"] + "-c", references=[a["id"], b["id"]])
        records, plans = d.reconcile(records, [c], cfg, NOW)
        self.assertEqual(plans[0]["affected"], ["new_york_ny", "second"])
        cancel = copy.deepcopy(c)
        cancel.update(
            id=a["id"] + "-cancel", references=[a["id"], c["id"]], message_type="Cancel"
        )
        records, plans = d.reconcile(records, [cancel], cfg, NOW)
        self.assertFalse(plans)
        self.assertEqual(records[c["id"]]["state"], "cancelled")
        self.assertEqual(records[cancel["id"]]["state"], "cancelled")

    def test_siblings_and_transient_loss(self):
        a = d.normalize(feature())
        for reverse in (False, True):
            for cancelled in (False, True):
                with self.subTest(reverse=reverse, cancelled=cancelled):
                    b = copy.deepcopy(a)
                    b.update(id=a["id"] + "-b", references=[a["id"]])
                    c = copy.deepcopy(b)
                    c["id"] = a["id"] + "-c"
                    if cancelled:
                        c["message_type"] = "Cancel"
                    else:
                        c["geometry"] = None
                    siblings = [b, c][:: -1 if reverse else 1]
                    previous, _ = d.reconcile({}, [a], config(), NOW)
                    records, plans = d.reconcile(previous, siblings, config(), NOW)
                    self.assertFalse(plans)
                    self.assertEqual(records[b["id"]]["state"], "active")
                    # A first-observed pair with the same qualifying action plans once.
                    c = copy.deepcopy(b)
                    c["id"] = a["id"] + "-c"
                    siblings = [b, c][:: -1 if reverse else 1]
                    _, plans = d.reconcile({}, siblings, config(), NOW)
                    self.assertEqual(len(plans), 1)
        records, _ = d.reconcile({}, [a], config(), NOW)
        records, _ = d.reconcile(records, [], config(), NOW)
        records, plans = d.reconcile(records, [a], config(), NOW)
        self.assertFalse(plans)
        stale = copy.deepcopy(a)
        stale["expires"] = "2026-11-15T19:59:00Z"
        records, plans = d.reconcile(records, [stale], config(), NOW)
        self.assertFalse(plans)
        update = copy.deepcopy(a)
        update.update(id=a["id"] + "-update", references=[a["id"]])
        records, plans = d.reconcile(records, [update], config(), NOW)
        self.assertFalse(plans)
        cancel = copy.deepcopy(update)
        cancel.update(
            id=a["id"] + "-cancel", references=[update["id"]], message_type="Cancel"
        )
        records, _ = d.reconcile(records, [cancel], config(), NOW)
        renewed = copy.deepcopy(a)
        renewed.update(id=a["id"] + "-new", references=[cancel["id"]])
        _, plans = d.reconcile(records, [renewed], config(), NOW)
        self.assertEqual(len(plans), 1)

    def test_inconsistent_windows_fail_closed(self):
        for changes in (
            {"sent": "2026-11-15T20:02:00Z", "expires": "2026-11-15T20:01:00Z"},
            {"effective": "2026-11-15T21:01:00Z"},
            {"onset": "2026-11-15T20:10:00Z", "ends": "2026-11-15T20:05:00Z"},
            {"effective": "2026-11-15T20:30:00Z", "ends": "2026-11-15T20:20:00Z"},
        ):
            event = d.normalize(feature())
            event.update(changes)
            self.assertFalse(d.qualify(event, config(), NOW)["qualifies"])

    def test_previous_journal_not_mutated(self):
        e = d.normalize(feature())
        records, _ = d.reconcile({}, [e], config(), NOW)
        before = copy.deepcopy(records)
        d.reconcile(records, [], config(), NOW)
        self.assertEqual(records, before)

    def test_merged_action_history_is_bounded(self):
        e = d.normalize(feature())
        e["references"] = [str(i) for i in range(101)]
        records = {
            str(i): {"state": "ineligible", "actions": {str(i): ["new_york_ny"]}}
            for i in range(101)
        }
        e["geometry"] = None
        with self.assertRaises(ValueError):
            d.reconcile(records, [e], config(), NOW)

    def test_antimeridian_fails_closed(self):
        g = {
            "type": "Polygon",
            "coordinates": [[[179, 0], [-179, 0], [-179, 2], [179, 2], [179, 0]]],
        }
        self.assertFalse(d.matches([0, 1], g))

    def test_config_validation(self):
        defaults = c.validate({})
        self.assertEqual(set(defaults["states"]), {"NY", "DC"})
        self.assertEqual(defaults["locations"], {})
        self.assertEqual(defaults["approved_rules"], {})
        self.assertEqual(defaults["phones"], [])
        self.assertFalse(defaults["live_enabled"])
        self.assertFalse(defaults["commissioning_passed"])
        for raw in (
            {"phones": ["notify.bad"]},
            {"live_enabled": "true"},
            {"locations": {"x": {"point": [999, 0]}}},
            {"states": ["NY&bad=1"]},
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                c.validate(raw)


class Services:
    def __init__(self):
        self.calls = []

    async def async_call(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class Delivery(unittest.IsolatedAsyncioTestCase):
    async def test_gates_and_routing(self):
        service = Services()
        cfg = config()
        plan = {
            "id": "alert",
            "fingerprint": "x",
            "event": "Tornado Warning",
            "instruction": "Take shelter",
            "phones": cfg["phones"],
            "affected": ["new_york_ny"],
        }
        items = delivery.targets(plan, cfg, NOW)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[-1]["target"], "media_player.new_york_ny")
        for live, commissioned in [(False, False), (True, False), (False, True)]:
            cfg.update(live_enabled=live, commissioning_passed=commissioned)
            for item in items:
                self.assertIsNone(await delivery.deliver_one(service, item, cfg))
        self.assertEqual(service.calls, [])
        cfg.update(live_enabled=True, commissioning_passed=True)
        for item in items:
            self.assertTrue(await delivery.deliver_one(service, item, cfg))
        self.assertEqual(len(service.calls), 3)
        self.assertEqual(
            service.calls[-1][0][2]["media_player_entity_id"],
            "media_player.new_york_ny",
        )
        self.assertIn("Affected: new_york_ny", service.calls[0][0][2]["message"])
        self.assertIn("Source: alert", service.calls[0][0][2]["message"])

    async def test_phone_url_and_bounded_speaker_instruction(self):
        cfg = config()
        cfg.update(live_enabled=True, commissioning_passed=True)
        url = "https://api.weather.gov/alerts/urn:oid:test"
        instruction = (
            "Take shelter immediately. " + "Remain inside and avoid windows. " * 100
        )
        plan = {
            "id": url,
            "fingerprint": "x",
            "event": "Tornado Warning",
            "instruction": instruction,
            "phones": cfg["phones"],
            "affected": ["new_york_ny"],
        }
        items = delivery.targets(plan, cfg, NOW)
        service = Services()
        await delivery.deliver_one(service, items[0], cfg)
        await delivery.deliver_one(service, items[-1], cfg)
        phone = service.calls[0][0][2]
        speaker = service.calls[1][0][2]["message"]
        self.assertIn(url, phone["message"])
        self.assertEqual(phone["data"]["url"], url)
        self.assertIn("Open source for full instructions.", phone["message"])
        self.assertNotIn(url, speaker)
        self.assertLessEqual(len(speaker), 650)
        self.assertIn(
            "Open the source link in the phone alert for full instructions.", speaker
        )

    async def test_payload_budget_unicode_and_site_specific_speech(self):
        import json

        cfg = config()
        cfg.update(live_enabled=True, commissioning_passed=True)
        for i in range(50):
            cfg["locations"][f"site_{i}"] = {"name": '🌪"\\' * 20, "speakers": []}
        cfg["locations"]["site_0"]["name"] = "New York"
        cfg["locations"]["site_0"]["speakers"] = ["media_player.one"]
        url = "https://api.weather.gov/alerts/urn:oid:" + "a" * 400
        plan = {
            "id": url,
            "fingerprint": "x",
            "event": "🌪" * 100,
            "instruction": '🌊"\\' * 2500,
            "phones": cfg["phones"],
            "affected": [f"site_{i}" for i in range(50)],
        }
        items = delivery.targets(plan, cfg, NOW)
        service = Services()
        await delivery.deliver_one(service, items[0], cfg)
        await delivery.deliver_one(service, items[-1], cfg)
        phone = service.calls[0][0][2]
        spoken = service.calls[1][0][2]["message"]
        self.assertLessEqual(
            len(json.dumps(phone, ensure_ascii=True).encode("utf-8")), 2800
        )
        self.assertIn("Open source for full instructions.", phone["message"])
        self.assertIn(url, phone["message"])
        self.assertEqual(phone["data"]["url"], url)
        self.assertLessEqual(len(spoken), 600)
        self.assertIn("New York", spoken)
        self.assertNotIn(url, spoken)
        self.assertIn("full instructions", spoken)

    def test_pending_retry_bounds_and_cancellation(self):
        from datetime import timedelta

        cfg = config()
        plan = {
            "id": "alert",
            "fingerprint": "x",
            "event": "Tornado Warning",
            "instruction": "Take shelter",
            "phones": cfg["phones"],
            "affected": ["new_york_ny"],
        }
        item = delivery.targets(plan, cfg, NOW)[0]
        records = {
            "alert": {
                "state": "active",
                "fingerprint": "x",
                "affected": ["new_york_ny"],
            }
        }
        self.assertTrue(delivery.pending_valid(item, records, cfg, NOW))
        self.assertFalse(
            delivery.pending_valid({**item, "attempts": 3}, records, cfg, NOW)
        )
        self.assertFalse(
            delivery.pending_valid(item, records, cfg, NOW + timedelta(minutes=16))
        )
        records["alert"]["state"] = "ended_or_absent"
        self.assertFalse(delivery.pending_valid(item, records, cfg, NOW))

    async def test_failed_output_independent(self):
        class Failing(Services):
            async def async_call(self, *args, **kwargs):
                self.calls.append((args, kwargs))
                if args[1] == "mobile_app_one":
                    raise RuntimeError("offline")

        service = Failing()
        cfg = config()
        cfg.update(live_enabled=True, commissioning_passed=True)
        plan = {
            "id": "alert",
            "fingerprint": "x",
            "event": "Tornado Warning",
            "instruction": "Take shelter",
            "phones": cfg["phones"],
            "affected": ["new_york_ny"],
        }
        results = [
            await delivery.deliver_one(service, item, cfg)
            for item in delivery.targets(plan, cfg, NOW)
        ]
        self.assertEqual(results, [False, True, True])


class Content:
    def __init__(self, b):
        self.b = b

    async def iter_chunked(self, n):
        yield self.b


class Response:
    def __init__(self, b, status=200):
        self.content = Content(b)
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class Session:
    def __init__(self, response):
        self.response = response
        self.urls = []

    def get(self, url, **kwargs):
        self.urls.append(url)
        return self.response


class Collector(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_and_failures(self):
        import json

        session = Session(
            Response(
                json.dumps(
                    {"type": "FeatureCollection", "features": [feature()]}
                ).encode()
            )
        )
        result = await collector.fetch(session, ["NY"])
        self.assertEqual(len(result), 1)
        self.assertNotIn("limit=", session.urls[0])
        session = Session(
            Response(json.dumps({"type": "FeatureCollection", "features": []}).encode())
        )
        await collector.fetch(session, ["NY", "DC"])
        self.assertEqual(len(session.urls), 1)
        self.assertIn("area=NY%2CDC", session.urls[0])
        for response in [
            Response(b"{}"),
            Response(b"{}", 503),
            Response(b"x" * (collector.MAX_BYTES + 1)),
        ]:
            with self.assertRaises((ValueError, UnicodeDecodeError)):
                await collector.fetch(Session(response), ["NY"])

    async def test_pagination_rejects_untrusted_origin(self):
        import json

        data = {
            "type": "FeatureCollection",
            "features": [],
            "pagination": {"next": "https://evil.test/alerts"},
        }
        with self.assertRaises(ValueError):
            await collector.fetch(Session(Response(json.dumps(data).encode())), ["NY"])


if __name__ == "__main__":
    unittest.main()
