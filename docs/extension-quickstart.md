# Situareness browser room

Extract the archive. In Chrome open `chrome://extensions`, enable Developer mode, select **Load unpacked**, and choose the `situareness-extension` directory. Use the extension toolbar button to open the room. Internet access is required; errors and stale data appear in the room. The room is read-only and does not provide independent background alarms. Closing Chrome or sleeping the computer stops collection. Home Assistant monitoring is separate and starts in shadow mode.

The New York City and Washington, DC defaults are examples. Settings and exports include watched locations and are sensitive. Keep a personal export private, for example under `ignored-resources/private-config/room.json`; import changes into the room because its active configuration is stored in Chrome. NWS and USGS polling targets are one minute and BBC is five minutes. USGS `all_hour` is post-event reporting, not early warning. Provider and network latency are uncertain.
