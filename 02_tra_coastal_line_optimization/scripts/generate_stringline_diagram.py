#!/usr/bin/env python3
"""
TRA Coastal Line (Tanwen - Zhuifen) 24-Hour Time-Space Stringline Diagram
(臺鐵海線 24小時列車運行圖 / Marey Chart)

Visualizes 19 hours of clockface train operations (05:00 - 24:00) across all 16 stations (K4.5 - K83.1).
Highlights the single-track river bridge bottleneck zones:
- Daan River Bridge (大安溪橋): K51.2 - K52.3
- Dajia River Bridge (大甲溪橋): K61.8 - K63.0

Demonstrates that under Lever 1 single-track bridge slots, all Express (red),
Commuter (blue), and Freight (green) trains operate 100% conflict-free without intersecting
inside the bridge bottleneck zones.
"""

import os
import sys
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import plotly.graph_objects as go

# Configure CJK typography support for macOS
plt.rcParams['font.sans-serif'] = ['PingFang TC', 'PingFang SC', 'Heiti TC', 'STHeiti', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, "outputs")
ROOT_OUTPUTS_DIR = os.path.join(PROJECT_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(ROOT_OUTPUTS_DIR, exist_ok=True)

# Station definitions
STATIONS = [
    ("STA01", "談文 Tanwen", 4.5),
    ("STA02", "大山 Dashan", 11.3),
    ("STA03", "後龍 Houlong", 15.0),
    ("STA04", "龍港 Longgang", 18.6),
    ("STA05", "白沙屯 Baishatun", 26.7),
    ("STA06", "新埔 Xinpu", 29.8),
    ("STA07", "通霄 Tongxiao", 35.6),
    ("STA08", "苑裡 Yuanli", 41.7),
    ("STA09", "日南 Rinan", 49.4),
    ("STA10", "大甲 Dajia", 54.1),
    ("STA11", "臺中港 Taichung Port", 59.3),
    ("STA12", "清水 Qingshui", 65.3),
    ("STA13", "沙鹿 Shalu", 68.5),
    ("STA14", "龍井 Longjing", 73.1),
    ("STA15", "大肚 Dadu", 78.1),
    ("STA16", "追分 Zhuifen", 83.1),
]

BOTTLENECKS = [
    {
        "id": "BRG03",
        "name_zh": "大安溪橋",
        "name_en": "Daan River Bridge",
        "k_start": 51.2,
        "k_end": 52.3,
        "length_m": 1100.0,
    },
    {
        "id": "BRG04",
        "name_zh": "大甲溪橋",
        "name_en": "Dajia River Bridge",
        "k_start": 61.8,
        "k_end": 63.0,
        "length_m": 1250.0,
    },
]

def load_segment_runtimes():
    csv_path = os.path.join(PROJECT_DIR, "03_timetable_baseline", "tra_nominal_runtimes.csv")
    segments = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            segments.append(row)
    return segments

def build_corridor_trajectories(segments):
    """
    Builds 24-hour deterministic train trajectories (05:00 to 24:00) using
    rigorously validated clockface headway intervals.
    """
    km_list = [s[2] for s in STATIONS]
    trains = []

    # Schedule pattern per hour H (5 to 23):
    # - Express SB: departs Tanwen at :00 (reaches Daan :27, Dajia :33)
    # - Express NB: departs Zhuifen at :44 (reaches Dajia :55, Daan :02 next hr)
    # - Commuter SB 1: departs Tanwen at :24 (reaches Daan :08, Dajia :18 next hr)
    # - Commuter SB 2: departs Tanwen at :54 (reaches Daan :38, Dajia :48 next hr)
    # - Commuter NB 1: departs Zhuifen at :20 (reaches Dajia :39, Daan :50)
    # - Commuter NB 2: departs Zhuifen at :50 (reaches Dajia :09, Daan :20 next hr)
    # - Freight (off-peak hours):
    #     SB in hours [9, 11, 13, 15, 21, 23] departs Tanwen at :23
    #     NB in hours [10, 12, 14, 22] departs Zhuifen at :40

    train_counter = 1
    for h in range(5, 24):
        # 1. Express
        trains.append({
            "train_id": f"EXP_SB_{train_counter:03d}",
            "train_name": f"新自強號 {100 + train_counter}次",
            "train_class": "Express",
            "direction": "SB",
            "dep_hour": h,
            "dep_min": 0,
            "color": "#dc2626", # Crimson red
            "runtime_key": "emu3000_express_runtime_sec"
        })
        train_counter += 1

        trains.append({
            "train_id": f"EXP_NB_{train_counter:03d}",
            "train_name": f"新自強號 {100 + train_counter}次",
            "train_class": "Express",
            "direction": "NB",
            "dep_hour": h,
            "dep_min": 44,
            "color": "#dc2626",
            "runtime_key": "emu3000_express_runtime_sec"
        })
        train_counter += 1

        # 2. Commuter
        trains.append({
            "train_id": f"COMM_SB_{train_counter:03d}",
            "train_name": f"區間車 {2500 + train_counter}次",
            "train_class": "Commuter",
            "direction": "SB",
            "dep_hour": h,
            "dep_min": 24,
            "color": "#2563eb", # Royal blue
            "runtime_key": "emu900_commuter_runtime_sec"
        })
        train_counter += 1

        trains.append({
            "train_id": f"COMM_SB_{train_counter:03d}",
            "train_name": f"區間車 {2500 + train_counter}次",
            "train_class": "Commuter",
            "direction": "SB",
            "dep_hour": h,
            "dep_min": 54,
            "color": "#2563eb",
            "runtime_key": "emu900_commuter_runtime_sec"
        })
        train_counter += 1

        trains.append({
            "train_id": f"COMM_NB_{train_counter:03d}",
            "train_name": f"區間車 {2500 + train_counter}次",
            "train_class": "Commuter",
            "direction": "NB",
            "dep_hour": h,
            "dep_min": 20,
            "color": "#2563eb",
            "runtime_key": "emu900_commuter_runtime_sec"
        })
        train_counter += 1

        trains.append({
            "train_id": f"COMM_NB_{train_counter:03d}",
            "train_name": f"區間車 {2500 + train_counter}次",
            "train_class": "Commuter",
            "direction": "NB",
            "dep_hour": h,
            "dep_min": 50,
            "color": "#2563eb",
            "runtime_key": "emu900_commuter_runtime_sec"
        })
        train_counter += 1

        # 3. Freight
        if h in [9, 11, 13, 15, 21, 23]:
            trains.append({
                "train_id": f"FRT_SB_{train_counter:03d}",
                "train_name": f"貨運列車 {7100 + train_counter}次",
                "train_class": "Freight",
                "direction": "SB",
                "dep_hour": h,
                "dep_min": 23,
                "color": "#16a34a", # Forest green
                "runtime_key": "freight_runtime_sec"
            })
            train_counter += 1

        if h in [10, 12, 14, 22]:
            trains.append({
                "train_id": f"FRT_NB_{train_counter:03d}",
                "train_name": f"貨運列車 {7100 + train_counter}次",
                "train_class": "Freight",
                "direction": "NB",
                "dep_hour": h,
                "dep_min": 40,
                "color": "#16a34a",
                "runtime_key": "freight_runtime_sec"
            })
            train_counter += 1

    # Compute trajectory points for each train
    computed_trajectories = []
    for tr in trains:
        t_start_sec = tr["dep_hour"] * 3600.0 + tr["dep_min"] * 60.0
        cur_t = t_start_sec
        key = tr["runtime_key"]

        if tr["direction"] == "SB":
            t_pts = [cur_t]
            k_pts = [km_list[0]]
            for idx, s in enumerate(segments):
                dur = float(s[key])
                cur_t += dur
                t_pts.append(cur_t)
                k_pts.append(km_list[idx + 1])
        else: # NB
            t_pts = [cur_t]
            k_pts = [km_list[-1]]
            rev_segs = list(reversed(segments))
            for idx, s in enumerate(rev_segs):
                dur = float(s[key])
                cur_t += dur
                t_pts.append(cur_t)
                k_pts.append(km_list[len(km_list) - 2 - idx])

        t_hours = np.array(t_pts) / 3600.0
        k_km = np.array(k_pts)

        computed_trajectories.append({
            **tr,
            "t_hours": t_hours,
            "k_km": k_km,
            "t_start_h": t_hours[0],
            "t_end_h": t_hours[-1]
        })

    return computed_trajectories

def verify_zero_bridge_conflicts(trajectories):
    """
    Rigorously asserts that no opposing train paths intersect inside
    the single-track river bridge bottleneck zones.
    """
    sb_trains = [t for t in trajectories if t["direction"] == "SB"]
    nb_trains = [t for t in trajectories if t["direction"] == "NB"]

    conflicts_daan = 0
    conflicts_dajia = 0
    total_crossings = 0

    daan_k0, daan_k1 = 51.2, 52.3
    dajia_k0, dajia_k1 = 61.8, 63.0

    for sb in sb_trains:
        for nb in nb_trains:
            # Overlap in time window?
            t_start = max(sb["t_start_h"], nb["t_start_h"])
            t_end = min(sb["t_end_h"], nb["t_end_h"])
            if t_start < t_end:
                t_grid = np.linspace(t_start, t_end, 500)
                k_sb_interp = np.interp(t_grid, sb["t_hours"], sb["k_km"])
                k_nb_interp = np.interp(t_grid, nb["t_hours"], nb["k_km"])
                diff = k_sb_interp - k_nb_interp
                sign_changes = np.where(np.diff(np.sign(diff)))[0]
                for sc in sign_changes:
                    total_crossings += 1
                    k_cross = k_sb_interp[sc]
                    if daan_k0 <= k_cross <= daan_k1:
                        conflicts_daan += 1
                    if dajia_k0 <= k_cross <= dajia_k1:
                        conflicts_dajia += 1

    print(f"=== BOTTLENECK CONFLICT VERIFICATION ===")
    print(f"  Total train paths: {len(trajectories)} ({len(sb_trains)} SB, {len(nb_trains)} NB)")
    print(f"  Total corridor opposing crossings analyzed: {total_crossings}")
    print(f"  Daan River Bridge (K51.2-K52.3) crossings: {conflicts_daan}")
    print(f"  Dajia River Bridge (K61.8-K63.0) crossings: {conflicts_dajia}")
    if conflicts_daan == 0 and conflicts_dajia == 0:
        print("  [SUCCESS] ZERO scheduled conflicts inside single-track bottlenecks!")
    else:
        raise ValueError(f"Found conflicts inside bridge bottlenecks: Daan={conflicts_daan}, Dajia={conflicts_dajia}")

def plot_matplotlib(trajectories, out_path):
    """
    Renders high-resolution 24-hour Stringline Diagram (Marey Chart) via Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(26, 14), dpi=300)
    plt.subplots_adjust(left=0.12, right=0.97, top=0.92, bottom=0.08)

    # Background styling
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#fafafa")

    # Time bounds (05:00 to 24:00)
    t_min, t_max = 5.0, 24.0
    k_min, k_max = 4.5, 83.1

    ax.set_xlim(t_min, t_max)
    ax.set_ylim(k_min, k_max)

    # Shaded horizontal bands for river bridges
    # Daan River Bridge
    ax.axhspan(51.2, 52.3, color="#ef4444", alpha=0.22, zorder=2)
    # Dajia River Bridge
    ax.axhspan(61.8, 63.0, color="#f59e0b", alpha=0.22, zorder=2)

    # Bridge annotations
    ax.text(5.1, 51.75, "■ 大安溪橋 Daan River Bridge (K51.2 - K52.3, 1,100m) [Single-Track Slot]",
            fontsize=10, fontweight="bold", color="#b91c1c", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fee2e2", edgecolor="#ef4444", alpha=0.9, lw=0.8),
            zorder=5)

    ax.text(5.1, 62.4, "■ 大甲溪橋 Dajia River Bridge (K61.8 - K63.0, 1,250m) [Single-Track Slot]",
            fontsize=10, fontweight="bold", color="#b45309", va="center",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fef3c7", edgecolor="#f59e0b", alpha=0.9, lw=0.8),
            zorder=5)

    # Station horizontal guide lines
    for st_id, st_name, st_k in STATIONS:
        lw = 0.9 if st_id in ["STA01", "STA08", "STA10", "STA12", "STA13", "STA16"] else 0.4
        color = "#94a3b8" if lw > 0.5 else "#cbd5e1"
        ax.axhline(st_k, color=color, linestyle="-", linewidth=lw, alpha=0.8, zorder=1)

    # Plot train lines
    legend_handles = {}
    for tr in trajectories:
        # Clip train lines to the time window 5.0 - 24.0
        t = tr["t_hours"]
        k = tr["k_km"]
        mask = (t >= t_min) & (t <= t_max)
        if not np.any(mask):
            continue

        lw = 1.6 if tr["train_class"] == "Express" else (1.2 if tr["train_class"] == "Commuter" else 1.4)
        ls = "-" if tr["train_class"] != "Freight" else "--"
        alpha = 0.88

        line, = ax.plot(t, k, color=tr["color"], linewidth=lw, linestyle=ls, alpha=alpha, zorder=3)
        if tr["train_class"] not in legend_handles:
            legend_handles[tr["train_class"]] = line

    # X-Axis formatting (Hours and Minutes)
    ax.set_xticks(range(5, 25))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(5, 25)], fontsize=11, fontweight="medium")
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(0.25)) # 15-minute minor ticks
    ax.grid(which="major", axis="x", color="#cbd5e1", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.grid(which="minor", axis="x", color="#e2e8f0", linestyle=":", linewidth=0.5, alpha=0.5)

    # Y-Axis formatting (Stations & Chainages)
    y_ticks = [s[2] for s in STATIONS]
    y_labels = [f"{s[1]} (K{s[2]:.1f})" for s in STATIONS]
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=10)

    # Labels and Title
    ax.set_xlabel("Time of Day (24-Hour Clockface Service Window)", fontsize=13, fontweight="bold", labelpad=10)
    ax.set_ylabel("Mainline Distance from Northern Gateway (Tanwen K4.5 to Zhuifen K83.1)", fontsize=13, fontweight="bold", labelpad=12)
    ax.set_title("TRA Western Trunk Coastal Line: 24-Hour Time-Space Stringline Diagram (列車運行圖)\n"
                 "Lever 1 River Bridge Bottleneck Optimization: Conflict-Free Single-Track Dispatch Across Daan & Dajia Bridges",
                 fontsize=15, fontweight="bold", pad=15)

    # Custom Legend
    from matplotlib.lines import Line2D
    custom_lines = [
        Line2D([0], [0], color="#dc2626", lw=2, label="海線新自強號 Express (EMU3000, 115 km/h)"),
        Line2D([0], [0], color="#2563eb", lw=1.6, label="海線區間車 Commuter (EMU900, 105 km/h)"),
        Line2D([0], [0], color="#16a34a", lw=1.8, linestyle="--", label="西部貨運列車 Freight (FREIGHT_E, 75 km/h)"),
        Line2D([0], [0], color="#ef4444", lw=8, alpha=0.35, label="大安溪橋單軌瓶頸 (K51.2 - K52.3)"),
        Line2D([0], [0], color="#f59e0b", lw=8, alpha=0.35, label="大甲溪橋單軌瓶頸 (K61.8 - K63.0)"),
    ]
    ax.legend(handles=custom_lines, loc="upper right", frameon=True, facecolor="#ffffff", framealpha=0.95, edgecolor="#94a3b8", fontsize=10)

    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  [SAVED] Matplotlib high-resolution PNG: {out_path}")

def plot_plotly(trajectories, out_path):
    """
    Renders interactive standalone HTML Stringline Diagram via Plotly.
    """
    fig = go.Figure()

    # Add Bottleneck bands
    fig.add_hrect(
        y0=51.2, y1=52.3,
        fillcolor="rgba(239, 68, 68, 0.25)",
        line_width=1,
        line_color="rgba(239, 68, 68, 0.6)",
        annotation_text="大安溪橋 Daan River Bridge (K51.2-K52.3)",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#b91c1c")
    )

    fig.add_hrect(
        y0=61.8, y1=63.0,
        fillcolor="rgba(245, 158, 11, 0.25)",
        line_width=1,
        line_color="rgba(245, 158, 11, 0.6)",
        annotation_text="大甲溪橋 Dajia River Bridge (K61.8-K63.0)",
        annotation_position="top left",
        annotation_font=dict(size=11, color="#b45309")
    )

    # Group traces by class for clean legend toggles
    added_legend = set()

    for tr in trajectories:
        t_hrs = tr["t_hours"]
        k_km = tr["k_km"]

        # Format time strings for hover
        time_strs = [f"{int(th):02d}:{int((th % 1)*60):02d}" for th in t_hrs]

        legend_group = tr["train_class"]
        show_in_legend = legend_group not in added_legend
        added_legend.add(legend_group)

        dash_style = "dash" if tr["train_class"] == "Freight" else "solid"

        fig.add_trace(go.Scatter(
            x=t_hrs,
            y=k_km,
            mode="lines",
            name=f"{tr['train_class']} ({tr['direction']})",
            legendgroup=legend_group,
            showlegend=show_in_legend,
            line=dict(
                color=tr["color"],
                width=2 if tr["train_class"] == "Express" else 1.5,
                dash=dash_style
            ),
            text=[f"<b>{tr['train_name']}</b><br>ID: {tr['train_id']}<br>Dir: {tr['direction']}<br>Time: {ts}<br>KM: K{km:.1f}"
                  for ts, km in zip(time_strs, k_km)],
            hoverinfo="text"
        ))

    # Layout styling
    y_ticks = [s[2] for s in STATIONS]
    y_labels = [f"{s[1]} (K{s[2]:.1f})" for s in STATIONS]

    x_ticks = list(range(5, 25))
    x_labels = [f"{h:02d}:00" for h in range(5, 25)]

    fig.update_layout(
        title=dict(
            text="<b>TRA Western Trunk Coastal Line: 24-Hour Time-Space Stringline Diagram (列車運行圖)</b><br>"
                 "<span style='font-size:13px;color:#64748b;'>Lever 1 Bridge Optimization — Conflict-Free Single-Track Dispatch Across Daan (K51.2) & Dajia (K61.8) Bridges</span>",
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Time of Day (05:00 - 24:00)",
            tickmode="array",
            tickvals=x_ticks,
            ticktext=x_labels,
            range=[5.0, 24.0],
            gridcolor="#e2e8f0",
            zeroline=False
        ),
        yaxis=dict(
            title="Corridor Distance from Tanwen (km)",
            tickmode="array",
            tickvals=y_ticks,
            ticktext=y_labels,
            range=[4.5, 83.1],
            gridcolor="#e2e8f0",
            zeroline=False
        ),
        hovermode="closest",
        plot_bgcolor="#fafafa",
        paper_bgcolor="#ffffff",
        margin=dict(l=140, r=40, t=80, b=60),
        legend=dict(
            x=1.01,
            y=1,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cbd5e1",
            borderwidth=1
        ),
        width=1600,
        height=950
    )

    fig.write_html(out_path, include_plotlyjs="cdn")
    print(f"  [SAVED] Interactive Plotly HTML: {out_path}")

def main():
    print("=================================================================")
    print("GENERATING TRA COASTAL LINE 24-HOUR STRINGLINE DIAGRAM")
    print("=================================================================")

    segments = load_segment_runtimes()
    trajectories = build_corridor_trajectories(segments)

    # 1. Assert conflict-free traversal
    verify_zero_bridge_conflicts(trajectories)

    # 2. Render Matplotlib PNG
    png_path = os.path.join(OUTPUTS_DIR, "stringline_diagram_24h.png")
    plot_matplotlib(trajectories, png_path)

    # Copy to root outputs for backup
    root_png_path = os.path.join(ROOT_OUTPUTS_DIR, "stringline_diagram_24h.png")
    import shutil
    shutil.copy2(png_path, root_png_path)

    # 3. Render Plotly HTML
    html_path = os.path.join(OUTPUTS_DIR, "stringline_diagram_24h.html")
    plot_plotly(trajectories, html_path)

    root_html_path = os.path.join(ROOT_OUTPUTS_DIR, "stringline_diagram_24h.html")
    shutil.copy2(html_path, root_html_path)

    print("\n[COMPLETE] 24-Hour Stringline Diagram generated successfully!")

if __name__ == "__main__":
    main()
