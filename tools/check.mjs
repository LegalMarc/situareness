import assert from 'node:assert/strict';
import { readdir, readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const loadJson = async (name) => JSON.parse(await readFile(path.join(root, name), 'utf8'));

async function walk(relative) {
  const files = [];
  for (const entry of await readdir(path.join(root, relative), { withFileTypes: true })) {
    const name = path.join(relative, entry.name);
    if (entry.isDirectory()) files.push(...await walk(name));
    else if (entry.isFile()) files.push(name);
  }
  return files;
}

const packageInfo = await loadJson('package.json');
const haManifest = await loadJson('custom_components/situareness/manifest.json');
const haExample = await loadJson('home-assistant/situareness.example.json');
assert.equal(haManifest.version, packageInfo.version, 'Home Assistant version mismatch');
assert.equal(haExample.live_enabled, false);
assert.equal(haExample.commissioning_passed, false);
assert.deepEqual(haExample.phones, []);
assert.equal(haExample.tts_entity, null);
assert.deepEqual(haExample.approved_rules, {});
assert.ok(Object.values(haExample.locations).every((location) => Object.keys(location).length === 0));
const manifest = await loadJson('extension/manifest.json');
assert.equal(manifest.version, packageInfo.version, 'Extension version mismatch');
assert.equal(manifest.manifest_version, 3);
assert.equal(manifest.background?.type, 'module');
assert.ok(manifest.background?.service_worker);
assert.ok(!manifest.content_scripts, 'The room does not need page injection.');
assert.ok(!manifest.externally_connectable, 'External message access is not needed.');
for (const host of manifest.host_permissions ?? []) {
  assert.ok(/^https:\/\/[a-z0-9.-]+\/\*$/.test(host), `Use explicit HTTPS hosts: ${host}`);
}
for (const entry of [manifest.background.service_worker, 'room.html']) {
  assert.ok((await stat(path.join(root, 'extension', entry))).isFile());
}

let scripts = 0;
for (const file of await walk('extension')) {
  if (file.endsWith('.json')) await loadJson(file);
  if (file.endsWith('.js') || file.endsWith('.mjs')) {
    const result = spawnSync(process.execPath, ['--check', path.join(root, file)], { encoding: 'utf8' });
    assert.equal(result.status, 0, `${file}: ${result.stderr}`);
    scripts += 1;
  }
}

const expectedLocations = [
  { id: 'nyc_sample', name: 'New York City, NY', counties: ['36005', '36047', '36061', '36081', '36085'] },
  { id: 'washington_dc_sample', name: 'Washington, DC', counties: ['11001'] },
];
for (const name of ['config/watch-configuration.json', 'extension/defaults/config.json']) {
  const config = await loadJson(name);
  assert.deepEqual(config.locations.map(({ id, name: label }) => ({ id, name: label })), expectedLocations.map(({ id, name: label }) => ({ id, name: label })), `${name}: expected generic sample places`);
  assert.equal(config.live_actions_enabled, false, `${name}: live actions must remain disabled`);
  assert.equal(config.alarm_policy.first_phone_delivery, 'all_enrolled_iphones');
  assert.equal(config.alarm_policy.speaker_and_horn_delivery, 'affected_locations_only');
  assert.deepEqual(config.enrolled_iphones, [], `${name}: device enrollment must be empty`);
  for (const [index, location] of config.locations.entries()) {
    const counties = Array.isArray(location.awareness_area?.county_fips) ? location.awareness_area.county_fips : [location.awareness_area?.county_fips];
    assert.deepEqual(counties, expectedLocations[index].counties, `${name}: sample place county coverage changed`);
    assert.equal(location.household_exposure, null);
    assert.deepEqual(location.google_speaker_targets, []);
    assert.deepEqual(location.horn_targets, []);
    assert.ok(!Object.hasOwn(location, 'latitude') && !Object.hasOwn(location, 'longitude'), `${name}: coordinates are not part of public samples`);
  }
  const nws = config.sources.find((source) => source.kind === 'nws');
  const usgs = config.sources.find((source) => source.kind === 'usgs');
  assert.equal(nws.interval_minutes, 1, `${name}: NWS should check every minute`);
  assert.equal(new URL(nws.url).searchParams.get('area'), 'NY,DC', `${name}: NWS areas should follow watched samples`);
  assert.equal(usgs.interval_minutes, 1, `${name}: USGS should check every minute`);
  assert.ok(new URL(usgs.url).pathname.endsWith('/all_hour.geojson'), `${name}: use the recent hourly earthquake feed`);
  assert.match(usgs.name, /post-event/i, `${name}: clarify the earthquake feed is post-event`);
  assert.ok(config.sources.filter((source) => source.kind === 'rss').every((source) => source.interval_minutes === 5), `${name}: news context should remain secondary cadence`);
}
console.log(`Static checks passed: Manifest V3, ${scripts} JavaScript files, and generic NYC/DC defaults with read-only safeguards.`);
