# Data Dictionary & Schema Specification

## 1. Overview
All data files in this repository use standardized UTF-8 CSV, GeoJSON (RFC 7946), XML (railML 3.2), or JSON formats. All numerical measurements adhere strictly to SI metric units.

---

## 2. Table Schemas & Column Definitions

### 2.1 Alignment Stations (`01_alignment_topology/alignment_stations.csv`)
- `station_id` (String): Unique identifier (`ST01` to `ST12`).
- `station_code` (String): Official DORTS planned station code (`Y29` to `Y39`, `Y01`).
- `station_name_zh` (String): Traditional Chinese station name.
- `station_name_en` (String): English official station name.
- `chainage_km` (Float): Centerline route chainage from Y29 origin (km).
- `interstation_dist_m` (Integer): Centerline distance to previous station (m).
- `easting_twd97` (Float): Easting in TWD97 / TM2 coordinate system (EPSG:3826) (m).
- `northing_twd97` (Float): Northing in TWD97 / TM2 coordinate system (EPSG:3826) (m).
- `longitude_wgs84` (Float): Geographic longitude in WGS84 (EPSG:4326) (decimal degrees).
- `latitude_wgs84` (Float): Geographic latitude in WGS84 (EPSG:4326) (decimal degrees).
- `platform_type` (String): Platform architectural configuration (`Island`, `Stacked Side`, `Stacked Island`).
- `platform_length_m` (Float): Usable platform length (m) (standard: 80.0 m for 68.4m 4-car EMU).
- `platform_width_m` (Float): Usable platform width (m).
- `track_level_depth_m` (Float): Depth of top-of-rail relative to finished street grade (m).
- `ground_elevation_m` (Float): Ground surface elevation above mean sea level (TWVD2001 datum) (m).
- `track_elevation_m` (Float): Top of rail elevation above mean sea level (m).
- `contract_package` (String): Civil construction procurement package (`CF710`, `CF720`, `CF750`, `CF760`, `CF763`).
- `transfer_lines` (String): Intersecting rapid transit, mainline rail, or high-speed rail lines.

### 2.2 Horizontal Curves (`01_alignment_topology/alignment_horizontal_curves.csv`)
- `curve_id` (String): Unique curve identifier (`C01` to `C10`).
- `start_chainage_km`, `end_chainage_km` (Float): Curve boundary chainages (km).
- `length_m` (Integer): Total length of circular arc plus transition spirals (m).
- `curve_radius_m` (Integer): Radius of curvature (m).
- `cant_superelevation_mm` (Integer): Applied track cross-level superelevation (mm).
- `spiral_transition_length_m` (Integer): Clothoid spiral transition length (m).
- `deflection_angle_deg` (Float): Total deflection angle of curve (degrees).
- `max_speed_kmh` (Integer): Governed curve speed restriction under CBTC ATO (km/h).

### 2.3 Vertical Gradients (`01_alignment_topology/alignment_vertical_gradients.csv`)
- `gradient_id` (String): Unique gradient segment identifier (`G01` to `G25`).
- `start_chainage_km`, `end_chainage_km` (Float): Gradient boundary chainages (km).
- `length_m` (Integer): Length of constant gradient section (m).
- `grade_permille` (Float): Longitudinal slope in permille (‰). Positive = climb; negative = descent.
- `start_elevation_m`, `end_elevation_m` (Float): Top of rail elevations at section boundaries (m MSL).
- `vertical_curve_radius_m` (Integer): Radius of parabolic/circular vertical curve at crest/sag (m).

### 2.4 Lifecycle Costs (`06_lifecycle_costs/lifecycle_cost_comparison_30yr.csv`)
- `alternative_id` (String): Code of infrastructure alternative (`BL-Double`, `ALT-S1`, `ALT-S2`, `ALT-S3`, `ALT-S4`).
- `initial_capex_twd_billion` (Float): Total upfront capital expenditure (NT$ Billions).
- `annual_opex_yr1_twd_billion` (Float): Annual operating and routine maintenance expenditure (NT$ Billions).
- `periodic_renewal_yr15_twd_billion` (Float): Mid-life overhaul and component replacement expenditure at Year 15.
- `salvage_value_yr30_twd_billion` (Float): Residual asset value at end of 30-year lifecycle horizon.
- `npv_30yr_3_5pct_twd_billion` (Float): Net Present Value of infrastructure lifecycle costs discounted at 3.5% per annum.
- `passenger_delay_penalty_npv_twd_billion` (Float): Economic cost of additional passenger waiting and travel delay monetized at VOT = NT$ 240/hour.
- `total_economic_cost_twd_billion` (Float): Comprehensive economic cost = NPV Lifecycle Cost + Passenger Delay Penalty.
- `cost_savings_vs_baseline_pct` (Float): Percentage economic cost saving relative to approved double-track baseline (+ = saving; - = net loss).
