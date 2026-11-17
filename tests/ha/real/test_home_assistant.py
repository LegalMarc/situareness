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
    return {
        "id": "https://api.weather.gov/alerts/urn:oid:test",
        "event": "Tornado Warning",
        "headline": "Test fixture",
        "status": "Actual",
        "message_type": "Alert",
        "sent": (now - timedelta(hours=2)).isoformat(),
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
        "events" not in row and "last_success" not in row for row in attrs
    )
    assert "events" in hass.states.get("sensor.situareness_monitoring").attributes
    assert "last_success" in hass.states.get("sensor.situareness_monitoring").attributes
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
