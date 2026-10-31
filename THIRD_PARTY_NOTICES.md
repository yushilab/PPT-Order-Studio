# Third party source notices

## PPTAgent optional Skill

`third_party/pptagent/` contains the complete standalone Skill source from
https://github.com/icip-cas/PPTAgent/tree/833cda553b343be0e486a93b0b57cac962cdd566/skills/pptagent
at revision `833cda553b343be0e486a93b0b57cac962cdd566`.

Copyright (c) 2025 ICIP-CAS. Licensed under MIT; the original license is retained
in `third_party/pptagent/LICENSE`. `UPSTREAM.json` records the source pin and
SHA-256 of the unmodified bundled files. Runtime environments, downloaded
dependencies, personal configuration and credentials are not bundled.

The snapshot/review verification in `src/pptstudio/pptagent_bridge.py` follows
the pinned MIT-licensed runtime's `input_snapshot`, `render_current` and final
acceptance contract. It adds project order/engine/round binding and local path
confinement. The optional Skill is not registered globally or run by default.

Dependencies downloaded by the explicit optional setup command retain their
own licenses. Bundling this source does not supply model credentials, grant
desktop execution permissions, or certify rendered visual quality.
