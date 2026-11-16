# Primary-source evidence

Checked November 16, 2026. These observations identify candidate issuing authorities and delivery routes. They do not establish a global latency ranking or future availability. An official page describing a channel is different from an anonymous fetch, a real installed-adapter test, and a successful household delivery.

## Weather warnings and faster transports

NWS recommends its API for CAP access. The current baseline consumes direct active alerts rather than a news republisher. API publication, caching, polling and network execution add delay. The separate NWWS Open Interface is an official Internet XMPP product stream requiring NWS-issued credentials and a suitable client. Evaluate its availability and observed timing before selecting it as an additional transport. No account has been enrolled here. [NWS CAP guidance](https://vlab.noaa.gov/web/nws-common-alerting-protocol), [API documentation](https://www.weather.gov/documentation/services-web-api), [NWWS description](https://www.weather.gov/nwws/Description), [NWWS requirements](https://www.weather.gov/nwws/SystemReq).

Public sample county codes were checked against the Census reference and NWS county-zone names. NYC includes Bronx, Kings, New York, Queens and Richmond counties: 36005, 36047, 36061, 36081 and 36085. DC uses 11001. These are regional awareness identifiers, not proof of household exposure. [Census county-code reference](https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt), [NWS New York county-zone endpoint](https://api.weather.gov/zones/county/NYC061), [NWS DC county-zone endpoint](https://api.weather.gov/zones/county/DCC001).

## Earthquakes

USGS documents minute updates for its real-time GeoJSON summary feeds. The baseline selects the past-hour feed, avoiding a dependency on a later significance label. Event occurrence, later scientific revision and feed publication are distinct times. This feed is not ShakeAlert early warning. [GeoJSON formats and cadence](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php), [past-hour JSON](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson), [USGS information timing](https://www.usgs.gov/faqs/how-quickly-earthquake-information-posted-usgs-website-and-sent-out-earthquake-notification), [ShakeAlert](https://earthquake.usgs.gov/data/shakealert/).

## NYC and DC local authority channels

Notify NYC is the city's official emergency-information channel. Its FAQ advertises RSS, but the inspected “RSS Link” currently points to `/notifynyc#Recent_Notifications`, an HTML page. Therefore a usable RSS/API endpoint remains unverified. The catalog records this limitation rather than inventing a feed URL. Subscriber channels are an independent option, not an established input to this application. [Official FAQ](https://a858-nycnotify.nyc.gov/Home/FAQ), [current public notifications](https://a858-nycnotify.nyc.gov/notifynyc/).

AlertDC's official page describes email, SMS and Everbridge app subscriptions and links to a public recent-alerts page. An anonymous machine-readable alert API was not established in this research. Keep it as a documented subscriber/manual channel until an adapter has a verified transport. [Official AlertDC guidance](https://hsema.dc.gov/page/alertdc-stay-informed-stay-safe), [recent alerts](https://hsema.dc.gov/alerts).

## National all-hazards coverage

FEMA's public archive explicitly has a 24-hour delay. It is useful for replay fixtures and historical evaluation, and is unsuitable for early detection. Live IPAWS All-Hazards Information Feed access has an agreement/application path; do not assume an ordinary anonymous public API or an approved individual account. Verify current eligibility and alternatives directly with FEMA before implementing it. [FEMA archive metadata](https://gis.fema.gov/arcgis/rest/services/FEMA/IPAWS_Archive/FeatureServer), [FEMA feed access fact sheet](https://content.govdelivery.com/attachments/USDHSFEMA/2020/09/24/file_attachments/1554592/IPAWS%20All%20Hazards%20Information%20Feed.pdf), [2026 IPAWS interface guide](https://content.govdelivery.com/attachments/USDHSFEMA/2026/08/17/file_attachments/3748713/IPAWS-OPEN-v4-07-00_InterfaceDesignGuide_Final.pdf).

## Preparation and national-impact candidates

NHC documents RSS access to cyclone advisories and corresponding text products. Treat each product's issuing cycle and action semantics independently. A forecast outlook, a watch and an immediate protective warning are different signals. [NHC RSS documentation](https://www.nhc.noaa.gov/aboutrss.shtml), [NHC product descriptions](https://www.nhc.noaa.gov/aboutnhcprod.shtml).

NOAA SWPC's official page links directly to `alerts.json`, which returned JSON during this research. That establishes a public data route, not a validated terrestrial household-consequence rule. This adapter remains proposed. [SWPC alerts documentation](https://www.spaceweather.gov/products/alerts-watches-and-warnings), [direct alert JSON](https://services.swpc.noaa.gov/products/alerts.json).

## How to maintain this evidence

For a new location or source, use the [companion skill](../../skills/situareness-sources/SKILL.md) and record official endorsement, jurisdiction, access status, endpoint format, validation time and unknowns. Recheck links and formats, and validate the local catalog before applying supported runtime configuration changes. Do not transform a source-discovery result into an alarm rule.
