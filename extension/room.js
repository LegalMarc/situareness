import { eventTimestamp, matchesEvent, nwsAwarenessLifecycle, parsePublicConfig, publicConfig, relativeAge, safeHttpUrl, sourceFreshness } from './ui/helpers.mjs';

const byId = (id) => document.getElementById(id);
const els = {
  collectorDot: byId('collector-dot'), collectorLabel: byId('collector-label'), pause: byId('pause-button'), refresh: byId('refresh-button'), settings: byId('settings-button'),
  ha: byId('ha-status'), places: byId('place-list'), placeCount: byId('place-count'), sources: byId('source-list'), sourceCount: byId('source-count'), sourceEmpty: byId('source-empty'),
  eventCount: byId('event-count'), lastUpdated: byId('last-updated'), state: byId('feed-state'), list: byId('event-list'), filteredEmpty: byId('filtered-empty'), notice: byId('notice'),
  freshness: byId('freshness-note'),
  dashboard: byId('dashboard-link'),
  search: byId('search-input'), category: byId('category-filter'), status: byId('status-filter'), clearFilters: byId('clear-filters'), dialog: byId('settings-dialog'), editor: byId('location-editor'), sourceEditor: byId('source-editor'),
  json: byId('config-json'), error: byId('settings-error'), saveSettings: byId('save-settings'), cancelSettings: byId('cancel-settings'), closeSettings: byId('close-settings'), exportButton: byId('export-button'), importFile: byId('import-file'),
};
let currentState = null;
let selectedLocation = null;
let busy = false;
let settingsEdits;
let connectionError = null;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function announce(message, kind = '') {
  els.notice.textContent = message;
  els.notice.className = `notice${kind ? ` ${kind}` : ''}`;
  els.notice.hidden = false;
}

function clearNotice() { els.notice.hidden = true; els.notice.textContent = ''; }

async function send(message) {
  if (!globalThis.chrome?.runtime?.sendMessage) throw new Error('Extension runtime is unavailable. Open this page from the installed Situareness extension.');
  let response;
  try { response = await chrome.runtime.sendMessage(message); }
  catch (error) { throw new Error(error?.message || 'Could not reach the local collector.'); }
  if (!response || response.ok !== true) throw new Error(typeof response?.error === 'string' ? response.error : 'The local collector returned an unexpected response.');
  return response.state;
}

function updateControls() {
  const unavailable = !currentState || Boolean(connectionError);
  for (const button of [els.pause, els.refresh, els.settings]) button.disabled = unavailable || busy;
  els.refresh.disabled = unavailable || busy || currentState?.collector?.paused === true;
  els.refresh.title = currentState?.collector?.paused ? 'Resume collection before refreshing.' : 'Run a bounded collection cycle.';
  els.refresh.textContent = busy ? 'Refreshing…' : '↻ Refresh';
  els.pause.textContent = currentState?.collector?.paused ? 'Resume collection' : 'Pause collection';
  els.pause.setAttribute('aria-label', currentState?.collector?.paused ? 'Resume collection' : 'Pause collection');
}

function renderStatus(state) {
  const collector = state?.collector || {};
  const paused = collector.paused === true;
  const running = collector.running === true;
  els.collectorDot.className = `status-dot ${paused ? 'paused' : (state?.sources || []).some((source) => source.status === 'error') ? 'error' : 'ok'}`;
  if (paused) els.collectorLabel.textContent = 'Collection paused';
  else if (running) els.collectorLabel.textContent = 'Collecting updates…';
  else if (collector.last_run_at) els.collectorLabel.textContent = `Collector active · last run ${relativeAge(collector.last_run_at)}`;
  else els.collectorLabel.textContent = 'Collector ready · awaiting first run';
  const haStatus = state?.ha?.status || 'not_connected';
  els.ha.textContent = haStatus === 'not_connected' ? 'Home Assistant is not connected. This room cannot activate household alerts.' : `Home Assistant status: ${String(haStatus).replaceAll('_', ' ')}. Room actions remain read-only.`;
  const dashboardUrl = safeHttpUrl(state?.config?.room?.primary_dashboard);
  els.dashboard.hidden = !dashboardUrl;
  if (dashboardUrl) els.dashboard.href = dashboardUrl;
}

function renderPlaces(state) {
  const places = Array.isArray(state?.config?.locations) ? state.config.locations : [];
  const events = Array.isArray(state?.events) ? state.events : [];
  els.placeCount.textContent = String(places.length);
  els.places.replaceChildren();
  const allButton = element('button', 'place-button');
  allButton.type = 'button'; allButton.setAttribute('aria-pressed', String(selectedLocation === null));
  allButton.append(element('span', 'place-indicator'), element('span', '', 'All places'));
  allButton.addEventListener('click', () => { selectedLocation = null; render(currentState); });
  els.places.append(allButton);
  for (const place of places) {
    if (!place || typeof place.id !== 'string') continue;
    const button = element('button', 'place-button');
    button.type = 'button'; button.setAttribute('aria-pressed', String(selectedLocation === place.id));
    button.append(element('span', 'place-indicator'), element('span', '', place.name || place.id));
    const count = events.filter((event) => Array.isArray(event.location_ids) && event.location_ids.includes(place.id)).length;
    if (count) button.append(element('span', 'place-event-count', count));
    button.addEventListener('click', () => { selectedLocation = selectedLocation === place.id ? null : place.id; render(currentState); });
    els.places.append(button);
  }
}

function renderSources(state) {
  const sources = Array.isArray(state?.sources) ? state.sources : [];
  const configuredSources = Array.isArray(state?.config?.sources) ? state.config.sources : [];
  els.sourceCount.textContent = String(sources.length);
  els.sources.replaceChildren();
  els.sourceEmpty.hidden = sources.length !== 0;
  for (const source of sources) {
    const configured = configuredSources.find((item) => item.id === source.id);
    const freshness = sourceFreshness({ ...source, interval_minutes: configured?.interval_minutes });
    const row = element('div', 'source-row');
    row.append(element('span', `source-status ${freshness}`), element('span', 'source-name', source.name || source.id || 'Unnamed source'));
    row.append(element('span', 'source-age', freshness === 'error' ? 'Failed' : relativeAge(source.last_success_at)));
    els.sources.append(row);
    if (freshness === 'error' && source.last_error) els.sources.append(element('span', 'source-detail', source.last_error));
    else if (freshness === 'stale') els.sources.append(element('span', 'source-detail', `Last good data · ${relativeAge(source.last_success_at)}`));
    else if (source.enabled === false) els.sources.append(element('span', 'source-detail', 'Disabled'));
    if (source.truncated === true) {
      const available = Number.isInteger(source.items_available) ? ` · ${source.items_available} available` : '';
      els.sources.append(element('span', 'source-detail source-truncation', `Limited to 200 recent items${available}`));
    }
  }
  const stale = sources.filter((source) => source.enabled !== false && sourceFreshness({ ...source, interval_minutes: configuredSources.find((item) => item.id === source.id)?.interval_minutes }) === 'stale');
  const errors = sources.filter((source) => source.enabled !== false && source.status === 'error');
  els.freshness.hidden = stale.length === 0 && errors.length === 0;
  const freshnessMessages = [];
  if (errors.length) freshnessMessages.push(`${errors.length} source${errors.length === 1 ? '' : 's'} failed. Cached items may be old; see source status.`);
  if (stale.length) freshnessMessages.push(`${stale.length} source${stale.length === 1 ? ' is' : 's are'} overdue. Items are shown with their collection times and may be stale.`);
  els.freshness.textContent = freshnessMessages.join(' ');
}

function displayTime(event) {
  const eventTime = eventTimestamp(event);
  if (!eventTime.value) return { date: 'Time unknown', time: '', label: eventTime.label };
  const date = new Date(eventTime.timestamp);
  return { date: new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date), time: new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' }).format(date), label: eventTime.label };
}

function renderEvent(event, locations) {
  const item = element('li', 'event-card');
  const time = displayTime(event);
  const timeBlock = element('time', 'event-time');
  timeBlock.append(element('span', 'event-time-label', time.label));
  const date = element('strong', '', time.date); timeBlock.append(date);
  if (time.time) timeBlock.append(document.createTextNode(time.time));
  const body = element('div', 'event-body');
  const top = element('div', 'event-topline');
  const category = typeof event.category === 'string' ? event.category.toLocaleLowerCase() : 'other';
  top.append(element('span', `category-pill ${['weather', 'earthquake'].includes(category) ? category : category === 'news' ? '' : 'other'}`, category || 'Other'));
  if (event.severity && event.severity !== 'unknown') top.append(element('span', 'severity-pill', event.severity));
  if (event.status && event.status !== 'actual') top.append(element('span', 'status-pill', event.status));
  const lifecycle = nwsAwarenessLifecycle(event, Date.now(), currentState?.config?.sources);
  if (lifecycle) {
    const labels = {
      current: ['In latest results', 'Present in the latest processed weather alert results.'],
      expired: ['Source expiry passed', 'The recorded source expiry has passed. This does not establish that the hazard ended.'],
      not_in_latest_fetch: ['Not in latest results', 'Absent from latest processed results. This is not an official cancellation or proof that the hazard ended.'],
      unknown: ['Presence unknown', 'Current presence in the latest processed weather alert results is unknown.'],
    };
    const [label, description] = labels[lifecycle];
    const badge = element('span', `presence-pill ${lifecycle}`, label);
    badge.title = description;
    badge.setAttribute('aria-label', `${label}. ${description}`);
    top.append(badge);
  }
  top.append(element('span', 'event-source', event.source_name || event.source_id || 'Unknown source'));
  if (event.official === true) top.append(element('span', 'official-mark', 'Official'));
  body.append(top, element('h3', 'event-title', event.title || 'Untitled event'));
  if (event.summary) body.append(element('p', 'event-summary', event.summary));
  const footer = element('div', 'event-footer');
  const locationsText = (Array.isArray(event.location_ids) ? event.location_ids : []).map((id) => locations.find((place) => place.id === id)?.name).filter(Boolean);
  if (locationsText.length) footer.append(element('span', 'event-location', `Regional coverage: ${locationsText.join(' · ')}`));
  if (event.collected_at) footer.append(element('span', '', `Collected ${relativeAge(event.collected_at)}`));
  const url = safeHttpUrl(event.url);
  if (url) {
    const link = element('a', 'source-link', 'Open source ↗');
    link.href = url; link.target = '_blank'; link.rel = 'noopener noreferrer';
    link.addEventListener('click', (click) => {
      if (!globalThis.chrome?.runtime?.sendMessage) return;
      click.preventDefault();
      send({ type: 'OPEN_SOURCE', url }).catch((error) => announce(error.message, 'error'));
    });
    footer.append(link);
  }
  if (footer.childNodes.length) body.append(footer);
  item.append(timeBlock, body);
  return item;
}

function renderFeed(state) {
  const events = Array.isArray(state?.events) ? state.events : [];
  const locations = Array.isArray(state?.config?.locations) ? state.config.locations : [];
  const filtered = events.filter((event) => matchesEvent(event || {}, { query: els.search.value, category: els.category.value, status: els.status.value, locationId: selectedLocation }, locations));
  filtered.sort((a, b) => eventTimestamp(b).timestamp - eventTimestamp(a).timestamp);
  els.eventCount.textContent = `${filtered.length} ${filtered.length === 1 ? 'item' : 'items'}`;
  els.list.replaceChildren(...filtered.map((event) => renderEvent(event || {}, locations)));
  const failedSources = (state?.sources || []).filter((source) => source.status === 'error');
  const paused = state?.collector?.paused === true;
  if (events.length === 0) {
    els.list.hidden = true; els.filteredEmpty.hidden = true; els.state.hidden = false;
    els.state.replaceChildren();
    const heading = element('strong', '', paused ? 'Collection is paused' : failedSources.length ? 'No events available' : 'No events collected yet');
    els.state.append(heading, element('span', '', failedSources.length ? 'One or more providers failed. Check source status for details.' : paused ? 'Resume collection to check your configured feeds.' : 'Your configured sources have not returned any events yet.'));
    if (!paused && failedSources.length === 0) { const spinner = element('span', 'spinner'); spinner.setAttribute('aria-hidden', 'true'); els.state.prepend(spinner); }
  } else {
    els.state.hidden = true;
    els.list.hidden = filtered.length === 0;
    els.filteredEmpty.hidden = filtered.length !== 0;
  }
  const latest = state?.collector?.last_run_at;
  els.lastUpdated.textContent = latest ? `Updated ${relativeAge(latest)}` : 'Waiting for first collection';
}

function render(state) {
  currentState = state && typeof state === 'object' ? state : null;
  connectionError = null;
  clearNotice();
  updateControls();
  if (!currentState) return;
  renderStatus(currentState); renderPlaces(currentState); renderSources(currentState); renderFeed(currentState);
}

async function refreshState() {
  if (busy) return;
  busy = true; updateControls();
  try { render(await send({ type: 'GET_STATE' })); }
  catch (error) {
    connectionError = error.message;
    els.collectorDot.className = 'status-dot error';
    els.collectorLabel.textContent = 'Collector disconnected';
    if (!currentState) { els.state.hidden = false; els.state.replaceChildren(element('strong', '', 'Unable to connect'), element('span', '', error.message)); }
    announce(`Local collector unavailable. Showing cached data; timestamps are unchanged. ${error.message}`, 'error');
  }
  finally { busy = false; updateControls(); }
}

async function runAction(message, success) {
  if (busy) return;
  busy = true; updateControls(); clearNotice();
  try { render(await send(message)); if (success) announce(success); }
  catch (error) {
    if (!/^(Configuration|Invalid|Private|Source URL|Paused|Unknown request)/.test(error.message)) {
      connectionError = error.message;
      els.collectorDot.className = 'status-dot error';
      els.collectorLabel.textContent = 'Collector disconnected';
      updateControls();
    }
    announce(error.message, 'error');
  }
  finally { busy = false; updateControls(); }
}

function openSettings() {
  if (!currentState) return;
  const config = publicConfig(currentState.config);
  els.json.value = JSON.stringify(config, null, 2);
  els.error.hidden = true; els.editor.replaceChildren();
  const locations = Array.isArray(config.locations) ? config.locations : [];
  for (const place of locations) {
    const row = element('div', 'location-edit-row');
    const name = document.createElement('input'); name.type = 'text'; name.value = place.name || place.id || ''; name.maxLength = 80; name.setAttribute('aria-label', `Place name for ${place.id || 'location'}`); name.dataset.locationName = place.id || '';
    const label = element('label', 'location-watch'); const toggle = document.createElement('input'); toggle.type = 'checkbox'; toggle.checked = place.watch_enabled !== false; toggle.setAttribute('aria-label', `Watch ${place.name || place.id || 'location'}`); toggle.dataset.locationWatch = place.id || '';
    label.append(toggle, document.createTextNode('Watching')); row.append(name, label); els.editor.append(row);
  }
  els.sourceEditor.replaceChildren();
  const allowedProviders = [['nws', 'National Weather Service alerts'], ['usgs', 'USGS earthquakes (post-event only)'], ['bbc_world', 'BBC News World'], ['bbc_us_canada', 'BBC News US & Canada']];
  const sources = Array.isArray(config.sources) ? config.sources : [];
  for (const [id, labelText] of allowedProviders) {
    const source = sources.find((item) => item.id === id);
    const row = element('div', 'location-edit-row');
    const label = element('label', 'location-watch'); const toggle = document.createElement('input'); toggle.type = 'checkbox'; toggle.checked = source?.enabled === true; toggle.dataset.sourceEnabled = id; toggle.setAttribute('aria-label', `Enable ${labelText}`);
    label.append(toggle, document.createTextNode(labelText));
    const intervalLabel = element('label', 'location-watch'); intervalLabel.append(document.createTextNode('Every '));
    const interval = document.createElement('select'); interval.dataset.sourceInterval = id; interval.setAttribute('aria-label', `${labelText} collection interval`);
    for (const minutes of [1, 2, 5, 10, 15, 30, 60]) { const option = element('option', '', `${minutes} min`); option.value = String(minutes); interval.append(option); }
    const configuredInterval = Number(source?.interval_minutes);
    if (![1, 2, 5, 10, 15, 30, 60].includes(configuredInterval)) {
      const current = element('option', '', `${configuredInterval} min (current)`); current.value = String(configuredInterval); interval.append(current);
    }
    interval.value = String(Number.isInteger(configuredInterval) && configuredInterval > 0 ? configuredInterval : 15);
    intervalLabel.append(interval); row.append(label, intervalLabel); els.sourceEditor.append(row);
  }
  settingsEdits = { names: new Set(), watch: new Set(), sources: new Set() };
  if (typeof els.dialog.showModal === 'function') els.dialog.showModal(); else els.dialog.setAttribute('open', '');
}

function getEditedConfig() {
  const config = parsePublicConfig(els.json.value);
  for (const input of els.editor.querySelectorAll('[data-location-name]')) {
    if (!settingsEdits.names.has(input.dataset.locationName)) continue;
    const place = config.locations.find((item) => item.id === input.dataset.locationName);
    if (place) place.name = input.value.trim() || place.id;
  }
  for (const input of els.editor.querySelectorAll('[data-location-watch]')) {
    if (!settingsEdits.watch.has(input.dataset.locationWatch)) continue;
    const place = config.locations.find((item) => item.id === input.dataset.locationWatch);
    if (place) place.watch_enabled = input.checked;
  }
  const sourceDefaults = {
    nws: { name: 'National Weather Service alerts', kind: 'nws', url: 'https://api.weather.gov/alerts/active?area=NY,DC', enabled: true, interval_minutes: 1 },
    usgs: { name: 'USGS earthquakes (post-event)', kind: 'usgs', url: 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson', enabled: true, interval_minutes: 1 },
    bbc_world: { name: 'BBC News World', kind: 'rss', url: 'https://feeds.bbci.co.uk/news/world/rss.xml', enabled: true, interval_minutes: 5 },
    bbc_us_canada: { name: 'BBC News US & Canada', kind: 'rss', url: 'https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml', enabled: true, interval_minutes: 5 },
  };
  if (!Array.isArray(config.sources)) config.sources = [];
  for (const [id, defaults] of Object.entries(sourceDefaults)) {
    if (!settingsEdits.sources.has(id)) continue;
    let source = config.sources.find((item) => item.id === id);
    const enabled = Boolean(els.sourceEditor.querySelector(`[data-source-enabled="${id}"]`)?.checked);
    if (!source && enabled) { source = { id, ...defaults }; config.sources.push(source); }
    if (source) {
      source.enabled = enabled;
      source.interval_minutes = Number(els.sourceEditor.querySelector(`[data-source-interval="${id}"]`)?.value || defaults.interval_minutes);
    }
  }
  config.live_actions_enabled = false;
  return config;
}

els.pause.addEventListener('click', () => runAction({ type: 'SET_PAUSED', paused: !currentState?.collector?.paused }, currentState?.collector?.paused ? 'Collection resumed.' : 'Collection paused.'));
els.refresh.addEventListener('click', () => runAction({ type: 'REFRESH' }));
els.settings.addEventListener('click', openSettings);
els.closeSettings.addEventListener('click', () => els.dialog.close());
byId('filter-form').addEventListener('submit', (event) => event.preventDefault());
els.dashboard.addEventListener('click', (event) => {
  const url = safeHttpUrl(els.dashboard.href);
  if (!url || !globalThis.chrome?.runtime?.sendMessage) return;
  event.preventDefault();
  send({ type: 'OPEN_SOURCE', url }).catch((error) => announce(error.message, 'error'));
});
for (const input of [els.search, els.category, els.status]) input.addEventListener(input === els.search ? 'input' : 'change', () => currentState && renderFeed(currentState));
els.clearFilters.addEventListener('click', () => { els.search.value = ''; els.category.value = 'all'; els.status.value = 'all'; selectedLocation = null; render(currentState); });
els.cancelSettings.addEventListener('click', () => els.dialog.close());
byId('settings-form').addEventListener('submit', (event) => event.preventDefault());
els.editor.addEventListener('input', (event) => {
  const target = event.target;
  if (target.matches('[data-location-name]')) settingsEdits.names.add(target.dataset.locationName);
  if (target.matches('[data-location-watch]')) settingsEdits.watch.add(target.dataset.locationWatch);
});
els.sourceEditor.addEventListener('input', (event) => {
  const target = event.target;
  if (target.matches('[data-source-enabled], [data-source-interval]')) settingsEdits.sources.add(target.dataset.sourceEnabled || target.dataset.sourceInterval);
});
els.json.addEventListener('input', () => { settingsEdits = { names: new Set(), watch: new Set(), sources: new Set() }; });
els.exportButton.addEventListener('click', () => {
  if (!currentState?.config) return;
  const json = JSON.stringify(publicConfig(currentState.config), null, 2);
  els.json.value = json;
  settingsEdits = { names: new Set(), watch: new Set(), sources: new Set() };
  const blobUrl = URL.createObjectURL(new Blob([json], { type: 'application/json' }));
  const download = document.createElement('a');
  download.href = blobUrl;
  download.download = 'situareness-browser-settings.json';
  download.click();
  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
});
els.importFile.addEventListener('change', async () => {
  const file = els.importFile.files?.[0]; if (!file) return;
  try {
    const text = await file.text(); const config = parsePublicConfig(text);
    els.json.value = JSON.stringify(config, null, 2);
    settingsEdits = { names: new Set(), watch: new Set(), sources: new Set() };
    for (const place of config.locations) {
      const name = els.editor.querySelector(`[data-location-name="${CSS.escape(place.id)}"]`);
      const watch = els.editor.querySelector(`[data-location-watch="${CSS.escape(place.id)}"]`);
      if (name) name.value = place.name || place.id;
      if (watch) watch.checked = place.watch_enabled !== false;
    }
    for (const source of config.sources || []) {
      const enabled = els.sourceEditor.querySelector(`[data-source-enabled="${CSS.escape(source.id)}"]`);
      const interval = els.sourceEditor.querySelector(`[data-source-interval="${CSS.escape(source.id)}"]`);
      if (enabled) enabled.checked = source.enabled === true;
      if (interval) {
        if (![...interval.options].some((option) => option.value === String(source.interval_minutes))) {
          const option = element('option', '', `${source.interval_minutes} min (imported)`); option.value = String(source.interval_minutes); interval.append(option);
        }
        interval.value = String(source.interval_minutes);
      }
    }
    for (const toggle of els.sourceEditor.querySelectorAll('[data-source-enabled]')) {
      const source = (config.sources || []).find((item) => item.id === toggle.dataset.sourceEnabled);
      toggle.checked = source?.enabled === true;
      if (!source) {
        const interval = els.sourceEditor.querySelector(`[data-source-interval="${CSS.escape(toggle.dataset.sourceEnabled)}"]`);
        if (interval) interval.value = toggle.dataset.sourceEnabled === 'nws' ? '2' : '5';
      }
    }
    els.error.hidden = true;
  }
  catch (error) { els.error.textContent = error.message; els.error.hidden = false; }
  finally { els.importFile.value = ''; }
});
els.saveSettings.addEventListener('click', async () => {
  els.error.hidden = true;
  try {
    const config = getEditedConfig();
    const state = await send({ type: 'UPDATE_CONFIG', config });
    render(state); els.dialog.close(); announce('Settings saved.');
  } catch (error) { els.error.textContent = error.message; els.error.hidden = false; }
});

refreshState();
window.setInterval(() => { void refreshState(); }, 15_000);
