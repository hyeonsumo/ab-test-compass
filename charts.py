import os
from pathlib import Path

MPL_CONFIG_DIR = Path("data") / ".matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR.resolve()))

import matplotlib

matplotlib.use("TkAgg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import theme as t


def _configure_korean_font():
    """Use the first installed Korean-capable font available on this PC."""
    candidates = [
        "Pretendard",
        "Malgun Gothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "NanumGothic",
    ]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    selected = next((font for font in candidates if font in installed), None)
    if selected:
        plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False


_configure_korean_font()


def _apply_light_style(fig, ax):
    """Apply the pastel light app style to a matplotlib chart."""
    fig.patch.set_facecolor(t.BG_SURFACE)
    ax.set_facecolor(t.BG_SURFACE)
    ax.tick_params(colors=t.TEXT_SECONDARY, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(t.BORDER)
    ax.grid(True, color=t.BORDER, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)


def make_comparison_chart(parent, result):
    """Render A/B conversion-rate bars."""
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=100)
    _apply_light_style(fig, ax)

    groups = ["A (대조군)", "B (실험군)"]
    rates = [result["rate_a"] * 100, result["rate_b"] * 100]
    colors = [
        t.ACCENT_LAVENDER,
        t.ACCENT_MINT if rates[1] > rates[0] else t.ACCENT_PEACH,
    ]

    bars = ax.bar(groups, rates, color=colors, width=0.55, edgecolor="none")
    for bar, rate in zip(bars, rates):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(rates) * 0.03,
            f"{rate:.2f}%",
            ha="center",
            va="bottom",
            color=t.TEXT_PRIMARY,
            fontsize=11,
            fontweight="bold",
        )

    ax.set_ylabel("전환율 (%)", color=t.TEXT_SECONDARY, fontsize=10)
    ax.set_ylim(0, max(rates) * 1.25 if max(rates) > 0 else 1)

    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    return canvas.get_tk_widget()


def make_trend_chart(parent, exposures_df, conversions_df, window_size=200):
    """Render cumulative conversion rates in exposure order."""
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=100)
    _apply_light_style(fig, ax)

    if len(exposures_df) == 0:
        ax.text(
            0.5,
            0.5,
            "데이터 없음",
            ha="center",
            va="center",
            color=t.TEXT_TERTIARY,
            fontsize=12,
            transform=ax.transAxes,
        )
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas.get_tk_widget()

    converted_users = (
        set(conversions_df["user_id"].tolist()) if len(conversions_df) > 0 else set()
    )
    exposures_df = exposures_df.reset_index(drop=True).copy()
    exposures_df["converted"] = exposures_df["user_id"].isin(converted_users).astype(int)

    a_df = exposures_df[exposures_df["variant"] == "A"].reset_index(drop=True)
    b_df = exposures_df[exposures_df["variant"] == "B"].reset_index(drop=True)

    def cumulative_rate(df):
        if len(df) == 0:
            return [], []
        cum_conv = df["converted"].cumsum()
        cum_idx = pd.Series(range(1, len(df) + 1))
        rates = (cum_conv / cum_idx) * 100
        stride = max(1, len(df) // max(window_size, 1))
        sampled_idx = cum_idx.iloc[::stride]
        sampled_rates = rates.iloc[::stride]
        if sampled_idx.iloc[-1] != cum_idx.iloc[-1]:
            sampled_idx = pd.concat([sampled_idx, cum_idx.iloc[[-1]]])
            sampled_rates = pd.concat([sampled_rates, rates.iloc[[-1]]])
        return sampled_idx.tolist(), sampled_rates.tolist()

    a_x, a_y = cumulative_rate(a_df)
    b_x, b_y = cumulative_rate(b_df)

    if a_x:
        ax.plot(a_x, a_y, color=t.TEXT_TERTIARY, linewidth=2, label="A (대조군)")
    if b_x:
        ax.plot(b_x, b_y, color=t.PRIMARY, linewidth=2, label="B (실험군)")

    ax.set_xlabel("누적 노출 수", color=t.TEXT_SECONDARY, fontsize=10)
    ax.set_ylabel("누적 전환율 (%)", color=t.TEXT_SECONDARY, fontsize=10)
    ax.legend(
        facecolor=t.BG_SURFACE,
        edgecolor=t.BORDER,
        labelcolor=t.TEXT_PRIMARY,
        fontsize=9,
    )

    fig.tight_layout()
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    return canvas.get_tk_widget()
