# Independent review of beta 10.2

Reviewed the published beta10.2 source at `7a90f1ca2c5ff8e447c0716d9a7098c0bbea1a2d`, not just the implementation description. Corrected continuation: **0.1.0-beta.10.2.1**. No printer installation or live motion/heating commands were run.

## Confirmed findings and corrections

| Priority | Finding in 10.2 | Correction |
|---|---|---|
| High | Matching G1 parameters alone did not establish matching native modal state or trajectory after hidden macro effects. Samples could carry the wrong emitted geometry/flow identity. | Verify native pre/post XYZ, extrusion modes/delta and inherited feed; mismatches remain recorded but are not attributable fit samples. Original native command still executes exactly once. |
| High | Queue lead was capped at 5 seconds, even when a long queued move had 20 seconds remaining. Offset/label windows could be scheduled early. | Preserve the complete finite nonnegative queue lead. |
| High | A force-limit stop created `knee_last` and used the successful-knee message, making an unfitted threshold available for later margin learning. | Preserve relief movement, mark the event `accepted: false`, clear the learnable result and report a stop rather than a successful fit. |
| Medium | Parser M82 ignored the effect of G91 on E, contrary to supplied native Klipper. Relative E after T also stayed unknown unnecessarily. | Match native effective absolute-E logic and derive relative delta directly without requiring an absolute E origin. |
| Medium | Pinned Orca emits selected-plate wipe-tower coordinates and then their serialized array under the same key. Literal conflict rejection could disable valid input. | Recognize the known two-write numeric pattern; preserve both variants and selected-plate coordinates. Unrelated conflicts still fail eligibility. |
| Medium | Numeric config vectors were split on semicolons, while Orca ConfigOptionFloats serializes with commas. Valid multi-entry filament dimensions/flow ratios could be rejected. | Use type-aware numeric splitting; keep serialized raw values unchanged and select only a verified single used-filament mapping. |
| Medium | virtual_sdcard closes its file before its last queued moves execute. Resetting attribution immediately could drop the end of a layer. | Retain the immutable current file/timeline through active capture; clock/velocity eligibility still excludes idle time. |
| Medium | Missing raft/mixing/spiral/flushing flags defaulted to disabled, conflicting with the stated unknown-data policy. | Missing relevant flags explicitly block fitting while passive data remains available. |
| Medium | Filament preset identity was excluded as cosmetic provenance, potentially merging different materials with otherwise identical settings. | Keep filament_settings_id in the physics fingerprint. Output filename and notes remain provenance-only. |

Additional robustness: enforce the scan byte bound even if a file grows during reading; refuse an encoded optional snapshot larger than the runtime can consume before creating its output file. These are parser/storage bounds, not Z-offset limits.

## Evidence and verification

An initial focused audit used the unmodified supplied Klipper `GCodeMove` methods plus the shipped integration. Before corrections, **6 of 7 focused cases failed**: modal mismatch, hidden coordinate change, G91/M82 extrusion, queue truncation, force-limit learning and EOF attribution. The native reference is included under tests/native_reference with its GPL notice and SHA-256. No native source was modified.

Expanded regressions cover inherited-feed and post-move rewrites, relative E after T, missing flags, actual Orca serialization, known duplicate plate keys, unrelated conflicts and material preset identity. The whole suite now passes **314 tests + 37 subtests**; tests/BETA10_2_1_VALIDATION.txt stores the source log. The extracted installation ZIP is checked separately. One dependency deprecation warning remains; it is not a runtime printer error.

Pinned Orca evidence: GCode.cpp append_full_config at 606b50f1 emits wipe_tower_x/y selected-plate values before the normal serialization branch. Config.hpp ConfigOptionFloatsTempl::serialize uses commas. Source: https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/libslic3r/GCode.cpp and https://github.com/OrcaSlicer/OrcaSlicer/blob/606b50f1/src/libslic3r/Config.hpp . The fetched Config.hpp SHA-256 is 8f690a9a2324f50bd60490a75359972b9f5178ed4a6a642b3cfe06fceaaa5353.

## Remaining limits

Physical printer validation is pending. Host receipt timing is not the ADC acquisition clock. The implementation does not fully reconstruct neighboring over-squeezed paths, prove stored-pressure causation, or resolve every inherited modifier/filament variant. Unsupported contexts are recorded and excluded. A successful software fit does not validate a universal knee margin or prove a clean first layer. Keep clean fixed-offset and recipe-transfer confirmation tests in the hardware plan.

Orca startup and layer hooks remain unchanged. Stable Auto Trim main is outside this patch.
