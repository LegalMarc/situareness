import copy
from datetime import datetime, timedelta, timezone
import importlib
import json
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
        for raw in (
            {"phones": ["notify.bad"]},
            {"live_enabled": "true"},
            {"locations": {"x": {"point": [999, 0]}}},
            {"states": ["NY&bad=1"]},
            {"acknowledge_degraded_at": "2026-11-17T10:00:00"},
            {"acknowledge_degraded_at": 123},
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
        # Future-dated invalid cancel fails cap_event_valid (so target is uncertain, not cancelled)
        # and must not mark `other` as superseded even if referenced.
        bad_cancel = cap_event("n1-cancel", 10, [target, other], "Cancel")
        result, _ = d.reconcile(records, [bad_cancel], config(), NOW)
        self.assertNotEqual(result[other["id"]]["state"], "superseded")

    def test_normalize_oversized_and_non_string_properties(self):
        oversized = feature()
        oversized["properties"]["instruction"] = "x" * 10001
        with self.assertRaises(d.OversizedFeature):
            d.normalize(oversized)
        bad_type = feature()
        bad_type["properties"]["headline"] = 123
        self.assertIsNone(d.normalize(bad_type))


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
        self.assertEqual([e["id"] for e in result], [successor["id"]])
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
        # Collector sees [first, second] cleanly and hides `first`.
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
        self.assertEqual([e["id"] for e in events], [second["id"]])
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
        # SIT-SPEC-03: [A, A, A_conflict] reports quarantined == 3.
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

        # SIT-R6 / SIT-DOC-04: 5000-ID cap counts feature_id AND reference IDs across
        # quarantined features including conflicting duplicates.
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

    def test_scoped_non_cancel_quarantine_and_scoped_cancel_quarantine(self):
        # SIT-SPEC-01: Malformed/oversized non-Cancel X referencing root R does NOT taint
        # independently valid sibling S referencing R.
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

        # SIT-R1: Scoped Cancel quarantine (quarantine_cancel_lineages) quarantines
        # target & its descendants while keeping unrelated/root sibling active.
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

        # Overflow prioritizes Cancel / state=="cancelled" over non-cancel protected records
        # and propagates dropped_horizon across evicted components.
        long_expiry = (NOW + timedelta(days=3)).isoformat()
        overflow_prior = {}
        for i in range(1002):
            eid = f"https://api.weather.gov/alerts/ov-{i}"
            overflow_prior[eid] = {
                "state": "cancelled" if i < 600 else "active",
                "cancel_message": i < 100,
                "lineage": [eid],
                "sent": NOW.isoformat(),
                "expires": long_expiry if i == 1001 else NOW.isoformat(),
                "updated": NOW.isoformat(),
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
        self.assertEqual(ctx.exception.dropped_horizon, NOW + timedelta(days=10))

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
        self.assertTrue(events.quarantine_ambiguous)
        bad["properties"]["references"] = [
            {"@id": f"https://api.weather.gov/alerts/{i}"} for i in range(5001)
        ]
        events = await collector.fetch(
            Session(Response(json.dumps(body).encode())), ["NY"]
        )
        self.assertTrue(events.quarantine_ambiguous)
        self.assertLessEqual(len(events.quarantined_lineages[0]), 5001)
        body["features"] = [feature()] * 1001
        with self.assertRaises(ValueError):
            await collector.fetch(Session(Response(json.dumps(body).encode())), ["NY"])

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
