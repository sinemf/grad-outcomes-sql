"""Render README charts from the results/ CSVs."""

import os
import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# palette / chrome
SURFACE = "#fcfcfb"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"

plt.rcParams.update({
    "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "savefig.dpi": 150,
    "axes.edgecolor": BASE, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.labelcolor": INK2,
})

os.makedirs("charts", exist_ok=True)


def style(ax, xgrid=True):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    if xgrid:
        ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def kfmt(ax):
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))


def wrap(s, w=26):
    return "\n".join(textwrap.wrap(s, w, max_lines=2, placeholder="…"))


def titles(fig, title, sub):
    fig.text(0.02, 0.965, title, fontsize=13, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.915, sub, fontsize=9.5, color=INK2, va="top")


# --- 1. Top undergraduate fields by income ----------------------------------
q2 = pd.read_csv("results/q2_top_fields.csv")
q2 = q2[q2.graduates >= 500].nlargest(10, "income_5yr").sort_values("income_5yr")

fig, ax = plt.subplots(figsize=(8, 5.6))
ax.barh([wrap(f) for f in q2.field], q2.income_5yr, color=BLUE, height=0.55)
for i, v in enumerate(q2.income_5yr):
    ax.text(v - 2000, i, f"${v/1000:.0f}k", va="center", ha="right",
            color="#ffffff", fontsize=9, fontweight="bold")
kfmt(ax)
style(ax)
ax.tick_params(axis="y", labelsize=9, labelcolor=INK2)
titles(fig, "What an undergraduate degree pays, by field",
       "Median employment income 5 years after graduation, 2017 cohort, fields with 500+ graduates (2024 dollars)")
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig("charts/top_fields_income.png")

# --- 2. Credential payoff dumbbell: 2yr -> 5yr ------------------------------
q1 = pd.read_csv("results/q1_credential_payoff.csv").sort_values("income_5yr")

fig, ax = plt.subplots(figsize=(8, 5.6))
y = range(len(q1))
ax.hlines(y, q1.income_2yr, q1.income_5yr, color=BASE, linewidth=2, zorder=1)
ax.plot(q1.income_2yr, y, "o", color=ORANGE, ms=8, zorder=2, label="2 years out")
ax.plot(q1.income_5yr, y, "o", color=BLUE, ms=8, zorder=2, label="5 years out")
ax.set_yticks(list(y), [wrap(c, 30) for c in q1.qualification], fontsize=9)
kfmt(ax)
style(ax)
ax.tick_params(axis="y", labelcolor=INK2)
ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK2)
titles(fig, "Every credential pays more by year five",
       "Median employment income 2 vs 5 years after graduation, 2017 cohort, Canada (2024 dollars)")
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig("charts/credential_payoff.png")

# --- 3. Cohort trend line ----------------------------------------------------
q7 = pd.read_csv("results/q7_cohort_trend.csv")

fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(q7.cohort_year, q7.income_2yr, color=BLUE, linewidth=2, marker="o", ms=5)
for yr in (2010, 2015, 2019):
    row = q7[q7.cohort_year == yr].iloc[0]
    ax.annotate(f"${row.income_2yr/1000:.1f}k", (yr, row.income_2yr),
                textcoords="offset points", xytext=(0, 10), ha="center",
                fontsize=9, color=INK2)
ax.set_xticks(q7.cohort_year)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v/1000:.0f}k"))
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
ax.tick_params(length=0)
ax.set_xlabel("Graduating cohort", fontsize=9)
titles(fig, "New grads' real earnings dipped, then recovered",
       "Median income of undergraduates 2 years after graduation, by cohort, inflation-adjusted (2024 dollars)")
fig.tight_layout(rect=(0, 0, 1, 0.87))
fig.savefig("charts/cohort_trend.png")

# --- 4. Gender gap dumbbell --------------------------------------------------
q5 = pd.read_csv("results/q5_gender_gap.csv").sort_values("women_pct_of_men",
                                                          ascending=False)
fig, ax = plt.subplots(figsize=(8, 5.6))
y = range(len(q5))
ax.hlines(y, q5.women, q5.men, color=BASE, linewidth=2, zorder=1)
ax.plot(q5.women, y, "o", color=ORANGE, ms=8, zorder=2, label="Women")
ax.plot(q5.men, y, "o", color=BLUE, ms=8, zorder=2, label="Men")
for i, r in enumerate(q5.itertuples()):
    ax.text((r.women + r.men) / 2, i + 0.32, f"{r.women_pct_of_men:.0f}¢/$",
            ha="center", fontsize=8, color=MUTED)
ax.set_yticks(list(y), [wrap(f) for f in q5.field], fontsize=9)
kfmt(ax)
style(ax)
ax.tick_params(axis="y", labelcolor=INK2)
ax.legend(loc="lower right", frameon=False, fontsize=9, labelcolor=INK2)
titles(fig, "The widest gender pay gaps, five years out",
       "Median income of undergraduate women vs men by field, 2017 cohort (2024 dollars)")
fig.tight_layout(rect=(0, 0, 1, 0.90))
fig.savefig("charts/gender_gap.png")

print("Saved 4 charts to charts/")
