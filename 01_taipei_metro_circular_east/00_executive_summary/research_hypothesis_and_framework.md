# Executive Research Framework: Counterfactual Single-Track Optimization

> **Audit qualification:** All findings below are hypotheses generated from a
> mixed-evidence preliminary dataset. Values labelled as savings, compliance,
> feasibility, or optimality are not validated conclusions. Use
> `../08_quality_control/validation_findings.csv` and
> `../08_analysis_ready/` for the current screened status.

## 1. Context and Problem Statement
The approved comprehensive plan describes a 13.25 km underground East Section
with ten new underground stations and an approved construction cost of
NT$102.486 billion. The collected 14.732 km model chainage has not been
reconciled to that official scope and must not be interpreted as an added
boundary-crossover allowance without documentary evidence.

This counterfactual research exercise evaluates whether targeted sections could be constructed with **one bidirectional track** while preserving:
1. Peak passenger carrying capacity;
2. All applicable project-authority and Taiwan life-safety requirements;
3. System reliability and delay recovery resilience;
4. Future growth headroom through the 2051 target design year (民國140年).

---

## 2. Current Screening Findings

### (A) Y39 ↔ Y01 / CF763: Rejected Under the Strict Alternating Screen (Alternative S1)
- **Geometry status**: The approved station interval is 3.24 km. The CF763
  page reports 3,132 m and 3,148 m for the two shield tunnels; the collected
  3,157 m counterfactual length is therefore retained only as an assumption.
- **Cost status**: The collected NT$5.85 billion initial saving is unverified
  and is not an accepted result.
- **Official demand correction**: The approved comprehensive plan reports **10,310 passengers/hour/direction** through Y39-Y01, not the collected 3,210-4,010 pphpd values. It reports 15,250 pphpd on the maximum-load Y36-Y35 link.
- **Service screening correction**: The approved plan gives a 3.24 km interval and 60.46 km/h average speed, implying approximately 193 seconds of one-way occupation before route-change allowances. A conflict-free 540-second directional cycle provides only about 4,333 nominal pphpd with 650-passenger trains. It therefore fails the official Y39-Y01 demand under the one-train-at-a-time alternating assumption.
- **Economic status**: The reported NT$5.83 billion saving is rejected as a current conclusion because the alternative fails the capacity screen. Independently, its lifecycle NPV does not reconcile to the stated inputs, and the collected 3.5% discount rate differs from the approved plan's 4% economic and 3% financial rates.
- **Life-safety condition**: Because a single-bore tunnel lacks an adjacent companion tunnel for cross-passage evacuation, S1 would require a project-authority-approved evacuation and smoke-control solution. The proposed parallel 3.0 m escape gallery is a research assumption, not a demonstrated compliance solution.

### (B) Y35 ↔ Y36: Preliminary Capacity Rejection (Alternative S2)
- **Geometry**: The official station chainages give a 1,685 m interval. The
  collected elevation and civil details remain unverified.
- **Demand**: The approved plan reports the line's target-year maximum flow as
  15,250 pphpd from Y36 to Y35; the collected 15,640 pphpd value is not used.
- **Result**: The collected strict-alternating capacity assumption of 6,500
  pphpd is below official demand, so S2 fails the nominal capacity screen. The
  reported NT$28.4 billion delay penalty is not accepted until demand,
  assignment and valuation inputs are traceable.

### (C) Y30 ↔ Y33: Not Yet Assessable (Alternative S3)
- The collected street width, demand range, construction effect and economic
  penalty lack traceable evidence. The collected assertion that Y31 is stacked
  also conflicts with the approved plan, which describes nine island stations
  and Y39 as the sole stacked station. S3 therefore remains a research concept,
  not a feasible alternative, until geometry and demand are rebuilt.

---

## 3. Mathematical Optimization Formulation Outline
The downstream co-optimization model solves:

$$\min_{\mathbf{x}_{infra}, \mathbf{t}_{sched}} \quad \text{CAPEX}(\mathbf{x}_{infra}) + \text{OPEX}_{NPV}(\mathbf{x}_{infra}, \mathbf{t}_{sched}) + \beta \cdot \text{Delay}_{user}(\mathbf{x}_{infra}, \mathbf{t}_{sched}) + \gamma \cdot \text{Risk}_{unreliability}$$

Subject to:
1. **Headway & Capacity**: $\text{Cap}(\mathbf{t}_{sched}) \ge D_{link}(t), \quad \forall t, \forall link$
2. **Single-Track Safety Interval**: $\Delta t_{clear} \ge t_{run}(i,j) + t_{dwell} + t_{margin} + t_{switch}$
3. **Life safety**: every configuration must satisfy authority-confirmed,
   project-specific fire, smoke-control, evacuation and rescue requirements;
   the collected NFPA timing table is a proxy rather than proof of compliance.
4. **Maintenance Feasibility**: Continuous 4.5-hour possession window without revenue disruption.
