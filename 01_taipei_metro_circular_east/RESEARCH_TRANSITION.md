# Strategic Research Transition: From Urban Metro Counterfactuals to Regional Rail Joint Optimization

**Document Classification:** Strategic Research Pivot & Route Selection Proposal  
**Originating Study:** Taipei Circular Line East Section Counterfactual Optimization (Phases 01–10)  
**Target Domain:** Taiwanese Regional Railway Network Optimization & Dynamic Dispatch  
**Selected Target Route:** TRA Western Trunk Coastal Line Double-Tracking Project (臺鐵海線 談文至追分段)  
**Date:** 2026-10-06  

---

## 1. Executive Context: Why We Pivot After Thorough Metro Investigation

Over Phases 01 through 10, our investigation conducted a fail-closed, multi-domain evaluation of bidirectional single-track tunnels on the **Taipei Metro Circular Line East Section (環狀線東環段 Y29–Y01)**. That study established definitive, mathematically provable boundaries explaining why flexible single-tracking fails in deep urban metro environments:

1. **The Inviolable Headway vs. Block Clearance Physics**:
   - Urban metro lines require **120s to 150s peak headways** to convey 10,000–15,250 passengers per hour per direction (pphpd).
   - A single-track segment requires an alternating block clearance cycle:
     $$\text{Cycle} = t_{cw} + t_{ccw} + 2 \times t_{\text{switch/clearance}} + t_{\text{buffer}}$$
     Over typical 1.5–3.2 km station gaps, this cycle spans **340s to 666s (5.5 to 11.1 minutes)**.
   - Result: Maximum throughput collapses to 3,500–6,800 pphpd ($V/C = 1.83$ to $3.41$), creating catastrophic station overcrowding.

2. **The Underground Civil Economics Paradox**:
   - Drilling continuous, uniform 6.1m circular tubes with a Tunnel Boring Machine (TBM) is highly industrialized and predictable.
   - Transitioning between 1-track and 2-track underground requires stopping TBM drives and mining **12m–15m wide horseshoe turnout caverns** via sequential excavation (NATM) deep in water-bearing fault zones.
   - Each underground crossover cavern costs **NT$ 1.5 to 3.0 billion**, completely consuming the civil excavation savings of omitting the second shield bore.

3. **The Mandatory Evacuation Trap (NFPA 130)**:
   - In twin-bore tunnels, emergency egress is provided by simple cross-passages every 300m into the pressurized companion tube.
   - A single-bore metro tunnel mandates boring a separate parallel pressurized rescue gallery or service duct, which negates the civil savings.

4. **Network Topology & Fragility**:
   - Because the Circular Line is a closed topological ring, any 45-second delay at a single-track meet instantly propagates bidirectionally around the entire 39 km loop.

---

## 2. The Natural Engineering Domain: Surface Regional Corridors

The physics and economics invert entirely when moving from **deep underground metros** to **surface regional railways**:

| Engineering Dimension | Deep Underground Metro (Taipei East Section) | Surface Regional Rail (Target Domain) |
| :--- | :--- | :--- |
| **Service Headway** | Rigid 2.0–2.5 min ($150\text{s}$) | Clockface 15–30 min (Express 30m, Local 15m) |
| **Turnout / Switch Cost** | NT$ 1.5–3.0B per mined underground cavern | Standard surface turnouts on ballasted track |
| **Emergency Safety** | NFPA 130 mandates parallel rescue tunnel | Trackside walkway evacuation to open right-of-way |
| **Meeting Mechanics** | Long stop-and-wait cycles | **Dynamic "Flying Meets"** (trains pass at 100 km/h without stopping) |
| **Long Bridge Crossings** | N/A (bored tunnels) | **35–45% superstructure/pier savings** by single-tracking major river bridges |
| **Delay Absorption** | Fragile closed-ring cascade | Robust schedule recovery buffers between clockface slots |

---

## 3. Route Selection: TRA Coastal Line Double-Tracking Project (臺鐵海線 談文至追分)

To anchor the joint infrastructure-timetable optimization and Reinforcement Learning (RL) dispatching methodology in an authoritative, numerically tractable environment, we select the **TRA Western Trunk Coastal Line Double-Tracking Project (談文至追分段)**.

### A. Official Planning Status & Real-World Decision Context
* **Project Name:** 臺鐵海線雙軌化（談文至追分）計畫
* **Jurisdiction:** Ministry of Transportation and Communications (MOTC), Railway Bureau (交通部鐵道局)
* **Status:** **Feasibility Study approved by Executive Yuan on 2024-01-29**; currently undergoing **Comprehensive Planning (綜合規劃作業中)**.
* **Corridor Extent:** From Tanwen Station (苗栗談文, K137+600) to Zhuifen Station (臺中追分, K186+500), corridor length $\approx 38.3\text{ km}$.
* **Active Policy Dilemma:**
  - **Full Elevation / Full Dual-Tracking Proposal (台中市山海環線):** Completely elevates and double-tracks the line, costing over **NT$ 80+ billion**.
  - **Targeted Bottleneck Dual-Tracking (鐵道局核定方案):** Retains surface alignment and upgrades existing single-track bottlenecks, estimated at **NT$ 16.195 billion**.
  - **The Research Opportunity:** Can an optimized combination of **flying-meet dynamic passing loops**, **single-track river bridge crossings with dual-track approaches**, and **RL-assisted speed regulation** deliver 95% of full double-track capacity for a fraction of the capital budget?

### B. The 5 Bottleneck Single-Track Sub-Segments
The 38.3 km corridor contains **5 distinct single-track bottleneck segments totaling 35.37 km**, separated by existing double-track stations/segments:

```
[Zhunan] ── (Double) ── [Tanwen] 
                          │ 
                          ├── 1. Tanwen – Dashan (談文–大山): ~5.4 km (Single, Zhonggang River Bridge)
                          │ 
                        [Dashan] ── (Passing Station) ── [Houlong] 
                          │ 
                          ├── 2. Baishatun – Xinpu (白沙屯–新埔): ~3.1 km (Single, Coastal Bluffs)
                          │ 
                        [Xinpu] ── (Passing Station) ── [Tongxiao] 
                          │ 
                          ├── 3. Tongxiao – Yuanli (通霄–苑裡): ~7.0 km (Single)
                          │ 
                        [Yuanli] ── (Passing Station) ── [Rinan] 
                          │ 
                          ├── 4. Rinan – Dajia (日南–大甲): ~4.6 km (Single, Daan River Bridge)
                          │ 
                        [Dajia] ── (Major Hub) ── [Taichung Port / Qingshui] 
                          │ 
                          ├── 5. Qingshui – Zhuifen (清水–沙鹿–龍井–大肚–追分): ~15.3 km (Single, Dajia River Bridge)
                          │ 
                        [Zhuifen] ── (Double Junction to Changhua & Taichung)
```

### C. Signature River Bridge Bottlenecks
The line traverses four major Class-A river crossings where bridge replacement costs dominate project CAPEX:
1. **Zhonggang River Bridge (中港溪橋)**: ~450 m
2. **Houlong River Bridge (後龍溪橋)**: ~700 m
3. **Daan River Bridge (大安溪橋)**: ~1,100 m
4. **Dajia River Bridge (大甲溪橋)**: ~1,250 m

Replacing a 1.2 km river bridge with a full 2-track structure requires massive foundation caissons and wide superstructures designed for dual freight loading ($2 \times \text{UIC 71}$). Evaluating **single-track bridge superstructures with high-speed double-track approaches at abutments** represents a classic civil-structural cost optimization.

---

## 4. Mathematical Formulation for the Numerical Study

We formulate a two-layer hierarchical optimization framework:

### Layer 1: Strategic Infrastructure Siting & Sizing (MILP)
* **Binary Decision Variables ($x_i \in \{0, 1\}$)**:
  - $x_{seg, i}^{\text{double}}$: Dual-track entire segment $i$ vs retain single-track with passing loop.
  - $x_{brg, j}^{\text{single}}$: Retain single-track bridge with double-track approach loops vs rebuild full 2-track bridge.
  - $L_{k}^{\text{loop}}$: Length and chainage coordinates of dynamic flying-meet loops ($2.0\text{ km} \le L_k \le 3.5\text{ km}$).
* **Objective Function**:
  $$\min \quad \text{CAPEX}(x) + \text{OPEX}_{30\text{yr}}(x) + \alpha \sum \text{PassengerDelay}(t) + \beta \sum \text{FreightTransitTime}(t)$$
* **Hard Constraints**:
  - Maintain Clockface Timetable: Express (EMU3000) every 30 min, Local Commuter (EMU900) every 15 min.
  - Flying Meet Feasibility: Opposing trains in nominal schedule must clear passing loops with zero scheduled dwell ($v \ge 100\text{ km/h}$).

### Layer 2: Operational Disruption Management & Speed Profiling (Reinforcement Learning)
* **Agent Role**: Dynamic Real-Time Dispatcher & Speed Advisory Controller.
* **Environment**: Microscopic / mesoscopic simulation of the 38.3 km Coastal corridor under stochastic primary delays (e.g. dwell stretch, signal check, grade-crossing incident).
* **State Space ($S_t$)**: Current position, velocity, schedule deviation, and signal aspect for all active trains; switch occupancy states at bridge abutments and loop bifurcations.
* **Action Space ($A_t$)**:
  - Dynamic speed profile commands ($v_{\text{target}} \in [60, 130]\text{ km/h}$) for green-wave arrival at passing loops.
  - Real-time meet rescheduling: swap meet location to upstream/downstream loop if inbound train delay $> \Delta t_{\text{threshold}}$.
  - Platooning order: Group 2 consecutive Northbound trains across single-track bridges before releasing Southbound slot.
* **Reward Function ($R_t$)**:
  $$R_t = - w_1 \cdot \text{SecondaryDelay} - w_2 \cdot \text{TractionEnergy} - w_3 \cdot \mathbf{1}_{\{\text{Unscheduled Stop at Loop}\}}$$

---

## 5. Next Operational Steps

1. **Open Data Ingestion**:
   - Ingest Ministry of Transportation and Communications (MOTC) **TDX Open Data API** for TRA Coastal Line GTFS timetables, station coordinates, and scheduled running times.
   - Extract track chainages, turnout locations, and speed limits from Railway Bureau public environmental impact assessments (EIA) and feasibility study disclosures.
2. **Benchmark Corridor Simulation**:
   - Model the 5 single-track bottleneck segments and 4 signature river bridges.
   - Baseline the current 2026 timetable and measure current meet-wait delay penalties.
3. **Pareto Frontier Exploration**:
   - Compute the trade-off curve: **Capital Expenditure (NT$ Billions)** vs. **Timetable Headway (Minutes)** vs. **Delay Recovery Resilience (Minutes)**.
