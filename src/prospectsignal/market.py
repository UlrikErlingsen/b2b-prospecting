"""Market-size views: counts only, never contact lists. Chart builders return plotly figures.

The builders set no brand colours or fonts: the Streamlit pages apply the Signal theme (template and palette from
``prospectsignal.ui.signal_theme``), so this module stays free of Streamlit."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from . import nace, regions
from .icp import ICP
from .schema import EMPLOYEE_BANDS


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
    figure.update_layout(title=dict(text=title), height=height)
    return figure


def fylke_map(
    fylke_counts: pd.DataFrame, colorscale: list | None = None, line_color: str | None = None
) -> go.Figure:
    """Choropleth of units per fylke. ``colorscale`` and ``line_color`` come from the caller's theme."""
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
            colorscale=colorscale,
            marker_line_color=line_color,
            marker_line_width=0.6,
            colorbar=dict(title="Units"),
        )
    )
    figure.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    return _layout(figure, "Units by fylke", height=520)


def bar(frame: pd.DataFrame, label: str, title: str, horizontal: bool = True, limit: int = 20) -> go.Figure:
    data = frame.head(limit)
    if horizontal:
        data = data.iloc[::-1]
        trace = go.Bar(x=data["units"], y=data[label].astype(str), orientation="h")
    else:
        trace = go.Bar(x=data[label].astype(str), y=data["units"])
    figure = go.Figure(trace)
    figure.update_traces(hovertemplate="%{y}: %{x:,}<extra></extra>" if horizontal else "%{x}: %{y:,}<extra></extra>")
    return _layout(figure, title, height=max(320, 28 * len(data) + 80) if horizontal else 360)


def registrations_chart(years: pd.DataFrame, since: int = 2000) -> go.Figure:
    data = years.loc[years["key"] >= since]
    figure = go.Figure(go.Bar(x=data["key"], y=data["units"]))
    figure.update_traces(hovertemplate="%{x}: %{y:,} registered<extra></extra>")
    return _layout(figure, f"Registered in Enhetsregisteret per year (still registered today, since {since})")
