# IFC4.3 Rail & Tunnel Entity Mapping Guide

## 1. Overview
The civil design entities are structured according to **buildingSMART IFC4.3 (IFC4X3_ADD2)**, supporting full BIM interoperability and digital twin integration.

## 2. Spatial Entity Mapping (`ifc_civil_identifiers_mapping.json`)
- `IfcProject`: Top-level project container (`Taipei_Metro_Circular_Line_East_Section`).
- `IfcSite`: Regional geographic location in Taipei (`Taipei_Metropolitan_Area_East_Corridor`).
- `IfcRailway`: Rail domain facility comprising running tracks, tunnels, and stations.
- `IfcTunnel`: Shield tunnel linear bores, segmented by contract package:
  - `IfcTunnelSegment`: Individual shield tunnel drives (e.g. `TUN_CF710_01`, `TUN_CF763_S1`).
  - `IfcCrossPassage`: Emergency cross-passages connecting twin bores (`IFC_CP01` through `IFC_CP06`).
- `IfcStation`: Underground station boxes (`STA_Y29` through `STA_Y01`) containing platforms, concourses, and egress stairwells.

## 3. PropertySets (Pset)
- `Pset_TunnelCommon`: Encapsulates outer diameter, lining thickness, concrete strength (C50/60), and groundwater design pressure.
- `Pset_TrackCommon`: Encapsulates gauge (1435mm), rail section (UIC 60), fastener type, and conductor rail voltage (750V DC).
- `Pset_StationCommon`: Encapsulates platform configuration, box depth, diaphragm wall thickness, and NFPA 130 egress compliance ratings.
