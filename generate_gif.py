"""
Generate an animated GIF showing Malaysia's population growth 1957-2024,
including ethnic group breakdown.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import imageio.v2 as imageio
import io

# ── Colour palette ────────────────────────────────────────────────────────────
BG       = '#0a0e1a'
CARD     = '#111827'
BORDER   = '#1f2937'
ACCENT   = '#f59e0b'
TEXT     = '#f1f5f9'
MUTED    = '#94a3b8'
C_BUMI   = '#f97316'
C_CHIN   = '#3b82f6'
C_IND    = '#22c55e'
C_OTH    = '#a855f7'
C_TOTAL  = '#f59e0b'

# ── Data ─────────────────────────────────────────────────────────────────────
# [year, total(M), bumi%, chinese%, indian%, others%]
RAW = [
    (1957,  6.28,  49.8, 37.1, 11.3,  1.8),
    (1960,  8.11,  50.5, 36.6, 11.0,  1.9),
    (1965,  9.24,  51.8, 35.5, 10.8,  1.9),
    (1970, 10.44,  53.2, 34.3, 10.6,  1.9),
    (1975, 12.30,  54.7, 33.5, 10.1,  1.7),
    (1980, 13.76,  56.4, 32.7,  9.3,  1.6),
    (1985, 15.68,  58.5, 31.2,  8.7,  1.6),
    (1991, 18.38,  60.6, 29.0,  8.0,  2.4),
    (1995, 20.69,  62.2, 27.8,  7.7,  2.3),
    (2000, 23.27,  65.1, 26.0,  7.7,  1.2),
    (2005, 25.72,  66.1, 25.3,  7.4,  1.2),
    (2010, 28.33,  67.4, 24.6,  7.3,  0.7),
    (2015, 30.34,  68.5, 23.4,  7.0,  1.1),
    (2020, 32.45,  69.6, 22.6,  6.8,  1.0),
    (2022, 32.97,  70.0, 22.2,  6.7,  1.1),
    (2024, 33.91,  70.2, 21.9,  6.8,  1.1),
]

def interpolate(raw):
    rows = []
    for i in range(len(raw) - 1):
        y0, t0, b0, c0, i0, o0 = raw[i]
        y1, t1, b1, c1, i1, o1 = raw[i+1]
        steps = y1 - y0
        for s in range(steps):
            f = s / steps
            rows.append((
                int(y0 + s),
                t0 + (t1-t0)*f,
                b0 + (b1-b0)*f,
                c0 + (c1-c0)*f,
                i0 + (i1-i0)*f,
                o0 + (o1-o0)*f,
            ))
    rows.append(raw[-1])
    return rows

YEARLY = interpolate(RAW)
YEARS  = [r[0] for r in YEARLY]
N      = len(YEARLY)

MILESTONES = {
    1957: "Independence — 31 Aug 1957",
    1963: "Formation of Malaysia (Sep 1963)",
    1965: "Singapore separates (Aug 1965)",
    1970: "New Economic Policy launched",
    1991: "Vision 2020 announced",
    1997: "Asian Financial Crisis",
    2000: "Population crosses 23 million",
    2020: "COVID-19 pandemic",
    2024: "Population reaches 33.9 million",
}

def get_milestone(year):
    result = ""
    for y, txt in MILESTONES.items():
        if y <= year:
            result = txt
    return result

# ── GIF settings ─────────────────────────────────────────────────────────────
# One frame every 3 years (roughly), so 24 frames total, plus final hold
FRAME_YEARS = list(range(1957, 2025, 2)) + [2024]  # every 2 years + final
FRAME_YEARS = sorted(set(FRAME_YEARS))

def row_for_year(year):
    for r in YEARLY:
        if r[0] >= year:
            return r
    return YEARLY[-1]

def make_frame(frame_year):
    idx = next(i for i, r in enumerate(YEARLY) if r[0] >= frame_year)
    subset = YEARLY[:idx+1]

    fig = plt.figure(figsize=(14, 9), facecolor=BG, dpi=100)
    fig.patch.set_facecolor(BG)

    gs = gridspec.GridSpec(
        3, 3,
        figure=fig,
        left=0.06, right=0.97,
        top=0.88, bottom=0.07,
        hspace=0.55, wspace=0.38,
    )

    # ── Title ─────────────────────────────────────────────────────────────────
    fig.text(0.5, 0.95, "Malaysia Population Growth  1957 – 2024",
             ha='center', va='top', fontsize=18, fontweight='bold',
             color=ACCENT, fontfamily='DejaVu Sans')
    fig.text(0.5, 0.91, "Total population & ethnic composition over 67 years",
             ha='center', va='top', fontsize=10, color=MUTED)

    year, total, bumi_p, chin_p, ind_p, oth_p = row_for_year(frame_year)
    bumi_m = total * bumi_p / 100
    chin_m = total * chin_p / 100
    ind_m  = total * ind_p / 100
    oth_m  = total * oth_p / 100
    growth = (total / YEARLY[0][1] - 1) * 100

    # ── Year badge (top-right) ────────────────────────────────────────────────
    fig.text(0.88, 0.935, str(year),
             ha='center', va='center', fontsize=26, fontweight='black',
             color=ACCENT, bbox=dict(
                 boxstyle='round,pad=0.4', facecolor='#1e3a5f',
                 edgecolor=ACCENT, linewidth=2))

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi_y = 0.895
    kpis = [
        (f"{total:.2f}M", "Total Population"),
        (f"{int(total*1e6/329847)}", "Persons / km²"),
        (f"+{growth:.0f}%", "Growth vs 1957"),
    ]
    for k, (val, lbl) in enumerate(kpis):
        x = 0.08 + k * 0.14
        fig.text(x, kpi_y, val, ha='left', fontsize=13, fontweight='bold', color=ACCENT)
        fig.text(x, kpi_y - 0.028, lbl, ha='left', fontsize=7.5, color=MUTED)

    # ── 1. Line chart — total population ─────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor(CARD)
    for spine in ax1.spines.values():
        spine.set_edgecolor(BORDER)
    ax1.tick_params(colors=MUTED, labelsize=8)
    ax1.grid(axis='y', color=BORDER, linewidth=0.6)

    xs = [r[0] for r in subset]
    ys = [r[1] for r in subset]
    ax1.fill_between(xs, ys, alpha=0.15, color=C_TOTAL)
    ax1.plot(xs, ys, color=C_TOTAL, linewidth=2.5, solid_capstyle='round')
    ax1.scatter([xs[-1]], [ys[-1]], color=C_TOTAL, s=60, zorder=5)
    ax1.set_xlim(1957, 2024)
    ax1.set_ylim(0, 37)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}M'))
    ax1.set_title("Total Population (millions)", color=MUTED, fontsize=8,
                  loc='left', pad=5)

    # ── 2. Stacked area chart — ethnic breakdown ──────────────────────────────
    ax2 = fig.add_subplot(gs[1, :2])
    ax2.set_facecolor(CARD)
    for spine in ax2.spines.values():
        spine.set_edgecolor(BORDER)
    ax2.tick_params(colors=MUTED, labelsize=8)
    ax2.grid(axis='y', color=BORDER, linewidth=0.6)

    xs2   = [r[0] for r in subset]
    bumi  = [r[1]*r[2]/100 for r in subset]
    chin  = [r[1]*r[3]/100 for r in subset]
    ind   = [r[1]*r[4]/100 for r in subset]
    oth   = [r[1]*r[5]/100 for r in subset]

    ax2.stackplot(xs2, bumi, chin, ind, oth,
                  colors=[C_BUMI, C_CHIN, C_IND, C_OTH],
                  alpha=0.85, labels=['Bumiputera','Chinese','Indian','Others'])
    ax2.set_xlim(1957, 2024)
    ax2.set_ylim(0, 37)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:.0f}M'))
    ax2.set_title("Population by Ethnic Group — stacked (millions)", color=MUTED,
                  fontsize=8, loc='left', pad=5)

    legend_patches = [
        mpatches.Patch(color=C_BUMI, label='Bumiputera'),
        mpatches.Patch(color=C_CHIN, label='Chinese'),
        mpatches.Patch(color=C_IND,  label='Indian'),
        mpatches.Patch(color=C_OTH,  label='Others'),
    ]
    ax2.legend(handles=legend_patches, loc='upper left',
               fontsize=7, framealpha=0.2, labelcolor=TEXT,
               facecolor=CARD, edgecolor=BORDER, ncol=4)

    # ── 3. Pie chart ──────────────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.set_facecolor(CARD)
    for spine in ax3.spines.values():
        spine.set_edgecolor(BORDER)

    wedges, texts, autotexts = ax3.pie(
        [bumi_p, chin_p, ind_p, oth_p],
        labels=['Bumi', 'Chinese', 'Indian', 'Others'],
        colors=[C_BUMI, C_CHIN, C_IND, C_OTH],
        autopct='%1.1f%%',
        startangle=140,
        pctdistance=0.75,
        wedgeprops=dict(width=0.6, edgecolor=BG, linewidth=2),
    )
    for t in texts:      t.set(color=MUTED, fontsize=7)
    for t in autotexts:  t.set(color=TEXT,  fontsize=7, fontweight='bold')
    ax3.set_title("Ethnic Share", color=MUTED, fontsize=8, pad=6)

    # ── 4. Horizontal ethnic bars ─────────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_facecolor(CARD)
    for spine in ax4.spines.values():
        spine.set_edgecolor(BORDER)
    ax4.tick_params(colors=MUTED, labelsize=8)
    ax4.set_xlim(0, 100)

    groups = [
        ('Bumiputera', bumi_p, bumi_m, C_BUMI),
        ('Chinese',    chin_p, chin_m, C_CHIN),
        ('Indian',     ind_p,  ind_m,  C_IND),
        ('Others',     oth_p,  oth_m,  C_OTH),
    ]
    y_pos = [3, 2, 1, 0]
    for (name, pct, pop, col), yp in zip(groups, y_pos):
        ax4.barh(yp, pct, color=col, alpha=0.85, height=0.6)
        ax4.text(pct + 1, yp, f'{pct:.1f}%  ({pop:.2f}M)',
                 va='center', fontsize=7.5, color=TEXT)
    ax4.set_yticks(y_pos)
    ax4.set_yticklabels(['Bumiputera','Chinese','Indian','Others'], color=TEXT, fontsize=8)
    ax4.xaxis.set_visible(False)
    ax4.set_title("Ethnic % breakdown", color=MUTED, fontsize=8, pad=6)

    # ── 5. Timeline bar (bottom strip) ───────────────────────────────────────
    ax5 = fig.add_subplot(gs[2, :])
    ax5.set_facecolor(CARD)
    for spine in ax5.spines.values():
        spine.set_edgecolor(BORDER)

    prog = (frame_year - 1957) / (2024 - 1957)
    ax5.barh(0, 100, color=BORDER, height=0.5)
    ax5.barh(0, prog * 100, color=ACCENT, height=0.5, alpha=0.9)
    ax5.set_xlim(0, 100)
    ax5.set_ylim(-1, 1)
    ax5.axis('off')

    milestone = get_milestone(frame_year)
    ax5.text(50, -0.7, milestone, ha='center', va='bottom',
             fontsize=8.5, color='#cbd5e1', style='italic')

    # decade ticks
    for yr in range(1957, 2025, 5):
        xp = (yr - 1957) / (2024 - 1957) * 100
        ax5.axvline(xp, color=BORDER, linewidth=0.8, ymin=0.3, ymax=0.7)
        ax5.text(xp, 0.55, str(yr), ha='center', va='bottom',
                 fontsize=6.5, color=MUTED)

    # current position dot
    ax5.scatter([prog * 100], [0], color=ACCENT, s=80, zorder=5)

    # ── Save frame to bytes ───────────────────────────────────────────────────
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, facecolor=BG)
    plt.close(fig)
    buf.seek(0)
    return imageio.imread(buf)

# ── Build GIF ────────────────────────────────────────────────────────────────
print(f"Rendering {len(FRAME_YEARS)} frames …")
frames = []
for i, fy in enumerate(FRAME_YEARS):
    print(f"  Frame {i+1}/{len(FRAME_YEARS)}  year={fy}", flush=True)
    frames.append(make_frame(fy))

# Hold on the last frame for 3 seconds (fps=2 → 6 repeats)
for _ in range(5):
    frames.append(frames[-1])

OUT = '/home/user/DailyBibleWebApp/malaysia-population-growth.gif'
imageio.mimsave(OUT, frames, duration=0.5, loop=0)
print(f"\nSaved → {OUT}")
print(f"File size: {__import__('os').path.getsize(OUT)/1024/1024:.1f} MB")
