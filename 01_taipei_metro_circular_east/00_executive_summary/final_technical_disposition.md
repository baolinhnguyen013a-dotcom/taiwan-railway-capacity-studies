# Final Executive Summary & Technical Disposition: Counterfactual Infrastructure Evaluation

**Taipei Metro Circular Line East Section (環狀線東環段 Y29–Y01)**  
*Project Data Maturity State:* `READY_FOR_PRELIMINARY_SCREENING_ONLY`  
*Governance Classification:* Closed Counterfactual Engineering Evaluation  
*Date:* 2026-10-06  

---

## 1. Executive Summary & Research Motivation

This investigation conducted a rigorous counterfactual engineering evaluation to assess whether selective segments of the **Taipei Metro Circular Line East Section** could be constructed as **single-track bidirectional tunnels** to reduce capital expenditure while maintaining operational feasibility.

The study established a fail-closed, multi-stage analytical framework across 10 data and analytical domains, maintaining strict preservation of the 36 foundational source files and retaining 10 explicit governance blockers against premature formal optimization or reinforcement learning (RL) dispatch training.

Through deterministic preliminary capacity screening (Phase 09) and multi-criteria synthesis (Phase 10), the hypothesis that single-track infrastructure could deliver net lifecycle benefits was subjected to empirical testing against authoritative Taipei Department of Rapid Transit Systems (DORTS) Comprehensive Plan demand benchmarks.

---

## 2. Definitive Technical Findings

### A. Physical Capacity Bottlenecks (Phase 09 Results)
Under deterministic peak AM demand (07:00–09:00), single-track sections without intermediate passing loops require unconstrained block clearance cycles ($t_{cw} + t_{ccw} + 2 \times \text{change} + \text{recovery}$) that severely restrict throughput:

1. **`ALT-S1` / `Y39–Y01` (Mountain Tunnel Bore, 3.24 km)**:
   - Operating cycle: **482.0 seconds** (8.03 min headway).
   - Maximum directional capacity: **4,855 pphpd** (at 650 pax/train nominal load).
   - Official peak demand: **10,310 pphpd** (Southbound/CCW toward Zoo).
   - Volume-to-Capacity ratio: **$V/C = 2.12$** $\rightarrow$ **`FAIL_CAPACITY`**.
2. **`ALT-S2` / `Y35–Y36` (Keelung River Undercrossing, 1.69 km)**:
   - Operating cycle: **342.6 seconds** (5.71 min headway).
   - Maximum directional capacity: **6,830 pphpd**.
   - Official peak demand: **15,250 pphpd** (Corridor peak load LK07 CCW).
   - Volume-to-Capacity ratio: **$V/C = 2.23$** $\rightarrow$ **`FAIL_CAPACITY`**.
3. **`ALT-S3` / `Y30–Y33` (Ruiguang Road Core Spine, 2.40 km)**:
   - Operating cycle: **597.2 seconds** (9.95 min headway across 2 intermediate stations).
   - Maximum directional capacity: **3,918 pphpd**.
   - Official peak demand: **7,170 pphpd**.
   - Volume-to-Capacity ratio: **$V/C = 1.83$** $\rightarrow$ **`FAIL_CAPACITY`**.
4. **`ALT-S4` / `Y38–Y01` (Southern Extended Tail, 4.24 km)**:
   - Operating cycle: **666.0 seconds** (11.10 min headway).
   - Maximum directional capacity: **3,512 pphpd**.
   - Official peak demand: **11,980 pphpd**.
   - Volume-to-Capacity ratio: **$V/C = 3.41$** $\rightarrow$ **`FAIL_CAPACITY`**.

Out of all 66 possible contiguous single-track sections evaluated in the corridor, **61 failed capacity** under baseline S00 demand. The 5 sections that nominally passed were exclusively single, short peripheral links carrying minimal suburban loads.

### B. Multi-Criteria Synthesis & Override of Economic Claims (Phase 10 Results)
In Phase 10, the empirical capacity failures were formally joined with the unverified economic claims in `06_lifecycle_costs`:
- **Override of `ALT-S1` ("Optimal Alternative")**: The initial claim of NT$ 5.83B lifecycle savings was formally **rejected and overridden**. Single-track infrastructure cannot carry the 10,310 pphpd peak flow without catastrophic passenger queuing.
- **Override of `ALT-S4` ("Strong Contender")**: The initial claim of NT$ 6.60B savings was formally **rejected and overridden**. Extended single tracking chokes southern corridor capacity ($V/C = 3.41$) and relies on unmodeled passing loops.
- **Reconfirmation of `ALT-S2` and `ALT-S3`**: Confirmed as **`REJECTED_CAPACITY_FAILURE`**, reinforcing their severe operational inadmissibility.
- **Sole Feasible Configuration (`BL-Double`)**: The approved continuous double-track alignment achieves **$V/C = 0.98$** at the 150s design headway, making it the **only viable infrastructure alternative** (`APPROVED_BASELINE_FEASIBLE`).

---

## 3. Governance, Integrity, and Verification State

All project invariants remain strictly certified:
* **Preservation**: Exactly 36 source data files across domains `01` through `07` remain byte-identical against their certified SHA-256 digests (`CURRENT_WORKSPACE_SNAPSHOT_MATCHED`).
* **Fail-Closed Readiness**: The repository retains all 10 blocking findings (`F-001`, `F-002`, `F-006`, `F-007`, `F-008`, `F-009`, `F-010`, `F-011`, `F-013`, `F-014`). Formal optimization, RL dispatch training, and safety certification remain disclaimed as unviable on the candidate single-track geometries.
* **Test Verification**: 
  - `python3 -m unittest discover -s tests -v`: **43/43 tests pass**.
  - `python3 scripts/verify_pipeline_integrity.py`: **48/48 structural checks pass**.
  - `python3 scripts/verify_source_snapshot.py`: **36/36 source digests pass**.
  - `python3 scripts/verify_multi_criteria_synthesis.py`: **63/63 checks pass**.

---

## 4. Final Engineering Conclusion

While single-track sections and timed meets have succeeded in moderate-frequency regional railways (such as Switzerland's Lötschberg Base Tunnel or Bellarena in Northern Ireland), **single-track bidirectional tunnels are physically and operationally incompatible with high-density urban metro corridors** operating automated 2–3 minute headways and carrying >10,000 pphpd.

The approved DORTS design—continuous twin-bore tunnels with full degraded-mode crossover redundancy—is affirmed as the only operationally sound, safe, and capacity-feasible engineering solution for the Taipei Circular Line East Section.

---

## 5. Next Research Phase: Transition to Regional Rail Optimization

Following these definitive negative boundary findings on urban metros, the project methodology transitions to its natural, high-impact application domain: **surface regional railways and long river bridge bottlenecks**.

See full strategic transition proposal: [RESEARCH_TRANSITION.md](../RESEARCH_TRANSITION.md), which selects the **TRA Western Trunk Coastal Line Double-Tracking Project (臺鐵海線 談文至追分段, 38.3 km)** as the target numerical case study.
