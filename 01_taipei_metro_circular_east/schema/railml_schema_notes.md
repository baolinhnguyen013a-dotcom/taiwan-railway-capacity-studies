# railML 3.2 Implementation & Topology Notes

## 1. Specification Compatibility
The infrastructure model in `01_alignment_topology/railml_infrastructure_east_section.xml` and the rolling stock model in `03_rolling_stock_signalling/railml_rollingstock_hitachi_emu.xml` are built against the **railML 3.2** standard schema (https://www.railml.org/schemas/3.2).

## 2. Key Modeling Objects
1. `<infrastructure>`:
   - `<netElements>`: Represents tracks as directed linear topology elements (`ne_trk_up_01`, `ne_trk_dn_01`, and `ne_trk_s1_single`).
   - `<netRelations>`: Represents switches and crossovers connecting the upbound and downbound tracks.
   - `<tracks>`: Defines functional tracks with designators corresponding to DORTS track codes.
   - `<operationalPoints>`: Encapsulates all 12 passenger stations with exact linear positions (pos in meters).
2. `<rollingstock>`:
   - `<vehicle>`: Declares the Hitachi Rail Italy 4-car medium-capacity EMU consist, including 16-axle propulsion, maximum tractive effort (164.8 kN), service/emergency braking deceleration, and passenger seating/standing capacities.

## 3. Micro-Simulation Interoperability
These railML XML files can be imported directly into rail network simulation software (OpenTrack, railSys, Viriato) to run synchronous dispatching simulations and verify headway feasibility under single-track constraints.
