import copy
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

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
            "sender": "nws@example.test",
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


def cap_event(name, minutes, refs=(), message_type="Update"):
    """Build a complete synthetic CAP message identity and directed references."""
    result = d.normalize(feature())
    url = "https://api.weather.gov/alerts/" + name
    sent = (NOW + timedelta(minutes=minutes)).isoformat()
    result.update(
        id=url,
        sent=sent,
        message_type=message_type,
        cap_identity=["nws@example.test", name, sent],
        references=[ref["id"] for ref in refs],
        reference_identities=[ref["cap_identity"] for ref in refs],
        cap_references_valid=True,
    )
    return result


def cohere(event, *refs):
    """Construct consistent synthetic CAP identity and directed references."""
    sent = d.timestamp(event["sent"])
    if refs:
        sent = max(
            sent, max(d.timestamp(ref["sent"]) for ref in refs) + timedelta(seconds=1)
        )
        if event.get("message_type") == "Alert":
            event["message_type"] = "Update"
    event["sent"] = sent.isoformat()
    identifier = event["id"].split("/alerts/", 1)[1]
    event["cap_identity"] = ["nws@example.test", identifier, event["sent"]]
    event["references"] = [ref["id"] for ref in refs]
    event["reference_identities"] = [ref["cap_identity"] for ref in refs]
    event["cap_references_valid"] = True
    return event


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
        with self.assertRaises(d.OversizedFeature):
            d.normalize(bad)

    def test_observed_nws_cap_tuples_and_conflicting_reference(self):
        # The public projection omits Feature.id; reconstruct only that API URL
        # from the retained property identifier as documented in its provenance.
        path = (
            Path(__file__).resolve().parents[1]
            / "fixtures/cap/nws-observed-segments.json"
        )
        fixture = json.loads(path.read_text(encoding="utf-8"))
        events = []
        for raw in fixture["features"]:
            raw["id"] = "https://api.weather.gov/alerts/" + raw["properties"]["id"]
            event = d.normalize(raw)
            self.assertIsNotNone(event["cap_identity"])
            self.assertEqual(
                len(event["reference_identities"]), len(event["references"])
            )
            self.assertTrue(all(event["reference_identities"]))
            events.append(event)
        # Replay the observed pairs as separate historical polls: their null
        # geometries cannot qualify, and both real Cancel identities persist.
        cancellations = [event for event in events if event["message_type"] == "Cancel"]
        replay_time = datetime(2026, 11, 17, tzinfo=timezone.utc)
        replay, plans = d.reconcile({}, cancellations, config(), replay_time)
        self.assertFalse(plans)
        self.assertEqual(
            sum(bool(record.get("cancel_message")) for record in replay.values()), 2
        )
        self.assertNotEqual(
            replay[cancellations[0]["id"]]["cap_references"],
            replay[cancellations[1]["id"]]["cap_references"],
        )
        updates = [event for event in events if event["message_type"] == "Update"]
        self.assertEqual(len(updates), 2)
        sibling_records, plans = d.reconcile({}, updates, config(), replay_time)
        self.assertFalse(plans)
        self.assertTrue(
            all(
                sibling_records[event["id"]]["state"] == "ineligible"
                for event in updates
            )
        )
        self.assertNotEqual(updates[0]["cap_identity"], updates[1]["cap_identity"])
        self.assertTrue(
            set(map(tuple, updates[0]["reference_identities"]))
            & set(map(tuple, updates[1]["reference_identities"]))
        )
        bad = fixture["features"][0]
        bad["properties"]["references"][0]["identifier"] = "different"
        self.assertIsNone(d.normalize(bad)["reference_identities"][0])

    def test_cancel_replay_and_siblings_use_directed_edges_across_restart(self):
        root = cap_event("root", -5, message_type="Alert")
        a = cap_event("a", -4, [root])
        sibling = cap_event("sibling", -4, [root])
        child = cap_event("child", -3, [a])
        cancel = cap_event("cancel", -2, [a], "Cancel")
        records, _ = d.reconcile({}, [root], config(), NOW)
        records, _ = d.reconcile(records, [a, sibling], config(), NOW)
        records, _ = d.reconcile(records, [child, sibling], config(), NOW)
        for ordered in ([cancel, child, sibling], [sibling, child, cancel]):
            result, plans = d.reconcile(copy.deepcopy(records), ordered, config(), NOW)
            self.assertEqual(result[a["id"]]["state"], "cancelled")
            self.assertEqual(result[child["id"]]["state"], "quarantined")
            self.assertEqual(result[sibling["id"]]["state"], "active")
            self.assertTrue(result[cancel["id"]]["cancel_message"])
            self.assertTrue(all(plan["id"] != child["id"] for plan in plans))
            # Reloading the persisted records cannot turn delayed exact replay into output.
            restored = json.loads(json.dumps(result))
            restored, replay_plans = d.reconcile(restored, [a, sibling], config(), NOW)
            self.assertEqual(restored[a["id"]]["state"], "cancelled")
            self.assertFalse(any(plan["id"] == a["id"] for plan in replay_plans))
            self.assertEqual(restored[sibling["id"]]["state"], "active")

    def test_missing_intermediate_path_is_uncertain_without_blocking_older_sibling(
        self,
    ):
        root = cap_event("old-root", -8, message_type="Alert")
        cancelled = cap_event("cancelled-part", -6, [root])
        missing = cap_event("missing-intermediate", -5, [cancelled])
        unknown = cap_event("unknown-child", -3, [missing, root])
        sibling = cap_event("verified-sibling", -3, [root])
        cancel = cap_event("cancel-part", -2, [cancelled], "Cancel")
        # The missing intermediate was pruned; its timestamp leaves a possible path.
        prior, _ = d.reconcile({}, [root, cancelled], config(), NOW)
        result, plans = d.reconcile(prior, [cancel, unknown, sibling], config(), NOW)
        self.assertEqual(result[unknown["id"]]["state"], "quarantined")
        self.assertEqual(result[sibling["id"]]["state"], "active")
        self.assertFalse(any(plan["id"] == unknown["id"] for plan in plans))

    def test_unrelated_missing_predecessor_stays_eligible_after_cancellation(self):
        target = cap_event("old-target", -10, message_type="Alert")
        cancel = cap_event("old-cancel", -9, [target], "Cancel")
        records, _ = d.reconcile({}, [cancel], config(), NOW)
        absent = cap_event("unrelated-missing", -4, message_type="Alert")
        unrelated = cap_event("unrelated-current", -3, [absent])
        result, plans = d.reconcile(records, [unrelated], config(), NOW)
        self.assertEqual(result[unrelated["id"]]["state"], "active")
        self.assertEqual(len(plans), 1)

    def test_cancellation_component_edges_survive_normal_history_pruning(self):
        root = cap_event("retained-root", -10, message_type="Alert")
        child = cap_event("retained-child", -9, [root])
        cancel = cap_event("retained-cancel", -8, [child], "Cancel")
        records, _ = d.reconcile({}, [root], config(), NOW)
        records, _ = d.reconcile(records, [child], config(), NOW)
        records, _ = d.reconcile(records, [cancel], config(), NOW)
        records.update(
            {
                f"old-{i}": {
                    "state": "ended_or_absent",
                    "actions": {},
                    "updated": (NOW + timedelta(days=1)).isoformat(),
                }
                for i in range(1000)
            }
        )
        result, _ = d.reconcile(records, [], config(), NOW)
        self.assertEqual(len(result), 1000)
        self.assertTrue({root["id"], child["id"], cancel["id"]} <= set(result))

    def test_cancel_arrives_before_target_and_blocks_delayed_exact_replay(self):
        target = cap_event("delayed-target", -5, message_type="Alert")
        cancel = cap_event("first-cancel", -4, [target], "Cancel")
        records, plans = d.reconcile({}, [cancel], config(), NOW)
        self.assertFalse(plans)
        restored = json.loads(json.dumps(records))
        result, plans = d.reconcile(restored, [target], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(result[target["id"]]["state"], "cancelled")
        self.assertTrue(result[cancel["id"]]["cancel_message"])

    def test_equal_time_and_conflicting_tuples_never_claim_cancellation(self):
        target = cap_event("time-target", -5, message_type="Alert")
        for change in ("equal", "sender", "future"):
            with self.subTest(change=change):
                cancel = cap_event("bad-cancel", -4, [target], "Cancel")
                if change == "equal":
                    cancel["sent"] = target["sent"]
                    cancel["cap_identity"][2] = target["cap_identity"][2]
                elif change == "sender":
                    cancel["reference_identities"][0] = [
                        "other@example.test",
                        *target["cap_identity"][1:],
                    ]
                else:
                    cancel["sent"] = (NOW + timedelta(minutes=6)).isoformat()
                    cancel["cap_identity"][2] = cancel["sent"]
                result, plans = d.reconcile({}, [target, cancel], config(), NOW)
                self.assertEqual(result[target["id"]]["state"], "quarantined")
                self.assertFalse(plans)

    def test_later_explicit_renewal_is_independently_evaluated(self):
        root = cap_event("root-renew", -5, message_type="Alert")
        cancel = cap_event("cancel-renew", -4, [root], "Cancel")
        renewal = cap_event("renewal", -3, [cancel, root])
        records, _ = d.reconcile({}, [root], config(), NOW)
        records, _ = d.reconcile(records, [cancel], config(), NOW)
        records, plans = d.reconcile(records, [renewal], config(), NOW)
        self.assertEqual(records[renewal["id"]]["state"], "active")
        self.assertEqual(len(plans), 1)
        bad = cap_event("renewal-invalid", -2, [cancel])
        bad["geometry"] = None
        result, plans = d.reconcile(records, [bad], config(), NOW)
        self.assertEqual(result[bad["id"]]["state"], "ineligible")
        self.assertFalse(plans)

    def test_directed_cancellation_keeps_uncancelled_sibling_separate(self):
        root = cap_event("root", -5, message_type="Alert")
        a = cap_event("a", -4, [root])
        b = cap_event("b", -4, [root])
        child = cap_event("child", -3, [a])
        cancel = cap_event("cancel", -2, [a], "Cancel")
        for batch in ([root, a, b, child, cancel], [cancel, child, b, a, root]):
            groups, _ = d.lineage_index({}, batch)
            direct, uncertain = d.cancellation_evidence({}, batch, groups, NOW)
            self.assertEqual(direct, {a["id"]})
            self.assertEqual(uncertain, {child["id"]})

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
        cohere(e)
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
        cohere(update, e)
        records, plans = d.reconcile(records, [update], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(records[e["id"]]["state"], "superseded")

    def test_expiry_only_update_does_not_repeat(self):
        e = d.normalize(feature())
        records, _ = d.reconcile({}, [e], config(), NOW)
        update = copy.deepcopy(e)
        update["id"] += "-update"
        update["references"] = [e["id"]]
        cohere(update, e)
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
                cohere(b, a)
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
                cohere(c, *(b, a) if reverse else (a, b))
                records, plans = d.reconcile(records, [c], config(), NOW)
                self.assertFalse(plans)
                self.assertEqual(records[b["id"]]["state"], "superseded")
                changed = copy.deepcopy(c)
                changed.update(
                    id=a["id"] + "-d",
                    references=[a["id"], c["id"]],
                    instruction="Take shelter in the basement.",
                )
                cohere(changed, a, c)
                records, plans = d.reconcile(records, [changed], config(), NOW)
                self.assertEqual(len(plans), 1)
                # An old equivalent ancestor must not suppress a changed current action.
                reverted = copy.deepcopy(c)
                reverted.update(id=a["id"] + "-e", references=[a["id"], changed["id"]])
                cohere(reverted, a, changed)
                _, plans = d.reconcile(records, [reverted], config(), NOW)
                self.assertEqual(len(plans), 1)

    def test_lineage_new_site_and_cancellation(self):
        cfg = config()
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], cfg, NOW)
        b = copy.deepcopy(a)
        b.update(id=a["id"] + "-b", references=[a["id"]])
        cohere(b, a)
        records, _ = d.reconcile(records, [b], cfg, NOW)
        cfg["locations"]["second"] = {"point": [0.6, 0.4], "speakers": []}
        c = copy.deepcopy(b)
        c.update(id=a["id"] + "-c", references=[a["id"], b["id"]])
        cohere(c, a, b)
        records, plans = d.reconcile(records, [c], cfg, NOW)
        self.assertEqual(plans[0]["affected"], ["new_york_ny", "second"])
        cancel = copy.deepcopy(c)
        cancel.update(
            id=a["id"] + "-cancel", references=[a["id"], c["id"]], message_type="Cancel"
        )
        records, plans = d.reconcile(records, [cancel], cfg, NOW)
        self.assertFalse(plans)
        # Incomplete legacy tuple data cannot establish the referenced scope.
        self.assertEqual(records[c["id"]]["state"], "quarantined")
        self.assertEqual(records[cancel["id"]]["state"], "cancelled")

    def test_siblings_and_transient_loss(self):
        a = d.normalize(feature())
        for reverse in (False, True):
            for cancelled in (False, True):
                with self.subTest(reverse=reverse, cancelled=cancelled):
                    b = copy.deepcopy(a)
                    b.update(id=a["id"] + "-b", references=[a["id"]])
                    cohere(b, a)
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
                    self.assertEqual(
                        records[b["id"]]["state"],
                        "quarantined" if cancelled else "active",
                    )
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
        renewed_records, plans = d.reconcile(records, [renewed], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(renewed_records[renewed["id"]]["state"], "quarantined")

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
        e["references"] = [str(i) for i in range(100)]
        records = {
            str(i): {
                "state": "ineligible",
                "updated": NOW.isoformat(),
                "actions": {str(i): ["new_york_ny"]},
                "action_identity": d.action_identity(e),
            }
            for i in range(100)
        }
        records["0"]["actions"]["extra"] = ["new_york_ny"]
        e["geometry"] = None
        result, plans = d.reconcile(records, [e], config(), NOW)
        self.assertEqual(result[e["id"]]["state"], "quarantined")
        self.assertFalse(plans)

    def test_cancellation_tombstone_survives_history_quarantine(self):
        event = d.normalize(feature())
        event.update(message_type="Cancel", references=[str(i) for i in range(100)])
        prior = {
            str(i): {
                "state": "ineligible",
                "updated": NOW.isoformat(),
                "actions": {str(i): ["new_york_ny"]},
                "action_identity": d.action_identity(event),
            }
            for i in range(100)
        }
        prior["0"]["actions"]["extra"] = ["new_york_ny"]
        result, plans = d.reconcile(prior, [event], config(), NOW)
        self.assertEqual(result[event["id"]]["state"], "cancelled")
        self.assertTrue(result[event["id"]]["cancel_message"])
        self.assertFalse(plans)

    def test_action_history_overflow_retains_valid_cancellation_evidence(self):
        root = cap_event("overflow-root", -10, message_type="Alert")
        branch = cap_event("overflow-branch", -9, [root])
        cancel = cap_event("overflow-cancel", -2, [branch], "Cancel")
        records, _ = d.reconcile({}, [root], config(), NOW)
        records, _ = d.reconcile(records, [branch], config(), NOW)
        for i in range(100):
            sibling = cap_event(f"overflow-sibling-{i}", -8, [root])
            records[sibling["id"]] = {
                "state": "ineligible",
                "updated": NOW.isoformat(),
                "actions": {f"fingerprint-{i}": ["new_york_ny"]},
                "action_identity": d.action_identity(cancel),
                "lineage": [sibling["id"], root["id"]],
                "cap_identity": sibling["cap_identity"],
                "cap_references": sibling["reference_identities"],
            }
        records[next(key for key in records if "overflow-sibling-" in key)]["actions"][
            "extra"
        ] = ["new_york_ny"]
        result, plans = d.reconcile(records, [cancel], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(result[cancel["id"]]["state"], "quarantined")
        self.assertEqual(
            result[cancel["id"]]["reasons"], ["action history limit exceeded"]
        )
        self.assertTrue(result[cancel["id"]]["cancel_message"])
        self.assertEqual(result[branch["id"]]["state"], "cancelled")

    def test_unknown_legacy_identity_does_not_preserve_changed_ineligible_action(self):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        legacy = records[a["id"]]
        legacy.pop("actions")
        legacy.pop("action_identity")
        b = copy.deepcopy(a)
        b.update(
            id=a["id"] + "-changed",
            references=[a["id"]],
            instruction="No protective action needed.",
        )
        result, plans = d.reconcile(records, [b], config(), NOW)
        self.assertFalse(plans)
        self.assertFalse(result[b["id"]]["actions"])

    def test_current_records_survive_journal_retention_limit(self):
        a = d.normalize(feature())
        prior = {
            f"old-{i}": {
                "state": "ended_or_absent",
                "actions": {},
                "updated": (NOW + timedelta(days=1)).isoformat(),
            }
            for i in range(1000)
        }
        result, _ = d.reconcile(prior, [a], config(), NOW)
        self.assertEqual(len(result), 1000)
        self.assertEqual(result[a["id"]]["state"], "active")

    def test_inactive_quarantine_does_not_restart_history_window(self):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        records, _ = d.reconcile(records, [], config(), NOW + timedelta(minutes=1))
        records, _ = d.reconcile(
            records,
            [],
            config(),
            NOW + timedelta(minutes=2),
            partial=True,
            quarantine_lineages=[[a["id"]]],
        )
        records, _ = d.reconcile(records, [], config(), NOW + timedelta(minutes=20))
        self.assertEqual(records[a["id"]]["state"], "ended_or_absent")
        self.assertEqual(
            records[a["id"]]["inactive_since"], (NOW + timedelta(minutes=1)).isoformat()
        )
        _, plans = d.reconcile(records, [a], config(), NOW + timedelta(minutes=21))
        self.assertEqual(len(plans), 1)

    def test_long_quarantine_preserves_active_action_until_safe_poll(self):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        for minutes in (1, 20, 40):
            records, _ = d.reconcile(
                records,
                [],
                config(),
                NOW + timedelta(minutes=minutes),
                partial=True,
                quarantine_lineages=[[a["id"]]],
            )
        later = NOW + timedelta(minutes=41)
        a["expires"] = (later + timedelta(hours=1)).isoformat()
        a["ends"] = a["expires"]
        result, plans = d.reconcile(records, [a], config(), later)
        self.assertEqual(result[a["id"]]["state"], "active")
        self.assertFalse(plans)

    def test_root_reference_and_reversion_use_current_action(self):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        b = copy.deepcopy(a)
        b.update(id=a["id"] + "-b", references=[a["id"]])
        cohere(b, a)
        records, plans = d.reconcile(records, [b], config(), NOW)
        self.assertFalse(plans)
        c = copy.deepcopy(a)
        c.update(id=a["id"] + "-c", references=[a["id"]])
        cohere(c, a)
        records, plans = d.reconcile(records, [c], config(), NOW)
        self.assertFalse(plans)
        changed = copy.deepcopy(c)
        changed.update(id=a["id"] + "-d", instruction="Take shelter in the basement.")
        cohere(changed, a)
        records, plans = d.reconcile(records, [changed], config(), NOW)
        self.assertEqual(len(plans), 1)
        reverted = copy.deepcopy(a)
        reverted.update(id=a["id"] + "-e", references=[a["id"]])
        cohere(reverted, a)
        _, plans = d.reconcile(records, [reverted], config(), NOW)
        self.assertEqual(len(plans), 1)

    def test_inactive_window_and_changed_unqualified_instruction(self):
        a = d.normalize(feature())
        for loss in ("geometry", "urgency", "absent"):
            for minutes, expected in ((14, 0), (16, 1)):
                with self.subTest(loss=loss, minutes=minutes):
                    records, _ = d.reconcile({}, [a], config(), NOW)
                    b = copy.deepcopy(a)
                    b.update(id=a["id"] + "-b", references=[a["id"]])
                    cohere(b, a)
                    if loss == "geometry":
                        b["geometry"] = None
                    elif loss == "urgency":
                        b["urgency"] = "Future"
                    records, _ = d.reconcile(
                        records, [] if loss == "absent" else [b], config(), NOW
                    )
                    update = copy.deepcopy(a)
                    update.update(
                        id=a["id"] + "-c",
                        references=[a["id"] if loss == "absent" else b["id"]],
                    )
                    cohere(update, a if loss == "absent" else b)
                    _, plans = d.reconcile(
                        records, [update], config(), NOW + timedelta(minutes=minutes)
                    )
                    self.assertEqual(len(plans), expected)
        records, _ = d.reconcile({}, [a], config(), NOW)
        b = copy.deepcopy(a)
        b.update(
            id=a["id"] + "-b",
            references=[a["id"]],
            instruction="No protective action needed.",
        )
        cohere(b, a)
        records, _ = d.reconcile(records, [b], config(), NOW)
        self.assertFalse(records[b["id"]]["actions"])

    def test_legacy_cancellation_relationship_remains_uncertain(self):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        b = copy.deepcopy(a)
        b.update(id=a["id"] + "-b", references=[a["id"]])
        cohere(b, a)
        records, _ = d.reconcile(records, [b], config(), NOW)
        cancel = copy.deepcopy(a)
        cancel.update(
            id=a["id"] + "-cancel", references=[a["id"]], message_type="Cancel"
        )
        records, plans = d.reconcile(records, [cancel], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(records[b["id"]]["state"], "quarantined")
        records, plans = d.reconcile(records, [b], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(records[b["id"]]["state"], "quarantined")

    def test_partial_quarantine_preserves_unrelated_history_and_processes_fresh_alerts(
        self,
    ):
        a = d.normalize(feature())
        records, _ = d.reconcile({}, [a], config(), NOW)
        unrelated = copy.deepcopy(a)
        unrelated["id"] += "-unrelated"
        cohere(unrelated)
        records, plans = d.reconcile(
            records,
            [unrelated],
            config(),
            NOW,
            partial=True,
            quarantine_lineages=[[a["id"] + "-oversize", a["id"]]],
        )
        self.assertEqual(len(plans), 1)
        self.assertEqual(records[a["id"]]["state"], "quarantined")
        self.assertTrue(records[a["id"]]["actions"])
        self.assertEqual(records[unrelated["id"]]["state"], "active")
        returned, plans = d.reconcile(
            records, [a, unrelated], config(), NOW + timedelta(minutes=1)
        )
        self.assertFalse(plans)
        self.assertEqual(returned[a["id"]]["state"], "active")

        other = copy.deepcopy(a)
        other["id"] += "-previous"
        cohere(other)
        prior, _ = d.reconcile({}, [other], config(), NOW)
        result, _ = d.reconcile(prior, [unrelated], config(), NOW, partial=True)
        self.assertEqual(result[other["id"]]["state"], "unconfirmed")
        self.assertTrue(result[other["id"]]["actions"])

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
        self.assertIsNone(defaults["acknowledge_degraded_at"])
        validated = c.validate({"acknowledge_degraded_at": "2026-11-17T10:00:00-05:00"})
        self.assertEqual(
            validated["acknowledge_degraded_at"], "2026-11-17T15:00:00+00:00"
        )
        future_iso = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
        over_len = "2026-11-17T10:00:00Z-" + "x" * 100
        for passthrough, expected in (
            ("2026-11-17T10:00:00", "2026-11-17T10:00:00"),
            ("not-a-timestamp", "not-a-timestamp"),
            (future_iso, future_iso),
            (over_len, over_len[:101]),
        ):
            parsed = c.validate({"acknowledge_degraded_at": passthrough})
            self.assertEqual(parsed["acknowledge_degraded_at"], expected)
        for raw in (
            {"phones": ["notify.bad"]},
            {"live_enabled": "true"},
            {"locations": {"x": {"point": [999, 0]}}},
            {"states": ["NY&bad=1"]},
            {"acknowledge_degraded_at": 123},
            {"acknowledge_degraded_at": "   "},
            {"acknowledge_degraded_at": "2026-11-17T10:00:00Z\n"},
            {"acknowledge_degraded_at": "2026-11-17T10:00:00Z\u007f"},
            {"acknowledge_degraded_at": "2026-11-17T10:00:00Z\u0085"},
            {"acknowledge_degraded_at": "2026-11-17T10:00:00Z\u009f"},
            {"locations": {"x": {"name": "New York\u007f"}}},
            {"locations": {"x": {"name": "New York\u0085"}}},
            {"locations": {"x": {"name": "New York\u009f"}}},
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                c.validate(raw)

    def test_max_acceptance_age_persisted_times_and_cancellation_horizon(self):
        self.assertEqual(d.MAX_ACCEPTANCE_AGE, timedelta(days=7))
        at_limit = d.normalize(feature())
        at_limit["sent"] = (NOW - timedelta(days=7)).isoformat()
        cohere(at_limit)
        self.assertTrue(d.qualify(at_limit, config(), NOW)["qualifies"])
        too_old = d.normalize(feature())
        too_old["sent"] = (NOW - timedelta(days=7, seconds=1)).isoformat()
        cohere(too_old)
        self.assertFalse(d.qualify(too_old, config(), NOW)["qualifies"])

        records, _ = d.reconcile({}, [at_limit], config(), NOW)
        rec = records[at_limit["id"]]
        self.assertEqual(rec["sent"], at_limit["sent"])
        self.assertEqual(rec["expires"], at_limit["expires"])
        self.assertEqual(rec["ends"], at_limit["ends"])
        suspended, _ = d.reconcile(
            records, [], config(), NOW + timedelta(minutes=1), partial=True
        )
        self.assertEqual(suspended[at_limit["id"]]["sent"], at_limit["sent"])
        self.assertEqual(suspended[at_limit["id"]]["expires"], at_limit["expires"])
        self.assertEqual(suspended[at_limit["id"]]["ends"], at_limit["ends"])

        self.assertIsNone(d.cancellation_horizon(["missing"], {}))
        horizon = d.cancellation_horizon(
            ["a", "b"],
            {
                "a": {
                    "sent": NOW.isoformat(),
                    "updated": (NOW + timedelta(days=5)).isoformat(),
                },
                "b": {
                    "cap_references": [
                        ["nws", "id", (NOW + timedelta(hours=3)).isoformat()]
                    ]
                },
            },
        )
        self.assertEqual(horizon, NOW + timedelta(hours=3) + d.MAX_ACCEPTANCE_AGE)
        # Only fall back to `updated` when a record has no source/reference timestamps.
        self.assertEqual(
            d.cancellation_horizon(["u"], {"u": {"updated": NOW.isoformat()}}),
            NOW + d.MAX_ACCEPTANCE_AGE,
        )

    def test_expired_cancellation_component_ages_out_after_horizon(self):
        old_time = NOW - timedelta(days=8)
        prior = {}
        for i in range(1001):
            eid = f"https://api.weather.gov/alerts/old-cancel-{i}"
            prior[eid] = {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [eid],
                "sent": old_time.isoformat(),
                "expires": old_time.isoformat(),
                "ends": old_time.isoformat(),
                "updated": old_time.isoformat(),
                "cap_identity": [
                    "nws@example.test",
                    f"old-cancel-{i}",
                    old_time.isoformat(),
                ],
                "cap_references": [
                    [
                        "nws@example.test",
                        f"old-target-{i}",
                        (old_time - timedelta(minutes=1)).isoformat(),
                    ]
                ],
            }
        fresh = cap_event("fresh-alert", -1, message_type="Alert")
        records, plans = d.reconcile(prior, [fresh], config(), NOW)
        self.assertEqual(len(records), 1000)
        self.assertEqual(records[fresh["id"]]["state"], "active")
        self.assertEqual(len(plans), 1)
        self.assertFalse(any(rec.get("cancel_message") for rec in records.values()))

    def test_historic_uncertainty_and_per_event_quarantine_are_scoped(self):
        root = cap_event("scoped-root", -10, message_type="Alert")
        child = cap_event("scoped-child", -9, [root])
        unrelated = cap_event("scoped-unrelated", -8, message_type="Alert")
        bad_id = cap_event("scoped-bad-id", -7, message_type="Alert")
        bad_id["cap_identity"][1] = "forged"
        cancel = cap_event("scoped-cancel", -6, [root], "Cancel")

        records, _ = d.reconcile({}, [root, unrelated], config(), NOW)
        records, _ = d.reconcile(records, [child, unrelated], config(), NOW)
        # Per-event identity_uncertain does NOT make unrelated absent active alerts unconfirmed.
        records, _ = d.reconcile(records, [bad_id], config(), NOW)
        self.assertEqual(records[bad_id["id"]]["state"], "quarantined")
        self.assertEqual(records[unrelated["id"]]["state"], "ended_or_absent")
        self.assertEqual(records[child["id"]]["state"], "ended_or_absent")

        # Historic cancellation uncertainty quarantines child while cancel is current,
        # then resolves child to ended_or_absent once both leave the feed.
        records2, _ = d.reconcile({}, [root, unrelated], config(), NOW)
        records2, _ = d.reconcile(records2, [child, unrelated], config(), NOW)
        records2, _ = d.reconcile(records2, [cancel, unrelated], config(), NOW)
        self.assertEqual(records2[child["id"]]["state"], "quarantined")
        self.assertEqual(records2[unrelated["id"]]["state"], "active")
        resolved, _ = d.reconcile(
            records2, [unrelated], config(), NOW + timedelta(minutes=1)
        )
        self.assertEqual(resolved[child["id"]]["state"], "ended_or_absent")
        self.assertEqual(resolved[unrelated["id"]]["state"], "active")

    def test_cancel_and_blocked_messages_do_not_supersede_references(self):
        target = cap_event("n1-target", -5, message_type="Alert")
        other = cap_event("n1-other", -5, message_type="Alert")
        records, _ = d.reconcile({}, [target, other], config(), NOW)
        # Future-dated invalid cancel fails cap_event_valid(event, now), isolates uncertain_targets
        # without merging target/other lineages, and stays non-cancelled even after clock catches up.
        bad_cancel = cap_event("n1-cancel", 10, [target, other], "Cancel")
        result, _ = d.reconcile(records, [bad_cancel], config(), NOW)
        self.assertNotEqual(result[other["id"]]["state"], "superseded")
        self.assertEqual(result[bad_cancel["id"]]["lineage"], [bad_cancel["id"]])
        self.assertEqual(
            result[bad_cancel["id"]]["uncertain_targets"],
            sorted([target["id"], other["id"]]),
        )
        self.assertEqual(result[target["id"]]["state"], "quarantined")
        self.assertEqual(result[other["id"]]["state"], "quarantined")
        groups, _ = d.lineage_index(result, [])
        self.assertNotEqual(groups[target["id"]], groups[other["id"]])

        result2, _ = d.reconcile(
            result, [bad_cancel], config(), NOW + timedelta(minutes=15)
        )
        self.assertEqual(result2[target["id"]]["state"], "quarantined")
        self.assertEqual(result2[other["id"]]["state"], "quarantined")

    def test_partial_cancellation_allows_continuing_updates_while_withholding_pre_cancel_actions(
        self,
    ):
        p = cap_event("can-p", -10, message_type="Alert")
        records, plans = d.reconcile({}, [p], config(), NOW)
        self.assertEqual([pl["id"] for pl in plans], [p["id"]])

        # Unchanged continuing update after Cancel withholds repeated pre-cancel action.
        cancel_c = cap_event("can-c", -5, [p], "Cancel")
        u_same = cap_event("can-u-same", -4, [p])
        u_same["instruction"] = p["instruction"]
        res_same, plans_same = d.reconcile(records, [cancel_c, u_same], config(), NOW)
        self.assertEqual(res_same[p["id"]]["state"], "cancelled")
        self.assertEqual(res_same[p["id"]]["cancelled_at"], cancel_c["sent"])
        self.assertEqual(res_same[u_same["id"]]["state"], "quarantined")
        self.assertEqual(plans_same, [])
        self.assertIn(
            res_same[u_same["id"]]["fingerprint"], res_same[u_same["id"]]["actions"]
        )
        res_same_later, plans_same_later = d.reconcile(
            res_same, [cancel_c, u_same], config(), NOW + timedelta(minutes=20)
        )
        self.assertEqual(res_same_later[u_same["id"]]["state"], "quarantined")
        self.assertEqual(plans_same_later, [])

        # Changed qualifying instruction on continuing update after Cancel qualifies and delivers,
        # and subsequent updates stay active without quarantining superseded active updates.
        u_new = cap_event("can-u-new", -4, [p])
        u_new["instruction"] = "Take shelter in a basement immediately."
        res_new, plans_new = d.reconcile(records, [cancel_c, u_new], config(), NOW)
        self.assertEqual(res_new[p["id"]]["state"], "cancelled")
        self.assertEqual(res_new[p["id"]]["cancelled_at"], cancel_c["sent"])
        self.assertEqual(res_new[u_new["id"]]["state"], "active")
        self.assertEqual([pl["id"] for pl in plans_new], [u_new["id"]])

        # Poll 3a: While Cancel C remains in the feed, u2 supersedes u_new cleanly without duplicate plans.
        u2 = cap_event("can-u2", -3, [p, u_new])
        u2["instruction"] = u_new["instruction"]
        res_u2, plans_u2 = d.reconcile(res_new, [cancel_c, u2], config(), NOW)
        self.assertEqual(res_u2[u_new["id"]]["state"], "superseded")
        self.assertEqual(res_u2[u2["id"]]["state"], "active")
        self.assertEqual(plans_u2, [])

        # Poll 3b: Cancel C leaves the feed while P remains cancelled; repeated action still deduplicates.
        res_u2_absent, plans_u2_absent = d.reconcile(res_u2, [u2], config(), NOW)
        self.assertEqual(res_u2_absent[u2["id"]]["state"], "active")
        self.assertEqual(plans_u2_absent, [])

        # Temporary geometry loss on continuing branch marks ineligible and preserves action history on restore.
        u_geom_lost = cap_event("can-u-geom-lost", -2.5, [p, u2])
        u_geom_lost["instruction"] = u_new["instruction"]
        u_geom_lost["geometry"] = None
        res_geom_lost, plans_geom_lost = d.reconcile(
            res_u2_absent, [u_geom_lost], config(), NOW
        )
        self.assertEqual(res_geom_lost[u_geom_lost["id"]]["state"], "ineligible")
        self.assertEqual(plans_geom_lost, [])

        u_restored = cap_event("can-u-restored", -2.2, [p, u_geom_lost])
        u_restored["instruction"] = u_new["instruction"]
        res_restored, plans_restored = d.reconcile(
            res_geom_lost, [u_restored], config(), NOW
        )
        self.assertEqual(res_restored[u_restored["id"]]["state"], "active")
        self.assertEqual(plans_restored, [])

        # Poll 4: New instruction on continuing branch plans once.
        u3 = cap_event("can-u3", -2, [p, u_restored])
        u3["instruction"] = "Take shelter in an interior room on the lowest floor."
        res_u3, plans_u3 = d.reconcile(res_restored, [u3], config(), NOW)
        self.assertEqual(res_u3[u3["id"]]["state"], "active")
        self.assertEqual([pl["id"] for pl in plans_u3], [u3["id"]])

    def test_reconcile_thousand_record_bounded_latency(self):
        import time

        prior = {}
        for i in range(500):
            eid = f"https://api.weather.gov/alerts/scale-act-{i}"
            prior[eid] = {
                "state": "active" if i < 250 else "ended_or_absent",
                "fingerprint": f"fp-{i}",
                "actions": {f"fp-{i}": ["new_york_ny"]},
                "lineage": [eid],
                "sent": (NOW - timedelta(minutes=30)).isoformat(),
                "expires": (NOW + timedelta(hours=1)).isoformat(),
                "ends": (NOW + timedelta(hours=1)).isoformat(),
                "updated": (NOW - timedelta(minutes=10)).isoformat(),
            }
        for i in range(250):
            target_id = f"https://api.weather.gov/alerts/scale-t-{i}"
            cancel_id = f"https://api.weather.gov/alerts/scale-c-{i}"
            target_ev = cap_event(f"scale-t-{i}", -20, message_type="Alert")
            cancel_ev = cap_event(f"scale-c-{i}", -10, [target_ev], "Cancel")
            prior[target_id] = {
                "state": "cancelled",
                "actions": {},
                "lineage": [target_id, cancel_id],
                "cap_identity": target_ev["cap_identity"],
                "cap_references": [],
                "cancel_message": False,
                "cancelled_at": cancel_ev["sent"],
                "sent": target_ev["sent"],
                "expires": target_ev["expires"],
                "ends": target_ev["ends"],
                "updated": (NOW - timedelta(minutes=5)).isoformat(),
            }
            prior[cancel_id] = {
                "state": "cancelled",
                "actions": {},
                "lineage": [cancel_id, target_id],
                "cap_identity": cancel_ev["cap_identity"],
                "cap_references": cancel_ev["reference_identities"],
                "cancel_message": True,
                "cancellation_expired": False,
                "sent": cancel_ev["sent"],
                "expires": cancel_ev["expires"],
                "ends": cancel_ev["ends"],
                "updated": (NOW - timedelta(minutes=5)).isoformat(),
            }
        current = [
            cap_event(f"scale-act-{i}", -2, message_type="Alert") for i in range(100)
        ]
        cfg = config()
        with patch.object(d, "deepcopy", wraps=d.deepcopy) as mock_deepcopy:
            start = time.perf_counter()
            records, _ = d.reconcile(prior, current, cfg, NOW)
            elapsed = time.perf_counter() - start
        mock_deepcopy.assert_called_once()
        self.assertLessEqual(len(records), 1000)
        self.assertLess(elapsed, 0.5)

    def test_normalize_oversized_and_non_string_properties(self):
        oversized = feature()
        oversized["properties"]["instruction"] = "x" * 10001
        with self.assertRaises(d.OversizedFeature):
            d.normalize(oversized)
        bad_type = feature()
        bad_type["properties"]["headline"] = 123
        self.assertIsNone(d.normalize(bad_type))

    def test_safe_url_and_references_ignore_non_string_ids(self):
        for bad in (
            123,
            ["https://api.weather.gov/alerts/1"],
            {"a": 1},
            b"https://api.weather.gov/alerts/1",
        ):
            self.assertIsNone(d.safe_url(bad))
        ev = feature()
        ev["properties"]["references"] = [
            {"@id": 123},
            {"@id": ["https://api.weather.gov/alerts/bad"]},
            {"@id": "https://api.weather.gov/alerts/ok"},
        ]
        normalized = d.normalize(ev)
        self.assertEqual(
            normalized["references"],
            ["https://api.weather.gov/alerts/ok"],
        )

    def test_collector_rejects_excessive_total_features(self):
        state = {
            "events": {},
            "conflicting_ids": set(),
            "id_counts": {},
            "cancel_seen_for_id": set(),
            "unrecoverable_cancel_for_id": set(),
            "quarantined": 0,
            "quarantined_lineages": [],
            "quarantined_cancel_lineages": [],
            "seen_quarantine_ids": set(),
            "quarantine_ambiguous": False,
            "uncertain_cancellation": False,
            "conflicting_cancellation": False,
            "feature_count": collector.MAX_TOTAL_FEATURES,
        }
        payload = json.dumps(
            {"type": "FeatureCollection", "features": [feature()]}
        ).encode()
        with self.assertRaises(ValueError):
            collector._parse_and_collect_page(payload, state)

    def test_partial_cancel_preserves_pre_cancel_actions_across_polls(self):
        cfg = config()
        p = cap_event("pc-p", -10, message_type="Alert")
        rec1, plans1 = d.reconcile({}, [p], cfg, NOW)
        self.assertEqual([pl["id"] for pl in plans1], [p["id"]])

        # Poll 2: partial Cancel arrives first without continuing segment (test both P absent and P present).
        cancel_c = cap_event("pc-c", -5, [p], "Cancel")
        for poll2_events in ([cancel_c], [cancel_c, p]):
            rec2, plans2 = d.reconcile(
                rec1, poll2_events, cfg, NOW + timedelta(minutes=1)
            )
            self.assertEqual(plans2, [])
            self.assertEqual(rec2[p["id"]]["state"], "cancelled")
            self.assertTrue(rec2[p["id"]]["actions"])

            # Poll 3: unreferenced continuing Update repeating pre-cancel action must stay withheld.
            u_same = cap_event("pc-u-same", -4, [p])
            u_same["instruction"] = p["instruction"]
            rec3, plans3 = d.reconcile(rec2, [u_same], cfg, NOW + timedelta(minutes=2))
            self.assertEqual(plans3, [])
            self.assertEqual(rec3[u_same["id"]]["state"], "quarantined")

            # Poll 3 with distinct qualifying instruction must qualify normally as active.
            u_new = cap_event("pc-u-new", -4, [p])
            u_new["instruction"] = "Take shelter in a sturdy building immediately."
            rec4, plans4 = d.reconcile(rec2, [u_new], cfg, NOW + timedelta(minutes=2))
            self.assertEqual([pl["id"] for pl in plans4], [u_new["id"]])
            self.assertEqual(rec4[u_new["id"]]["state"], "active")

    def test_collector_mixed_valid_and_malformed_duplicate_isolation(self):
        target_id = "https://api.weather.gov/alerts/dup-target"
        dup_id = "https://api.weather.gov/alerts/dup-upd"

        def make_state():
            return {
                "events": {},
                "conflicting_ids": set(),
                "malformed_by_id": {},
                "id_counts": {},
                "cancel_seen_for_id": set(),
                "unrecoverable_cancel_for_id": set(),
                "quarantined": 0,
                "quarantined_lineages": [],
                "quarantined_cancel_lineages": [],
                "seen_quarantine_ids": set(),
                "quarantine_ambiguous": False,
                "uncertain_cancellation": False,
                "conflicting_cancellation": False,
                "feature_count": 0,
            }

        valid_upd = feature()
        valid_upd["id"] = dup_id
        valid_upd["properties"]["id"] = dup_id.rsplit("/", 1)[-1]
        valid_upd["properties"]["messageType"] = "Update"
        valid_upd["properties"]["references"] = [{"@id": target_id}]
        malformed_upd = copy.deepcopy(valid_upd)
        malformed_upd["properties"]["headline"] = 123

        for order in ([valid_upd, malformed_upd], [malformed_upd, valid_upd]):
            st = make_state()
            payload = json.dumps(
                {"type": "FeatureCollection", "features": order}
            ).encode()
            collector._parse_and_collect_page(payload, st)
            self.assertNotIn(dup_id, st["events"])
            self.assertEqual(st["quarantined"], 2)
            self.assertFalse(st["conflicting_cancellation"])

        valid_can = copy.deepcopy(valid_upd)
        valid_can["properties"]["messageType"] = "Cancel"
        malformed_bad_ref = copy.deepcopy(valid_upd)
        malformed_bad_ref["properties"]["headline"] = 123
        malformed_bad_ref["properties"]["references"] = ["bad-ref"]
        for order in ([valid_can, malformed_bad_ref], [malformed_bad_ref, valid_can]):
            st = make_state()
            payload = json.dumps(
                {"type": "FeatureCollection", "features": order}
            ).encode()
            collector._parse_and_collect_page(payload, st)
            self.assertNotIn(dup_id, st["events"])
            self.assertTrue(st["conflicting_cancellation"])

    def test_conflicting_cancel_against_persisted_uncertain_targets_quarantines_new_target(
        self,
    ):
        cfg = config()
        a1 = cap_event("unc-a1", -15, message_type="Alert")
        a2 = cap_event("unc-a2", -5, message_type="Alert")
        bad_c1 = cap_event("unc-c1", -10, [a1], "Cancel")
        bad_c1["cap_references_valid"] = False
        rec1, _ = d.reconcile({}, [bad_c1], cfg, NOW)
        self.assertEqual(rec1[bad_c1["id"]]["uncertain_targets"], [a1["id"]])

        conflict_c1 = cap_event("unc-c1", -5, [a2], "Cancel")
        conflict_c1["cap_references_valid"] = True
        rec2, plans2 = d.reconcile(
            rec1, [conflict_c1, a2], cfg, NOW + timedelta(minutes=1)
        )
        self.assertEqual(plans2, [])
        self.assertEqual(rec2[a2["id"]]["state"], "quarantined")

    def test_actual_cancel_with_mixed_valid_and_unrecoverable_refs_is_malformed(self):
        cfg = config()
        target_id = "https://api.weather.gov/alerts/a1"
        for bad_ref in (
            {"@id": "https://api.weather.gov/zones/NYZ072"},
            "not-a-dict",
        ):
            raw = feature()
            raw["properties"]["messageType"] = "Cancel"
            raw["properties"]["references"] = [
                {
                    "@id": target_id,
                    "identifier": "a1",
                    "sender": "w-nws.webmaster@noaa.gov",
                    "sent": raw["properties"]["sent"],
                },
                bad_ref,
            ]
            norm = d.normalize(raw)
            self.assertEqual(norm["references"], [target_id])
            self.assertFalse(norm["references_complete"])
            st = {
                "events": {},
                "conflicting_ids": set(),
                "malformed_by_id": {},
                "id_counts": {},
                "cancel_seen_for_id": set(),
                "unrecoverable_cancel_for_id": set(),
                "quarantined": 0,
                "quarantined_lineages": [],
                "quarantined_cancel_lineages": [],
                "seen_quarantine_ids": set(),
                "quarantine_ambiguous": False,
                "uncertain_cancellation": False,
                "conflicting_cancellation": False,
                "feature_count": 0,
            }
            payload = json.dumps(
                {"type": "FeatureCollection", "features": [raw]}
            ).encode()
            collector._parse_and_collect_page(payload, st)
            self.assertTrue(st["uncertain_cancellation"])
            self.assertTrue(bool(d.qualify(norm, cfg, NOW)))

    def test_activate_preserves_continuing_withheld_quarantine_while_qualifying_new_action(
        self,
    ):
        cfg = config()
        p = cap_event("act-cw-p", -10, message_type="Alert")
        rec1, plans1 = d.reconcile({}, [p], cfg, NOW)
        self.assertEqual([pl["id"] for pl in plans1], [p["id"]])

        cancel_c = cap_event("act-cw-c", -5, [p], "Cancel")
        u_same = cap_event("act-cw-usame", -4, [p])
        u_same["instruction"] = p["instruction"]
        u_new = cap_event("act-cw-unew", -4, [p])
        u_new["instruction"] = "Take shelter in a basement immediately."
        rec2, plans2 = d.reconcile(
            rec1, [cancel_c, u_same, u_new], cfg, NOW, activate=False
        )
        self.assertEqual(rec2[u_same["id"]]["state"], "quarantined")
        self.assertEqual(rec2[u_new["id"]]["state"], "active")
        self.assertEqual([pl["id"] for pl in plans2], [u_new["id"]])

        # Shadow-to-live activation must NOT release continuing_withheld pre-cancellation actions.
        rec3, plans3 = d.reconcile(
            rec2, [u_same, u_new], cfg, NOW + timedelta(minutes=1), activate=True
        )
        self.assertEqual(rec3[u_same["id"]]["state"], "quarantined")
        self.assertEqual(
            rec3[u_same["id"]]["reasons"], ["cancellation scope uncertain"]
        )
        self.assertNotIn(u_same["id"], [pl["id"] for pl in plans3])
        self.assertEqual([pl["id"] for pl in plans3], [u_new["id"]])

        rec4, plans4 = d.reconcile(
            rec3, [u_same, u_new], cfg, NOW + timedelta(minutes=2), activate=False
        )
        self.assertEqual(rec4[u_same["id"]]["state"], "quarantined")
        self.assertEqual(plans4, [])

    def test_expired_absent_cancelled_record_does_not_bridge_or_protect(self):
        cfg = config()
        p = cap_event("exp-can-p", -10, message_type="Alert")
        rec1, _ = d.reconcile({}, [p], cfg, NOW)
        fp1 = rec1[p["id"]]["fingerprint"]

        cancel_t = NOW + timedelta(minutes=1)
        cancel_c = cap_event("exp-can-c", 1, [p], "Cancel")
        rec2, _ = d.reconcile(rec1, [cancel_c], cfg, cancel_t)
        self.assertEqual(rec2[p["id"]]["state"], "cancelled")
        self.assertEqual(rec2[p["id"]]["inactive_since"], cancel_t.isoformat())
        self.assertEqual(rec2[p["id"]]["affected"], [])
        self.assertEqual(list(rec2[p["id"]]["actions"]), [fp1])

        # Verify legacy absent cancelled record lacking inactive_since keeps historical anchor on expiry.
        legacy_id = "https://api.weather.gov/alerts/exp-can-legacy"
        legacy_cancel_id = "https://api.weather.gov/alerts/exp-can-legacy-c"
        later = NOW + d.MAX_ACCEPTANCE_AGE + timedelta(days=1)
        later_min = int((later - NOW).total_seconds() // 60) - 1
        probe_records = {
            **rec2,
            legacy_id: {
                "state": "cancelled",
                "fingerprint": fp1,
                "actions": {fp1: ["new_york_ny"]},
                "lineage": [legacy_id, legacy_cancel_id],
                "cancelled_at": cancel_t.isoformat(),
                "updated": cancel_t.isoformat(),
            },
        }
        probe_prior = {k: dict(v) for k, v in probe_records.items()}
        _, members = d.lineage_index(probe_records, [])
        d._expire_cancellation_horizons(
            probe_prior, probe_records, members, set(), later
        )
        self.assertEqual(probe_records[p["id"]]["state"], "ended_or_absent")
        self.assertEqual(probe_records[p["id"]]["inactive_since"], cancel_t.isoformat())
        self.assertEqual(probe_records[legacy_id]["state"], "ended_or_absent")
        self.assertEqual(
            probe_records[legacy_id]["inactive_since"], cancel_t.isoformat()
        )
        self.assertEqual(probe_prior[legacy_id]["inactive_since"], cancel_t.isoformat())

        # Fresh alert repeating fp1 after 7-day expiry must qualify (not suppressed via stale Day-0 bridge)
        # and the expired absent record is not protected past the 1,000-record cap.
        fresh_ev = cap_event("exp-can-fresh", later_min, [p], "Update")
        fresh_ev["effective"] = fresh_ev["sent"]
        fresh_ev["expires"] = (later + timedelta(hours=1)).isoformat()
        fresh_ev["ends"] = (later + timedelta(hours=1)).isoformat()
        fresh_ev["instruction"] = p["instruction"]
        rec3, plans3 = d.reconcile(rec2, [fresh_ev], cfg, later)
        self.assertEqual([pl["id"] for pl in plans3], [fresh_ev["id"]])

        noise = []
        for idx in range(1005):
            n = cap_event(f"exp-can-noise-{idx}", later_min, message_type="Alert")
            n["effective"] = n["sent"]
            n["expires"] = (later + timedelta(hours=1)).isoformat()
            n["ends"] = (later + timedelta(hours=1)).isoformat()
            n["geometry"] = None
            noise.append(n)
        rec4, _ = d.reconcile(rec2, noise, cfg, later)
        self.assertEqual(len(rec4), 1000)
        self.assertNotIn(p["id"], rec4)

    def test_hidden_actual_alert_persists_empty_cap_references_for_later_cancellation(
        self,
    ):
        cfg = config()
        # Subcase (a): Poll 1 receives Actual Alert A hidden by Actual Update U; Poll 2 receives Cancel C(A)
        # + continuing Update U2(A) with a distinct qualifying protective action.
        a = cap_event("hid-a", -20, message_type="Alert")
        u = cap_event("hid-u", -15, [a], "Update")
        cands1 = d.resolve_candidates({}, [a, u], [a, u], now=NOW)
        self.assertEqual([e["id"] for e in cands1], [u["id"]])
        rec1, _ = d.reconcile({}, cands1, cfg, NOW, graph_events=[a, u])
        self.assertEqual(rec1[a["id"]]["state"], "superseded")
        self.assertEqual(rec1[a["id"]]["cap_references"], [])

        cancel_c = cap_event("hid-c", -10, [a], "Cancel")
        u2 = cap_event("hid-u2", -5, [a], "Update")
        u2["instruction"] = "Take shelter in a basement immediately."
        cands2 = d.resolve_candidates(
            rec1, [cancel_c, u2], [cancel_c, u2], now=NOW + timedelta(minutes=1)
        )
        rec2, plans2 = d.reconcile(
            rec1,
            cands2,
            cfg,
            NOW + timedelta(minutes=1),
            graph_events=[cancel_c, u2],
        )
        self.assertEqual(rec2[a["id"]]["state"], "cancelled")
        self.assertEqual(rec2[u2["id"]]["state"], "active")
        self.assertEqual([pl["id"] for pl in plans2], [u2["id"]])

        # Subcase (b): hidden Actual Alert A + U + sibling S, followed by sibling-only Cancel CU(U).
        a_b = cap_event("hidb-a", -20, message_type="Alert")
        u_b = cap_event("hidb-u", -15, [a_b], "Update")
        s_b = cap_event("hidb-s", -14, [a_b], "Update")
        cands_b1 = d.resolve_candidates({}, [a_b, u_b, s_b], [a_b, u_b, s_b], now=NOW)
        rec_b1, _ = d.reconcile({}, cands_b1, cfg, NOW, graph_events=[a_b, u_b, s_b])
        self.assertEqual(rec_b1[a_b["id"]]["state"], "superseded")
        self.assertEqual(rec_b1[a_b["id"]]["cap_references"], [])

        cu_b = cap_event("hidb-cu", -10, [u_b], "Cancel")
        cands_b2 = d.resolve_candidates(
            rec_b1, [cu_b, s_b], [cu_b, s_b], now=NOW + timedelta(minutes=1)
        )
        rec_b2, _ = d.reconcile(
            rec_b1,
            cands_b2,
            cfg,
            NOW + timedelta(minutes=1),
            graph_events=[cu_b, s_b],
        )
        self.assertEqual(rec_b2[a_b["id"]]["state"], "superseded")
        self.assertEqual(rec_b2[u_b["id"]]["state"], "cancelled")
        self.assertEqual(rec_b2[s_b["id"]]["state"], "active")
        for rec in rec_b2.values():
            self.assertNotIn("cancellation scope uncertain", rec.get("reasons", []))

    def test_duplicate_conflicting_non_cancel_preserves_local_cancel_scope_across_orders(
        self,
    ):
        dup_id = "https://api.weather.gov/alerts/dup-order-x"
        target_id = "https://api.weather.gov/alerts/dup-order-target"

        cancel_with_refs = feature()
        cancel_with_refs["id"] = dup_id
        cancel_with_refs["properties"]["id"] = "dup-order-x"
        cancel_with_refs["properties"]["messageType"] = "Cancel"
        cancel_with_refs["properties"]["references"] = [
            {
                "@id": target_id,
                "identifier": "dup-order-target",
                "sender": "w-nws.webmaster@noaa.gov",
                "sent": cancel_with_refs["properties"]["sent"],
            }
        ]
        alert_copy = feature()
        alert_copy["id"] = dup_id
        alert_copy["properties"]["id"] = "dup-order-x"
        alert_copy["properties"]["messageType"] = "Alert"
        alert_copy["properties"]["references"] = []

        def new_state():
            return {
                "events": {},
                "conflicting_ids": set(),
                "malformed_by_id": {},
                "id_counts": {},
                "cancel_seen_for_id": set(),
                "unrecoverable_cancel_for_id": set(),
                "quarantined": 0,
                "quarantined_lineages": [],
                "quarantined_cancel_lineages": [],
                "seen_quarantine_ids": set(),
                "quarantine_ambiguous": False,
                "uncertain_cancellation": False,
                "conflicting_cancellation": False,
                "feature_count": 0,
            }

        for pages in (
            [[cancel_with_refs, alert_copy, alert_copy]],
            [[alert_copy, alert_copy, cancel_with_refs]],
            [[cancel_with_refs, alert_copy], [alert_copy]],
        ):
            st = new_state()
            for feats in pages:
                payload = json.dumps(
                    {"type": "FeatureCollection", "features": feats}
                ).encode()
                collector._parse_and_collect_page(payload, st)
            self.assertNotIn(dup_id, st["events"])
            self.assertIn(dup_id, st["conflicting_ids"])
            self.assertFalse(st["conflicting_cancellation"])
            self.assertFalse(st["uncertain_cancellation"])
            self.assertTrue(
                any(
                    target_id in lin and dup_id in lin
                    for lin in st["quarantined_cancel_lineages"]
                )
            )

        # Negative control: Cancel lacking recoverable targets still escalates conflicting_cancellation.
        cancel_no_refs = feature()
        cancel_no_refs["id"] = dup_id
        cancel_no_refs["properties"]["id"] = "dup-order-x"
        cancel_no_refs["properties"]["messageType"] = "Cancel"
        cancel_no_refs["properties"]["references"] = []
        st_bad = new_state()
        payload_bad = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [cancel_no_refs, alert_copy, alert_copy],
            }
        ).encode()
        collector._parse_and_collect_page(payload_bad, st_bad)
        self.assertTrue(st_bad["conflicting_cancellation"])

    def test_adv01_quarantined_cancel_persists_tombstone_and_quarantines_target_after_cancel_leaves(
        self,
    ):
        cfg = config()
        alert_a = cap_event("adv01-a", -5, message_type="Alert")
        cancel_over_id = "https://api.weather.gov/alerts/adv01-oversized-cancel"

        # Subcase A: Oversized Actual Cancel (quarantined_cancel_lineages) persists a
        # tombstone and keeps A quarantined on Poll 2 after the Cancel leaves the feed.
        rec1, plans1 = d.reconcile(
            {},
            [alert_a],
            cfg,
            NOW,
            partial=True,
            quarantine_lineages=[[cancel_over_id, alert_a["id"]]],
            quarantine_cancel_lineages=[[cancel_over_id, alert_a["id"]]],
        )
        self.assertEqual(plans1, [])
        self.assertEqual(rec1[alert_a["id"]]["state"], "quarantined")
        self.assertIn(cancel_over_id, rec1)
        tombstone = rec1[cancel_over_id]
        self.assertEqual(tombstone["state"], "cancelled")
        self.assertTrue(tombstone["cancel_message"])
        self.assertFalse(tombstone["cancellation_expired"])
        self.assertEqual(tombstone["uncertain_targets"], [alert_a["id"]])
        self.assertEqual(tombstone["reasons"], ["quarantined cancellation evidence"])

        # Poll 2: Oversized Cancel is absent; A stays quarantined and never fires.
        rec2, plans2 = d.reconcile(rec1, [alert_a], cfg, NOW + timedelta(minutes=1))
        self.assertEqual(plans2, [])
        self.assertEqual(rec2[alert_a["id"]]["state"], "quarantined")
        self.assertIn(cancel_over_id, rec2)
        self.assertEqual(rec2[cancel_over_id]["uncertain_targets"], [alert_a["id"]])

        # Tombstone with uncertain_targets survives a 1,000-record ineligible burst.
        noise = []
        for idx in range(1000):
            ev = cap_event(f"adv01-noise-{idx}", -1, message_type="Alert")
            ev["instruction"] = "Stay tuned for routine updates."
            noise.append(ev)
        rec_burst, plans_burst = d.reconcile(
            rec2, [alert_a, *noise], cfg, NOW + timedelta(minutes=2)
        )
        self.assertEqual(plans_burst, [])
        self.assertEqual(len(rec_burst), 1000)
        self.assertIn(cancel_over_id, rec_burst)
        self.assertIn(alert_a["id"], rec_burst)
        self.assertEqual(rec_burst[alert_a["id"]]["state"], "quarantined")

        # Subcase B: Conflicting-duplicate Cancel against existing persisted Cancel
        # preserves cap_identity/cap_references and merges targets across polls.
        a0 = cap_event("adv01-a0", -15, message_type="Alert")
        a1 = cap_event("adv01-a1", -5, message_type="Alert")
        c_dup = cap_event("adv01-cdup", -10, [a0], "Cancel")
        rec_c1, _ = d.reconcile({}, [c_dup], cfg, NOW)
        orig_cap_id = rec_c1[c_dup["id"]]["cap_identity"]
        orig_cap_refs = rec_c1[c_dup["id"]]["cap_references"]
        rec_c2, plans_c2 = d.reconcile(
            rec_c1,
            [a1],
            cfg,
            NOW + timedelta(minutes=1),
            partial=True,
            quarantine_lineages=[[c_dup["id"], a1["id"]]],
            quarantine_cancel_lineages=[[c_dup["id"], a1["id"]]],
        )
        self.assertEqual(plans_c2, [])
        self.assertEqual(rec_c2[c_dup["id"]]["state"], "cancelled")
        self.assertTrue(rec_c2[c_dup["id"]]["cancel_message"])
        self.assertEqual(rec_c2[c_dup["id"]]["cap_identity"], orig_cap_id)
        self.assertEqual(rec_c2[c_dup["id"]]["cap_references"], orig_cap_refs)
        self.assertEqual(
            rec_c2[c_dup["id"]]["reasons"], ["conflicting cancellation evidence"]
        )
        self.assertEqual(
            rec_c2[c_dup["id"]]["uncertain_targets"], sorted([a0["id"], a1["id"]])
        )
        rec_c3, plans_c3 = d.reconcile(
            rec_c2, [a0, a1], cfg, NOW + timedelta(minutes=2)
        )
        self.assertEqual(plans_c3, [])
        self.assertEqual(rec_c3[a0["id"]]["state"], "quarantined")
        self.assertEqual(rec_c3[a1["id"]]["state"], "quarantined")

        # Subcase C: Quarantined Cancel colliding with existing persisted Alert
        # suspends it with list[str] uncertain_targets (and omits key when empty).
        c_alert = cap_event("adv01-calert", -10, message_type="Alert")
        a2 = cap_event("adv01-a2", -5, message_type="Alert")
        rec_a1, _ = d.reconcile({}, [c_alert], cfg, NOW)
        rec_a2, plans_a2 = d.reconcile(
            rec_a1,
            [a2],
            cfg,
            NOW + timedelta(minutes=1),
            partial=True,
            quarantine_lineages=[[c_alert["id"], a2["id"]]],
            quarantine_cancel_lineages=[[c_alert["id"], a2["id"]]],
        )
        self.assertEqual(plans_a2, [])
        self.assertEqual(rec_a2[c_alert["id"]]["state"], "quarantined")
        self.assertFalse(rec_a2[c_alert["id"]]["cancel_message"])
        self.assertEqual(
            rec_a2[c_alert["id"]]["reasons"], ["conflicting cancellation evidence"]
        )
        self.assertEqual(rec_a2[c_alert["id"]]["uncertain_targets"], [a2["id"]])
        rec_a3, plans_a3 = d.reconcile(rec_a2, [a2], cfg, NOW + timedelta(minutes=2))
        self.assertEqual(plans_a3, [])
        self.assertEqual(rec_a3[a2["id"]]["state"], "quarantined")

        rec_empty, _ = d.reconcile(
            rec_a1,
            [],
            cfg,
            NOW + timedelta(minutes=1),
            partial=True,
            quarantine_lineages=[[c_alert["id"]]],
            quarantine_cancel_lineages=[[c_alert["id"]]],
        )
        self.assertNotIn("uncertain_targets", rec_empty[c_alert["id"]])

    def test_adv02_conflicting_cancel_against_persisted_alert_and_expired_cancel_persists_uncertain_targets(
        self,
    ):
        cfg = config()
        # Subcase A: Conflicting Cancel reusing an existing persisted Alert ID.
        x_alert = cap_event("adv02-x", -10, message_type="Alert")
        y_alert = cap_event("adv02-y", -5, message_type="Alert")
        rec1, plans1 = d.reconcile({}, [x_alert], cfg, NOW)
        self.assertEqual([pl["id"] for pl in plans1], [x_alert["id"]])

        cancel_reusing_x = cap_event("adv02-x", -2, [y_alert], "Cancel")
        rec2, plans2 = d.reconcile(
            rec1, [cancel_reusing_x, y_alert], cfg, NOW + timedelta(minutes=1)
        )
        self.assertEqual(plans2, [])
        self.assertEqual(rec2[x_alert["id"]]["state"], "quarantined")
        self.assertFalse(rec2[x_alert["id"]]["cancel_message"])
        self.assertEqual(rec2[x_alert["id"]]["uncertain_targets"], [y_alert["id"]])
        self.assertEqual(rec2[y_alert["id"]]["state"], "quarantined")

        # Poll 3: Conflicting Cancel leaves; Y must stay quarantined.
        rec3, plans3 = d.reconcile(rec2, [y_alert], cfg, NOW + timedelta(minutes=2))
        self.assertEqual(plans3, [])
        self.assertEqual(rec3[y_alert["id"]]["state"], "quarantined")
        self.assertEqual(rec3[x_alert["id"]]["uncertain_targets"], [y_alert["id"]])

        # Subcase B: Conflicting Cancel reusing a Day-0 expired Cancel ID.
        x0 = cap_event("adv02-x0", -20, message_type="Alert")
        c_day0 = cap_event("adv02-cexp", -10, [x0], "Cancel")
        rec_d0, _ = d.reconcile({}, [x0, c_day0], cfg, NOW)
        day8 = NOW + d.MAX_ACCEPTANCE_AGE + timedelta(days=1)
        rec_d8_exp, _ = d.reconcile(rec_d0, [], cfg, day8)
        self.assertFalse(rec_d8_exp[c_day0["id"]]["cancel_message"])
        self.assertTrue(rec_d8_exp[c_day0["id"]]["cancellation_expired"])

        day8_min = int((day8 - NOW).total_seconds() // 60)
        y2 = cap_event("adv02-y2", day8_min - 5, message_type="Alert")
        y2["effective"] = y2["sent"]
        y2["onset"] = y2["sent"]
        y2["expires"] = (day8 + timedelta(hours=1)).isoformat()
        y2["ends"] = (day8 + timedelta(hours=1)).isoformat()

        cancel_reusing_expired = cap_event("adv02-cexp", day8_min - 1, [y2], "Cancel")
        cancel_reusing_expired["effective"] = cancel_reusing_expired["sent"]
        cancel_reusing_expired["expires"] = (day8 + timedelta(hours=1)).isoformat()
        cancel_reusing_expired["ends"] = (day8 + timedelta(hours=1)).isoformat()

        rec_p2, plans_p2 = d.reconcile(
            rec_d8_exp,
            [cancel_reusing_expired, y2],
            cfg,
            day8 + timedelta(minutes=1),
        )
        self.assertEqual(plans_p2, [])
        self.assertEqual(rec_p2[c_day0["id"]]["state"], "quarantined")
        self.assertFalse(rec_p2[c_day0["id"]]["cancel_message"])
        self.assertEqual(rec_p2[c_day0["id"]]["uncertain_targets"], [y2["id"]])
        self.assertEqual(rec_p2[y2["id"]]["state"], "quarantined")

        # Poll 3: Conflicting Cancel leaves; 7-day horizon anchored to Day-8 observation
        # prevents immediate expiry and keeps Y2 quarantined.
        rec_p3, plans_p3 = d.reconcile(rec_p2, [y2], cfg, day8 + timedelta(minutes=2))
        self.assertEqual(plans_p3, [])
        self.assertEqual(rec_p3[y2["id"]]["state"], "quarantined")
        self.assertEqual(rec_p3[c_day0["id"]]["uncertain_targets"], [y2["id"]])

        # Non-cancel collision against expired Cancel must not store uncertain_targets=None.
        alert_reusing_expired = cap_event(
            "adv02-cexp", day8_min - 1, message_type="Alert"
        )
        rec_non_cancel, _ = d.reconcile(
            rec_d8_exp, [alert_reusing_expired], cfg, day8 + timedelta(minutes=1)
        )
        self.assertNotIn("uncertain_targets", rec_non_cancel[c_day0["id"]])

    def test_adv04_collector_late_cancel_promotes_refs_and_overflow_order_independent(
        self,
    ):
        cfg = config()
        alert_a_id = "https://api.weather.gov/alerts/adv04-a"
        target_b_id = "https://api.weather.gov/alerts/adv04-b"
        target_c_id = "https://api.weather.gov/alerts/adv04-c"
        dup_x_id = "https://api.weather.gov/alerts/adv04-x"

        def raw_msg(
            fid,
            msg_type,
            refs,
            *,
            sent="2026-11-15T19:56:00Z",
            instruction="Take shelter now.",
        ):
            f = feature()
            f["id"] = fid
            f["properties"]["id"] = fid.rsplit("/", 1)[-1]
            f["properties"]["messageType"] = msg_type
            f["properties"]["sent"] = sent
            f["properties"]["instruction"] = instruction
            f["properties"]["references"] = [
                {
                    "@id": r,
                    "identifier": r.rsplit("/", 1)[-1],
                    "sender": "nws@example.test",
                    "sent": "2026-11-15T19:55:00Z",
                }
                for r in refs
            ]
            return f

        def new_state():
            return {
                "events": {},
                "conflicting_ids": set(),
                "malformed_by_id": {},
                "id_counts": {},
                "cancel_seen_for_id": set(),
                "unrecoverable_cancel_for_id": set(),
                "quarantined": 0,
                "quarantined_lineages": [],
                "quarantined_cancel_lineages": [],
                "seen_quarantine_ids": set(),
                "quarantine_ambiguous": False,
                "uncertain_cancellation": False,
                "conflicting_cancellation": False,
                "feature_count": 0,
            }

        # Trace A: [A, f1, f2, f3] vs [A, f3, f1, f2] where f1 & f2 are conflicting
        # non-cancels referencing A & B, and f3 is a late Actual Cancel referencing C.
        feat_a = raw_msg(alert_a_id, "Alert", [], sent="2026-11-15T19:55:00Z")
        f1 = raw_msg(dup_x_id, "Update", [alert_a_id], sent="2026-11-15T19:56:00Z")
        f2 = raw_msg(
            dup_x_id,
            "Update",
            [target_b_id],
            sent="2026-11-15T19:57:00Z",
            instruction="Take shelter in a basement now.",
        )
        f3 = raw_msg(dup_x_id, "Cancel", [target_c_id], sent="2026-11-15T19:58:00Z")

        for order in ([feat_a, f1, f2, f3], [feat_a, f3, f1, f2]):
            st = new_state()
            payload = json.dumps(
                {"type": "FeatureCollection", "features": order}
            ).encode()
            collector._parse_and_collect_page(payload, st)
            self.assertNotIn(dup_x_id, st["events"])
            self.assertIn(alert_a_id, st["events"])
            self.assertFalse(st["conflicting_cancellation"])
            self.assertFalse(st["uncertain_cancellation"])
            promoted_targets = {
                target
                for lin in st["quarantined_cancel_lineages"]
                if lin and lin[0] == dup_x_id
                for target in lin[1:]
            }
            self.assertEqual(promoted_targets, {alert_a_id, target_b_id, target_c_id})

            # End-to-end: A is quarantined on Poll 1 and stays quarantined on Poll 2.
            events_p1 = list(st["events"].values())
            rec1, plans1 = d.reconcile(
                {},
                events_p1,
                cfg,
                NOW,
                partial=True,
                quarantine_lineages=st["quarantined_lineages"],
                quarantine_cancel_lineages=st["quarantined_cancel_lineages"],
            )
            self.assertEqual(plans1, [])
            self.assertEqual(rec1[alert_a_id]["state"], "quarantined")
            self.assertEqual(
                rec1[dup_x_id]["uncertain_targets"],
                sorted([alert_a_id, target_b_id, target_c_id]),
            )
            rec2, plans2 = d.reconcile(rec1, events_p1, cfg, NOW + timedelta(minutes=1))
            self.assertEqual(plans2, [])
            self.assertEqual(rec2[alert_a_id]["state"], "quarantined")

        # Trace B: 5,000-ID overflow [f1, f2, f3] vs [f3, f1, f2] must set
        # conflicting_cancellation in BOTH orders even when f3 only references an
        # already-tracked ID.
        ov_x_id = "https://api.weather.gov/alerts/adv04-ov-x"
        ov_refs_1 = [f"https://api.weather.gov/alerts/adv04-r-{i}" for i in range(3000)]
        ov_refs_2 = [
            f"https://api.weather.gov/alerts/adv04-r-{i}" for i in range(3000, 5500)
        ]
        ov_f1 = feature()
        ov_f1["id"] = ov_x_id
        ov_f1["properties"]["id"] = "adv04-ov-x"
        ov_f1["properties"]["messageType"] = "Update"
        ov_f1["properties"]["references"] = [{"@id": r} for r in ov_refs_1]
        ov_f2 = feature()
        ov_f2["id"] = ov_x_id
        ov_f2["properties"]["id"] = "adv04-ov-x"
        ov_f2["properties"]["messageType"] = "Update"
        ov_f2["properties"]["references"] = [{"@id": r} for r in ov_refs_2]
        ov_f3 = raw_msg(ov_x_id, "Cancel", [ov_refs_1[0]], sent="2026-11-15T19:58:00Z")

        for order in ([ov_f1, ov_f2, ov_f3], [ov_f3, ov_f1, ov_f2]):
            st = new_state()
            payload = json.dumps(
                {"type": "FeatureCollection", "features": order}
            ).encode()
            collector._parse_and_collect_page(payload, st)
            self.assertTrue(st["quarantine_ambiguous"])
            self.assertTrue(st["conflicting_cancellation"])
            self.assertIn(ov_x_id, st["overflowed_ids"])

    def test_adv05_conflicting_prior_cancel_quarantines_renewal_and_continuing_update_on_poll2_and_poll3(
        self,
    ):
        cfg = config()
        alert_a = cap_event("adv05-a", -20, message_type="Alert")
        alert_b = cap_event("adv05-b", -18, message_type="Alert")
        cancel_c = cap_event("adv05-c", -15, [alert_a], "Cancel")

        # Poll 1: Valid Cancel C cancels Alert A.
        rec1, plans1 = d.reconcile(
            {}, [alert_a, cancel_c], cfg, NOW, graph_events=[alert_a, cancel_c]
        )
        self.assertEqual(plans1, [])
        self.assertEqual(rec1[alert_a["id"]]["state"], "cancelled")
        self.assertTrue(rec1[cancel_c["id"]]["cancel_message"])
        self.assertNotIn("uncertain_targets", rec1[cancel_c["id"]])

        # Poll 2: Conflicting Cancel reusing ID C (targeting B) arrives alongside
        # Renewal R referencing C and Continuing Update U referencing A.
        conflict_c = cap_event("adv05-c", -12, [alert_b], "Cancel")
        renewal_r = cap_event("adv05-r", -5, [cancel_c], "Update")
        renewal_r["instruction"] = "Take shelter in an interior room immediately."
        cont_u = cap_event("adv05-u", -4, [alert_a], "Update")
        cont_u["instruction"] = "Take shelter in a basement immediately."

        rec2, plans2 = d.reconcile(
            rec1,
            [conflict_c, renewal_r, cont_u],
            cfg,
            NOW + timedelta(minutes=1),
            graph_events=[conflict_c, renewal_r, cont_u],
        )
        self.assertEqual(plans2, [])
        self.assertEqual(rec2[renewal_r["id"]]["state"], "quarantined")
        self.assertEqual(rec2[cont_u["id"]]["state"], "quarantined")
        self.assertEqual(
            rec2[cancel_c["id"]]["uncertain_targets"],
            sorted([alert_a["id"], alert_b["id"]]),
        )

        # Poll 3: Conflicting Cancel leaves; R and U remain quarantined (matching Poll 2).
        rec3, plans3 = d.reconcile(
            rec2,
            [renewal_r, cont_u],
            cfg,
            NOW + timedelta(minutes=2),
            graph_events=[renewal_r, cont_u],
        )
        self.assertEqual(plans3, [])
        self.assertEqual(rec3[renewal_r["id"]]["state"], "quarantined")
        self.assertEqual(rec3[cont_u["id"]]["state"], "quarantined")

        # Also verify conflicting non-Cancel Alert reusing ID C (empty incoming refs)
        # persists prior cap_references as uncertain_targets and quarantines R & U on Poll 2 and Poll 3.
        conflict_alert_c = cap_event("adv05-c", -12, message_type="Alert")
        rec2_alt, plans2_alt = d.reconcile(
            rec1,
            [conflict_alert_c, renewal_r, cont_u],
            cfg,
            NOW + timedelta(minutes=1),
            graph_events=[conflict_alert_c, renewal_r, cont_u],
        )
        self.assertEqual(plans2_alt, [])
        self.assertEqual(rec2_alt[renewal_r["id"]]["state"], "quarantined")
        self.assertEqual(rec2_alt[cont_u["id"]]["state"], "quarantined")
        self.assertEqual(rec2_alt[cancel_c["id"]]["uncertain_targets"], [alert_a["id"]])

        rec3_alt, plans3_alt = d.reconcile(
            rec2_alt,
            [renewal_r, cont_u],
            cfg,
            NOW + timedelta(minutes=2),
            graph_events=[renewal_r, cont_u],
        )
        self.assertEqual(plans3_alt, [])
        self.assertEqual(rec3_alt[renewal_r["id"]]["state"], "quarantined")
        self.assertEqual(rec3_alt[cont_u["id"]]["state"], "quarantined")


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
    async def test_conflicting_update_cannot_hide_or_connect_valid_alert(self):
        good = feature()
        forged = copy.deepcopy(good)
        forged["id"] += "-forged"
        forged["properties"].update(
            id=good["properties"]["id"] + "-forged",
            messageType="Update",
            sent="2026-11-15T19:56:00Z",
            references=[
                {
                    "@id": good["id"],
                    "identifier": good["properties"]["id"],
                    "sender": "other@example.test",
                    "sent": good["properties"]["sent"],
                }
            ],
        )
        body = {"type": "FeatureCollection", "features": [good, forged]}
        result = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual({event["id"] for event in result}, {good["id"], forged["id"]})
        records, plans = d.reconcile(
            {}, result, config(), NOW, graph_events=result.all_events
        )
        self.assertEqual(records[good["id"]]["state"], "active")
        self.assertEqual(records[forged["id"]]["state"], "quarantined")
        self.assertEqual([plan["id"] for plan in plans], [good["id"]])
        # The forged edge must not reappear through persisted lineage on restart.
        restored = json.loads(json.dumps(records))
        groups, _ = d.lineage_index(restored, [])
        self.assertNotEqual(groups[good["id"]], groups[forged["id"]])
        replay, plans = d.reconcile(
            restored, result, config(), NOW, graph_events=result.all_events
        )
        self.assertEqual(replay[good["id"]]["state"], "active")
        self.assertFalse(plans)

    async def test_one_conflicting_reference_removes_all_supersession_authority(self):
        first = feature()
        second = copy.deepcopy(first)
        second["id"] += "-second"
        second["properties"]["id"] += "-second"
        update = copy.deepcopy(first)
        update["id"] += "-update"
        update["properties"].update(
            id=first["properties"]["id"] + "-update",
            messageType="Update",
            sent="2026-11-15T19:56:00Z",
            references=[
                {
                    "@id": first["id"],
                    "identifier": first["properties"]["id"],
                    "sender": first["properties"]["sender"],
                    "sent": first["properties"]["sent"],
                },
                {
                    "@id": second["id"],
                    "identifier": second["properties"]["id"],
                    "sender": "other@example.test",
                    "sent": second["properties"]["sent"],
                },
            ],
        )
        body = {"type": "FeatureCollection", "features": [first, second, update]}
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual(
            {event["id"] for event in events}, {first["id"], second["id"], update["id"]}
        )
        records, plans = d.reconcile(
            {}, events, config(), NOW, graph_events=events.all_events
        )
        self.assertEqual(records[first["id"]]["state"], "active")
        self.assertEqual(records[second["id"]]["state"], "active")
        self.assertEqual(records[update["id"]]["state"], "quarantined")
        self.assertEqual({plan["id"] for plan in plans}, {first["id"], second["id"]})

    async def test_superseded_messages_and_oversized_cancel_remain_evidence(self):
        predecessor = feature()
        successor = copy.deepcopy(predecessor)
        successor["id"] += "-update"
        successor["properties"]["id"] += "-update"
        successor["properties"]["messageType"] = "Update"
        successor["properties"]["sent"] = "2026-11-15T19:56:00Z"
        successor["properties"]["references"] = [
            {
                "@id": predecessor["id"],
                "identifier": predecessor["properties"]["id"],
                "sender": predecessor["properties"]["sender"],
                "sent": predecessor["properties"]["sent"],
            }
        ]
        cancel = copy.deepcopy(predecessor)
        cancel["id"] += "-cancel"
        cancel["properties"].update(
            messageType="Cancel", references=[{"@id": predecessor["id"]}] * 101
        )
        body = {
            "type": "FeatureCollection",
            "features": [predecessor, successor, cancel],
        }
        result = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual(
            {e["id"] for e in result}, {predecessor["id"], successor["id"]}
        )
        self.assertEqual(
            [e["id"] for e in d.resolve_candidates({}, result, result.all_events)],
            [successor["id"]],
        )
        self.assertEqual(
            {e["id"] for e in result.all_events}, {predecessor["id"], successor["id"]}
        )
        self.assertFalse(result.uncertain_cancellation)
        self.assertEqual(
            result.quarantined_cancel_lineages, [[cancel["id"], predecessor["id"]]]
        )

    async def test_failed_pagination_and_cancelled_error_after_cancel_propagate(self):
        import asyncio

        cancel = feature()
        cancel["properties"]["messageType"] = "Cancel"
        body = {
            "type": "FeatureCollection",
            "features": [cancel],
            "pagination": {
                "next": "https://api.weather.gov/alerts/active?cursor=repeat"
            },
        }
        with self.assertRaises(ValueError):
            await collector.fetch(Session(Response(json.dumps(body).encode())), ["NY"])

        class CancelSession:
            def get(self, url, **kwargs):
                raise asyncio.CancelledError()

        with self.assertRaises(asyncio.CancelledError):
            await collector.fetch(CancelSession(), ["NY"])

    async def test_malformed_single_feature_is_quarantined_without_failing_collection(
        self,
    ):
        bad_prop = feature()
        bad_prop["id"] += "-bad-prop"
        bad_prop["properties"]["headline"] = 123
        bad_prop["properties"]["references"] = [{"@id": feature()["id"]}]

        oversized_prop = feature()
        oversized_prop["id"] += "-oversize-prop"
        oversized_prop["properties"]["instruction"] = "x" * 10001
        oversized_prop["properties"]["references"] = [{"@id": feature()["id"]}]

        bad_id = feature()
        bad_id["id"] = "https://evil.test/alerts/123"

        body = {
            "type": "FeatureCollection",
            "features": [bad_prop, oversized_prop, feature()],
        }
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual((len(events), events.quarantined), (1, 2))
        self.assertFalse(events.quarantine_ambiguous)
        self.assertEqual(len(events.quarantined_lineages), 2)

        body_ambiguous = {"type": "FeatureCollection", "features": [bad_id, feature()]}
        events_ambiguous = await collector.fetch(
            Session(Response(json.dumps(body_ambiguous).encode())), ["NY"]
        )
        self.assertEqual((len(events_ambiguous), events_ambiguous.quarantined), (1, 1))
        self.assertTrue(events_ambiguous.quarantine_ambiguous)

        oversized_cancel = feature()
        oversized_cancel["id"] += "-oversize-cancel"
        oversized_cancel["properties"].update(
            messageType="Cancel",
            instruction="x" * 10001,
            references=[{"@id": feature()["id"]}],
        )
        events_cancel = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "features": [oversized_cancel, feature()],
                        }
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertFalse(events_cancel.uncertain_cancellation)
        self.assertFalse(events_cancel.quarantine_ambiguous)
        self.assertEqual((len(events_cancel), events_cancel.quarantined), (1, 1))
        self.assertEqual(
            events_cancel.quarantined_cancel_lineages,
            [[oversized_cancel["id"], feature()["id"]]],
        )

        empty_ref_cancel = feature()
        empty_ref_cancel["id"] += "-empty-ref-cancel"
        empty_ref_cancel["properties"].update(
            id=feature()["properties"]["id"] + "-empty-ref-cancel",
            messageType="Cancel",
            references=[],
        )
        events_empty_cancel = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "features": [empty_ref_cancel, feature()],
                        }
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertTrue(events_empty_cancel.uncertain_cancellation)

    async def test_update_rejected_against_prior_restores_hidden_predecessor(self):
        first = feature()
        second = copy.deepcopy(first)
        second["id"] += "-update"
        second["properties"].update(
            id=first["properties"]["id"] + "-update",
            messageType="Update",
            sent="2026-11-15T19:56:00Z",
            references=[
                {
                    "@id": first["id"],
                    "identifier": first["properties"]["id"],
                    "sender": first["properties"]["sender"],
                    "sent": first["properties"]["sent"],
                }
            ],
        )
        # Collector returns [first, second]; clean candidate resolution hides `first`.
        events = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {"type": "FeatureCollection", "features": [first, second]}
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertEqual({e["id"] for e in events}, {first["id"], second["id"]})
        self.assertEqual(
            [e["id"] for e in d.resolve_candidates({}, events, events.all_events)],
            [second["id"]],
        )
        # Prior state had a conflicting identity for `second`, so `second` is invalid in reconcile.
        prior = {
            second["id"]: {
                "state": "ineligible",
                "cap_identity": [
                    "other@example.test",
                    second["properties"]["id"],
                    second["properties"]["sent"],
                ],
                "updated": NOW.isoformat(),
            }
        }
        restored = d.resolve_candidates(prior, events, events.all_events)
        self.assertEqual({e["id"] for e in restored}, {first["id"], second["id"]})
        records, plans = d.reconcile(
            prior, events, config(), NOW, graph_events=events.all_events
        )
        self.assertEqual(records[first["id"]]["state"], "active")
        self.assertEqual(records[second["id"]]["state"], "quarantined")
        self.assertEqual([p["id"] for p in plans], [first["id"]])

    def test_conflicting_cancel_preserves_prior_cancellation_evidence(self):
        t1 = cap_event("h2-t1", -10, message_type="Alert")
        t2 = cap_event("h2-t2", -9, message_type="Alert")
        c = cap_event("h2-c", -5, [t1], "Cancel")
        records, _ = d.reconcile({}, [t1, t2, c], config(), NOW)
        self.assertEqual(records[t1["id"]]["state"], "cancelled")
        self.assertEqual(records[t2["id"]]["state"], "active")

        c_conflict = copy.deepcopy(c)
        c_conflict["references"] = [t2["id"]]
        c_conflict["reference_identities"] = [t2["cap_identity"]]
        updated, plans = d.reconcile(records, [c_conflict, t2], config(), NOW)
        self.assertFalse(plans)
        self.assertEqual(updated[c["id"]]["state"], "cancelled")
        self.assertTrue(updated[c["id"]]["cancel_message"])
        self.assertEqual(updated[c["id"]]["cap_references"], c["reference_identities"])
        self.assertEqual(updated[t1["id"]]["state"], "cancelled")
        self.assertEqual(updated[t2["id"]]["state"], "quarantined")

        # Even if c_conflict leaves, t1 replay stays cancelled under preserved evidence.
        replayed, replay_plans = d.reconcile(
            updated, [t1], config(), NOW + timedelta(minutes=1)
        )
        self.assertFalse(replay_plans)
        self.assertEqual(replayed[t1["id"]]["state"], "cancelled")

    async def test_conflicting_duplicate_feature_quarantines_without_failing_poll(self):
        first = feature()
        dup = copy.deepcopy(first)
        dup["properties"]["headline"] = "Different duplicate payload"
        dup3 = copy.deepcopy(first)
        dup3["properties"]["headline"] = "Third duplicate payload"
        valid = feature()
        valid["id"] += "-valid"
        valid["properties"]["id"] += "-valid"
        events = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "features": [first, dup, dup3, valid],
                        }
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertEqual([e["id"] for e in events], [valid["id"]])
        self.assertEqual(events.quarantined, 3)
        self.assertEqual(events.source_count, 4)
        self.assertFalse(events.conflicting_cancellation)

        c1 = feature()
        c1["properties"]["messageType"] = "Cancel"
        c2 = copy.deepcopy(c1)
        c2["properties"]["headline"] = "Conflicting cancel copy"
        events_cancel = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {"type": "FeatureCollection", "features": [c1, c2, valid]}
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertEqual([e["id"] for e in events_cancel], [valid["id"]])
        self.assertTrue(events_cancel.conflicting_cancellation)

    async def test_conflicting_identical_triplicate_and_5000_id_cap(self):
        # Duplicate copies plus a conflicting third copy quarantine all three instances.
        a1 = feature()
        a2 = copy.deepcopy(a1)
        a_conflict = copy.deepcopy(a1)
        a_conflict["properties"]["headline"] = "Conflicting third copy"
        valid = feature()
        valid["id"] += "-ok"
        valid["properties"]["id"] += "-ok"
        res = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {
                            "type": "FeatureCollection",
                            "features": [a1, a2, a_conflict, valid],
                        }
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertEqual([e["id"] for e in res], [valid["id"]])
        self.assertEqual(res.quarantined, 3)
        self.assertEqual(res.source_count, 4)

        # 5000-ID cap counts feature_id and reference IDs across quarantined features.
        many_bad = []
        # 50 features * 100 IDs (1 feature_id + 99 refs) = 5000 IDs (fits cleanly),
        # plus 1 more feature pushing past 5000 -> quarantine_ambiguous = True.
        for i in range(51):
            bad = feature()
            bad["id"] = f"https://api.weather.gov/alerts/q-{i}"
            bad["properties"]["headline"] = 123
            bad["properties"]["references"] = [
                {"@id": f"https://api.weather.gov/alerts/r-{i}-{j}"} for j in range(99)
            ]
            many_bad.append(bad)
        res_cap = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {"type": "FeatureCollection", "features": many_bad}
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertTrue(res_cap.quarantine_ambiguous)
        total_retained = sum(len(lineage) for lineage in res_cap.quarantined_lineages)
        self.assertEqual(total_retained, 5000)

        # Shared roots/references across quarantined features are counted once per poll.
        shared_bad = []
        shared_refs = [
            {"@id": f"https://api.weather.gov/alerts/shared-r-{j}"} for j in range(99)
        ]
        for i in range(51):
            bad = feature()
            bad["id"] = f"https://api.weather.gov/alerts/sq-{i}"
            bad["properties"]["headline"] = 123
            bad["properties"]["references"] = shared_refs
            shared_bad.append(bad)
        res_shared = await collector.fetch(
            Session(
                Response(
                    json.dumps(
                        {"type": "FeatureCollection", "features": shared_bad}
                    ).encode()
                )
            ),
            ["NY"],
        )
        self.assertFalse(res_shared.quarantine_ambiguous)
        self.assertEqual(len(res_shared.quarantined_lineages), 51)

    def test_scoped_non_cancel_quarantine_and_scoped_cancel_quarantine(self):
        # Malformed or oversized non-Cancel referencing root R leaves sibling S active.
        root = cap_event("spec01-root", -10, message_type="Alert")
        sibling = cap_event("spec01-sibling", -5, [root])
        sibling["instruction"] = "Take shelter in a basement now."
        records, _ = d.reconcile({}, [root], config(), NOW)
        records, plans = d.reconcile(
            records,
            [sibling],
            config(),
            NOW,
            partial=True,
            quarantine_lineages=[["https://api.weather.gov/alerts/bad-x", root["id"]]],
        )
        self.assertEqual(records[sibling["id"]]["state"], "active")
        self.assertEqual(len(plans), 1)
        self.assertEqual(records[root["id"]]["state"], "superseded")

        # Scoped Cancel quarantine blocks target and descendants while sibling stays active.
        target = cap_event("r1-target", -8, [root])
        target_child = cap_event("r1-target-child", -6, [target])
        recs2, _ = d.reconcile({}, [root, target, target_child], config(), NOW)
        recs2, plans2 = d.reconcile(
            recs2,
            [target_child, sibling],
            config(),
            NOW,
            partial=True,
            quarantine_cancel_lineages=[
                ["https://api.weather.gov/alerts/oversized-cancel", target["id"]]
            ],
        )
        self.assertEqual(recs2[target["id"]]["state"], "quarantined")
        self.assertEqual(recs2[target_child["id"]]["state"], "quarantined")
        self.assertEqual(recs2[sibling["id"]]["state"], "active")
        self.assertEqual([p["id"] for p in plans2], [sibling["id"]])

    def test_cancelled_record_without_cancel_retains_protection_and_overflow_horizon(
        self,
    ):
        # A persisted state=="cancelled" record (whose Cancel was evicted) still blocks
        # replay within 7 days and transitions to ended_or_absent once past horizon.
        target = cap_event("m1-target", -5, message_type="Alert")
        prior = {
            target["id"]: {
                "state": "cancelled",
                "cancel_message": False,
                "lineage": [target["id"]],
                "cap_identity": target["cap_identity"],
                "cap_references": target["reference_identities"],
                "sent": target["sent"],
                "expires": target["expires"],
                "ends": target["ends"],
                "updated": NOW.isoformat(),
            }
        }
        replayed, plans = d.reconcile(
            prior, [target], config(), NOW + timedelta(days=2)
        )
        self.assertFalse(plans)
        self.assertEqual(replayed[target["id"]]["state"], "cancelled")

        expired, _ = d.reconcile(prior, [], config(), NOW + timedelta(days=8))
        self.assertEqual(expired[target["id"]]["state"], "ended_or_absent")

    def test_invalid_cancel_with_references_isolates_target_and_expires_after_horizon(
        self,
    ):
        root = cap_event("ha01-root", -20, message_type="Alert")
        target = cap_event("ha01-target", -10, [root])
        sibling = cap_event("ha01-sibling", -8, [root])
        sibling["instruction"] = "Take shelter in an interior room."
        bad_cancel = cap_event("ha01-bad-cancel", -5, [target], message_type="Cancel")
        bad_cancel["cap_references_valid"] = False
        bad_cancel["reference_identities"] = []

        # Poll 1: invalid Cancel quarantines target and isolates lineage without poisoning sibling.
        records, plans = d.reconcile(
            {}, [root, target, sibling, bad_cancel], config(), NOW
        )
        self.assertEqual(records[target["id"]]["state"], "quarantined")
        self.assertEqual(records[sibling["id"]]["state"], "active")
        self.assertEqual([p["id"] for p in plans], [sibling["id"]])
        self.assertEqual(records[bad_cancel["id"]]["lineage"], [bad_cancel["id"]])
        self.assertEqual(records[bad_cancel["id"]]["uncertain_targets"], [target["id"]])
        self.assertEqual(
            records[bad_cancel["id"]]["cap_identity"], bad_cancel["cap_identity"]
        )
        self.assertIsNone(records[bad_cancel["id"]]["cap_references"])
        self.assertFalse(
            d.conflicting_prior_cancel(bad_cancel, records[bad_cancel["id"]])
        )

        # Poll 2: bad_cancel is only in prior records; target stays quarantined while sibling remains active.
        records2, plans2 = d.reconcile(
            records, [target, sibling], config(), NOW + timedelta(minutes=1)
        )
        self.assertEqual(records2[target["id"]]["state"], "quarantined")
        self.assertEqual(records2[sibling["id"]]["state"], "active")
        self.assertEqual(plans2, [])

        # Poll 3 (>7 days later with bad_cancel and target absent): horizon expires uncertain_targets.
        records3, _ = d.reconcile(records2, [], config(), NOW + timedelta(days=8))
        self.assertEqual(records3[bad_cancel["id"]]["state"], "ended_or_absent")
        self.assertFalse(records3[bad_cancel["id"]]["cancel_message"])
        self.assertTrue(records3[bad_cancel["id"]]["cancellation_expired"])
        self.assertNotIn("uncertain_targets", records3[bad_cancel["id"]])
        self.assertEqual(records3[target["id"]]["state"], "ended_or_absent")

        # Syntactically valid Cancel with inverted ref timestamp (ref[2] >= identity[2]) also
        # isolates target instead of poisoning sibling's group.
        inv_cancel = cap_event("ha01-inv-cancel", -15, [target], message_type="Cancel")
        records_b, plans_b = d.reconcile(
            {}, [root, target, sibling, inv_cancel], config(), NOW
        )
        self.assertEqual(records_b[target["id"]]["state"], "quarantined")
        self.assertEqual(records_b[sibling["id"]]["state"], "active")
        self.assertEqual([p["id"] for p in plans_b], [sibling["id"]])

        # Overflow prioritizes Cancel / state=="cancelled" over non-cancel protected records
        # and computes dropped_horizon strictly from dropped protected/cancellation groups.
        protected_expiry = (NOW + timedelta(days=3)).isoformat()
        unprotected_expiry = (NOW + timedelta(days=30)).isoformat()
        older_updated = (NOW - timedelta(seconds=1)).isoformat()
        overflow_prior = {}
        for i in range(1002):
            eid = f"https://api.weather.gov/alerts/ov-{i}"
            overflow_prior[eid] = {
                "state": "cancelled" if i < 600 else "active",
                "cancel_message": i < 100,
                "lineage": [eid],
                "sent": NOW.isoformat(),
                "expires": (
                    protected_expiry
                    if i == 599
                    else unprotected_expiry
                    if i == 1001
                    else NOW.isoformat()
                ),
                "updated": older_updated if i == 599 else NOW.isoformat(),
            }
        # Put all records in protected via a shared cancel component or 1002 active/cancelled records:
        # 100 Cancel + 500 cancelled + 402 current graph events -> 1002 protected.
        extra_events = [
            cap_event(f"ov-ev-{i}", -1, message_type="Alert") for i in range(402)
        ]
        with self.assertRaises(d.CancellationEvidenceOverflow) as ctx:
            d.reconcile(overflow_prior, extra_events, config(), NOW)
        retained = ctx.exception.records
        self.assertEqual(len(retained), 1000)
        self.assertTrue(
            all(
                f"https://api.weather.gov/alerts/ov-{i}" in retained for i in range(100)
            )
        )
        self.assertEqual(
            ctx.exception.dropped_horizon,
            (NOW - timedelta(seconds=1)) + timedelta(minutes=5) + d.MAX_ACCEPTANCE_AGE,
        )

    async def test_malformed_actual_cancel_is_not_lost_as_a_simple_poll_error(self):
        bad = feature()
        bad["id"] = "not-a-valid-nws-id"
        bad["properties"]["messageType"] = "Cancel"
        body = {"type": "FeatureCollection", "features": [bad, feature()]}
        result = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertTrue(result.uncertain_cancellation)
        self.assertTrue(result.quarantine_ambiguous)
        self.assertEqual(result.quarantined, 1)
        self.assertEqual(len(result), 1)

    async def test_oversized_feature_is_quarantined_without_losing_other_alerts(self):
        import json

        bad = feature()
        bad["id"] += "-oversize"
        bad["properties"]["references"] = [{"@id": feature()["id"]}] * 101
        body = {"type": "FeatureCollection", "features": [bad, feature()]}
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual((len(events), events.quarantined), (1, 1))
        self.assertIn(feature()["id"], events.quarantined_lineages[0])
        self.assertFalse(events.quarantine_ambiguous)
        bad["properties"]["references"] = [
            {"@id": "https://api.weather.gov/alerts/" + "a" * 513}
        ]
        body["features"] = [bad, feature()]
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertFalse(events.quarantine_ambiguous)
        self.assertEqual(events.quarantined_lineages, [[bad["id"]]])
        self.assertEqual(len(events), 1)
        bad["properties"]["references"] = [
            {"@id": f"https://api.weather.gov/alerts/{i}"} for i in range(5001)
        ]
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertTrue(events.quarantine_ambiguous)
        self.assertLessEqual(len(events.quarantined_lineages[0]), 5001)
        body["features"] = [feature()] * 1001
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events.source_count, 1001)
        distinct_features = []
        for i in range(1005):
            item = feature()
            item["id"] = f"https://api.weather.gov/alerts/bulk-{i:04d}"
            distinct_features.append(item)
        body["features"] = distinct_features
        distinct_events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertEqual(len(distinct_events), 1005)
        self.assertEqual(distinct_events.source_count, 1005)

    async def test_null_properties_with_valid_feature_id_quarantines_locally(self):
        import json

        bad = {
            "type": "Feature",
            "id": "https://api.weather.gov/alerts/null-props",
            "properties": None,
            "geometry": None,
        }
        valid = feature()
        body = {"type": "FeatureCollection", "features": [bad, valid]}
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertFalse(events.quarantine_ambiguous)
        self.assertEqual(events.quarantined, 1)
        self.assertEqual(events.quarantined_lineages, [[bad["id"]]])
        self.assertEqual([e["id"] for e in events], [valid["id"]])

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

    async def test_pagination_allows_50_pages_and_rejects_51(self):
        import json

        class PaginatedSession:
            def __init__(self, total_pages):
                self.total_pages = total_pages
                self.urls = []

            def get(self, url, **kwargs):
                page = len(self.urls) + 1
                self.urls.append(url)
                ev = feature()
                cap_id = f"urn:oid:page-{page:02d}"
                ev["id"] = f"https://api.weather.gov/alerts/{cap_id}"
                ev["properties"] = {**ev["properties"], "id": cap_id}
                body = {"type": "FeatureCollection", "features": [ev]}
                if page < self.total_pages:
                    body["pagination"] = {
                        "next": f"https://api.weather.gov/alerts?page={page + 1}"
                    }
                return Response(json.dumps(body).encode())

        session_12 = PaginatedSession(12)
        events_12 = await collector.fetch(session_12, ["NY"])
        self.assertEqual(len(events_12), 12)
        self.assertEqual(len(session_12.urls), 12)

        session_51 = PaginatedSession(51)
        with self.assertRaisesRegex(ValueError, "NWS pagination limit reached"):
            await collector.fetch(session_51, ["NY"])

    async def test_pagination_enforces_total_fetch_timeout(self):
        import asyncio
        import json
        from unittest.mock import patch

        class SlowPageSession:
            def __init__(self):
                self.urls = []

            def get(self, url, **kwargs):
                page = len(self.urls) + 1
                self.urls.append(url)
                ev = feature()
                cap_id = f"urn:oid:slow-{page:02d}"
                ev["id"] = f"https://api.weather.gov/alerts/{cap_id}"
                ev["properties"] = {**ev["properties"], "id": cap_id}
                body = {
                    "type": "FeatureCollection",
                    "features": [ev],
                    "pagination": {
                        "next": f"https://api.weather.gov/alerts?page={page + 1}"
                    },
                }
                resp = Response(json.dumps(body).encode())

                class SlowContext:
                    async def __aenter__(self_ctx):
                        await asyncio.sleep(0.03)
                        return resp

                    async def __aexit__(self_ctx, *args):
                        pass

                return SlowContext()

        with patch.object(collector, "MAX_FETCH_SECONDS", 0.05):
            with self.assertRaises(TimeoutError):
                await collector.fetch(SlowPageSession(), ["NY"])

    async def test_fetch_offloads_page_parsing_via_asyncio_to_thread(self):
        import asyncio
        import json
        from unittest.mock import patch

        calls = []
        orig_to_thread = asyncio.to_thread

        async def recording_to_thread(func, *args, **kwargs):
            calls.append(func)
            return await orig_to_thread(func, *args, **kwargs)

        body = {"type": "FeatureCollection", "features": [feature()]}
        with patch.object(
            collector.asyncio, "to_thread", side_effect=recording_to_thread
        ):
            events = await collector.fetch(
                Session(Response(json.dumps(body).encode())), ["NY"]
            )
        self.assertEqual(len(events), 1)
        self.assertEqual(calls, [collector._parse_and_collect_page])

    def test_expiry_reason_distinguishes_age_clock_rollback_and_target_removed(self):
        cfg = config()
        ev = d.normalize(feature())
        ev["id"] = "https://api.weather.gov/alerts/exp-reason-1"
        ev["sent"] = (NOW - timedelta(minutes=1)).isoformat()
        ev["effective"] = (NOW - timedelta(minutes=1)).isoformat()
        ev["onset"] = NOW.isoformat()
        ev["expires"] = (NOW + timedelta(hours=1)).isoformat()
        ev["ends"] = (NOW + timedelta(hours=1)).isoformat()
        ev = cohere(ev)
        records, plans = d.reconcile({}, [ev], cfg, NOW)
        item = delivery.targets(plans[0], cfg, NOW)[0]

        self.assertIsNone(delivery.expiry_reason(item, records, cfg, NOW))
        self.assertEqual(
            delivery.expiry_reason(
                {**item, "created": (NOW + timedelta(minutes=2)).isoformat()},
                records,
                cfg,
                NOW,
            ),
            "clock_rollback",
        )
        self.assertEqual(
            delivery.expiry_reason(
                {**item, "created": (NOW - timedelta(minutes=20)).isoformat()},
                records,
                cfg,
                NOW,
            ),
            "age",
        )
        self.assertEqual(
            delivery.expiry_reason(item, records, {**cfg, "phones": []}, NOW),
            "target_removed",
        )

    def test_out_of_range_timestamps_and_horizon_overflow_resilience(self):
        self.assertIsNone(d.timestamp("9999-12-31T23:59:59Z"))
        self.assertIsNone(d.timestamp("0001-01-01T00:00:00Z"))
        self.assertIsNotNone(d.timestamp("9998-12-31T23:59:59Z"))
        self.assertIsNotNone(d.timestamp("0002-01-01T00:00:00Z"))

        valid = d.normalize(feature())
        valid["id"] = "https://api.weather.gov/alerts/valid-range"
        cohere(valid)

        # Far-future expires/ends/sent and year-9999 Cancel alerts fail closed per feature/lineage
        # without OverflowError or storing year-9999 cap_identity/cap_references tuples.
        bad_exp = d.normalize(feature())
        bad_exp["id"] = "https://api.weather.gov/alerts/year9999-exp"
        cohere(bad_exp)
        bad_exp["expires"] = "9999-12-31T23:59:59Z"

        raw_sent = feature()
        raw_sent["id"] = "https://api.weather.gov/alerts/year9999-sent"
        raw_sent["properties"]["id"] = "year9999-sent"
        raw_sent["properties"]["sent"] = "9999-12-31T23:59:59Z"
        bad_sent = d.normalize(raw_sent)
        self.assertIsNone(bad_sent["cap_identity"])

        target_9999 = d.normalize(feature())
        target_9999["id"] = "https://api.weather.gov/alerts/target-9999"
        cohere(target_9999)

        raw_cancel = feature()
        raw_cancel["id"] = "https://api.weather.gov/alerts/year9999-cancel"
        raw_cancel["properties"]["id"] = "year9999-cancel"
        raw_cancel["properties"]["messageType"] = "Cancel"
        raw_cancel["properties"]["sent"] = "9999-12-31T23:59:59Z"
        raw_cancel["properties"]["references"] = [
            {
                "@id": target_9999["id"],
                "identifier": "target-9999",
                "sender": "test@weather.gov",
                "sent": "9999-12-31T23:59:59Z",
            }
        ]
        bad_cancel = d.normalize(raw_cancel)
        self.assertIsNone(bad_cancel["cap_identity"])
        self.assertFalse(bad_cancel["cap_references_valid"])

        records, plans = d.reconcile(
            {}, [valid, target_9999, bad_exp, bad_sent, bad_cancel], config(), NOW
        )
        self.assertEqual([p["id"] for p in plans], [valid["id"]])
        self.assertEqual(records[valid["id"]]["state"], "active")
        self.assertEqual(records[bad_exp["id"]]["state"], "ineligible")
        self.assertEqual(records[bad_sent["id"]]["state"], "quarantined")
        self.assertIsNone(records[bad_sent["id"]].get("cap_identity"))
        self.assertEqual(records[target_9999["id"]]["state"], "quarantined")
        self.assertEqual(records[bad_cancel["id"]]["state"], "cancelled")
        self.assertIsNone(records[bad_cancel["id"]].get("cap_identity"))
        self.assertIsNone(records[bad_cancel["id"]].get("cap_references"))

        # Invalid far-future Cancel (sent/expires +365d, updated=NOW) clamps cancellation_horizon
        # to observed + 5m + MAX_ACCEPTANCE_AGE and ages out cleanly after 8 days.
        fut_target = d.normalize(feature())
        fut_target["id"] = "https://api.weather.gov/alerts/fut-target"
        cohere(fut_target)
        fut_cancel = d.normalize(feature())
        fut_cancel["id"] = "https://api.weather.gov/alerts/fut-cancel"
        fut_cancel["message_type"] = "Cancel"
        fut_cancel["sent"] = (NOW + timedelta(days=365)).isoformat()
        fut_cancel["expires"] = (NOW + timedelta(days=365)).isoformat()
        cohere(fut_cancel, fut_target)
        fut_records, _ = d.reconcile({}, [fut_target, fut_cancel], config(), NOW)
        fut_horizon = d.cancellation_horizon(
            [fut_target["id"], fut_cancel["id"]], fut_records
        )
        self.assertEqual(fut_horizon, NOW + timedelta(minutes=5) + d.MAX_ACCEPTANCE_AGE)
        valid_day8 = d.normalize(feature())
        valid_day8["id"] = "https://api.weather.gov/alerts/valid-day8"
        for key, delta in [
            ("sent", -60),
            ("effective", -60),
            ("onset", 0),
            ("expires", 1800),
            ("ends", 1800),
        ]:
            valid_day8[key] = (NOW + timedelta(days=8, seconds=delta)).isoformat()
        cohere(valid_day8)
        day8_records, day8_plans = d.reconcile(
            fut_records,
            [valid_day8],
            config(),
            NOW + timedelta(days=8),
        )
        self.assertEqual([p["id"] for p in day8_plans], [valid_day8["id"]])
        self.assertEqual(day8_records[fut_target["id"]]["state"], "ended_or_absent")
        self.assertEqual(day8_records[fut_cancel["id"]]["state"], "ended_or_absent")
        self.assertTrue(day8_records[fut_cancel["id"]]["cancellation_expired"])

        # Near-MAX_TIMESTAMP cancellation_horizon / _bound_records clamp cleanly to MAX_TIMESTAMP.
        near_max = {
            "https://api.weather.gov/alerts/near-max": {
                "state": "cancelled",
                "expires": "9998-12-30T00:00:00+00:00",
                "updated": NOW.isoformat(),
            },
            "https://api.weather.gov/alerts/near-max-unbounded": {
                "state": "cancelled",
                "expires": "9998-12-30T00:00:00+00:00",
            },
            "https://api.weather.gov/alerts/near-max-legacy-cap": {
                "state": "cancelled",
                "expires": "9998-12-30T00:00:00+00:00",
                "updated": "9998-12-30T00:00:00+00:00",
            },
        }
        self.assertEqual(
            d.cancellation_horizon(
                ["https://api.weather.gov/alerts/near-max-legacy-cap"], near_max
            ),
            d.MAX_TIMESTAMP,
        )
        self.assertEqual(
            d.cancellation_horizon(
                ["https://api.weather.gov/alerts/near-max-unbounded"], near_max, now=NOW
            ),
            NOW + timedelta(minutes=5) + d.MAX_ACCEPTANCE_AGE,
        )
        self.assertEqual(
            d.cancellation_horizon(
                ["https://api.weather.gov/alerts/near-max"], near_max
            ),
            NOW + timedelta(minutes=5) + d.MAX_ACCEPTANCE_AGE,
        )

        overflow_records = {
            f"https://api.weather.gov/alerts/ov-max-{i}": {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [f"https://api.weather.gov/alerts/ov-max-{i}"],
                "sent": NOW.isoformat(),
                "expires": NOW.isoformat(),
                "updated": NOW.isoformat(),
            }
            for i in range(1002)
        }
        with self.assertRaises(d.CancellationEvidenceOverflow) as ctx:
            d._bound_records(
                overflow_records,
                (),
                {eid: eid for eid in overflow_records},
                set(),
                set(),
                datetime(9998, 12, 30, tzinfo=timezone.utc),
                [],
            )
        self.assertEqual(ctx.exception.dropped_horizon, d.MAX_TIMESTAMP)

    async def test_non_actual_and_alert_messages_do_not_supersede_actual_alerts(self):
        import json

        actual_raw = feature()
        actual_raw["id"] = "https://api.weather.gov/alerts/actual-p"
        actual_raw["properties"]["id"] = "actual-p"
        actual_raw["properties"]["sent"] = "2026-11-15T19:55:00Z"
        actual_norm = d.normalize(actual_raw)

        for status in ("Test", "Exercise", "System"):
            for msg_type in ("Update", "Cancel"):
                non_actual_raw = copy.deepcopy(actual_raw)
                non_actual_raw["id"] = (
                    f"https://api.weather.gov/alerts/{status.lower()}-{msg_type.lower()}"
                )
                non_actual_raw["properties"]["id"] = (
                    f"{status.lower()}-{msg_type.lower()}"
                )
                non_actual_raw["properties"]["status"] = status
                non_actual_raw["properties"]["messageType"] = msg_type
                non_actual_raw["properties"]["sent"] = "2026-11-15T19:56:00Z"
                non_actual_raw["properties"]["references"] = [
                    {
                        "@id": actual_raw["id"],
                        "identifier": actual_raw["properties"]["id"],
                        "sender": actual_raw["properties"]["sender"],
                        "sent": actual_raw["properties"]["sent"],
                    }
                ]
                non_actual_norm = d.normalize(non_actual_raw)

                # collector.fetch and resolve_candidates do not hide actual_raw.
                body = {
                    "type": "FeatureCollection",
                    "features": [actual_raw, non_actual_raw],
                }
                fetched = await collector.fetch(
                    Session(Response(json.dumps(body).encode())), ["NY"]
                )
                self.assertEqual(
                    {e["id"] for e in fetched},
                    {actual_raw["id"], non_actual_raw["id"]},
                )
                resolved = d.resolve_candidates(
                    {},
                    [actual_norm, non_actual_norm],
                    [actual_norm, non_actual_norm],
                    NOW,
                )
                self.assertEqual(
                    {e["id"] for e in resolved},
                    {actual_raw["id"], non_actual_raw["id"]},
                )

                # reconcile does not supersede, cancel, or merge lineage with actual_norm.
                prior, _ = d.reconcile({}, [actual_norm], config(), NOW)
                recs_absent, _ = d.reconcile(prior, [non_actual_norm], config(), NOW)
                self.assertEqual(
                    recs_absent[actual_norm["id"]]["state"], "ended_or_absent"
                )
                self.assertEqual(
                    recs_absent[non_actual_norm["id"]]["lineage"],
                    [non_actual_norm["id"]],
                )
                recs_both, plans_both = d.reconcile(
                    prior, [actual_norm, non_actual_norm], config(), NOW
                )
                self.assertEqual(recs_both[actual_norm["id"]]["state"], "active")
                self.assertEqual(plans_both, [])

        # An Actual Alert with spurious references also does not supersede prior actual_norm.
        spurious_alert = d.normalize(actual_raw)
        spurious_alert["id"] = "https://api.weather.gov/alerts/spurious-alert"
        spurious_alert["sent"] = "2026-11-15T19:57:00Z"
        spurious_alert["cap_identity"] = [
            "nws@example.test",
            "spurious-alert",
            spurious_alert["sent"],
        ]
        spurious_alert["references"] = [actual_norm["id"]]
        spurious_alert["reference_identities"] = [actual_norm["cap_identity"]]
        spurious_alert["cap_references_valid"] = True
        resolved_spurious = d.resolve_candidates(
            {}, [actual_norm, spurious_alert], [actual_norm, spurious_alert], NOW
        )
        self.assertEqual(
            {e["id"] for e in resolved_spurious},
            {actual_norm["id"], spurious_alert["id"]},
        )
        prior_p, _ = d.reconcile({}, [actual_norm], config(), NOW)
        recs_spurious, _ = d.reconcile(prior_p, [spurious_alert], config(), NOW)
        self.assertEqual(recs_spurious[actual_norm["id"]]["state"], "ended_or_absent")
        self.assertEqual(
            recs_spurious[spurious_alert["id"]]["lineage"],
            [spurious_alert["id"]],
        )

    def test_ineligible_current_burst_does_not_crowd_out_protected_tombstones(self):
        prior = {
            f"https://api.weather.gov/alerts/tomb-{i}": {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [f"https://api.weather.gov/alerts/tomb-{i}"],
                "cap_identity": [
                    "nws@example.test",
                    f"tomb-{i}",
                    NOW.isoformat(),
                ],
                "cap_references": [],
                "sent": NOW.isoformat(),
                "expires": NOW.isoformat(),
                "ends": NOW.isoformat(),
                "updated": NOW.isoformat(),
            }
            for i in range(100)
        }
        active_events = [
            cap_event(f"burst-act-{i}", -2, message_type="Alert") for i in range(5)
        ]
        ineligible_events = []
        for i in range(950):
            ev = cap_event(f"burst-inelig-{i}", -1, message_type="Alert")
            ev["instruction"] = "Stay tuned for routine updates."
            ineligible_events.append(ev)

        records, plans = d.reconcile(
            prior, active_events + ineligible_events, config(), NOW
        )
        self.assertEqual(len(records), 1000)
        self.assertEqual({p["id"] for p in plans}, {e["id"] for e in active_events})
        self.assertTrue(
            all(
                f"https://api.weather.gov/alerts/tomb-{i}" in records
                for i in range(100)
            )
        )
        self.assertTrue(all(e["id"] in records for e in active_events))
        kept_inelig = sum(1 for e in ineligible_events if e["id"] in records)
        self.assertEqual(kept_inelig, 895)

    def test_absent_actionable_records_survive_ineligible_burst_without_replanning(
        self,
    ):
        cfg = config()
        bridge_ev = cap_event("bridge-act", -2, message_type="Alert")
        bridge_fp = d.fingerprint(bridge_ev, d.qualify(bridge_ev, cfg, NOW))
        unconf_id = "https://api.weather.gov/alerts/absent-unconf"
        quar_id = "https://api.weather.gov/alerts/absent-quar"
        prior = {
            unconf_id: {
                "state": "unconfirmed",
                "prior_state": "active",
                "fingerprint": "fp-unconf",
                "actions": {"fp-unconf": ["new_york_ny"]},
                "lineage": [unconf_id],
                "cap_identity": ["nws@example.test", "absent-unconf", NOW.isoformat()],
                "cap_references": [],
                "sent": (NOW - timedelta(minutes=20)).isoformat(),
                "expires": (NOW + timedelta(hours=1)).isoformat(),
                "ends": (NOW + timedelta(hours=1)).isoformat(),
                "updated": (NOW - timedelta(minutes=20)).isoformat(),
            },
            quar_id: {
                "state": "quarantined",
                "prior_state": "active",
                "fingerprint": "fp-quar",
                "actions": {"fp-quar": ["new_york_ny"]},
                "lineage": [quar_id],
                "cap_identity": ["nws@example.test", "absent-quar", NOW.isoformat()],
                "cap_references": [],
                "sent": (NOW - timedelta(minutes=20)).isoformat(),
                "expires": (NOW + timedelta(hours=1)).isoformat(),
                "ends": (NOW + timedelta(hours=1)).isoformat(),
                "updated": (NOW - timedelta(minutes=20)).isoformat(),
            },
            bridge_ev["id"]: {
                "state": "ended_or_absent",
                "prior_state": "active",
                "fingerprint": bridge_fp,
                "actions": {bridge_fp: ["new_york_ny"]},
                "lineage": [bridge_ev["id"]],
                "cap_identity": bridge_ev["cap_identity"],
                "cap_references": [],
                "sent": bridge_ev["sent"],
                "expires": bridge_ev["expires"],
                "ends": bridge_ev["ends"],
                "inactive_since": (NOW - timedelta(minutes=5)).isoformat(),
                "updated": (NOW - timedelta(minutes=5)).isoformat(),
            },
        }
        ineligible_burst = []
        for i in range(1000):
            ev = cap_event(f"abs-inelig-{i}", -1, message_type="Alert")
            ev["instruction"] = "Stay tuned for routine updates."
            ineligible_burst.append(ev)

        records, plans = d.reconcile(prior, ineligible_burst, cfg, NOW)
        self.assertEqual(len(records), 1000)
        self.assertEqual(plans, [])
        self.assertIn(unconf_id, records)
        self.assertIn(quar_id, records)
        self.assertIn(bridge_ev["id"], records)

        # Returning bridge alert within 15 minutes does not re-plan duplicate alarm.
        records_back, plans_back = d.reconcile(
            records, [bridge_ev], cfg, NOW + timedelta(minutes=1)
        )
        self.assertEqual(records_back[bridge_ev["id"]]["state"], "active")
        self.assertEqual(plans_back, [])

    def test_superseded_placeholders_in_non_actionable_groups_truncate_without_overflow(
        self,
    ):
        cfg = config()
        prior = {}
        ineligible_events = []
        for i in range(500):
            ev = cap_event(f"sup-inelig-{i}", -1, message_type="Alert")
            ev["instruction"] = "Stay tuned for routine updates."
            sup_id = f"https://api.weather.gov/alerts/sup-hidden-{i}"
            lineage = sorted([sup_id, ev["id"]])
            prior[sup_id] = {
                "state": "superseded",
                "lineage": lineage,
                "cap_identity": [
                    "nws@example.test",
                    f"sup-hidden-{i}",
                    NOW.isoformat(),
                ],
                "cap_references": [],
                "sent": NOW.isoformat(),
                "expires": NOW.isoformat(),
                "ends": NOW.isoformat(),
                "updated": (NOW - timedelta(hours=1)).isoformat(),
            }
            ev["references"] = [sup_id]
            ev["reference_identities"] = [prior[sup_id]["cap_identity"]]
            ev["cap_references_valid"] = True
            ineligible_events.append(ev)
        for i in range(50):
            tomb_id = f"https://api.weather.gov/alerts/sup-tomb-{i}"
            prior[tomb_id] = {
                "state": "cancelled",
                "cancel_message": True,
                "lineage": [tomb_id],
                "cap_identity": ["nws@example.test", f"sup-tomb-{i}", NOW.isoformat()],
                "cap_references": [],
                "sent": NOW.isoformat(),
                "expires": NOW.isoformat(),
                "ends": NOW.isoformat(),
                "updated": NOW.isoformat(),
            }

        records, plans = d.reconcile(
            prior, ineligible_events, cfg, NOW, graph_events=ineligible_events
        )
        self.assertEqual(len(records), 1000)
        self.assertEqual(plans, [])
        self.assertTrue(
            all(
                f"https://api.weather.gov/alerts/sup-tomb-{i}" in records
                for i in range(50)
            )
        )

    def test_quarantine_all_over_1000_ineligible_truncates_without_overflow_while_protecting_actionable(
        self,
    ):
        cfg = config()
        ineligible_burst = []
        for i in range(1005):
            ev = cap_event(f"qall-{i}", -1, message_type="Alert")
            ev["instruction"] = "Stay tuned for routine updates."
            ineligible_burst.append(ev)

        prior = {
            "https://api.weather.gov/alerts/qall-prior-active": {
                "state": "unconfirmed",
                "prior_state": "active",
                "fingerprint": "fp-prior-act",
                "actions": {"fp-prior-act": ["new_york_ny"]},
                "lineage": ["https://api.weather.gov/alerts/qall-prior-active"],
                "cap_identity": ["nws@example.test", "qall-prior-act", NOW.isoformat()],
                "cap_references": [],
                "sent": (NOW - timedelta(minutes=30)).isoformat(),
                "expires": (NOW + timedelta(hours=1)).isoformat(),
                "ends": (NOW + timedelta(hours=1)).isoformat(),
                "updated": (NOW - timedelta(minutes=30)).isoformat(),
            },
            "https://api.weather.gov/alerts/qall-bridge": {
                "state": "quarantined",
                "prior_state": None,
                "fingerprint": "fp-bridge",
                "actions": {"fp-bridge": ["new_york_ny"]},
                "lineage": ["https://api.weather.gov/alerts/qall-bridge"],
                "cap_identity": ["nws@example.test", "qall-bridge", NOW.isoformat()],
                "cap_references": [],
                "sent": (NOW - timedelta(minutes=5)).isoformat(),
                "expires": (NOW + timedelta(hours=1)).isoformat(),
                "ends": (NOW + timedelta(hours=1)).isoformat(),
                "inactive_since": (NOW - timedelta(minutes=5)).isoformat(),
                "updated": (NOW - timedelta(minutes=5)).isoformat(),
            },
        }
        records_qall, plans_qall = d.reconcile(
            prior,
            ineligible_burst,
            cfg,
            NOW,
            quarantine_all=True,
        )
        self.assertEqual(len(records_qall), 1000)
        self.assertEqual(plans_qall, [])
        self.assertIn("https://api.weather.gov/alerts/qall-prior-active", records_qall)
        self.assertIn("https://api.weather.gov/alerts/qall-bridge", records_qall)

        # Normal poll (quarantine_all=False) still protects scoped state == "quarantined".
        scoped_prior = {
            "https://api.weather.gov/alerts/scoped-q": {
                "state": "quarantined",
                "prior_state": None,
                "lineage": ["https://api.weather.gov/alerts/scoped-q"],
                "cap_identity": None,
                "cap_references": None,
                "updated": (NOW - timedelta(hours=2)).isoformat(),
            }
        }
        records_scoped, _ = d.reconcile(
            scoped_prior,
            ineligible_burst[:1000],
            cfg,
            NOW,
            partial=True,
            quarantine_lineages=[["https://api.weather.gov/alerts/scoped-q"]],
            quarantine_all=False,
        )
        self.assertEqual(len(records_scoped), 1000)
        self.assertIn("https://api.weather.gov/alerts/scoped-q", records_scoped)


if __name__ == "__main__":
    unittest.main()
