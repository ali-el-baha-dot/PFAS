import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import json
import urllib.request


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="STEU – Boues & Épandage",
    page_icon="🌊",
    layout="wide",
)

# ── Column mapping ────────────────────────────────────────────────────────────
COLUMN_MAP = {
    "Numéro département": "Departement",
    "Nom de la région": "region",
    "Tranche obligation": "obligation_band",
    "Nature du STEU": "nature_steu",
    "Latitude du rejet (WGS84)": "x_coord",
    "Longitude du rejet (WGS84)": "y_coord",
    "Calcul production de boue à partir de la charge max (EH) en tMS/an": "sludge_production_tms",
    "Prod boues sans réactif (tMS/an) (avec virgule)": "sludge_no_reagent_tms",
    "Quantité retour au sol + STEU (épandage + compostage + métha) (tMS:an)": "sludge_land_application_tms",
}

DEPARTEMENT_NAMES = {
    "1": "Ain",
    "2": "Aisne",
    "3": "Allier",
    "4": "Alpes-de-Haute-Provence",
    "5": "Hautes-Alpes",
    "6": "Alpes-Maritimes",
    "7": "Ardèche",
    "8": "Ardennes",
    "9": "Ariège",
    "10": "Aube",
    "11": "Aude",
    "12": "Aveyron",
    "13": "Bouches-du-Rhône",
    "14": "Calvados",
    "15": "Cantal",
    "16": "Charente",
    "17": "Charente-Maritime",
    "18": "Cher",
    "19": "Corrèze",
    "21": "Côte-d'Or",
    "22": "Côtes-d'Armor",
    "23": "Creuse",
    "24": "Dordogne",
    "25": "Doubs",
    "26": "Drôme",
    "27": "Eure",
    "28": "Eure-et-Loir",
    "29": "Finistère",
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "30": "Gard",
    "31": "Haute-Garonne",
    "32": "Gers",
    "33": "Gironde",
    "34": "Hérault",
    "35": "Ille-et-Vilaine",
    "36": "Indre",
    "37": "Indre-et-Loire",
    "38": "Isère",
    "39": "Jura",
    "40": "Landes",
    "41": "Loir-et-Cher",
    "42": "Loire",
    "43": "Haute-Loire",
    "44": "Loire-Atlantique",
    "45": "Loiret",
    "46": "Lot",
    "47": "Lot-et-Garonne",
    "48": "Lozère",
    "49": "Maine-et-Loire",
    "50": "Manche",
    "51": "Marne",
    "52": "Haute-Marne",
    "53": "Mayenne",
    "54": "Meurthe-et-Moselle",
    "55": "Meuse",
    "56": "Morbihan",
    "57": "Moselle",
    "58": "Nièvre",
    "59": "Nord",
    "60": "Oise",
    "61": "Orne",
    "62": "Pas-de-Calais",
    "63": "Puy-de-Dôme",
    "64": "Pyrénées-Atlantiques",
    "65": "Hautes-Pyrénées",
    "66": "Pyrénées-Orientales",
    "67": "Bas-Rhin",
    "68": "Haut-Rhin",
    "69": "Rhône",
    "70": "Haute-Saône",
    "71": "Saône-et-Loire",
    "72": "Sarthe",
    "73": "Savoie",
    "74": "Haute-Savoie",
    "75": "Paris",
    "76": "Seine-Maritime",
    "77": "Seine-et-Marne",
    "78": "Yvelines",
    "79": "Deux-Sèvres",
    "80": "Somme",
    "81": "Tarn",
    "82": "Tarn-et-Garonne",
    "83": "Var",
    "84": "Vaucluse",
    "85": "Vendée",
    "86": "Vienne",
    "87": "Haute-Vienne",
    "88": "Vosges",
    "89": "Yonne",
    "90": "Territoire de Belfort",
    "91": "Essonne",
    "92": "Hauts-de-Seine",
    "93": "Seine-Saint-Denis",
    "94": "Val-de-Marne",
    "95": "Val-d'Oise",
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
}


NUMERIC_COLS = [
    "x_coord",
    "y_coord",
    "sludge_production_tms",
    "sludge_no_reagent_tms",
    "sludge_land_application_tms",
]

# ── Band config (single source of truth) ─────────────────────────────────────
BAND_ORDER = [
    "Taille < 200 EH",
    "[ 200 ; 2 000 [ EH",
    "[ 2 000 ; 10 000 [ EH",
    "[ 10 000 ; 100 000 [ E",
    "[ 100 000 ; ... [ EH",
]

BAND_COLORS = {
    "Taille < 200 EH":          "#1f77b4",
    "[ 200 ; 2 000 [ EH":       "#ff7f0e",
    "[ 2 000 ; 10 000 [ EH":    "#2ca02c",
    "[ 10 000 ; 100 000 [ E":   "#d62728",
    "[ 100 000 ; ... [ EH":     "#9467bd",
}

# Scattermapbox only supports "circle" (and maki icons) as marker symbols.
# square/diamond/triangle/star are silently ignored (markers become invisible).
# We differentiate bands by color + size instead.
BAND_SIZES = {
    "Taille < 200 EH":          7,
    "[ 200 ; 2 000 [ EH":       9,
    "[ 2 000 ; 10 000 [ EH":    11,
    "[ 10 000 ; 100 000 [ E":   14,
    "[ 100 000 ; ... [ EH":     18,
}

NATURE_ORDER = [
    "Agricole",
    "Inconnue",
    "Industri",
    "Mixte",
    "Prive",
    "Urbain",
]

# ── Data processing ───────────────────────────────────────────────────────────
@st.cache_data(show_spinner="Traitement des données…")
def process(file_bytes: bytes):
    df_raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name="Format Excel")

    available = [c for c in COLUMN_MAP if c in df_raw.columns]
    df = df_raw[available].copy()
    df = df.rename(columns={k: COLUMN_MAP[k] for k in available})

    # Keep Departement as string to handle mixed values like "2A", "2B"
    if "Departement" in df.columns:
        df["Departement"] = df["Departement"].astype(str).str.strip()
        # Replace pandas NA string representation with actual NA
        df["Departement"] = df["Departement"].replace({"nan": pd.NA, "": pd.NA})
        df["Departement_nom"] = (df["Departement"].map(DEPARTEMENT_NAMES).fillna(df["Departement"]))

    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["has_geometry"] = df["x_coord"].notna() & df["y_coord"].notna()

    regional = (
        df.groupby("region", dropna=False)
        .agg(
            total_sludge=("sludge_production_tms", "sum"),
            total_land_application=("sludge_land_application_tms", "sum"),
            plants=("region", "count"),
        )
        .reset_index()
    )




    kpis = {
        "plants_total": len(df),
        "plants_with_geo": int(df["has_geometry"].sum()),
        "total_sludge_tms": df["sludge_production_tms"].sum(),
        "total_land_application_tms": df["sludge_land_application_tms"].sum(),
    }

    return df, regional, kpis


def fmt(val, decimals=0):
    if pd.isna(val):
        return "–"
    return f"{val:,.{decimals}f}".replace(",", " ")




# for tab 2 
@st.cache_data(show_spinner="Chargement des contours de régions…")
def load_regions_geojson() -> dict:
    """French regions GeoJSON (simplified) from gregoiredavid/france-geojson."""
    url = (
        "https://raw.githubusercontent.com/gregoiredavid/"
        "france-geojson/master/regions-version-simplifiee.geojson"
    )
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())


@st.cache_data(show_spinner=False)
def compute_region_bounds(geojson: dict) -> dict:
    """Pre-compute [[min_lat, min_lon], [max_lat, max_lon]] per region name."""
    bounds = {}
    for feat in geojson["features"]:
        name = feat["properties"].get("nom")
        if not name:
            continue
        coords = feat["geometry"]["coordinates"]
        rings = coords if feat["geometry"]["type"] == "Polygon" else (
            ring for poly in coords for ring in poly
        )
        lons, lats = [], []
        for ring in rings:
            for lon, lat in ring:
                lons.append(lon)
                lats.append(lat)
        bounds[name] = [[min(lats), min(lons)], [max(lats), max(lons)]]
    return bounds



# ── Session state ─────────────────────────────────────────────────────────────
if "analyse_triggered" not in st.session_state:
    st.session_state["analyse_triggered"] = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Dashboard")
    st.markdown("Analyse des boues et de l'épandage par région.")
    uploaded = st.file_uploader(
        "Importer le fichier Excel",
        type=["xlsx", "xls"],
        help='Le fichier doit contenir une feuille "Format Excel".',
    )

    if uploaded is None:
        st.session_state["analyse_triggered"] = False

    if uploaded is not None:
        if st.button("🔍 Analyser le document", use_container_width=True, type="primary"):
            st.session_state["analyse_triggered"] = True

    st.divider()
    st.caption("Données : colonnes STEU · Épandage · Géolocalisation")

# ── Home screen ────────────────────────────────────────────────────────────
if uploaded is None:
    st.markdown(
        """
        ## IEIC Dashboard
        Importez votre fichier Excel STEU dans le panneau de gauche pour commencer.

        **Colonnes attendues dans la feuille `Format Excel` :**
        | Colonne d'origine | Champ interne |
        |---|---|
        | Numéro département | `Departement` |
        | Nom de la région | `region` |
        | Tranche obligation | `obligation_band` |
        | Nature du STEU | `nature_steu` |
        | Coordonnée X du STEU | `x_coord` |
        | Coordonnée Y du STEU | `y_coord` |
        | Production de boue (EH) en tMS/an | `sludge_production_tms` |
        | Prod boues sans réactif (tMS/an) | `sludge_no_reagent_tms` |
        | Retour au sol + STEU (tMS/an) | `sludge_land_application_tms` |
        """
    )
    st.stop()

if not st.session_state["analyse_triggered"]:
    st.info("📂 Fichier chargé. Cliquez sur **Analyser le document** dans le panneau de gauche pour afficher le tableau de bord.")
    st.stop()

# ── Load & process ────────────────────────────────────────────────────────────
try:
    df, regional, kpis = process(uploaded.read())
except Exception as e:
    st.error(f"Erreur lors de la lecture du fichier : {e}")
    st.stop()

# ── Filters ────────────────────────────────────────────────────────────────
available_bands = [b for b in BAND_ORDER if b in df["obligation_band"].dropna().unique()]
available_natures = [
    n for n in NATURE_ORDER
    if "nature_steu" in df.columns and n in df["nature_steu"].dropna().unique()
]

# Build the sorted department list (numeric-first, then alphanumeric like 2A/2B)
# so the multiselect options feel natural to the user
if "Departement" in df.columns:
    raw_depts = df["Departement"].dropna().unique().tolist()

    def _dept_sort_key(d):
        try:
            return (0, int(d), "")
        except (ValueError, TypeError):
            return (1, 0, str(d))

    available_depts = sorted(raw_depts, key=_dept_sort_key)
else:
    available_depts = []

selected_bands   = st.sidebar.multiselect("Tranche d'obligation", options=available_bands)
selected_natures = st.sidebar.multiselect("Nature du STEU", options=available_natures)
# ── NEW: department filter ────────────────────────────────────────────────────
selected_depts   = st.sidebar.multiselect("Numéro département", options=available_depts)

df_filtered = df.dropna(subset=["obligation_band"]).copy()

if selected_bands:
    df_filtered = df_filtered[df_filtered["obligation_band"].isin(selected_bands)]

if selected_natures and "nature_steu" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["nature_steu"].isin(selected_natures)]

# ── NEW: apply department filter ──────────────────────────────────────────────
if selected_depts and "Departement" in df_filtered.columns:
    df_filtered = df_filtered[df_filtered["Departement"].isin(selected_depts)]

# Recompute regional KPIs after filters
regional = (
    df_filtered.groupby("region", dropna=False)
    .agg(
        total_sludge=("sludge_production_tms", "sum"),
        total_land_application=("sludge_land_application_tms", "sum"),
        plants=("region", "size"),
    )
    .reset_index()
)

departmental = (
    df_filtered.groupby("Departement_nom", dropna=False)
    .agg(
        total_sludge=("sludge_production_tms", "sum"),
        total_land_application=("sludge_land_application_tms", "sum"),
        plants=("Departement", "size"),
    )
    .reset_index()
)

kpis = {
    "plants_total": len(df_filtered),
    "plants_with_geo": int(df_filtered["has_geometry"].sum()),
    "total_sludge_tms": df_filtered["sludge_production_tms"].sum(),
    "total_land_application_tms": df_filtered["sludge_land_application_tms"].sum(),
}



# ── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "📊 Dashboard",
    "🗺️ Carte dupliquée",
])

with tab1:
    # ── KPIs ──────────────────────────────────────────────────────────────────────
    st.subheader("KPIs globaux")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Stations (STEU)", fmt(kpis["plants_total"]))
    k2.metric("Avec coordonnées GPS", fmt(kpis.get("plants_with_geo", 0)))
    k3.metric("Production boues (tMS/an)", fmt(kpis["total_sludge_tms"]))
    k4.metric("Retour au sol (tMS/an)", fmt(kpis["total_land_application_tms"]))

    land_pct = (
        kpis["total_land_application_tms"] / kpis["total_sludge_tms"] * 100
        if kpis["total_sludge_tms"] > 0
        else 0
    )
    st.caption(f"Taux d'épandage global : **{land_pct:.1f} %** de la production totale.")
    st.divider()

    # ── Charts ────────────────────────────────────────────────────────────────────
    title_col, switch_col = st.columns([6, 2])

    with title_col:
        st.subheader("Analyse territoriale")

    with switch_col:
        view_mode = st.segmented_control(
            "",
            ["Régional", "Départemental"],
            default="Régional",
            label_visibility="collapsed",
        )

    if view_mode == "Régional":
        agg_df = regional.copy()
        territory_col = "region"
        territory_label = "Région"
    else:
        agg_df = departmental.copy()
        territory_col = "Departement_nom"
        territory_label = "Département"

    agg_sorted = agg_df.sort_values(
        "total_sludge",
        ascending=False
    )

    col_left, col_right = st.columns(2)


    with col_left:
        st.subheader(f"Production de boues par {territory_label.lower()}")
        fig_bar = px.bar(
            agg_sorted,
            x=territory_col,
            y="total_sludge",
            color="total_sludge",
            color_continuous_scale="Blues",
            labels={territory_col: territory_label, "total_sludge": "Production (tMS/an)"},
            height=380,
        )
        fig_bar.update_layout(
            coloraxis_showscale=False,
            xaxis_tickangle=-35,
            margin=dict(t=20, b=80),
        )
        fig_bar.update_yaxes(title="tMS/an", tickformat=",.0f", autorange=True, rangemode="tozero")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader(f"Épandage vs Production (Top 15 {territory_label.lower()}s)")
        top15 = agg_sorted.head(15)
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Production (tMS/an)",
            x=top15[territory_col],
            y=top15["total_sludge"],
            marker_color="#1f77b4",
        ))
        fig_comp.add_trace(go.Bar(
            name="Retour au sol (tMS/an)",
            x=top15[territory_col],
            y=top15["total_land_application"],
            marker_color="#2ca02c",
        ))
        fig_comp.update_layout(
            barmode="group",
            height=380,
            xaxis_tickangle=-35,
            margin=dict(t=20, b=80),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        )
        fig_comp.update_yaxes(title="tMS/an", tickformat=",.0f", autorange=True, rangemode="tozero")
        st.plotly_chart(fig_comp, use_container_width=True)

    st.divider()

    # ── Map ───────────────────────────────────────────────────────────────────────
    df_geo = df_filtered[df_filtered["has_geometry"]].copy()

    if not df_geo.empty:
        st.subheader(f"Carte des STEU géolocalisées ({len(df_geo)} stations)")

        x_med = df_geo["x_coord"].median()

        if x_med > 1000:  # Lambert-93
            try:
                import pyproj
                transformer = pyproj.Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
                df_geo["lon"], df_geo["lat"] = transformer.transform(
                    df_geo["x_coord"].values,
                    df_geo["y_coord"].values,
                )
            except ImportError:
                df_geo["lon"] = (df_geo["x_coord"] - 700_000) / 111_320
                df_geo["lat"] = ((df_geo["y_coord"] - 6_600_000) / 110_540) + 46.5
        else:
            df_geo["lat"] = df_geo["x_coord"]
            df_geo["lon"] = df_geo["y_coord"]

        df_geo = df_geo[df_geo["lat"].between(-90, 90) & df_geo["lon"].between(-180, 180)]

        if not df_geo.empty:
            # ── FIX: build one trace per band manually so color+symbol are
            #    guaranteed correct regardless of trace-name matching issues ──────
            fig_map = go.Figure()

            # Determine which bands are actually present in the filtered data
            present_bands = [b for b in BAND_ORDER if b in df_geo["obligation_band"].unique()]

            for band in present_bands:
                subset = df_geo[df_geo["obligation_band"] == band]

                # Build hover text manually
                hover_parts = (
                    "<b>%{customdata[0]}</b><br>"
                    "Département : %{customdata[4]}<br>"
                    "Tranche : " + band + "<br>"
                    "Nature : %{customdata[1]}<br>"
                    "Production : %{customdata[2]:,.0f} tMS/an<br>"
                    "Retour sol : %{customdata[3]:,.0f} tMS/an"
                    "<extra></extra>"
                )

                # Include Departement in customdata (index 4)
                custom_cols = [
                    "region",
                    "nature_steu" if "nature_steu" in subset.columns else "region",
                    "sludge_production_tms",
                    "sludge_land_application_tms",
                    "Departement_nom" if "Departement_nom" in subset.columns else "region",
                ]

                fig_map.add_trace(go.Scattermapbox(
                    name=band,
                    lat=subset["lat"],
                    lon=subset["lon"],
                    mode="markers",
                    marker=go.scattermapbox.Marker(
                        size=BAND_SIZES.get(band, 10),
                        color=BAND_COLORS.get(band, "#888888"),
                        # NOTE: only "circle" is valid for Scattermapbox;
                        # other symbol names (square, diamond, etc.) are silently
                        # rendered invisible. Differentiation is via color + size.
                    ),
                    customdata=subset[custom_cols].fillna("–").values,
                    hovertemplate=hover_parts,
                ))

            fig_map.update_layout(
                mapbox_style="carto-positron",
                mapbox_zoom=4.5,
                mapbox_center={"lat": 46.6, "lon": 2.3},
                height=520,
                margin=dict(l=0, r=0, t=0, b=0),
                legend=dict(
                    title="Tranche obligation",
                    orientation="v",
                    x=0.01,
                    y=0.99,
                    bgcolor="rgba(255,255,255,0.8)",
                    bordercolor="rgba(0,0,0,0.2)",
                    borderwidth=1,
                ),
            )

            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Aucune station n'a pu être projetée sur la carte.")
    else:
        st.info("Aucune coordonnée GPS disponible dans ce fichier.")

    st.divider()

    # ── Obligation band stats ─────────────────────────────────────────────────────
    st.subheader("Nombre de stations par tranche")

    band_counts = (
        df_filtered["obligation_band"]
        .value_counts(dropna=False)
        .reindex(BAND_ORDER)   # ensures consistent ordering
        .fillna(0)
        .astype(int)
        .reset_index()
    )

    band_counts.columns = ["obligation_band", "stations"]

    fig_band = px.bar(
        band_counts,
        x="obligation_band",
        y="stations",
        color="obligation_band",
        color_discrete_map=BAND_COLORS,
    )

    fig_band.update_layout(
        xaxis_title="Tranche d'obligation",
        yaxis_title="Nombre de stations",
        showlegend=False,
        xaxis_tickangle=-30,
        margin=dict(t=20, b=80),
    )

    st.plotly_chart(fig_band, use_container_width=True)

    # ── Regional table ────────────────────────────────────────────────────────────
    st.subheader(
        f"Tableau {territory_label.lower()}"
    )

    table_display = agg_df.copy()

    table_display = table_display.rename(columns={
        territory_col: territory_label,
        "total_sludge": "Production boues (tMS/an)",
        "total_land_application": "Retour au sol (tMS/an)",
        "plants": "Stations",
    })

    table_display = table_display.sort_values(
        "Production boues (tMS/an)",
        ascending=False,
    )

    st.dataframe(
        table_display.style.format({
            "Production boues (tMS/an)": "{:,.0f}",
            "Retour au sol (tMS/an)": "{:,.0f}",
            "Stations": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )


with tab2:

    st.subheader("Carte interactive ")
    st.caption(
        "Cliquez sur une région pour zoomer. "
        "Cliquez sur un marqueur pour voir le détail de la station. "
        "Utilisez le panneau en haut à droite pour filtrer par tranche."
    )

    # ── Preconditions ────────────────────────────────────────────────────────
    df_geo_raw = df_filtered[df_filtered["has_geometry"]].copy()

    if df_geo_raw.empty:
        st.info("Aucune coordonnée GPS disponible dans ce fichier.")

    else:
        # Coordinate conversion — identical logic to tab1
        x_med = df_geo_raw["x_coord"].median()

        if pd.isna(x_med) or x_med > 1000:
            try:
                import pyproj
                transformer = pyproj.Transformer.from_crs(
                    "EPSG:2154", "EPSG:4326", always_xy=True,
                )
                df_geo_raw["lon"], df_geo_raw["lat"] = transformer.transform(
                    df_geo_raw["x_coord"].values,
                    df_geo_raw["y_coord"].values,
                )
            except ImportError:
                df_geo_raw["lon"] = (df_geo_raw["x_coord"] - 700_000) / 111_320
                df_geo_raw["lat"] = ((df_geo_raw["y_coord"] - 6_600_000) / 110_540) + 46.5
        else:
            df_geo_raw["lat"] = df_geo_raw["x_coord"]
            df_geo_raw["lon"] = df_geo_raw["y_coord"]

        df_geo = df_geo_raw[
            df_geo_raw["lat"].between(-90, 90)
            & df_geo_raw["lon"].between(-180, 180)
        ]

        if df_geo.empty:
            st.info("Aucune station n'a pu être projetée sur la carte.")

        else:
            # ── Session state for the current zoomed region ──────────────────
            if "selected_region" not in st.session_state:
                st.session_state["selected_region"] = None

            selected_region = st.session_state["selected_region"]

            # ── Load regions GeoJSON + pre-computed bounds ────────────────────
            try:
                regions_geojson = load_regions_geojson()
                region_bounds = compute_region_bounds(regions_geojson)
            except Exception as e:
                st.error(f"Impossible de charger les contours de régions : {e}")
                st.stop()

            # ── Header row: current region badge + Reset button ──────────────
            hdr_l, hdr_r = st.columns([6, 1])
            with hdr_l:
                if selected_region:
                    n_in_region = int((df_geo["region"] == selected_region).sum())
                    st.info(
                        f"📍 Vue active : **{selected_region}** "
                        f"— {n_in_region} station(s) visible(s)"
                    )
                else:
                    st.caption(f"🗺️ {len(df_geo)} stations géolocalisées au total")
            with hdr_r:
                if st.button(
                    "🔄 Reset",
                    help="Revenir à la vue France entière",
                    use_container_width=True,
                ):
                    st.session_state["selected_region"] = None
                    st.rerun()

            # ── Build the Folium map ─────────────────────────────────────────
            m = folium.Map(
                location=[46.6, 2.3],
                zoom_start=5,
                tiles="cartodbpositron",
                control_scale=True,
            )

            # If a region is selected, fit the map to its bounds on render
            if selected_region and selected_region in region_bounds:
                m.fit_bounds(region_bounds[selected_region], padding=[20, 20])

            # Clickable regions overlay
            folium.GeoJson(
                regions_geojson,
                name="Régions",
                style_function=lambda f: {
                    "fillColor": "#ffffff",
                    "color": "#333333",
                    "weight": 1.5,
                    "fillOpacity": 0.08,
                },
                highlight_function=lambda f: {
                    "fillColor": "#ffcc00",
                    "color": "#000000",
                    "weight": 2.5,
                    "fillOpacity": 0.4,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["nom"],
                    aliases=["Région :"],
                    sticky=False,
                    style=(
                        "background-color: #fff;"
                        "border: 1px solid #333;"
                        "padding: 4px 8px;"
                        "font-family: Arial;"
                        "font-size: 12px;"
                    ),
                ),
            ).add_to(m)

            # ── STEU markers — grouped by band for the layer-control legend ──
            present_bands = [
                b for b in BAND_ORDER
                if b in df_geo["obligation_band"].unique()
            ]

            # Auto-cluster for large datasets to keep panning smooth
            USE_CLUSTER = len(df_geo) > 300

            if USE_CLUSTER:
                cluster = MarkerCluster(
                    name=f"● STEU ({len(df_geo)} stations)",
                    show=True,
                    options={
                        "disableClusteringAtZoom": 9,
                        "spiderfyOnMaxZoom": True,
                        "showCoverageOnHover": False,
                    },
                ).add_to(m)

            for band in present_bands:
                subset = df_geo[df_geo["obligation_band"] == band]

                fg = folium.FeatureGroup(name=f"● {band}", show=True)

                for _, row in subset.iterrows():
                    popup_html = (
                        "<div style='font-family: Arial; font-size: 12px; "
                        "min-width: 180px;'>"
                        f"<b style='font-size: 13px;'>{row.get('region', '–')}</b><br>"
                        f"<b>Département :</b> "
                        f"{row.get('Departement_nom', '–')}<br>"
                        f"<b>Tranche :</b> {band}<br>"
                        f"<b>Nature :</b> {row.get('nature_steu', '–')}<br>"
                        f"<b>Production :</b> "
                        f"{row.get('sludge_production_tms', 0) or 0:,.0f} tMS/an<br>"
                        f"<b>Retour sol :</b> "
                        f"{row.get('sludge_land_application_tms', 0) or 0:,.0f} tMS/an"
                        "</div>"
                    )

                    radius = max(3, BAND_SIZES.get(band, 7) // 2)

                    marker = folium.CircleMarker(
                        location=[row["lat"], row["lon"]],
                        radius=radius,
                        color=BAND_COLORS.get(band, "#888888"),
                        weight=1,
                        fill=True,
                        fill_color=BAND_COLORS.get(band, "#888888"),
                        fill_opacity=0.75,
                        popup=folium.Popup(popup_html, max_width=320),
                    )

                    if USE_CLUSTER:
                        marker.add_to(cluster)
                    else:
                        marker.add_to(fg)

                if not USE_CLUSTER:
                    fg.add_to(m)

            folium.LayerControl(collapsed=False, position="topright").add_to(m)

            # ── Render the map + capture click events ────────────────────────
            map_data = st_folium(
                m,
                height=700,
                returned_objects=["last_object_clicked"],
                key="folium_steu_map",
                use_container_width=True,
            )

            # ── Region click → zoom-in (triggers a rerun) ────────────────────
            if map_data and map_data.get("last_object_clicked"):
                clicked = map_data["last_object_clicked"]
                if isinstance(clicked, dict) and "properties" in clicked:
                    clicked_region = clicked["properties"].get("nom")
                    if (
                        clicked_region
                        and clicked_region != st.session_state["selected_region"]
                    ):
                        st.session_state["selected_region"] = clicked_region
                        st.rerun()
