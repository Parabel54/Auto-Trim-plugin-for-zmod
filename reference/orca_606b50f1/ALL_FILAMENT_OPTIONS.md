# ALL FILAMENT OPTIONS

Pinned OrcaSlicer 2.5.0-dev 606b50f1. This is an availability inventory, not your current profile values. No missing value is filled from its definition default. Hidden categories can overlap. Actual visibility depends on printer, enabled features and selected variant.

| Key | Page/group | Mode | Hidden/dependency category | Variant scoped | G-code export |
|---|---|---|---|---|---|
| `activate_air_filtration` | Cooling/Exhaust fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `activate_air_filtration_during_print` | Cooling/Exhaust fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `activate_air_filtration_on_completion` | Cooling/Exhaust fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `activate_chamber_temp_control` | Filament/Print chamber temperature | comSimple | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `adaptive_pressure_advance` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `adaptive_pressure_advance_bridges` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `adaptive_pressure_advance_model` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `adaptive_pressure_advance_overhangs` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `additional_cooling_fan_speed` | Cooling/Auxiliary part cooling fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `additional_fan_full_speed_layer` | Backend only/ | comSimple | not_bound_on_filament_pages | False | if present/non-nil |
| `chamber_minimal_temperature` | Filament/Print chamber temperature | unspecified/default |  | False | if present/non-nil |
| `chamber_temperature` | Filament/Print chamber temperature | unspecified/default |  | False | if present/non-nil |
| `close_additional_fan_first_x_layers` | Backend only/ | comSimple | not_bound_on_filament_pages | False | if present/non-nil |
| `close_fan_the_first_x_layers` | Cooling/Cooling for specific layer | comSimple | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `compatible_printers` | Dependencies/Compatible printers | comAdvanced | advanced_mode | False | banned from config dump |
| `compatible_printers_condition` | Dependencies/Compatible printers | comAdvanced | advanced_mode | False | if present/non-nil |
| `compatible_prints` | Dependencies/Compatible process profiles | comAdvanced | advanced_mode | False | banned from config dump |
| `compatible_prints_condition` | Dependencies/Compatible process profiles | comAdvanced | advanced_mode | False | if present/non-nil |
| `complete_print_exhaust_fan_speed` | Cooling/Exhaust fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `cool_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `cool_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `default_filament_colour` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `dont_slow_down_outer_wall` | Cooling/Part cooling fan | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `during_print_exhaust_fan_speed` | Cooling/Exhaust fan | comSimple | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `enable_overhang_bridge_fan` | Cooling/Part cooling fan | comSimple | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `enable_pressure_advance` | Filament/Flow ratio and Pressure Advance | unspecified/default | conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `eng_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `eng_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `fan_cooling_layer_time` | Cooling/Part cooling fan | comSimple |  | False | if present/non-nil |
| `fan_max_speed` | Cooling/Part cooling fan | comSimple |  | True | if present/non-nil |
| `fan_min_speed` | Cooling/Part cooling fan | comSimple |  | True | if present/non-nil |
| `filament_adaptive_volumetric_speed` | Filament/Volumetric speed limitation | comDevelop | developer, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `filament_adhesiveness_category` | Filament/Basic information | comDevelop | developer | False | if present/non-nil |
| `filament_change_extrusion_role_gcode` | Advanced/Change extrusion role G-code | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_change_length` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_change_length_nc` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_cooling_before_tower` | Backend only/ | comDevelop | developer, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_cooling_final_speed` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_cooling_initial_speed` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_cooling_moves` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_cost` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_density` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_deretraction_speed` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_dev_ams_drying_ams_limitations` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_ams_drying_heat_distortion_temperature` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_ams_drying_temperature` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_ams_drying_time` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_chamber_drying_bed_temperature` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_chamber_drying_time` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_drying_cooling_temperature` | Backend only/ | comSimple | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_dev_drying_softening_temperature` | Backend only/ | unspecified/default | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_diameter` | Filament/Basic information | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_end_gcode` | Advanced/Filament end G-code | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_extruder_compatibility` | Backend only/ | comDevelop | developer, not_bound_on_filament_pages | False | banned from config dump |
| `filament_extruder_variant` | Backend only/ | unspecified/default | not_bound_on_filament_pages | True | if present/non-nil |
| `filament_flow_ratio` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_flush_temp` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_flush_temp_fast` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | False | banned from config dump |
| `filament_flush_volumetric_speed` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_ironing_flow` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_ironing_inset` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_ironing_spacing` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_ironing_speed` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_is_support` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_loading_speed` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_loading_speed_start` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_long_retractions_when_cut` | Setting Overrides/Dynamic override | comDevelop | developer | True | if present/non-nil |
| `filament_max_volumetric_speed` | Filament/Volumetric speed limitation | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_minimal_purge_on_wipe_tower` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `filament_multitool_ramming` | Multimaterial/Tool change parameters with multi extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `filament_multitool_ramming_flow` | Multimaterial/Tool change parameters with multi extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `filament_multitool_ramming_volume` | Multimaterial/Tool change parameters with multi extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `filament_notes` | Notes/Notes | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_plugin_config_overrides` | Advanced/Plugin Configuration | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_pre_cooling_temperature` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_pre_cooling_temperature_nc` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_preheat_temperature_delta` | Backend only/ | comDevelop | developer, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_prime_volume` | Backend only/ | comSimple | not_bound_on_filament_pages | False | if present/non-nil |
| `filament_prime_volume_nc` | Backend only/ | comSimple | not_bound_on_filament_pages | False | if present/non-nil |
| `filament_printable` | Backend only/ | comDevelop | developer, not_bound_on_filament_pages | False | if present/non-nil |
| `filament_ramming_parameters` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_ramming_travel_time` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_ramming_travel_time_nc` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_ramming_volumetric_speed` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_ramming_volumetric_speed_nc` | Backend only/ | comAdvanced | advanced_mode, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_retract_after_wipe` | Setting Overrides/Dynamic override | comExpert | expert_mode | True | if present/non-nil |
| `filament_retract_before_wipe` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_length_nc` | Backend only/ | comDevelop | developer, not_bound_on_filament_pages | True | if present/non-nil |
| `filament_retract_length_toolchange` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_lift_above` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_lift_below` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_lift_enforce` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_restart_extra` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_restart_extra_toolchange` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retract_when_changing_layer` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retraction_distances_when_cut` | Setting Overrides/Dynamic override | comDevelop | developer | True | if present/non-nil |
| `filament_retraction_length` | Setting Overrides/Dynamic override | comSimple |  | True | if present/non-nil |
| `filament_retraction_minimum_travel` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_retraction_speed` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_shrink` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_shrinkage_compensation_z` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_soluble` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_stamping_distance` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_stamping_loading_speed` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_start_gcode` | Advanced/Filament start G-code | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_toolchange_delay` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_tower_interface_pre_extrusion_dist` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_tower_interface_pre_extrusion_length` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_tower_interface_print_temp` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_tower_interface_purge_volume` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_tower_ironing_area` | Multimaterial/Wipe tower parameters | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_type` | Filament/Basic information | comSimple |  | False | if present/non-nil |
| `filament_unloading_speed` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_unloading_speed_start` | Multimaterial/Tool change parameters with single extruder MM printers | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `filament_vendor` | Filament/Basic information | comAdvanced | advanced_mode | False | if present/non-nil |
| `filament_wipe` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_wipe_distance` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `filament_z_hop` | Setting Overrides/Dynamic override | comSimple |  | True | if present/non-nil |
| `filament_z_hop_types` | Setting Overrides/Dynamic override | comAdvanced | advanced_mode | True | if present/non-nil |
| `first_x_layer_fan_speed` | Backend only/ | comSimple | not_bound_on_filament_pages | False | if present/non-nil |
| `full_fan_speed_layer` | Cooling/Cooling for specific layer | comAdvanced | advanced_mode | False | if present/non-nil |
| `hot_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `hot_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `idle_temperature` | Filament/Basic information | unspecified/default |  | False | if present/non-nil |
| `inherits` | Backend only/ | unspecified/default | not_bound_on_filament_pages | False | if present/non-nil |
| `initial_layer_fan_speed` | Cooling/Cooling for specific layer | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `internal_bridge_fan_speed` | Cooling/Part cooling fan | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `ironing_fan_speed` | Cooling/Part cooling fan | comAdvanced | advanced_mode | False | if present/non-nil |
| `long_retractions_when_ec` | Multimaterial/Multi Filament | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `nozzle_temperature` | Filament/Print temperature | unspecified/default |  | True | if present/non-nil |
| `nozzle_temperature_initial_layer` | Filament/Print temperature | unspecified/default |  | True | if present/non-nil |
| `nozzle_temperature_range_high` | Filament/Basic information | unspecified/default |  | True | if present/non-nil |
| `nozzle_temperature_range_low` | Filament/Basic information | unspecified/default |  | True | if present/non-nil |
| `overhang_fan_speed` | Cooling/Part cooling fan | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `overhang_fan_threshold` | Cooling/Part cooling fan | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `pellet_flow_coefficient` | Filament/Flow ratio and Pressure Advance | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `pressure_advance` | Filament/Flow ratio and Pressure Advance | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `reduce_fan_stop_start_freq` | Cooling/Part cooling fan | unspecified/default |  | False | if present/non-nil |
| `required_nozzle_HRC` | Filament/Basic information | comDevelop | developer | False | if present/non-nil |
| `retraction_distances_when_ec` | Multimaterial/Multi Filament | comAdvanced | advanced_mode, conditional_or_disabled_by_dependencies | True | if present/non-nil |
| `slow_down_for_layer_cooling` | Cooling/Part cooling fan | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `slow_down_layer_time` | Cooling/Part cooling fan | comSimple |  | False | if present/non-nil |
| `slow_down_min_speed` | Cooling/Part cooling fan | comAdvanced | advanced_mode | False | if present/non-nil |
| `supertack_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `supertack_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `support_material_interface_fan_speed` | Cooling/Part cooling fan | comAdvanced | advanced_mode | False | if present/non-nil |
| `temperature_vitrification` | Filament/Basic information | comSimple |  | False | if present/non-nil |
| `textured_cool_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `textured_cool_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `textured_plate_temp` | Filament/Bed temperature | unspecified/default |  | False | if present/non-nil |
| `textured_plate_temp_initial_layer` | Filament/Bed temperature | unspecified/default | conditional_or_disabled_by_dependencies | False | if present/non-nil |
| `volumetric_speed_coefficients` | Backend only/ | unspecified/default | not_bound_on_filament_pages, conditional_or_disabled_by_dependencies | True | if present/non-nil |
