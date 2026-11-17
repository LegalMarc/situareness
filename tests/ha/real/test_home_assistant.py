"""Optional tests against real Home Assistant; network and devices remain simulated."""

import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from homeassistant import loader
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.components.recorder.common import async_wait_recording_done

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def hass_storage():
    # Override the HA helper's mocked storage to exercise actual disk I/O.
    return {}


@pytest.fixture
def hass_config_dir(tmp_path):
    (tmp_path / "custom_components").mkdir()
    (tmp_path / "custom_components" / "situareness").symlink_to(
        ROOT / "custom_components" / "situareness", target_is_directory=True
    )
    return str(tmp_path)


def alert():
    # Synthetic coordinates do not represent a household or either sample city.
    now = datetime.now(timezone.utc)
    sent = (now - timedelta(hours=2)).isoformat()
    return {
        "id": "https://api.weather.gov/alerts/urn:oid:test",
        "event": "Tornado Warning",
        "headline": "Test fixture",
        "status": "Actual",
        "message_type": "Alert",
        "sent": sent,
        "cap_identity": ["nws@example.test", "urn:oid:test", sent],
        "reference_identities": [],
        "cap_references_valid": True,
        "effective": (now - timedelta(hours=2)).isoformat(),
        "onset": now.isoformat(),
        "expires": (now + timedelta(hours=1)).isoformat(),
        "ends": (now + timedelta(hours=1)).isoformat(),
        "urgency": "Immediate",
        "certainty": "Observed",
        "instruction": "Take shelter immediately.",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
        },
        "references": [],
    }


async def integration_module(hass, monkeypatch, events):
    integration = await loader.async_get_integration(hass, "situareness")
    component = await integration.async_get_component()

    async def fetch(session, states):
        return events

    monkeypatch.setattr(component, "fetch", fetch)
    return component


async def test_flow_sensor_storage_and_unload(hass, monkeypatch):
    await integration_module(hass, monkeypatch, [])
    result = await hass.config_entries.flow.async_init(
        "situareness", context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    entry = result["result"]
    assert entry.state is ConfigEntryState.LOADED
    state = hass.states.get("sensor.situareness_monitoring")
    assert state is not None and state.state == "0"
    assert state.attributes["shadow"] is True
    assert state.attributes["event_count"] == 0
    assert (
        Path(hass.config.path(".storage")) / ("situareness." + entry.entry_id)
    ).exists()
    translations = await async_get_translations(hass, "en", "config", {"situareness"})
    assert translations["component.situareness.config.step.user.title"] == "Situareness"
    assert (
        "shadow"
        in translations["component.situareness.config.step.user.description"].lower()
    )
    sensor = hass.data["situareness"][entry.entry_id]
    from custom_components.situareness.sensor import SituarenessSensor

    assert {"events", "last_success"} <= SituarenessSensor(
        sensor, entry.entry_id
    )._unrecorded_attributes
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert hass.states.get("sensor.situareness_monitoring").state == "unavailable"
    assert entry.entry_id not in hass.data["situareness"]
    await hass.config_entries.async_remove(entry.entry_id)
    assert not (
        Path(hass.config.path(".storage")) / ("situareness." + entry.entry_id)
    ).exists()


async def test_real_service_registry_and_shadow_gate(hass, monkeypatch):
    config = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(config))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    await integration_module(hass, monkeypatch, [alert()])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert len(calls) == 1 and "New York" in calls[0]["message"]
    assert calls[0]["data"]["push"]["sound"]["critical"] == 1
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_real_ha_quarantines_invalid_identity_without_blocking_independent_alert(
    hass, monkeypatch
):
    config = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(config))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    invalid = alert()
    invalid["cap_identity"][1] = "wrong-identifier"
    independent = alert()
    independent["id"] += "-independent"
    independent["cap_identity"][1] += "-independent"
    await integration_module(hass, monkeypatch, [invalid, independent])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert len(calls) == 1
    assert calls[0]["data"]["url"] == independent["id"]
    data = hass.data["situareness"][entry.entry_id].data
    assert data["partial"] is True
    assert {event["id"]: event["state"] for event in data["events"]} == {
        invalid["id"]: "quarantined",
        independent["id"]: "active",
    }
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_real_ha_shadow_blocks_service(hass, monkeypatch):
    config = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(config))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    events = []
    await integration_module(hass, monkeypatch, events)
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = hass.data["situareness"][entry.entry_id]
    assert coordinator.update_interval == timedelta(minutes=1)
    events.append(alert())
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert calls == []
    assert coordinator.data["planned_count"] == 1
    assert coordinator.data["shadow"] is True
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_recorder_excludes_high_churn_attributes(
    recorder_mock, hass, monkeypatch
):
    from homeassistant.components.recorder.db_schema import (
        StateAttributes,
        States,
        StatesMeta,
    )
    from homeassistant.helpers.recorder import session_scope
    from sqlalchemy import select

    await hass.async_start()
    await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await async_wait_recording_done(hass)

    def stored_attributes():
        with session_scope(hass=hass, read_only=True) as session:
            return list(
                session.scalars(
                    select(StateAttributes.shared_attrs)
                    .join(States, States.attributes_id == StateAttributes.attributes_id)
                    .join(StatesMeta, States.metadata_id == StatesMeta.metadata_id)
                    .where(StatesMeta.entity_id == "sensor.situareness_monitoring")
                )
            )

    rows = await hass.async_add_executor_job(stored_attributes)
    assert rows
    attrs = [json.loads(row) for row in rows if row]
    assert attrs and all(
        "events" not in row
        and "last_success" not in row
        and "degraded_at" not in row
        and "degraded_until" not in row
        for row in attrs
    )
    assert "events" in hass.states.get("sensor.situareness_monitoring").attributes
    assert "last_success" in hass.states.get("sensor.situareness_monitoring").attributes
    assert "degraded_at" in hass.states.get("sensor.situareness_monitoring").attributes
    assert (
        "degraded_until" in hass.states.get("sensor.situareness_monitoring").attributes
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_removal_cannot_recreate_store_during_refresh(hass, monkeypatch):
    component = await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    coordinator = hass.data["situareness"][entry.entry_id]
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_fetch(*args):
        started.set()
        await release.wait()
        return []

    monkeypatch.setattr(component, "fetch", slow_fetch)
    refresh = asyncio.create_task(coordinator._async_update_data())
    await started.wait()
    unloading = asyncio.create_task(hass.config_entries.async_unload(entry.entry_id))
    await asyncio.sleep(0)
    release.set()
    await refresh
    assert await unloading
    await hass.config_entries.async_remove(entry.entry_id)
    assert not (
        Path(hass.config.path(".storage")) / ("situareness." + entry.entry_id)
    ).exists()


async def test_real_ha_degraded_collection_withholds_output_and_recovers_on_ack(
    hass, monkeypatch
):
    from custom_components.situareness.collector import CollectedEvents

    cfg = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    config_path = Path(hass.config.path("situareness.json"))
    config_path.write_text(json.dumps(cfg))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    ev = alert()
    degraded_events = CollectedEvents([ev], 1, [], False, uncertain_cancellation=True)
    component = await integration_module(hass, monkeypatch, degraded_events)
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.situareness_monitoring")
    assert state is not None and state.state == "unknown"
    assert state.attributes["evidence_degraded"] is True
    assert state.attributes["output_blocked"] is True
    assert state.attributes["degraded_reason"] == "malformed_cancellation"
    assert state.attributes["event_count"] == 1
    assert calls == []
    notifications = hass.data.get("persistent_notification", {})
    assert "situareness_degraded" in notifications

    # Clean poll while degraded still collects without delivering.
    clean_events = CollectedEvents([ev], 0, [], False)

    async def fetch_clean(session, states):
        return clean_events

    monkeypatch.setattr(component, "fetch", fetch_clean)
    coordinator = hass.data["situareness"][entry.entry_id]
    await coordinator.async_request_refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.situareness_monitoring")
    assert state.attributes["evidence_degraded"] is True
    assert state.attributes["output_blocked"] is True
    assert calls == []

    # Reload with a future acknowledge_degraded_at stays loaded in degraded mode (not SETUP_RETRY)
    # and exposes acknowledge_rejected=True while keeping situareness_degraded raised.
    future_ack = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    config_path.write_text(json.dumps({**cfg, "acknowledge_degraded_at": future_ack}))
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.situareness_monitoring")
    assert state is not None and state.state == "unknown"
    assert state.attributes["evidence_degraded"] is True
    assert state.attributes["acknowledge_rejected"] is True
    assert "situareness_degraded" in hass.data.get("persistent_notification", {})

    # Reload with a valid non-future acknowledge_degraded_at (>= degraded_at) restores normal output.
    ack_time = datetime.now(timezone.utc).isoformat()
    assert state.attributes["degraded_at"] <= ack_time
    config_path.write_text(json.dumps({**cfg, "acknowledge_degraded_at": ack_time}))
    fresh_ev = alert()
    fresh_ev["id"] += "-fresh"
    fresh_ev["cap_identity"][1] += "-fresh"
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    # Withheld alert `ev` from the degraded poll is delivered once recovery occurs.
    assert len(calls) == 1
    assert calls[0]["data"]["url"] == ev["id"]
    monkeypatch.setattr(
        component,
        "fetch",
        lambda session, states: asyncio.sleep(0, result=[fresh_ev]),
    )
    await hass.data["situareness"][entry.entry_id].async_request_refresh()
    await hass.async_block_till_done()
    state = hass.states.get("sensor.situareness_monitoring")
    assert state.state == "1"
    assert state.attributes["evidence_degraded"] is False
    assert state.attributes["output_blocked"] is False
    assert state.attributes["degraded_reason"] is None
    assert "situareness_degraded" not in hass.data.get("persistent_notification", {})
    assert len(calls) == 2
    assert calls[1]["data"]["url"] == fresh_ev["id"]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_real_ha_missing_store_after_init_latches_journal_lost(hass, monkeypatch):
    cfg = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(cfg))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    component = await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data.get("journal_initialized") is True

    # Simulate persisted journal file disappearing while entry remains initialized.
    assert await hass.config_entries.async_unload(entry.entry_id)
    storage_file = Path(hass.config.path(".storage")) / (
        "situareness." + entry.entry_id
    )
    storage_file.unlink()
    monkeypatch.setattr(
        component,
        "fetch",
        lambda session, states: asyncio.sleep(0, result=[alert()]),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.situareness_monitoring")
    assert state is not None and state.state == "unknown"
    assert state.attributes["evidence_degraded"] is True
    assert state.attributes["output_blocked"] is True
    assert state.attributes["degraded_reason"] == "journal_lost"
    assert calls == []
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_real_ha_journal_lost_first_poll_failure_and_remove_dismisses_notification(
    hass, monkeypatch
):
    cfg = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(cfg))
    hass.services.async_register("notify", "mobile_app_test", lambda call: None)
    component = await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data.get("journal_initialized") is True

    # Simulate missing store while the first reload poll fails due to NWS outage.
    assert await hass.config_entries.async_unload(entry.entry_id)
    storage_file = Path(hass.config.path(".storage")) / (
        "situareness." + entry.entry_id
    )
    storage_file.unlink()

    async def failing_fetch(session, states):
        raise ConnectionError("NWS unreachable")

    monkeypatch.setattr(component, "fetch", failing_fetch)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data.get("journal_lost_at") is not None
    assert "situareness_degraded" in hass.data.get("persistent_notification", {})
    from homeassistant.helpers.storage import Store

    saved = await Store(
        hass, 1, "situareness." + entry.entry_id, private=True
    ).async_load()
    assert saved is not None
    assert saved["degraded"] is True
    assert saved["degraded_reason"] == "journal_lost"
    assert saved["degraded_at"] == entry.data["journal_lost_at"]

    # Removing the failed config entry dismisses the persistent notification cleanly.
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "situareness_degraded" not in hass.data.get("persistent_notification", {})


async def test_real_ha_corrupt_json_store_latches_malformed_store(hass, monkeypatch):
    cfg = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(cfg))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)

    storage_dir = Path(hass.config.path(".storage"))
    storage_file = storage_dir / ("situareness." + entry.entry_id)
    storage_file.write_text("{not valid json", encoding="utf-8")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.situareness_monitoring")
    assert state is not None and state.state == "unknown"
    assert state.attributes["evidence_degraded"] is True
    assert state.attributes["output_blocked"] is True
    assert state.attributes["degraded_reason"] == "malformed_store"
    assert state.attributes["degraded_until"] is None
    assert entry.data.get("journal_initialized") is True
    assert "situareness_degraded" in hass.data.get("persistent_notification", {})
    assert calls == []

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "situareness_degraded" not in hass.data.get("persistent_notification", {})
    assert not list(storage_dir.glob(f"situareness.{entry.entry_id}.corrupt.*"))


async def test_real_ha_storage_version_mismatch_latches_malformed_store(
    hass, monkeypatch
):
    cfg = {
        "states": ["NY"],
        "locations": {"new_york_ny": {"name": "New York", "point": [0.5, 0.5]}},
        "approved_rules": {"Tornado Warning": ["Take shelter immediately"]},
        "phones": ["mobile_app_test"],
        "live_enabled": True,
        "commissioning_passed": True,
    }
    Path(hass.config.path("situareness.json")).write_text(json.dumps(cfg))
    calls = []
    hass.services.async_register(
        "notify", "mobile_app_test", lambda call: calls.append(call.data)
    )
    await integration_module(hass, monkeypatch, [])
    entry = MockConfigEntry(domain="situareness", title="Situareness", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)

    storage_file = Path(hass.config.path(".storage")) / (
        "situareness." + entry.entry_id
    )
    for bad_envelope in (
        {
            "version": 0,
            "minor_version": 1,
            "key": "situareness." + entry.entry_id,
            "data": {"records": {}},
        },
        {
            "version": 2,
            "minor_version": 1,
            "key": "situareness." + entry.entry_id,
            "data": {"records": {}},
        },
    ):
        raw_text = json.dumps(bad_envelope)
        storage_file.write_text(raw_text, encoding="utf-8")
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        state = hass.states.get("sensor.situareness_monitoring")
        assert state is not None and state.state == "unknown"
        assert state.attributes["evidence_degraded"] is True
        assert state.attributes["output_blocked"] is True
        assert state.attributes["degraded_reason"] == "malformed_store"
        assert state.attributes["degraded_until"] is None
        assert "situareness_degraded" in hass.data.get("persistent_notification", {})
        assert storage_file.read_text(encoding="utf-8") == raw_text
        assert calls == []
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert "situareness_degraded" not in hass.data.get("persistent_notification", {})
