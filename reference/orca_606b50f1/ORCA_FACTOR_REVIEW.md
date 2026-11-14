# Deep Calibration: OrcaSlicer parameter review

Reviewed for the user's **OrcaSlicer 2.5.0-dev, commit 606b50f1**, identified from the supplied Troubleshoot Center screenshot. This is the current official Deep Calibration beta10.1 continuation's research/design record, not a separate plugin fork. The runtime has not been modified by this audit.

## Coverage

| Process tab | Explicit setting bindings reviewed |
|---|---:|
| Quality | 109 |
| Strength | 66 |
| Speed | 50 |
| Support | 49 |
| Multimaterial | 49 |
| Others | 55 |
| Total | **378** |

The complete per-setting inventory is in ALL_PROCESS_PARAMETERS.md, the CSV and parameter_registry_606b50f1.json. It includes the source label, internal key, type, raw default expression, visibility mode, group, source locations and a handling decision for every field. No Basic/Advanced/Expert/Developer filter or feature-enable condition was applied. These counts are explicit unique key bindings in the six TabPrint page builders, not a claim all controls are simultaneously visible or applicable to an AD5X.

Developer mode does not activate every conditional feature. Some controls depend on Arachne, a selected pattern, enabled supports, a tower, a printer capability, an installed plugin or another master switch. The registry also includes **61 literal-key definitions marked comDevelop across the complete configuration definitions**, many in material/printer/internal settings rather than these six tabs, and **79 selected material/machine dependencies**. The dynamic per-preset plugin-configuration registration loop was resolved explicitly; no process binding remains unresolved.

An initial v2.4.2/main comparison was superseded by the user's exact commit. Source hashes are retained. No Windows app/profile was opened, no private preset values were obtained from the screenshot, and no current setting values are inferred from defaults. The current nightly can differ from later main or a stable release.

## Main conclusion

**Keep the material dimensions, but the beta10.1 recipe key is not yet a complete calibration identity.** Material/height/width/speed/filament diameter/nominal flow are necessary context, not enough to establish equivalent nozzle clearance or force conditions. Adding all378 values as independent numeric model inputs would also be wrong: some change physics directly, others identify paths to exclude, and some are only output/provenance settings.

Use three linked records:

1. **Resolved slicer/project snapshot:** slicer commit, merged machine/material/process/plate/object/modifier settings, raw values and units, enabled flags, resolved values, active tool/profile mapping, source G-code and postprocessing/plugin fingerprints. This covers all settings without pretending every one predicts offset. Keep a full archive hash and a separate physics/settings fingerprint; changing only a filename or note should not invalidate a physically equivalent margin.
2. **Per-extrusion segment context:** object, tool/spool, material, extrusion role, actual layer/bed-contact identity, resolved local height/width, commanded XYZ/E trajectory, effective speed/acceleration/cornering, temperatures/targets/fans, pressure advance/flow overrides, preceding retractions and extrusion history, deposited neighboring paths and mesh context. A snapshot of initial slicer SPEED is not a substitute for the executed role's speed.
3. **Eligibility and learning:** fit only comparable, sufficiently long steady model-on-bed segments. Keep supports, raft, tower/flush, skirt/brim, ironing, bridge, seam/scarf, travel and tool-change transitions out of the ordinary knee fit unless an explicitly validated separate mode handles them. Preserve excluded samples with reasons. Learned margins should reference the recipe plus compatible physics fingerprint and feature conditions, with provenance and observed rate/settling quality.

## Quality

- **Layer height/line width:** capture initial-layer height and initial-layer width as resolved millimeters. Preserve percentage/auto/inherited values as well. Arachne transitions, first-layer minimum bead width, minimum wall/feature size and per-role widths mean width is not necessarily constant within a layer.
- **Seam and scarf:** seam position/gap, conditional scarf criteria, scarf start height/length/steps, speed and flow ratio can deliberately change Z, volume and path overlap. Wipe direction/distance/speed and wipe-on-loop options introduce pressure/geometry transients. A global Z offset does not equal local scarf gap. Exclude these transitions rather than infer that an increased force is a bed-height change.
- **Precision:** XY hole/contour and elephant-foot compensation change outline placement/spacing; elephant-foot density and layer count alter deposited material. Arc fitting, slicing resolution, polyholes and precise-Z behavior can change small-segment speed/quantization or effective gap. Record emitted coordinates; object bounding boxes are not exact deposition geometry.
- **Ironing and Z contouring:** these can create intentional surface contact, low-flow paths or nonplanar Z. A single-layer pad can contain roles usually associated with later layers. Do not blanket-assume a setting is irrelevant merely because its name says top surface.
- **Wall generator/wall-surface options:** record Classic/Arachne and all transition/min-width controls, wall/infill ordering/direction, single-wall first-layer settings and area flow compensation. These directly influence local extrusion and previously deposited neighboring lines.
- **Flow ratios:** include print flow ratio, filament flow ratio, role ratios, bottom/top ratios, first-layer ratio, scarf ratio and area compensation, together with their enable switches. Do not multiply every listed ratio indiscriminately; the emitter chooses role- and condition-specific branches.
- **Bridging/overhangs:** retain all geometry/flow/speed/thickness/reversal controls in the project snapshot. Apply their physical effects only when those paths are emitted; an ordinary supported bed path is not a bridge. Disable ordinary knee learning on unsupported extrusion.

## Strength

- **Walls:** wall loops, alternating extra walls and thin-wall detection change path role durations, overlap history, curvature and short-segment transients.
- **Top/bottom:** bottom density/pattern/order/direction and shell counts/thickness affect the first solid layer. Top/color-penetration/expansion rules matter if the test also exposes a top or mixed-color surface. Top/bottom overlap changes material near walls. Record effective roles, not just the global infill pattern.
- **Infill:** sparse versus internal solid versus bottom-surface patterns are separate. Direction/rotation templates, multiline, smooth factors, anchors, overlap, gap fill, separated infills, gyroid/lattice/locked-zag/skin/skeleton settings and adaptive density alter path length, turns, intersections and adjacent deposited material. Fitting the force from all these roles together would confound gap with topology.
- **Advanced:** combined-layer infill and its maximum height, narrow-solid handling, vertical shell thickness, extra infill and bridge-angle controls can change actual bead height or path schedule. Record them even when inactive during the particular first layer; gate their influence by emitted role/layer.

## Speed

- **First-layer speed and first-layer infill speed are distinct.** In the pinned emitter, first-layer perimeter/brim paths generally select initial_layer_speed while other applicable roles select initial_layer_infill_speed; bottom-surface handling is its own branch. Slow-layer ramps, role overrides and small-feature thresholds can select another speed. Passing only initial_layer_speed to DEEP_CALIBRATION_ARM can misdescribe the force-bearing infill used for a knee search.
- **Other-layer/overhang speeds:** preserve all role speeds, percentage/inherited values and enable switches. Most are conditional; one-layer ironing/top/bridge/support roles can still invoke them. Small support perimeter speed is present in this nightly and must not be omitted.
- **Travel:** separate first-layer travel, ordinary travel, Z motion, retraction and the post-travel refill/settling period. Travel can produce a bed force signal without model deposition.
- **Acceleration, accel-to-decel, jerk and junction deviation:** distinguish slicer requests from firmware limits and G-code flavor translation. Klipper square_corner_velocity is not automatically the UI's jerk value. Include requested and effective acceleration/cornering, input shaping and speed overrides. A fixed recipe speed is often never reached on short paths.
- **Extrusion-rate smoothing:** slope limits, smoothing segment length and external-perimeter-only switch change pressure history. Preserve the resulting E trajectory and time since a rate change, not just static volumetric flow.

## Support

- Record enable/type/style, thresholds and plate-only/critical-region logic. They determine whether the observed bed-contact line is a support base or model.
- **Raft is a different calibration geometry.** Model first layer above raft is not model-on-bed layer1. Raft first-layer density, expansion, raft layers/contact gap and independent support heights affect what the load cell feels and what the layer marker means.
- Track support/interface filament assignments and actual tool, base/interface patterns, spacing/density, top/bottom Z gaps, XY/first-layer gaps, expansion, interface layers and support ironing.
- Tree tip/branch diameters, spacing, angles, walls and automatic/tree brim controls alter footprint and pressure transients. They remain in provenance; tree-base force must not teach the model material's normal first-layer margin.

## Multimaterial

- **Prime tower:** record tower geometry, brim, volume, purge flow/speed, sparse-layer/no-sparse-layer rules, framework, cooling/interface features and first priming. A load cell under the bed sees tower deposition too. This is not a model first layer just because the reported layer is1.
- **Feature filaments:** actual outer/inner wall, bottom/top/solid/sparse/tower/support assignments can use different materials within one layer. Initial tool identity alone is insufficient.
- **Ooze prevention:** standby temperature delta and preheat time/steps affect viscosity and pressure after a tool switch. Record targets and actual temperatures, not just the process temperature field.
- **Flush into infill/objects/support:** mark those segments and subsequent stabilization separately; commanded waste volume and mixed residual material can overwhelm the relation to nozzle clearance.
- **Interlocks/interface shells/tool ordering:** capture generated interleaved paths and material identity. Nightly toolchange ordering/cyclic first-layer controls are included in the inventory. Unknown tool-change or IFS/native purge macro execution must suspend ordinary knee training.

## Others

- **Skirt/brim:** loops, minimum extrusion, distance/start angle/speed/height, draft shield and brim geometry/flow/gap/ears affect priming and nearby material. Exclude their paths from model calibration, but retain their pressure/deposition history. Brim flow is not automatically governed by the same first-layer multiplier as model paths.
- **Special mode:** sequential object printing, intra-layer order, vase smoothing/start/finish flow and slicing mode can alter the meaning of layer1 or deliberately vary flow/height. Timelapse and wrapping-detection moves may lift/park/wipe the nozzle. They are eligibility/scheduling factors, not direct gap predictors.
- **Fuzzy skin:** this nightly can enable it on the first layer. Noise type, point distance, thickness, scale, octaves/persistence/ripples and first-layer enable alter local geometry and acceleration. Ordinary constant-gap knee fitting should exclude affected paths.
- **G-code output:** precision affects quantization; object/feature comments aid alignment; exclusions change actual path order. Filename, notes and numbering are provenance/parser concerns rather than physical margin predictors. Reduce-infill-retraction changes pressure history.
- **Custom role G-code, postprocessing, slicing plugins and per-process plugin capability overrides:** preserve source/hash/version/config plus the final G-code. These can alter motion, E, Z, temperature and roles after the process settings are resolved. Import them as data, never execute them during analysis. Any opaque transform prevents silently trusting preset values as actual printing conditions.

## Material and machine dependencies outside the requested tabs

The six tabs do not contain everything needed to interpret their settings. The registry includes selected dependencies, and the source definitions are archived so the full set can be revisited.

- Filament identity/profile/spool/blend, diameter, flow ratio and volumetric speed limits; experimental adaptive volumetric speed, whose fitted limit can depend on line width and height.
- Nozzle diameter/type/condition, machine model, extruder/tool mapping and active bed surface. Filament diameter is not nozzle diameter; beta10.1 currently keys only the former.
- Initial/later nozzle and bed targets, actual temperatures, chamber/ambient/soak state and material cooling; main/aux/chamber fans and fan behavior on the first layers.
- Pressure advance including enabled/adaptive models and their role/flow behavior, retraction length/speed, restart extra, wipe, Z-hop, tool-change/cutter retractions and delays. Do not infer melt pressure from the PA setting alone.
- Minimum-layer-time cooling slowdown, minimum speed, maximum volumetric speed, machine/extruder limits and firmware M220/M221-style overrides.
- Machine, filament, before/after-layer and tool-change G-code; actual firmware macros/settings, probe offset, mesh/profile/transform/fade, bed mounting and collision/tare behavior.
- Per-object/per-part/modifier/height-range/plate overrides, painted features/supports and selected tools. The same named global process preset can generate different effective local conditions.

## Source-confirmed volume and flow

For the ordinary rounded-rectangle bead model in Flow.cpp:

    area = height * (width - height * (1 - pi/4))

The bridge model uses a circular cross-section instead. Orca subsequently applies applicable print, filament and role flow factors and limits speed. First-layer flow ratio is gated by set_other_flow_ratios in this revision and does not apply to brim/skirt in that branch. See GCode.cpp lines9488–9527; exact enabled behavior matters.

Consequently beta10.1's height*width*speed value must remain labeled **nominal recipe flow**, not physically delivered volume or even necessarily the emitted G-code flow. As an illustration, h0.2/w0.5/v110 gives nominal11mm3/s, but the ordinary rounded bead model is about10.06mm3/s before other multipliers/limits. This illustration does not re-analyze the user's previous11mm3/s recording.

When available, derive a separate commanded feed-volume estimate from positive extruder velocity * pi * filament_diameter^2/4 over the aligned deposition interval. Exclude retraction and refill; label whether this is G-code E, native extrusion trajectory or PA-adjusted motion. Neither a requested trajectory nor changing raw counts proves instantaneous nozzle output, force latency or statistical independence.

## What beta10.1 currently has versus what remains

| Area | Already present | Still needed for comprehensive slicer-aware learning |
|---|---|---|
| Recipe | Material, height, width, speed, filament diameter, nominal flow | Effective per-role/per-segment geometry, flow factors, nozzle/temp/PA/pattern identity |
| Context | Requested motion/E, temperatures/fans, mesh and other printer context | Persistent joined slicer manifest and role/tool/object alignment to samples |
| Margin identity | Full basic recipe key | Compatible physics fingerprint and validation gates; not all378 settings as independent regressors |
| Search abort | Recipe and speed/extrusion factor changes | Role/tool/temp/fan/PA changes, material mixing, unsupported/nonplanar paths, short/unstable segments |
| Recording | Continuous accel/ADC and10Hz-capable force feed; inferred labels | Segment masks and deposition/pressure-history eligibility before fitting/learning |
| This audit | All378 process bindings classified;61 developer definitions and79 selected dependencies retained | Real user's resolved project/profile values and a deliberate tested implementation |

This audit does not add a script to the slicer or make new G-code parameters mandatory. It also does not claim the full profile snapshot or every eligibility gate is already implemented. Existing beta10.1 runtime test results remain unchanged; the new checks validate inventory coverage, classification and source traceability only.

## Practical interpretation of the knee trials

- Keep descending and ascending force histories separate. Nearby over-squeezed material, pressure recovery, changing role/flow and spatial effects can all change the return path; time-only settling is not sufficient proof of equivalent conditions.
- At roughly10Hz, sample positions are widely spaced at fast speeds; a0.1s interval is about10mm of path at100mm/s before accounting for receipt/queue/board latency. Small gaps, scarf ramps and corners are not resolved cleanly by a force sample alone.
- Fit only a window with adequate samples, steady motion/temperature and consistent eligible role/tool/gap, excluding transition tails. Keep timing uncertainty and search history in the result. Faster printing can improve force visibility but also increases transient/inertial effects and melt-capacity demand.
- A clean fixed-offset confirmation and layer2 inspection remain necessary. The candidate-0.075 and its provisional fast-flow margin are not universal settings validated by this parameter audit.

## Source references

- [Exact process UI / Tab.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/slic3r/GUI/Tab.cpp): six pages, multi-field rows, conditional features and plugin controls.
- [Exact definitions / PrintConfig.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/libslic3r/PrintConfig.cpp): labels/types/modes/defaults/tooltips, adaptive volumetric speed, ratios and dynamic plugin overrides.
- [Exact feature conditions / ConfigManipulation.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/slic3r/GUI/ConfigManipulation.cpp): applicability and toggle dependencies. These were inspected as source, not replayed in a GUI.
- [Exact bead model / Flow.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/libslic3r/Flow.cpp#L226).
- [Exact G-code emission / GCode.cpp](https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/libslic3r/GCode.cpp#L9488): role-dependent flow multipliers and first-layer handling; role speed selection near9611 and MVS limit near9660.

The source inspection establishes available fields and their implemented emission branches, not the user's effective settings. No printer, GitHub, Windows vault or slicer profile changes were made.
