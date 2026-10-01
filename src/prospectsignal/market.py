"""Market-size views: counts only, never contact lists. Chart builders return plotly figures."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import nace, regions
from .icp import ICP
from .schema import EMPLOYEE_BANDS

COLORS = {"ink": "#17322E", "teal": "#173C3A", "coral": "#D95B40", "mint": "#83D2B4", "gold": "#F2C66D"}
FONT = dict(family="Inter, Arial, sans-serif", color=COLORS["ink"])


def market_tables(store, icp: ICP) -> dict[str, pd.DataFrame]:
    """Counts by fylke, NACE division, employee band, organisation form and registration year."""
    fylke = store.counts_by(icp, "fylke")
    fylke["fylke"] = fylke["key"].map(regions.fylke_name)
    division = store.counts_by(icp, "nace_division")
    division["industry"] = division["key"].map(lambda code: nace.label(code) if code else "No code")
    band = store.counts_by(icp, "employee_band")
    band["order"] = band["key"].map(lambda key: EMPLOYEE_BANDS.index(key) if key in EMPLOYEE_BANDS else 99)
    band = band.sort_values("order").drop(columns="order")
    years = store.counts_by(icp, "registered_year").dropna(subset=["key"]).sort_values("key")
    forms = store.counts_by(icp, "org_form")
    return {
        "fylke": fylke,
        "nace_division": division,
        "employee_band": band,
        "registered_year": years,
        "org_form": forms,
    }


def _layout(figure: go.Figure, title: str, height: int = 380) -> go.Figure:
    figure.update_layout(
        title=dict(text=title, font=dict(size=16)),
        font=FONT,
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figure


def fylke_map(fylke_counts: pd.DataFrame) -> go.Figure:
    geojson = regions.fylker_geojson()
    data = pd.DataFrame({"key": list(regions.FYLKER)})
    data = data.merge(fylke_counts[["key", "units"]], on="key", how="left").fillna({"units": 0})
    data["name"] = data["key"].map(regions.fylke_name)
    figure = go.Figure(
        go.Choropleth(
            geojson=geojson,
            featureidkey="properties.fylkesnummer",
            locations=data["key"],
            z=data["units"],
            text=data["name"],
            hovertemplate="%{text}: %{z:,} units<extra></extra>",
            colorscale=[[0, "#EEF2EB"], [0.5, COLORS["mint"]], [1, COLORS["teal"]]],
            marker_line_color="white",
            marker_line_width=0.6,
            colorbar=dict(title="Units"),
        )
    )
    figure.update_geos(fitbounds="locations", visible=False)
    return _layout(figure, "Units by fylke", height=520)


def bar(frame: pd.DataFrame, label: str, title: str, horizontal: bool = True, limit: int = 20) -> go.Figure:
    data = frame.head(limit)
    if horizontal:
        data = data.iloc[::-1]
        trace = go.Bar(x=data["units"], y=data[label].astype(str), orientation="h", marker_color=COLORS["teal"])
    else:
        trace = go.Bar(x=data[label].astype(str), y=data["units"], marker_color=COLORS["teal"])
    figure = go.Figure(trace)
    figure.update_traces(hovertemplate="%{y}: %{x:,}<extra></extra>" if horizontal else "%{x}: %{y:,}<extra></extra>")
    return _layout(figure, title, height=max(320, 28 * len(data) + 80) if horizontal else 360)


def registrations_chart(years: pd.DataFrame, since: int = 2000) -> go.Figure:
    data = years.loc[years["key"] >= since]
    figure = go.Figure(go.Bar(x=data["key"], y=data["units"], marker_color=COLORS["coral"]))
    figure.update_traces(hovertemplate="%{x}: %{y:,} registered<extra></extra>")
    return _layout(figure, f"Registered in Enhetsregisteret per year (still registered today, since {since})")
