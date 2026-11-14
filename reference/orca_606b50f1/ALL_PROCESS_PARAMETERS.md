# All six OrcaSlicer process tabs — 2.5.0-dev / 606b50f1

Complete static-source coverage, including Basic/Advanced/Expert/Developer modes and conditional controls. Counts are setting bindings, not screenshots of all widgets simultaneously. Every row has a handling decision. Definition modes are source metadata, not a claim the field is currently active.

## Quality — 109 settings

### Layer height

Resolve first-printing height including adaptive/sublayer changes; later-layer height is not a substitute. Block mixed-color sublayers from ordinary knee learning.

| Setting / key | Mode | Treatment |
|---|---|---|
| Layer height / `layer_height` | unspecified/default | Resolve first-printing height including adaptive/sublayer changes; later-layer height is not a substitute. Block mixed-color sublayers from ordinary knee learning. |
| First layer height / `initial_layer_print_height` | unspecified/default | Resolve first-printing height including adaptive/sublayer changes; later-layer height is not a substitute. Block mixed-color sublayers from ordinary knee learning. |
| Mixed color sublayer / `enable_mixed_color_sublayer` | Simple | Resolve first-printing height including adaptive/sublayer changes; later-layer height is not a substitute. Block mixed-color sublayers from ordinary knee learning. |

### Line width

Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width.

| Setting / key | Mode | Treatment |
|---|---|---|
| Default / `line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| First layer / `initial_layer_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Outer wall / `outer_wall_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Inner wall / `inner_wall_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Top surface / `top_surface_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Sparse infill / `sparse_infill_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Internal solid infill / `internal_solid_infill_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Support / `support_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |
| Bridge / `bridge_line_width` | Advanced | Resolve default/percentage/auto widths and each extrusion role; measure emitted segment width rather than use one global width. |

### Seam

Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them.

| Setting / key | Mode | Treatment |
|---|---|---|
| Seam position / `seam_position` | Simple | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Staggered inner seams / `staggered_inner_seams` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Seam gap / `seam_gap` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf joint seam (beta) / `seam_slope_type` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Conditional scarf joint / `seam_slope_conditional` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Conditional angle threshold / `scarf_angle_threshold` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Conditional overhang threshold / `scarf_overhang_threshold` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf joint speed / `scarf_joint_speed` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf start height / `seam_slope_start_height` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf around entire wall / `seam_slope_entire_loop` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf length / `seam_slope_min_length` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf steps / `seam_slope_steps` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf joint flow ratio / `scarf_joint_flow_ratio` | Expert | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Scarf joint for inner walls / `seam_slope_inner_walls` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Role based wipe speed / `role_based_wipe_speed` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Wipe speed / `wipe_speed` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Wipe on loops / `wipe_on_loops` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Wipe inward / `wipe_inward` | Expert | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Wipe inward distance / `wipe_inward_distance` | Expert | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |
| Wipe before external loop / `wipe_before_external_loop` | Advanced | Seam ramps, scarf Z/flow/speed and wipe/loop moves change pressure and clearance. Mark seams/wipes and settling zones; do not fit a constant-gap knee through them. |

### Precision

Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions.

| Setting / key | Mode | Treatment |
|---|---|---|
| Slice gap closing radius / `slice_closing_radius` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Resolution / `resolution` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Arc fitting / `enable_arc_fitting` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| X-Y hole compensation / `xy_hole_compensation` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| X-Y contour compensation / `xy_contour_compensation` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Elephant foot compensation / `elefant_foot_compensation` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Elephant foot layers density / `elefant_foot_layers_density` | Expert | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Elephant foot compensation layers / `elefant_foot_compensation_layers` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Precise wall / `precise_outer_wall` | unspecified/default | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Precise Z height / `precise_z_height` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Convert holes to polyholes / `hole_to_polyhole` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Polyhole detection margin / `hole_to_polyhole_threshold` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Polyhole twist / `hole_to_polyhole_twisted` | Advanced | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |
| Maximum Polyhole edge count / `hole_to_polyhole_max_edges` | Expert | Geometry compensation, curve resolution and Z rounding alter toolpath position, spacing and contact history. Record actual path/mesh coordinates and resolved dimensions. |

### Ironing

Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition.

| Setting / key | Mode | Treatment |
|---|---|---|
| Ironing type / `ironing_type` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Ironing Pattern / `ironing_pattern` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Ironing flow / `ironing_flow` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Ironing line spacing / `ironing_spacing` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Ironing inset / `ironing_inset` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Ironing angle offset / `ironing_angle` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |
| Fixed ironing angle / `ironing_angle_fixed` | Advanced | Ironing has intentionally different flow/gap/contact. Keep it separate; if present on a one-layer part it is not ordinary first-layer deposition. |

### Z contouring

Nonplanar/Z-contouring moves can change clearance independently of a global offset. Disable ordinary knee learning for nonplanar segments unless explicitly supported.

| Setting / key | Mode | Treatment |
|---|---|---|
| Z contouring enabled / `zaa_enabled` | Expert | Nonplanar/Z-contouring moves can change clearance independently of a global offset. Disable ordinary knee learning for nonplanar segments unless explicitly supported. |
| Minimize wall height angle / `zaa_minimize_perimeter_height` | Expert | Nonplanar/Z-contouring moves can change clearance independently of a global offset. Disable ordinary knee learning for nonplanar segments unless explicitly supported. |
| Minimum Z height / `zaa_min_z` | Expert | Nonplanar/Z-contouring moves can change clearance independently of a global offset. Disable ordinary knee learning for nonplanar segments unless explicitly supported. |
| Don't alternate fill direction / `zaa_dont_alternate_fill_direction` | Expert | Nonplanar/Z-contouring moves can change clearance independently of a global offset. Disable ordinary knee learning for nonplanar segments unless explicitly supported. |

### Wall generator

Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately.

| Setting / key | Mode | Treatment |
|---|---|---|
| Wall generator / `wall_generator` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Wall transitioning threshold angle / `wall_transition_angle` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Wall transitioning filter margin / `wall_transition_filter_deviation` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Wall transition length / `wall_transition_length` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Wall distribution count / `wall_distribution_count` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| First layer minimum wall width / `initial_layer_min_bead_width` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Minimum wall width / `min_bead_width` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Minimum feature size / `min_feature_size` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Minimum wall length / `min_length_factor` | Advanced | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Maximum wall resolution / `wall_maximum_resolution` | Expert | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |
| Maximum wall deviation / `wall_maximum_deviation` | Expert | Arachne can vary local bead widths and transitions despite identical nominal settings. Keep generator and local widths; exclude transitions or model separately. |

### Walls and surfaces

Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context.

| Setting / key | Mode | Treatment |
|---|---|---|
| Walls printing order / `wall_sequence` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Print infill first / `is_infill_first` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Wall loop direction / `wall_direction` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Flow ratio / `print_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Top surface flow ratio / `top_solid_infill_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Bottom surface flow ratio / `bottom_solid_infill_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Set other flow ratios / `set_other_flow_ratios` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| First layer flow ratio / `first_layer_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Outer wall flow ratio / `outer_wall_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Inner wall flow ratio / `inner_wall_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Overhang flow ratio / `overhang_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Sparse infill flow ratio / `sparse_infill_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Internal solid infill flow ratio / `internal_solid_infill_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Gap fill flow ratio / `gap_fill_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Support flow ratio / `support_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Support interface flow ratio / `support_interface_flow_ratio` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Only one wall on first layer / `only_one_wall_first_layer` | unspecified/default | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Only one wall on top surfaces / `only_one_wall_top` | unspecified/default | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| One wall threshold / `min_width_top_surface` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Avoid crossing walls / `reduce_crossing_wall` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Avoid crossing walls - Max detour length / `max_travel_detour_distance` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Small area flow compensation (beta) / `small_area_infill_flow_compensation` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |
| Flow Compensation Model / `small_area_infill_flow_compensation_model` | Advanced | Capture effective role flow ratios, first-layer switches and wall/infill ordering. Area compensation and overlaps change deposition and subsequent contact; fingerprint plus per-role/segment context. |

### Bridging

Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance.

| Setting / key | Mode | Treatment |
|---|---|---|
| Bridge flow ratio / `bridge_flow` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Internal bridge flow ratio / `internal_bridge_flow` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| External bridge density / `bridge_density` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Internal bridge density / `internal_bridge_density` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Thick external bridges / `thick_bridges` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Thick internal bridges / `thick_internal_bridges` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Extra bridge layers (beta) / `enable_extra_bridge_layer` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Filter out small internal bridges / `dont_filter_internal_bridges` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |
| Bridge counterbore holes / `counterbore_hole_bridging` | Advanced | Bridge flow, density, thickness and unsupported cross-section use different geometry. Exclude bridge roles from ordinary bed-contact fitting; retain settings for provenance. |

### Overhangs

Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment.

| Setting / key | Mode | Treatment |
|---|---|---|
| Detect overhang walls / `detect_overhang_wall` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Print unsupported walls last / `unsupported_wall_last` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Make overhangs printable / `make_overhang_printable` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Make overhangs printable - Maximum angle / `make_overhang_printable_angle` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Make overhangs printable - Hole area / `make_overhang_printable_hole_size` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Extra perimeters on overhangs / `extra_perimeters_on_overhangs` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Reverse on even / `overhang_reverse` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Reverse only internal perimeters / `overhang_reverse_internal_only` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |
| Reverse threshold / `overhang_reverse_threshold` | Advanced | Overhang generation/reversal and ordering change unsupported paths/pressure. Use emitted role and support state; do not assume these affect every first-layer segment. |

## Strength — 66 settings

### Walls

Wall count, alternation and thin-wall handling affect role duration, nearby material and short-segment transients. Preserve path order and exclude mixed roles from one knee hold.

| Setting / key | Mode | Treatment |
|---|---|---|
| Wall loops / `wall_loops` | unspecified/default | Wall count, alternation and thin-wall handling affect role duration, nearby material and short-segment transients. Preserve path order and exclude mixed roles from one knee hold. |
| Alternate extra wall / `alternate_extra_wall` | Advanced | Wall count, alternation and thin-wall handling affect role duration, nearby material and short-segment transients. Preserve path order and exclude mixed roles from one knee hold. |
| Detect thin walls / `detect_thin_wall` | Advanced | Wall count, alternation and thin-wall handling affect role duration, nearby material and short-segment transients. Preserve path order and exclude mixed roles from one knee hold. |

### Top/bottom shells

First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference.

| Setting / key | Mode | Treatment |
|---|---|---|
| Top shell layers / `top_shell_layers` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top shell thickness / `top_shell_thickness` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top paint penetration layers / `top_color_penetration_layers` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top surface density / `top_surface_density` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top surface pattern / `top_surface_pattern` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top surface fill order / `top_surface_fill_order` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top layer direction / `top_layer_direction` | Simple | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top surface expansion / `top_surface_expansion` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top expansion wall margin / `top_surface_expansion_margin` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top expansion direction / `top_surface_expansion_direction` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom shell layers / `bottom_shell_layers` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom shell thickness / `bottom_shell_thickness` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom paint penetration layers / `bottom_color_penetration_layers` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom surface density / `bottom_surface_density` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom surface pattern / `bottom_surface_pattern` | unspecified/default | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom surface fill order / `bottom_surface_fill_order` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Bottom layer direction / `bottom_layer_direction` | Simple | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Center surface pattern on / `center_of_surface_pattern` | Expert | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |
| Top/Bottom solid infill/wall overlap / `top_bottom_infill_wall_overlap` | Advanced | First layers are often bottom solid fill, while one-layer pads may also be top surfaces. Density, pattern, expansion and overlap change local volume and adjacent-line interference. |

### Infill

Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths.

| Setting / key | Mode | Treatment |
|---|---|---|
| Sparse infill density / `sparse_infill_density` | unspecified/default | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Fill Multiline / `fill_multiline` | unspecified/default | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Sparse infill pattern / `sparse_infill_pattern` | unspecified/default | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Adaptive density (experimental) / `adaptive_infill_mode` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Interior density / `adaptive_infill_interior_density` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Adaptive gradient / `adaptive_infill_gradient` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Z-buckling bias optimization (experimental) / `gyroid_optimized` | unspecified/default | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Sparse infill smooth factor / `sparse_infill_smooth_factor` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Sparse infill direction / `infill_direction` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Sparse infill rotation template / `sparse_infill_rotate_template` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Skin infill density / `skin_infill_density` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Skeleton infill density / `skeleton_infill_density` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Infill lock depth / `infill_lock_depth` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Skin infill depth / `skin_infill_depth` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Skin line width / `skin_infill_line_width` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Skeleton line width / `skeleton_infill_line_width` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Symmetric infill Y axis / `symmetric_infill_y_axis` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Fill pattern tops / `infill_complete_top` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Infill shift step / `infill_shift_step` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Lateral lattice angle 1 / `lateral_lattice_angle_1` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Lateral lattice angle 2 / `lateral_lattice_angle_2` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Infill overhang angle / `infill_overhang_angle` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Lightning overhang angle / `lightning_overhang_angle` | Expert | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Prune angle / `lightning_prune_angle` | Expert | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Straightening angle / `lightning_straightening_angle` | Expert | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Maximum length of the infill anchor / `infill_anchor_max` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Sparse infill anchor length / `infill_anchor` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Internal solid infill pattern / `internal_solid_infill_pattern` | unspecified/default | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Solid infill direction / `solid_infill_direction` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Solid infill rotation template / `solid_infill_rotate_template` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Apply gap fill / `gap_fill_target` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Filter out tiny gaps / `filter_out_gap_fill` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Separated infills / `separated_infills` | Expert | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |
| Infill/wall overlap / `infill_wall_overlap` | Advanced | Pattern, direction/rotation, density, spacing, anchoring and gap fill alter adjacency, crossings and reversals. Distinguish sparse from solid/bottom fill and record prior deposited paths. |

### Advanced

Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1.

| Setting / key | Mode | Treatment |
|---|---|---|
| Align directions to model / `align_infill_direction_to_model` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Insert solid layers / `extra_solid_infills` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| External bridge infill direction / `bridge_angle` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Internal bridge infill direction / `internal_bridge_angle` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Relative bridge angle / `relative_bridge_angle` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Minimum sparse infill threshold / `minimum_sparse_infill_area` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Infill combination / `infill_combination` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Infill combination - Max layer height / `infill_combination_max_layer_height` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Detect narrow internal solid infills / `detect_narrow_internal_solid_infill` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |
| Ensure vertical shell thickness / `ensure_vertical_shell_thickness` | Advanced | Combined/narrow/extra infill and bridge rules change effective heights and role scheduling. Apply only to emitted roles; retain profile setting even when inactive on layer1. |

## Speed — 50 settings

### First layer speed

Record actual first-layer wall, infill and travel speeds separately and resolve slow-layer ramps. Slicer requested speed is not the executed speed on short segments.

| Setting / key | Mode | Treatment |
|---|---|---|
| First layer / `initial_layer_speed` | Advanced | Record actual first-layer wall, infill and travel speeds separately and resolve slow-layer ramps. Slicer requested speed is not the executed speed on short segments. |
| First layer infill / `initial_layer_infill_speed` | Advanced | Record actual first-layer wall, infill and travel speeds separately and resolve slow-layer ramps. Slicer requested speed is not the executed speed on short segments. |
| First layer travel speed / `initial_layer_travel_speed` | Advanced | Record actual first-layer wall, infill and travel speeds separately and resolve slow-layer ramps. Slicer requested speed is not the executed speed on short segments. |
| Number of slow layers / `slow_down_layers` | Advanced | Record actual first-layer wall, infill and travel speeds separately and resolve slow-layer ramps. Slicer requested speed is not the executed speed on short segments. |

### Other layers speed

These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED.

| Setting / key | Mode | Treatment |
|---|---|---|
| Outer wall / `outer_wall_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Inner wall / `inner_wall_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Small perimeters / `small_perimeter_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Small perimeters threshold / `small_perimeter_threshold` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Sparse infill / `sparse_infill_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Internal solid infill / `internal_solid_infill_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Top surface / `top_surface_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Gap infill / `gap_infill_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Ironing speed / `ironing_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Support / `support_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Support interface / `support_interface_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Small support perimeters / `small_support_perimeter_speed` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |
| Small support perimeters threshold / `small_support_perimeter_threshold` | Advanced | These speeds can matter to top, support, ironing or small features, including special first-layer roles. Use role-specific emitted/resolved values, not one recipe SPEED. |

### Overhang speed

Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history.

| Setting / key | Mode | Treatment |
|---|---|---|
| Slow down for overhangs / `enable_overhang_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| Slow down for curled perimeters / `slowdown_for_curled_perimeters` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| "10%" / `overhang_1_4_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| "25%" / `overhang_2_4_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| "50%" / `overhang_3_4_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| "75%" / `overhang_4_4_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| External / `bridge_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |
| Internal / `internal_bridge_speed` | Advanced | Percent/inherited overhang and bridge limits select speeds by geometry/role. Exclude unsupported roles from flat-bed fitting; retain speed selections for history. |

### Travel speed

Travel causes inertial load and pressure relaxation/retraction gaps. Exclude nondeposition and post-travel transients, retaining length and time since extrusion.

| Setting / key | Mode | Treatment |
|---|---|---|
| Travel / `travel_speed` | Advanced | Travel causes inertial load and pressure relaxation/retraction gaps. Exclude nondeposition and post-travel transients, retaining length and time since extrusion. |

### Acceleration

Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady.

| Setting / key | Mode | Treatment |
|---|---|---|
| Normal printing / `default_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Outer wall / `outer_wall_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Inner wall / `inner_wall_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Bridge / `bridge_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Sparse infill / `sparse_infill_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Internal solid infill / `internal_solid_infill_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| First layer / `initial_layer_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| First layer travel / `initial_layer_travel_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Top surface / `top_surface_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Travel / `travel_acceleration` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| Enable accel_to_decel / `accel_to_decel_enable` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |
| accel_to_decel / `accel_to_decel_factor` | Advanced | Acceleration/deceleration, role overrides and accel-to-decel affect force, pressure and reachable speed. Capture effective firmware acceleration and settling; do not treat all samples in a hold as steady. |

### Junction Deviation

Firmware/flavor-dependent cornering control changes corner speed and inertial/pressure transients. Preserve applicability and actual emitted commands.

| Setting / key | Mode | Treatment |
|---|---|---|
| Junction Deviation / `default_junction_deviation` | Advanced | Firmware/flavor-dependent cornering control changes corner speed and inertial/pressure transients. Preserve applicability and actual emitted commands. |

### Jerk(XY)

Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context.

| Setting / key | Mode | Treatment |
|---|---|---|
| Default / `default_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| Outer wall / `outer_wall_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| Inner wall / `inner_wall_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| Infill / `infill_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| Top surface / `top_surface_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| First layer / `initial_layer_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| First layer travel / `initial_layer_travel_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |
| Travel / `travel_jerk` | Advanced | Requested role jerk is not automatically Klipper square-corner velocity. Check emitted commands and firmware translation; preserve role cornering and transient context. |

### Advanced

Volumetric rate-slope limits and smoothing reshape extrusion through time. Record resulting E/XYZ trajectory and transition history rather than assume constant nominal flow.

| Setting / key | Mode | Treatment |
|---|---|---|
| Extrusion rate smoothing / `max_volumetric_extrusion_rate_slope` | Advanced | Volumetric rate-slope limits and smoothing reshape extrusion through time. Record resulting E/XYZ trajectory and transition history rather than assume constant nominal flow. |
| Smoothing segment length / `max_volumetric_extrusion_rate_slope_segment_length` | Advanced | Volumetric rate-slope limits and smoothing reshape extrusion through time. Record resulting E/XYZ trajectory and transition history rather than assume constant nominal flow. |
| Apply only on external features / `extrusion_rate_smoothing_external_perimeter_only` | Advanced | Volumetric rate-slope limits and smoothing reshape extrusion through time. Record resulting E/XYZ trajectory and transition history rather than assume constant nominal flow. |

## Support — 49 settings

### Support

Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles.

| Setting / key | Mode | Treatment |
|---|---|---|
| Enable support / `enable_support` | unspecified/default | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Type / `support_type` | Simple | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Style / `support_style` | Advanced | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Threshold angle / `support_threshold_angle` | Simple | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Threshold overlap / `support_threshold_overlap` | Simple | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| First layer density / `raft_first_layer_density` | Advanced | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| First layer expansion / `raft_first_layer_expansion` | Advanced | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| On build plate only / `support_on_build_plate_only` | Simple | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Support critical regions only / `support_critical_regions_only` | Advanced | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |
| Ignore small overhangs / `support_remove_small_overhang` | Advanced | Support enable/type/thresholds change whether first-layer samples are support or model. Raft density/expansion are distinct contact geometry; do not learn a model margin from these roles. |

### Raft

Raft changes what rests on the bed and model first-layer height/reference. Ordinary model-on-bed knee calibration is ineligible; use a separately validated raft model.

| Setting / key | Mode | Treatment |
|---|---|---|
| Raft layers / `raft_layers` | Advanced | Raft changes what rests on the bed and model first-layer height/reference. Ordinary model-on-bed knee calibration is ineligible; use a separately validated raft model. |
| Raft contact Z distance / `raft_contact_distance` | Advanced | Raft changes what rests on the bed and model first-layer height/reference. Ordinary model-on-bed knee calibration is ineligible; use a separately validated raft model. |
| Raft expansion / `raft_expansion` | Advanced | Raft changes what rests on the bed and model first-layer height/reference. Ordinary model-on-bed knee calibration is ineligible; use a separately validated raft model. |

### Filament for Supports

Support and interface can select another filament/tool and temperature/flow calibration. Track actual material and role; exclude from model-material margin learning.

| Setting / key | Mode | Treatment |
|---|---|---|
| Support/raft base / `support_filament` | Simple | Support and interface can select another filament/tool and temperature/flow calibration. Track actual material and role; exclude from model-material margin learning. |
| Support/raft interface / `support_interface_filament` | Simple | Support and interface can select another filament/tool and temperature/flow calibration. Track actual material and role; exclude from model-material margin learning. |
| Avoid interface filament for base / `support_interface_not_for_body` | Simple | Support and interface can select another filament/tool and temperature/flow calibration. Track actual material and role; exclude from model-material margin learning. |

### Support ironing

Support ironing is a different flow/contact operation. Separate role and avoid learning its force as a model first-layer height.

| Setting / key | Mode | Treatment |
|---|---|---|
| Ironing Support Interface / `support_ironing` | Advanced | Support ironing is a different flow/contact operation. Separate role and avoid learning its force as a model first-layer height. |
| Support Ironing Pattern / `support_ironing_pattern` | Advanced | Support ironing is a different flow/contact operation. Separate role and avoid learning its force as a model first-layer height. |
| Support Ironing flow / `support_ironing_flow` | Advanced | Support ironing is a different flow/contact operation. Separate role and avoid learning its force as a model first-layer height. |
| Support Ironing line spacing / `support_ironing_spacing` | Advanced | Support ironing is a different flow/contact operation. Separate role and avoid learning its force as a model first-layer height. |

### Advanced

Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity.

| Setting / key | Mode | Treatment |
|---|---|---|
| Top Z distance / `support_top_z_distance` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Bottom Z distance / `support_bottom_z_distance` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Support wall loops / `tree_support_wall_count` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Base pattern / `support_base_pattern` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Base pattern spacing / `support_base_pattern_spacing` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Pattern angle / `support_angle` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Top interface layers / `support_interface_top_layers` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Bottom interface layers / `support_interface_bottom_layers` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Interface pattern / `support_interface_pattern` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Top interface spacing / `support_interface_spacing` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Bottom interface spacing / `support_bottom_interface_spacing` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Normal support expansion / `support_expansion` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Support/object XY distance / `support_object_xy_distance` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Support/object first layer gap / `support_object_first_layer_gap` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Don't support bridges / `bridge_no_support` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Max bridge length / `max_bridge_length` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |
| Independent support layer height / `independent_support_layer_height` | Advanced | Z gaps, pattern spacing/density/angles, independent heights and interface layers change support contact and neighboring paths. Preserve effective support heights and role identity. |

### Tree supports

Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths.

| Setting / key | Mode | Treatment |
|---|---|---|
| Tip Diameter / `tree_support_tip_diameter` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch distance / `tree_support_branch_distance` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch distance / `tree_support_branch_distance_organic` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Branch Density / `tree_support_top_rate` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch diameter / `tree_support_branch_diameter` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch diameter / `tree_support_branch_diameter_organic` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Branch Diameter Angle / `tree_support_branch_diameter_angle` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch angle / `tree_support_branch_angle` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support branch angle / `tree_support_branch_angle_organic` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Preferred Branch Angle / `tree_support_angle_slow` | Advanced | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Auto brim width / `tree_support_auto_brim` | unspecified/default | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |
| Tree support brim width / `tree_support_brim_width` | unspecified/default | Tree branches/brims/walls and geometry change support footprint and short isolated paths. Retain provenance and support masks; no ordinary model-knee fit on these paths. |

## Multimaterial — 49 settings

### Prime tower

Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes.

| Setting / key | Mode | Treatment |
|---|---|---|
| Enable / `enable_prime_tower` | Simple | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Skip points / `prime_tower_skip_points` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Enable tower interface features / `enable_tower_interface_features` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Cool down from interface boost during prime tower / `enable_tower_interface_cooldown_during_tower` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Internal ribs / `prime_tower_enable_framework` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Width / `prime_tower_width` | Simple | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Belt purge tower width / `belt_purge_tower_width` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Prime volume / `prime_volume` | Simple | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Brim width / `prime_tower_brim_width` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Infill gap / `prime_tower_infill_gap` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Wipe tower rotation angle / `wipe_tower_rotation_angle` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Maximal bridging distance / `wipe_tower_bridging` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Wipe tower purge lines spacing / `wipe_tower_extra_spacing` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Extra flow for purging / `wipe_tower_extra_flow` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Maximum wipe tower print speed / `wipe_tower_max_purge_speed` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Wall type / `wipe_tower_wall_type` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Stabilization cone apex angle / `wipe_tower_cone_angle` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Extra rib length / `wipe_tower_extra_rib_length` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Rib width / `wipe_tower_rib_width` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Fillet wall / `wipe_tower_fillet_wall` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| No sparse layers (beta) / `wipe_tower_no_sparse_layers` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Combine sparse layers / `wipe_tower_sparse_layers_combination` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |
| Prime all printing extruders / `single_extruder_multi_material_priming` | Advanced | Tower priming/flow/cooling/geometry and sparse-layer scheduling affect pressure, temperature and deposited bed mass. Exclude tower samples and require recovery after tool changes. |

### Filament for Features

Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder.

| Setting / key | Mode | Treatment |
|---|---|---|
| Outer walls / `outer_wall_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Inner walls / `inner_wall_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Infill / `sparse_infill_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Internal solid infill / `internal_solid_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Top surface / `top_surface_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Bottom surface / `bottom_surface_filament_id` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |
| Wipe tower / `wipe_tower_filament` | Advanced | Material may vary between wall, bottom, infill and tower in the same layer. Record actual tool/spool/profile per segment, not just initial_extruder. |

### Ooze prevention

Standby/preheat timing and temperature alter viscosity, ooze and pressure at resume. Capture targets/actual temperature and settling before re-eligibility.

| Setting / key | Mode | Treatment |
|---|---|---|
| Enable / `ooze_prevention` | Advanced | Standby/preheat timing and temperature alter viscosity, ooze and pressure at resume. Capture targets/actual temperature and settling before re-eligibility. |
| Temperature variation / `standby_temperature_delta` | Advanced | Standby/preheat timing and temperature alter viscosity, ooze and pressure at resume. Capture targets/actual temperature and settling before re-eligibility. |
| Preheat time / `preheat_time` | Advanced | Standby/preheat timing and temperature alter viscosity, ooze and pressure at resume. Capture targets/actual temperature and settling before re-eligibility. |
| Preheat steps / `preheat_steps` | Develop | Standby/preheat timing and temperature alter viscosity, ooze and pressure at resume. Capture targets/actual temperature and settling before re-eligibility. |

### Flush options

Flush into object/infill/support intentionally changes material/volume/state. Reject those portions and settling windows from ordinary force/margin training.

| Setting / key | Mode | Treatment |
|---|---|---|
| Flush into objects' infill / `flush_into_infill` | unspecified/default | Flush into object/infill/support intentionally changes material/volume/state. Reject those portions and settling windows from ordinary force/margin training. |
| Flush into this object / `flush_into_objects` | unspecified/default | Flush into object/infill/support intentionally changes material/volume/state. Reject those portions and settling windows from ordinary force/margin training. |
| Flush into objects' support / `flush_into_support` | unspecified/default | Flush into object/infill/support intentionally changes material/volume/state. Reject those portions and settling windows from ordinary force/margin training. |

### Advanced

Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key.

| Setting / key | Mode | Treatment |
|---|---|---|
| Use beam interlocking / `interlocking_beam` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Toolchange ordering / `toolchange_ordering` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Cyclic order / `toolchange_cyclic_order` | Expert | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Apply cyclic order to first layer / `toolchange_cyclic_first_layer` | Expert | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interface shells / `interface_shells` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Maximum width of a segmented region / `mmu_segmented_region_max_width` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking depth of a segmented region / `mmu_segmented_region_interlocking_depth` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking beam width / `interlocking_beam_width` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking direction / `interlocking_orientation` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking beam layers / `interlocking_beam_layer_count` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking depth / `interlocking_depth` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |
| Interlocking boundary avoidance / `interlocking_boundary_avoidance` | Advanced | Interlocks, interface shells and tool-change order alter local material and path history. Segment by actual role/tool; fingerprint settings rather than share one whole-layer key. |

## Others — 55 settings

### Skirt

Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment.

| Setting / key | Mode | Treatment |
|---|---|---|
| Skirt loops / `skirt_loops` | Simple | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt type / `skirt_type` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt minimum extrusion length / `min_skirt_length` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt distance / `skirt_distance` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt start point / `skirt_start_angle` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt speed / `skirt_speed` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Skirt height / `skirt_height` | Simple | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Draft shield / `draft_shield` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |
| Single loop after first layer / `single_loop_draft_shield` | Advanced | Skirt/draft shield has its own speed, path and pressure history. Exclude skirt while retaining priming history and time before the model segment. |

### Brim

Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history.

| Setting / key | Mode | Treatment |
|---|---|---|
| Brim type / `brim_type` | Simple | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim width / `brim_width` | Simple | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Leading brim length / `leading_brim_length` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Extra brim width / `extra_brim_width` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim-object gap / `brim_object_gap` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim flow ratio / `brim_flow_ratio` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim follows compensated outline / `brim_use_efc_outline` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Combine brims / `combine_brims` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim ear max angle / `brim_ears_max_angle` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim ear detection radius / `brim_ears_detection_length` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |
| Brim ears outer only / `brim_ears_outer_only` | Advanced | Brim flow, gap and geometry change bed-contact extrusion near parts. Brim is not the model role and its first-layer flow multiplier treatment differs; retain masks/pressure history. |

### Special mode

Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support.

| Setting / key | Mode | Treatment |
|---|---|---|
| Slicing Mode / `slicing_mode` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Print sequence / `print_sequence` | Simple | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Intra-layer order / `print_order` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Spiral vase / `spiral_mode` | Simple | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Smooth Spiral / `spiral_mode_smooth` | Simple | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Max XY Smoothing / `spiral_mode_max_xy_smoothing` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Spiral starting flow ratio / `spiral_starting_flow_ratio` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Spiral finishing flow ratio / `spiral_finishing_flow_ratio` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Timelapse / `timelapse_type` | Simple | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |
| Enable clumping detection / `enable_wrapping_detection` | Advanced | Vase, object sequence, mixed layer identity and timelapse/wrapping moves can invalidate first-layer markers and constant clearance. Exclude incompatible modes until explicit support. |

### Fuzzy skin

Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit.

| Setting / key | Mode | Treatment |
|---|---|---|
| Fuzzy skin / `fuzzy_skin` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin generator mode / `fuzzy_skin_mode` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin noise type / `fuzzy_skin_noise_type` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin point distance / `fuzzy_skin_point_distance` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin thickness / `fuzzy_skin_thickness` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin feature size / `fuzzy_skin_scale` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy Skin Noise Octaves / `fuzzy_skin_octaves` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Fuzzy skin noise persistence / `fuzzy_skin_persistence` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Number of ripples per layer / `fuzzy_skin_ripples_per_layer` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Ripple offset / `fuzzy_skin_ripple_offset` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Layers between ripple offset / `fuzzy_skin_layers_between_ripple_offset` | Advanced | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |
| Apply fuzzy skin to first layer / `fuzzy_skin_first_layer` | Simple | Fuzzy skin can apply to layer1; point spacing/noise/width perturbations affect flow and inertia. Exclude affected paths from a flat steady-state knee fit. |

### G-code output

Preserve effective G-code precision, object/role labels and retraction policy. Formatting-only keys need provenance, not physical margin fitting.

| Setting / key | Mode | Treatment |
|---|---|---|
| Reduce infill retraction / `reduce_infill_retraction` | Advanced | Preserve effective G-code precision, object/role labels and retraction policy. Formatting-only keys need provenance, not physical margin fitting. |
| Add line number / `gcode_add_line_number` | Develop | Parser/provenance: numbering/checksum handling, not force physics. |
| Verbose G-code / `gcode_comments` | Advanced | Keep available role/width/height markers for segment classification; do not assume ordinary comments execute as firmware commands. |
| High precision G-code (experimental) / `high_precision_gcode` | Expert | Coordinate/E quantization changes can matter on thin layers; record precision and emitted values. |
| Label objects / `gcode_label_objects` | Advanced | Retain object-to-path identity for spatial comparison; labels do not change clearance by themselves. |
| Exclude objects / `exclude_object` | Advanced | Track actual excluded objects and modified path order; do not compare absent paths as though printed. |
| Outline tolerance / `exclude_object_tolerance` | Expert | Track bounds simplification/labeling uncertainty; verify actual paths rather than use object bounds as precise deposition masks. |
| Filename format / `filename_format` | Advanced | Output naming only: provenance, not a physical margin feature. |

### Change extrusion role G-code

Custom role scripts can modify temperatures, offsets, flow and motion. Keep their content/hash and actual effects; never execute scripts while importing profiles.

| Setting / key | Mode | Treatment |
|---|---|---|
| Change extrusion role G-code (process) / `process_change_extrusion_role_gcode` | Advanced | Custom role scripts can modify temperatures, offsets, flow and motion. Keep their content/hash and actual effects; never execute scripts while importing profiles. |

### Post-processing Scripts

External scripts can change emitted G-code after settings resolve. Save final G-code hash and effective settings; do not execute them in analysis or trust preset values alone.

| Setting / key | Mode | Treatment |
|---|---|---|
| Post-processing Scripts / `post_process` | Advanced | External scripts can change emitted G-code after settings resolve. Save final G-code hash and effective settings; do not execute them in analysis or trust preset values alone. |

### Slicing Pipeline Plugin

Nightly Python pipeline plugins can alter slicing stages; snapshot identifiers/version/config and resulting paths. Unknown effects make automated margin reuse ineligible.

| Setting / key | Mode | Treatment |
|---|---|---|
| Slicing Pipeline Plugin / `slicing_pipeline_plugin` | Advanced | Nightly Python pipeline plugins can alter slicing stages; snapshot identifiers/version/config and resulting paths. Unknown effects make automated margin reuse ineligible. |

### Plugin Configuration

Per-process plugin capability overrides can change slicing. Retain final configuration/fingerprint and emitted output; presence in UI is not proof the plugin ran.

| Setting / key | Mode | Treatment |
|---|---|---|
| Capabilities / `print_plugin_config_overrides` | Advanced | Per-process plugin capability overrides can change slicing. Retain final configuration/fingerprint and emitted output; presence in UI is not proof the plugin ran. |

### Notes

User notes do not directly change deposition. Archive them; do not make them a physical regression input or mandatory margin-identity component.

| Setting / key | Mode | Treatment |
|---|---|---|
| Configuration notes / `notes` | Advanced | User notes do not directly change deposition. Archive them; do not make them a physical regression input or mandatory margin-identity component. |

## Developer definitions outside and inside these tabs

61 literal-key definitions are marked comDevelop in the pinned PrintConfig.cpp. Only preheat_steps and gcode_add_line_number are among the six process-page bindings; the others are machine/material/internal settings. Expert fields such as scarf flow are included above regardless. Some developer definitions are internal, unavailable on AD5X, or require another feature; do not force-enable them.

| Key | Label | Why retain |
|---|---|---|
| `nozzle_height` | Nozzle height | L("The height of nozzle tip.") |
| `grab_length` | Grab length |  |
| `required_nozzle_HRC` | Required nozzle HRC | L("Minimum HRC of nozzle required to print the filament. A value of 0 means no checking of the nozzle\'s HRC.") |
| `filament_map` | Filament map to extruder | L("Filament map to extruder.") |
| `filament_map_2` | "Filament map plus for multi nozzle" | "Filament map to the index identified by extruder and nozzle_volume_type" |
| `filament_volume_map` | filament_volume_map |  |
| `physical_extruder_map` | "Map the logical extruder to physical extruder" | "Map the logical extruder to physical extruder." |
| `filament_nozzle_map` | filament_nozzle_map |  |
| `filament_adaptive_volumetric_speed` | Adaptive volumetric speed | L("When enabled, the extrusion flow is limited by the smaller of " "the fitted value (calculated from line width and layer height) and the user-defined maximum flow." " When disabled, only the user-defined maximum flow is applied.  " "Note: Experimental and incomplete feature imported from BBS. Functional for some profiles that already have the variable saved.") |
| `filament_adhesiveness_category` | Adhesiveness Category | L("Filament category.") |
| `filament_cooling_before_tower` | Wipe tower cooling | L("Temperature drop before entering the wipe tower.") |
| `filament_is_mixed` | Is mixed filament | L("Whether this filament slot is a mixed filament composed of multiple physical filaments") |
| `filament_mixed_components` | Mixed filament components | L("Comma-separated 1-based indices of component filaments, e.g. \"1,3\"") |
| `filament_mixed_sublayer_ratios` | Mixed filament sublayer ratios | L("Comma-separated ratio values summing to 1.0, e.g. \"0.7,0.3\"") |
| `filament_mixed_gradient` | Mixed filament gradient | L("Enable Z-direction gradient mode for mixed filament sub-layers. " "When enabled, the sub-layer ratios vary linearly across layers.") |
| `filament_mixed_gradient_range` | Mixed filament gradient range | L("Start and end ratios for the first component in gradient mode. " "Comma-separated pair, e.g. \"0.10,0.90\" means 10% to 90%.") |
| `filament_mixed_gradient_curve` | Mixed filament gradient curve | L("Optional Photoshop-style custom curve mapping Z progress to the first " "component ratio. Encoded as pipe-separated control points, " "either \"x,y\" (legacy) or \"x,y,m_in,m_out\" when a tangent override " "is needed (empty token or \"nan\" means use PCHIP default). " "x in [0,1] |
| `filament_mixed_gradient_per_part` | Mixed filament per-part gradient | L("When gradient mode is enabled, apply the gradient to each part of an " "assembly independently rather than treating the whole assembly as one " "Z range.") |
| `filament_printable` | Filament printable | L("The filament is printable in extruder.") |
| `filament_extruder_compatibility` | Filament-extruder compatibility | L("A single 32-bit int encoding the compatibility level of a filament across all extruders (up to 10). " "Every 3 bits represent one extruder (bits [3*i, 3*i+2] for extruder i). " "0: printable, 1: error, 2: critical warning, 3: warning, 4-7: reserved.") |
| `gcode_add_line_number` | Add line number | L("Enable this to add line number(Nx) at the beginning of each G-code line.") |
| `nozzle_hrc` | Nozzle HRC | L("The nozzle\'s hardness. Zero means no checking for nozzle hardness during slicing.") |
| `printer_structure` | Printer structure | L("The physical arrangement and components of a printing device.") |
| `fan_direction` | Fan direction | L("Cooling fan direction of the printer") |
| `support_air_filtration` | Support air filtration | L("Enable this if the printer supports air filtration G-code command: M106 P3 S(0-255)") |
| `wrapping_detection_layers` | Clumping detection layers | L("Clumping detection layers.") |
| `calib_flowrate_topinfill_special_order` | calib_flowrate_topinfill_special_order |  |
| `machine_min_extruding_rate` | Minimum speed for extruding | L("Minimum speed for extruding (M205 S)") |
| `machine_min_travel_rate` | Minimum travel speed | L("Minimum travel speed (M205 T)") |
| `machine_max_force_Y` | Maximum force of the Y axis | L("The allowed maximum output force of Y axis") |
| `machine_bed_mass_Y` | Bed mass of the Y axis | L("The machine bed mass load of Y axis") |
| `machine_max_printed_mass` | The allowed max printed mass | L("The allowed max printed mass on a plate") |
| `start_end_points` | Start end points | L("The start and end points which are from the cutter area to the excess chute.") |
| `plugins` | Plugins Used | L("Plugin capabilities referenced by this preset, stored as name |
| `enable_long_retraction_when_cut` | enable_long_retraction_when_cut |  |
| `long_retractions_when_cut` | Long retraction when cut (beta) | L("Experimental feature: Retracting and cutting off the filament at a longer distance during changes to minimize purge. " "While this reduces flush significantly, it may also raise the risk of nozzle clogs or other printing problems.") |
| `retraction_distances_when_cut` | Retraction distance when cut | L("Experimental feature: Retraction length before cutting off during filament change.") |
| `default_nozzle_volume_type` | "Default Nozzle Volume Type." | "Default Nozzle volume type for extruders in this printer." |
| `extruder_nozzle_count` | "extruder nozzle count" | "extruder nozzle count" |
| `extruder_nozzle_volume_type` | "Extruder nozzle volume type" | "Nozzle volume type per physical nozzle of an extruder." |
| `enable_filament_dynamic_map` | Enable filament dynamic map | L("Enable dynamic filament mapping during print.") |
| `has_filament_switcher` | Has filament switcher | L("Printer has a filament switcher hardware (e.g., AMS).") |
| `deretract_speed_extruder_change` | Deretraction speed (extruder change) | L("Speed for reloading filament into the nozzle when switching extruder.") |
| `preheat_steps` | Preheat steps | L("Insert multiple preheat commands (e.g. M104.1). Only useful for Prusa XL. For other printers, please set it to 1.") |
| `imex_head_filament_map` | IDEX/IQEX head filament map | L("Per-plate override mapping physical heads to filament slots " "(1-based). Empty means each head uses the first filament that the " "printer's physical extruder map routes to it.") |
| `enforce_support_layers` | enforce_support_layers |  |
| `belt_slice_rotation` | Belt tilt axis | L("Axis the mesh is rotated about before slicing. This is the belt " "printer's tilt: an isometric (no distortion) rotation that also " "drives bed rendering and support gravity tilt, and that the G-code " "back-transform inverts before the machine-frame shear/scale and remap. " "X is the typical gantry tilt (belt travels along Y).") |
| `head_wrap_detect_zone` | "Head wrap detect zone" |  |
| `travel_speed_z` | travel_speed_z |  |
| `prime_volume_mode` | Prime volume mode | L("Selects how the wipe-tower prime and flush volumes are computed on multi-extruder printers.") |
| `wipe_tower_x` | wipe_tower_x |  |
| `wipe_tower_y` | wipe_tower_y |  |
| `belt_purge_tower_object` | Belt purge tower object | L("Marks the auto-generated belt purge prism. Managed automatically |
| `group_algo_with_time` | group_algo_with_time |  |
| `machine_prepare_compensation_time` | machine_prepare_compensation_time |  |
| `handle_hotend_as_extruder` | handle_hotend_as_extruder |  |
| `filament_max_temperature_drop_when_ec` | filament_max_temperature_drop_when_ec |  |
| `filament_retract_length_nc` | length when change hotend | L("When this retraction value is modified, it will be used as the amount of filament retracted " "inside the hotend before changing hotends.") |
| `extruder_max_nozzle_count` | extruder_max_nozzle_count |  |
| `support_fast_purge_mode` | Support fast purge mode | L("Whether this printer supports fast purge mode with optimized temperature and multiplier.") |
| `filament_preheat_temperature_delta` | Preheat temperature delta | L("Temperature delta applied during pre-heating before tool change.") |
