# Beta 10.2.2 validation and filament scan scope

The active user request was to validate again, then include all hidden filament options and scan the actual used filament profile. The accidentally pasted MCP-install command was not executed after the user said to continue the existing work. No Orca MCP tools are connected in this environment, and no current user filament preset/G-code/project export was available. The inventory and scanner are complete; actual user values are not fabricated.

## Confirmed timing finding

Native ToolHead.move can process lookahead moves and yield in _check_pause before the surrounding G1 handler returns. The earlier end callback was registered after that return. In particular, split/long moves could already execute with no complete attribution interval. The corrected hook attaches per-native-move timing callbacks at lookahead insertion, before queue processing. A parent command's native modal/position/feed validation is retained. Invalid/error parents exclude their children. Native queue and command return values/errors remain unchanged.

Tests load the supplied unmodified native Move, LookAheadQueue and ToolHead class definitions, use the real move/planning/pause methods and replace only hardware I/O/time sinks. They verify known intervals while the native G1 remains in its pause path, separate split intervals, single native calls, error propagation and annotation-failure isolation. Unsupported native APIs do not get guessed. This is software verification, not a physical execution claim.

## Filament catalog

Pinned source: OrcaSlicer 2.5.0-dev 606b50f1 Preset.cpp filament-options list, Tab.cpp filament/override builders and dependencies, and PrintConfig.cpp definitions, variant and developer sets. 152 settings, 83 advanced, 1 expert, 18 developer, 45 dependency-controlled and 31 without an explicit binding in the scanned builders. Groups overlap; 130 form the potentially hidden union. Generic dialogs and actual printer/mode conditions can change visibility. No missing source default is used as an observed value.

Reports preserve G-code/preset raw values, verified single-used-filament identity where available, missing values, unresolved variants, supplied-parent origins and explicit nil overrides. Current firmware conditions are labelled separately. The offline scanner does not automatically fetch or invent unavailable system parents. The project sidecar still archives scoped data without proving inheritance/variant resolution. The plugin does not apply temperatures, extrusion settings or any preset while scanning.

## Validation

Source: 329 tests +37 subtests pass; one pytest dependency deprecation warning. Full extracted-package test results are stored with build evidence. Tests cover both native timing and inventory/scan behavior, current/last-file console reports, one-command background completion, unknown/default isolation, parent cycles/missing parents and disabled overrides.

Physical printer validation, exact ADC acquisition alignment, neighborhood-path reconstruction and universal knee-margin transfer remain open. No live printer installation, heating, homing or offset changes were run. Stable Auto Trim main is outside this continuation.
