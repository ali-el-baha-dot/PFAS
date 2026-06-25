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
import unicodedata
import re


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

    # ── NEW: the 3 category columns used by the map ────────────────────────
    "Unité de méthanisation": "unite_methanisation",
    "Quantité épandage agricole (tMS/an)": "qty_epandage",
    "Quantité Compostage «produit» (tMS/an)": "qty_compostage",
}


NUMERIC_COLS = [
    "x_coord",
    "y_coord",
    "sludge_production_tms",
    "sludge_no_reagent_tms",
    "sludge_land_application_tms",

    # ── NEW ────────────────────────────────────────────────────────────────
    "unite_methanisation",
    "qty_epandage",
    "qty_compostage",
]


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


# --- Constants ---
REGION_COL = "Nom de la région"
QTY_COLS = [                                # ← matches display_df
    "Méthanisation (tMS/an)",
    "Épandage (tMS/an)",
    "Compostage (tMS/an)",
]
REQUIRED_COLS = [REGION_COL] + QTY_COLS
COLORS_OPTIONS = {
    "Red": "#E63946",
    "Blue": "#1D3557",
    "Green": "#2A9D8F",
    "Orange": "#F4A261",
    "Purple": "#8338EC",
    "Yellow": "#FFB703",
    "Pink": "#FF6B9D",
    "Teal": "#06A77D"
}


# ── Session state ─────────────────────────────────────────────────────────────
if "analyse_triggered" not in st.session_state:
    st.session_state["analyse_triggered"] = False

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.sidebar.image(
        "logo.jpg",               # path to your logo file (or URL)
        use_container_width=True, # fills the sidebar width
        # width=180,              # OR set a fixed width in pixels
    )

    st.title("Analyse des données")
    st.markdown("Veuillez importer un fichier Excel pour commencer l'analyse.")
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
    st.caption("informations : stations · Épandage · Géolocalisation")


if not st.session_state["analyse_triggered"]:
    st.info(" Veuillez importer un fichier Excel ")
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

# ── Map constants (tab2) ─────────────────────────────────────────────────────
MAP_REGION_COL = "region"
MAP_QTY_COLS = ["unite_methanisation", "qty_epandage", "qty_compostage"]
MAP_DEFAULT_COLORS = ["#E63946", "#1D3557", "#2A9D8F"]
MAP_DEFAULT_LABELS = ["Méthanisation", "Épandage", "Compostage"]

GEOJSON_REGIONS = {
    "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
    "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
    "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
    "Pays de la Loire", "Provence-Alpes-Côte d'Azur",
}

# ── Helper functions (add once, near the other helpers) ──────────────────────
def _normalize_region_name(name):
    """Convert any region-name variant to the canonical form used in the GeoJSON."""
    if pd.isna(name):
        return None
    s = str(name).strip().upper()
    s = re.sub(r"[-_'/]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    CANONICAL = {
        "AUVERGNE RHONE ALPES":          "Auvergne-Rhône-Alpes",
        "BOURGOGNE FRANCHE COMTE":       "Bourgogne-Franche-Comté",
        "BRETAGNE":                      "Bretagne",
        "CENTRE VAL DE LOIRE":           "Centre-Val de Loire",
        "CORSE":                         "Corse",
        "GRAND EST":                     "Grand Est",
        "HAUTS DE FRANCE":               "Hauts-de-France",
        "ILE DE FRANCE":                 "Île-de-France",
        "NORMANDIE":                     "Normandie",
        "NOUVELLE AQUITAINE":            "Nouvelle-Aquitaine",
        "OCCITANIE":                     "Occitanie",
        "PAYS DE LA LOIRE":              "Pays de la Loire",
        "PROVENCE ALPES COTE D AZUR":    "Provence-Alpes-Côte d'Azur",
        "GUADELOUPE": None, "MARTINIQUE": None, "GUYANE": None,
        "REUNION": None, "MAYOTTE": None,
        "OUTRE MERS": None, "OUTRE MER": None,
        "DOM TOM": None, "DROM COM": None,
    }
    return CANONICAL.get(s, s.title())


@st.cache_data(show_spinner=False)
def _compute_region_centroids(geojson: dict) -> dict:
    centroids = {}
    for feature in geojson["features"]:
        name = feature["properties"].get("nom")
        geom = feature["geometry"]
        coords = []
        if geom["type"] == "Polygon":
            coords = geom["coordinates"][0]
        elif geom["type"] == "MultiPolygon":
            for poly in geom["coordinates"]:
                coords.extend(poly[0])
        if not coords:
            continue
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        centroids[name] = (sum(lats) / len(lats), sum(lons) / len(lons))
    return centroids


def _build_pie_html(values, colors, size=130, show_center=True) -> str:
    total = sum(values)
    if total <= 0:
        return f"""
        <div style="width:{size}px;height:{size}px;border-radius:50%;
                    background:#eee;border:3px solid #888;
                    display:flex;align-items:center;justify-content:center;
                    font-size:11px;color:#666;">N/A</div>
        """
    stops, cumulative = [], 0
    for v, c in zip(values, colors):
        pct = v / total * 100
        stops.append(f"{c} {cumulative:.2f}%")
        cumulative += pct
        stops.append(f"{c} {cumulative:.2f}%")
    gradient = ", ".join(stops)

    center_html = ""
    if show_center:
        center_html = f"""
        <div style="
            position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);
            background:white;width:42%;height:42%;border-radius:50%;
            display:flex;flex-direction:column;align-items:center;
            justify-content:center;font-family:Arial;
            box-shadow:inset 0 0 4px rgba(0,0,0,0.15);
        ">
            <div style="font-size:9px;color:#666;line-height:1;">Total</div>
            <div style="font-size:13px;font-weight:bold;color:#222;line-height:1.1;">
                {total:,.0f}
            </div>
        </div>
        """
    return f"""
    <div style="
        position:relative;width:{size}px;height:{size}px;
        background:conic-gradient({gradient});
        border-radius:50%;
        border:3px solid white;
        box-shadow:0 3px 8px rgba(0,0,0,0.35);
    ">{center_html}</div>
    """


# ── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "Dashboard",
    "Carte dupliquée 2",
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
    st.title("app")
    st.caption(
        "Chaque diagramme circulaire représente la proportion des 3 catégories "
        "pour la région. Cliquez sur un diagramme pour voir le détail."
    )

    # ── Customization ───────────────────────────────────────────────────────
    with st.expander("Personnalisation de la carte", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            pie_size = st.slider("Taille des diagrammes (px)", 80, 220, 130, 10)
            show_center = st.checkbox("Afficher le total au centre", value=True)
        with c2:
            st.markdown("**Couleurs des catégories**")
            custom_colors = []
            for i, default in enumerate(MAP_DEFAULT_COLORS):
                c = st.color_picker(
                    f"Couleur : {MAP_DEFAULT_LABELS[i]}", default
                )
                custom_colors.append(c)

    # ── Prepare data: normalize names + filter to metropolitan regions ──────
    df_map = df_filtered.copy()
    df_map[MAP_REGION_COL] = df_map[MAP_REGION_COL].apply(_normalize_region_name)

    # Show unmatchable names BEFORE filtering
    unmatched = sorted(
        set(df_map[MAP_REGION_COL].dropna()) - GEOJSON_REGIONS - {None}
    )
    if unmatched:
        with st.expander(f"⚠️ Régions non reconnues ({len(unmatched)})"):
            st.write("Ces noms seront exclus de la carte :")
            st.code(", ".join(unmatched))
            st.caption(
                "💡 Si une région française métropolitaine manque ici, "
                "ajoutez son mapping dans `CANONICAL`."
            )

    df_map = df_map[df_map[MAP_REGION_COL].isin(GEOJSON_REGIONS)].copy()

    if df_map.empty:
        st.error("❌ Aucune région compatible avec le GeoJSON après normalisation.")
        st.stop()

    # Group & aggregate
    df_map_grouped = (
        df_map.groupby(MAP_REGION_COL, as_index=False)[MAP_QTY_COLS]
        .sum()
        .sort_values(MAP_QTY_COLS[0], ascending=False)
        .reset_index(drop=True)
    )
    df_map_grouped["Total"] = df_map_grouped[MAP_QTY_COLS].sum(axis=1)

    # ── Load regions GeoJSON ────────────────────────────────────────────────
    try:
        regions_geojson = load_regions_geojson()
    except Exception as e:
        st.error(f"Impossible de charger les contours de régions : {e}")
        st.stop()

    region_centroids = _compute_region_centroids(regions_geojson)
    region_bounds = compute_region_bounds(regions_geojson)  # already defined in main.py

    # ── Matching diagnostics ───────────────────────────────────────────────
    with st.expander("Correspondance des noms de régions"):
        geo_regions = sorted(region_centroids.keys())
        data_regions = sorted(df_map_grouped[MAP_REGION_COL].unique())
        matched = set(geo_regions) & set(data_regions)
        st.write(f"**Régions dans le GeoJSON :** {len(geo_regions)}")
        st.write(f"**Régions reconnues dans les données :** {len(data_regions)}")
        st.success(f"Correspondances : {len(matched)}")
        unmatched_data = set(data_regions) - set(geo_regions)
        if unmatched_data:
            st.warning(f"Sans contour : {sorted(unmatched_data)}")

    # ── Click-to-zoom state ────────────────────────────────────────────────
    if "map_selected_region" not in st.session_state:
        st.session_state["map_selected_region"] = None
    selected_region = st.session_state["map_selected_region"]

    # ── Header row ─────────────────────────────────────────────────────────
    h_l, h_r = st.columns([6, 1])
    with h_l:
        if selected_region:
            st.info(f"📍 Vue active : **{selected_region}**")
        else:
            st.caption(
                f"🗺️ {len(df_map_grouped)} régions — "
                f"{len(df_map):,} lignes au total"
            )
    with h_r:
        if st.button("🔄 Reset", key="reset_map", use_container_width=True):
            st.session_state["map_selected_region"] = None
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # BUILD THE FOLIUM MAP
    # ══════════════════════════════════════════════════════════════════════
    m = folium.Map(
        location=[46.6, 2.3],
        zoom_start=5,
        tiles="cartodbpositron",
        control_scale=True,
    )

    if selected_region and selected_region in region_bounds:
        m.fit_bounds(region_bounds[selected_region], padding=[30, 30])

    # ── Region overlay ────────────────────────────────────────────────────
    folium.GeoJson(
        regions_geojson,
        name="Régions",
        style_function=lambda f: {
            "fillColor": "#ffffff", "color": "#333333",
            "weight": 1.5, "fillOpacity": 0.08,
        },
        highlight_function=lambda f: {
            "fillColor": "#ffcc00", "color": "#000000",
            "weight": 2.5, "fillOpacity": 0.4,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nom"], aliases=["Région :"], sticky=False,
            style="background:#fff;border:1px solid #333;padding:4px 8px;"
                  "font-family:Arial;font-size:12px;",
        ),
    ).add_to(m)

    # ── Pie chart markers ─────────────────────────────────────────────────
    pie_group = folium.FeatureGroup(
        name="Répartition par région", show=True
    )

    for _, row in df_map_grouped.iterrows():
        region = row[MAP_REGION_COL]
        if region not in region_centroids:
            continue

        values = [row[c] for c in MAP_QTY_COLS]
        if sum(values) == 0:
            continue

        lat, lon = region_centroids[region]
        pie_html = _build_pie_html(
            values, custom_colors, size=pie_size, show_center=show_center
        )

        rows_html = ""
        for label, val, col in zip(MAP_DEFAULT_LABELS, values, custom_colors):
            pct = val / sum(values) * 100 if sum(values) else 0
            rows_html += f"""
            <tr>
                <td style="padding:3px 8px;">
                    <span style="display:inline-block;width:10px;height:10px;
                                 background:{col};border-radius:2px;margin-right:6px;">
                    </span>{label}
                </td>
                <td style="padding:3px 8px;text-align:right;">
                    <b>{val:,.0f}</b>
                </td>
                <td style="padding:3px 8px;text-align:right;color:#666;">
                    {pct:.1f}%
                </td>
            </tr>
            """
        popup_html = f"""
        <div style="font-family:Arial;font-size:12px;min-width:240px;">
            <div style="font-size:14px;font-weight:bold;margin-bottom:6px;
                        border-bottom:1px solid #ddd;padding-bottom:4px;">
                {region}
            </div>
            <table style="width:100%;border-collapse:collapse;">{rows_html}</table>
            <div style="margin-top:6px;padding-top:6px;border-top:1px solid #ddd;
                        text-align:right;font-weight:bold;">
                Total : {sum(values):,.0f}
            </div>
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            icon=folium.DivIcon(
                html=f"<div style='cursor:pointer;'>{pie_html}</div>",
                icon_size=(pie_size, pie_size),
                icon_anchor=(pie_size // 2, pie_size // 2),
            ),
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f" {region} — Total : {sum(values):,.0f}",
        ).add_to(pie_group)

    pie_group.add_to(m)

    # ── Fixed HTML legend ─────────────────────────────────────────────────
    legend_items = "".join(
        f"""
        <div style="display:flex;align-items:center;margin:3px 0;">
            <span style="display:inline-block;width:14px;height:14px;
                         background:{c};border-radius:3px;margin-right:8px;
                         border:1px solid #333;"></span>
            <span style="font-size:12px;">{lbl}</span>
        </div>
        """
        for lbl, c in zip(MAP_DEFAULT_LABELS, custom_colors)
    )
    legend_html = f"""
    <div style="
        position:fixed; top:15px; left:55px; z-index:9999;
        background:white; padding:10px 12px; border:2px solid #333;
        border-radius:6px; box-shadow:0 2px 6px rgba(0,0,0,0.3);
        font-family:Arial; max-width:220px;
    ">
        <div style="font-weight:bold;font-size:12px;margin-bottom:6px;
                    border-bottom:1px solid #ddd;padding-bottom:4px;">
            Catégories
        </div>
        {legend_items}
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # ══════════════════════════════════════════════════════════════════════
    # RENDER + INTERACTION
    # ══════════════════════════════════════════════════════════════════════
    map_data = st_folium(
        m, height=700,
        returned_objects=["last_object_clicked"],
        key="folium_pie_map_tab2",
        use_container_width=True,
    )

    if map_data and map_data.get("last_object_clicked"):
        clicked = map_data["last_object_clicked"]
        if isinstance(clicked, dict) and "properties" in clicked:
            clicked_region = clicked["properties"].get("nom")
            if (
                clicked_region
                and clicked_region != st.session_state["map_selected_region"]
            ):
                st.session_state["map_selected_region"] = clicked_region
                st.rerun()

    