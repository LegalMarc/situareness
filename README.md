# Situareness

Situareness is a local Chrome situation room with a separate, optional Home Assistant integration for weather monitoring. The room presents NWS alerts, USGS earthquake information, and BBC reporting. Home Assistant evaluates its own NWS feed independently of Chrome. New York City and Washington, DC are editable examples, not preconfigured household footprints.

The integration starts in shadow mode. It has not been commissioned for a household or tested with real delivery devices. Keep independent official alert channels in use.

- [Room setup and privacy](docs/setup.md)
- [Home Assistant setup and commissioning limits](docs/ha/README.md)
- [Primary-source roadmap](docs/plans/primary-source-roadmap.md)
- [Source research catalog](docs/reference/primary-sources.md)
- [Documentation index](docs/INDEX.md)
- [Source research skill](skills/situareness-sources/SKILL.md)

The room polls NWS and USGS on a one-minute target and BBC on a five-minute target. USGS `all_hour` reports earthquakes after they occur; it is not an earthquake early-warning system. Provider propagation, caching, network delays and polling make actual latency uncertain; no earliest-delivery guarantee is made. Closing Chrome or sleeping the computer stops room collection. The Home Assistant monitor runs independently when separately installed.

An optional World Monitor link opens a third-party context dashboard. It is not an issuing authority or a source of automatic household alarms. Its display URL can be changed or hidden in room settings.

Configuration is editable JSON, chosen for portability and straightforward inspection. No new application server or database is required. Keep personal room exports in `ignored-resources/private-config/room.json` and private Home Assistant configuration in `ignored-resources/private-config/home-assistant.json`; the latter must be copied to Home Assistant as `<config>/situareness.json`. These paths are local working conventions. Room settings include watched locations and must not be treated as safe to share.

`config/source-catalog.example.json` is a research catalog, not a runtime input. The included skill can maintain a local catalog and propose supported room configuration changes with validation; adding sources to the catalog does not create a collector. See the roadmap for adapter work.

MIT licensed; see [LICENSE](LICENSE).
