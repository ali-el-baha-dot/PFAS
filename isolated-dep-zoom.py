import io
import json
import urllib.request
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium





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


# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Carte des départements", page_icon="🗺️", layout="wide")

# ── Constants ─────────────────────────────────────────────────────────────────





NUMERIC_COLS = ["unite_methanisation", "qty_epandage", "qty_compostage"]

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



DEPARTEMENT_NAMES = {
    "01": "Ain", "02": "Aisne", "03": "Allier", "04": "Alpes-de-Haute-Provence", "05": "Hautes-Alpes", "06": "Alpes-Maritimes", "07": "Ardèche", "08": "Ardennes", "09": "Ariège",
    "10": "Aube","11": "Aude","12": "Aveyron","13": "Bouches-du-Rhône","14": "Calvados","15": "Cantal","16": "Charente","17": "Charente-Maritime","18": "Cher","19": "Corrèze",
    "21": "Côte-d'Or","22": "Côtes-d'Armor","23": "Creuse","24": "Dordogne","25": "Doubs","26": "Drôme","27": "Eure","28": "Eure-et-Loir","29": "Finistère","2A": "Corse-du-Sud",
    "2B": "Haute-Corse","30": "Gard","31": "Haute-Garonne","32": "Gers","33": "Gironde","34": "Hérault","35": "Ille-et-Vilaine","36": "Indre","37": "Indre-et-Loire","38": "Isère",
    "39": "Jura","40": "Landes","41": "Loir-et-Cher","42": "Loire","43": "Haute-Loire","44": "Loire-Atlantique","45": "Loiret","46": "Lot","47": "Lot-et-Garonne","48": "Lozère",
    "49": "Maine-et-Loire","50": "Manche","51": "Marne","52": "Haute-Marne","53": "Mayenne","54": "Meurthe-et-Moselle","55": "Meuse","56": "Morbihan","57": "Moselle","58": "Nièvre",
    "59": "Nord","60": "Oise","61": "Orne","62": "Pas-de-Calais","63": "Puy-de-Dôme","64": "Pyrénées-Atlantiques", "65": "Hautes-Pyrénées", "66": "Pyrénées-Orientales","67": "Bas-Rhin",
    "68": "Haut-Rhin","69": "Rhône","70": "Haute-Saône","71": "Saône-et-Loire","72": "Sarthe","73": "Savoie","74": "Haute-Savoie","75": "Paris","76": "Seine-Maritime","77": "Seine-et-Marne",
    "78": "Yvelines","79": "Deux-Sèvres","80": "Somme","81": "Tarn","82": "Tarn-et-Garonne","83": "Var","84": "Vaucluse","85": "Vendée","86": "Vienne","87": "Haute-Vienne","88": "Vosges",
    "89": "Yonne","90": "Territoire de Belfort","91": "Essonne","92": "Hauts-de-Seine","93": "Seine-Saint-Denis","94": "Val-de-Marne","95": "Val-d'Oise","971": "Guadeloupe","972": "Martinique",
    "973": "Guyane","974": "La Réunion","976": "Mayotte",
}

MAP_REGION_COL = "region"
MAP_DEPT_COL = "Departement_nom"
MAP_QTY_COLS = ["unite_methanisation", "qty_epandage", "qty_compostage"]
MAP_DEFAULT_COLORS = ["#E63946", "#1D3557", "#2A9D8F"]
MAP_DEFAULT_LABELS = ["Méthanisation", "Épandage", "Compostage"]

GEOJSON_DEPARTEMENTS = {
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15",
    "16","17","18","19","2A","2B","21","22","23","24","25","26","27","28","29",
    "30","31","32","33","34","35","36","37","38","39","40","41","42","43","44",
    "45","46","47","48","49","50","51","52","53","54","55","56","57","58","59",
    "60","61","62","63","64","65","66","67","68","69","70","71","72","73","74",
    "75","76","77","78","79","80","81","82","83","84","85","86","87","88","89",
    "90","91","92","93","94","95"
}


GEOJSON_REGIONS = {
    "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
    "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
    "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
    "Pays de la Loire", "Provence-Alpes-Côte d'Azur",
}

# ── Band config (single source of truth) ─────────────────────────────────────
BAND_ORDER = [
    "Taille < 200 EH",
    "[ 200 ; 2 000 [ EH",
    "[ 2 000 ; 10 000 [ EH",
    "[ 10 000 ; 100 000 [ E",
    "[ 100 000 ; ... [ EH",
]




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

    if "Departement" in df.columns:
        df["Departement"] = df["Departement"].astype(str).str.strip()
        df["Departement"] = df["Departement"].replace({"nan": pd.NA, "": pd.NA})
        df["Departement_nom"] = df["Departement"].map(DEPARTEMENT_NAMES).fillna(df["Departement"])

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

    return df, regional, kpis          # ← was buried inside load_departements_geojson

@st.cache_data
def compute_geo_index(geojson):
    centroids, bounds, name_to_code = {}, {}, {}
    for f in geojson["features"]:
        props = f["properties"]
        code = str(props.get("code"))
        name = props.get("nom")
        geom = f["geometry"]
        coords = geom["coordinates"][0] if geom["type"] == "Polygon" else [c for poly in geom["coordinates"] for c in poly[0]]
        if coords:
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            centroids[code] = (sum(lats) / len(lats), sum(lons) / len(lons))
            bounds[code] = [[min(lats), min(lons)], [max(lats), max(lons)]]
        if name:
            name_to_code[name] = code
    return centroids, bounds, name_to_code

@st.cache_data(show_spinner="Chargement des contours…")
def load_departements_geojson():
    url = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson"
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read())



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



# ── Helper functions (add once, near the other helpers) ──────────────────────


# ── Helpers ───────────────────────────────────────────────────────────────────
def normalize_dept_code(code):
    code = str(code).strip().upper()
    if code in ["2A", "2B"]:
        return code
    return code.zfill(2) if code.isdigit() else code



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












# ══════════════════════════════════════════════════════════════════════
# MERGED MAP — Régions (zoom < 7) + Départements (zoom ≥ 7)
# ══════════════════════════════════════════════════════════════════════

# ── New variable ───────────────────────────────────────────────────────────
ZOOM_THRESHOLD = 7          # below → region pies visible; at/above → dept pies

# ── Customization (shared panel) ──────────────────────────────────────────
with st.expander("Personnalisation de la carte", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        pie_size_region = st.slider("Taille des camemberts — Régions (px)", 80, 220, 130, 10)
        pie_size_dept   = st.slider("Taille des camemberts — Départements (px)", 40, 120, 70, 10)
        show_center = st.checkbox("Afficher le total au centre", value=True)
    with c2:
        st.markdown("**Couleurs des catégories**")
        custom_colors = []
        for i, default in enumerate(MAP_DEFAULT_COLORS):
            c = st.color_picker(f"Couleur : {MAP_DEFAULT_LABELS[i]}", default)
            custom_colors.append(c)

# ── Prepare REGION data ───────────────────────────────────────────────────
df_map = df_filtered.copy()
df_map[MAP_REGION_COL] = df_map[MAP_REGION_COL].apply(_normalize_region_name)
df_map = df_map[df_map[MAP_REGION_COL].isin(GEOJSON_REGIONS)].copy()

if df_map.empty:
    st.error("❌ Aucune région compatible avec le GeoJSON après normalisation.")
    st.stop()

df_map_grouped = (
    df_map.groupby(MAP_REGION_COL, as_index=False)[MAP_QTY_COLS]
    .sum()
    .sort_values(MAP_QTY_COLS[0], ascending=False)
    .reset_index(drop=True)
)
df_map_grouped["Total"] = df_map_grouped[MAP_QTY_COLS].sum(axis=1)

# ── Prepare DEPARTMENT data ───────────────────────────────────────────────
df_dept = df_filtered.copy()

# Use the raw code column, not the name column
df_dept["Departement"] = df_dept["Departement"].astype(str).apply(normalize_dept_code)
df_dept = df_dept[df_dept["Departement"].isin(GEOJSON_DEPARTEMENTS)].copy()

df_dept_grouped = pd.DataFrame()
if not df_dept.empty:
    df_dept_grouped = (
        df_dept.groupby("Departement", as_index=False)[MAP_QTY_COLS].sum()
    )
    df_dept_grouped["Total"] = df_dept_grouped[MAP_QTY_COLS].sum(axis=1)

# ── Load GeoJSONs ─────────────────────────────────────────────────────────
try:
    regions_geojson = load_regions_geojson()
except Exception as e:
    st.error(f"Impossible de charger les contours de régions : {e}")
    st.stop()

try:
    depts_geojson = load_departements_geojson()
except Exception as e:
    st.error(f"Impossible de charger les contours de départements : {e}")
    st.stop()

region_centroids = _compute_region_centroids(regions_geojson)
region_bounds    = compute_region_bounds(regions_geojson)
dept_centroids, dept_bounds, dept_name_to_code = compute_geo_index(depts_geojson)

# ── Session state ─────────────────────────────────────────────────────────
if "map_selected_region" not in st.session_state:
    st.session_state["map_selected_region"] = None

selected_region = st.session_state["map_selected_region"]

# ── Header row ────────────────────────────────────────────────────────────
h_l, h_r = st.columns([6, 1])
with h_l:
    if selected_region:
        st.info(f"📍 Vue active : **{selected_region}**")
    else:
        st.caption(
            f"🗺️ {len(df_map_grouped)} régions — "
            f"zoom ≥ {ZOOM_THRESHOLD} pour afficher les départements"
        )
with h_r:
    if st.button("🔄 Reset", key="reset_map_merged", use_container_width=True):
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

# ── GeoJSON overlays ──────────────────────────────────────────────────────
folium.GeoJson(
    regions_geojson,
    name="Contours régions",
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
    ),
).add_to(m)

folium.GeoJson(
    depts_geojson,
    name="Contours départements",
    style_function=lambda f: {
        "fillColor": "#ffffff", "color": "#666666",
        "weight": 1.0, "fillOpacity": 0.06,
    },
    highlight_function=lambda f: {
        "fillColor": "#ffcc00", "color": "#000000",
        "weight": 2.0, "fillOpacity": 0.35,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["nom"], aliases=["Département :"], sticky=False,
    ),
).add_to(m)

# ── Region pie FeatureGroup (visible by default) ──────────────────────────
region_pie_group = folium.FeatureGroup(
    name="Camemberts — Régions", show=True
)

for _, row in df_map_grouped.iterrows():
    region = row[MAP_REGION_COL]
    if region not in region_centroids:
        continue
    values = [row[c] for c in MAP_QTY_COLS]
    if sum(values) == 0:
        continue

    lat, lon = region_centroids[region]
    pie_html = _build_pie_html(values, custom_colors, size=pie_size_region, show_center=show_center)

    rows_html = ""
    for label, val, col in zip(MAP_DEFAULT_LABELS, values, custom_colors):
        pct = val / sum(values) * 100 if sum(values) else 0
        rows_html += (
            f'<tr>'
            f'<td style="padding:3px 8px;">'
            f'<span style="display:inline-block;width:10px;height:10px;'
            f'background:{col};border-radius:2px;margin-right:6px;"></span>{label}'
            f'</td>'
            f'<td style="padding:3px 8px;text-align:right;"><b>{val:,.0f}</b></td>'
            f'<td style="padding:3px 8px;text-align:right;color:#666;">{pct:.1f}%</td>'
            f'</tr>'
        )
    popup_html = (
        f'<div style="font-family:Arial;font-size:12px;min-width:240px;">'
        f'<div style="font-size:14px;font-weight:bold;margin-bottom:6px;'
        f'border-bottom:1px solid #ddd;padding-bottom:4px;">{region}</div>'
        f'<table style="width:100%;border-collapse:collapse;">{rows_html}</table>'
        f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid #ddd;'
        f'text-align:right;font-weight:bold;">Total : {sum(values):,.0f}</div>'
        f'</div>'
    )

    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=f"<div style='cursor:pointer;'>{pie_html}</div>",
            icon_size=(pie_size_region, pie_size_region),
            icon_anchor=(pie_size_region // 2, pie_size_region // 2),
        ),
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f" {region} — Total : {sum(values):,.0f}",
    ).add_to(region_pie_group)

region_pie_group.add_to(m)

# ── Department pie FeatureGroup (hidden by default) ───────────────────────
dept_pie_group = folium.FeatureGroup(
    name="Camemberts — Départements", show=False   # hidden at start
)

for _, row in df_dept_grouped.iterrows():
    code = str(row["Departement"])
    if code not in dept_centroids:
        continue
    values = [row[c] for c in MAP_QTY_COLS]
    if sum(values) == 0:
        continue

    lat, lon = dept_centroids[code]
    dept_name = DEPARTEMENT_NAMES.get(code, code)
    pie_html  = _build_pie_html(values, custom_colors, size=pie_size_dept, show_center=show_center)

    rows_html = "".join(
        f'<tr>'
        f'<td style="padding:3px 8px;">'
        f'<span style="display:inline-block;width:10px;height:10px;'
        f'background:{col};border-radius:2px;margin-right:6px;"></span>{lbl}'
        f'</td>'
        f'<td style="padding:3px 8px;text-align:right;"><b>{v:,.0f}</b></td>'
        f'<td style="padding:3px 8px;text-align:right;color:#666;">{v/sum(values)*100:.1f}%</td>'
        f'</tr>'
        for lbl, v, col in zip(MAP_DEFAULT_LABELS, values, custom_colors)
    )
    popup_html = (
        f'<div style="font-family:Arial;font-size:12px;min-width:240px;">'
        f'<div style="font-size:14px;font-weight:bold;margin-bottom:6px;'
        f'border-bottom:1px solid #ddd;padding-bottom:4px;">{dept_name} — Répartition</div>'
        f'<table style="width:100%;border-collapse:collapse;">{rows_html}</table>'
        f'<div style="margin-top:6px;padding-top:6px;border-top:1px solid #ddd;'
        f'text-align:right;font-weight:bold;">Total : {sum(values):,.0f}</div>'
        f'</div>'
    )

    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(
            html=f"<div style='cursor:pointer;'>{pie_html}</div>",
            icon_size=(pie_size_dept, pie_size_dept),
            icon_anchor=(pie_size_dept // 2, pie_size_dept // 2),
        ),
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f" {dept_name} — Total : {sum(values):,.0f}",
    ).add_to(dept_pie_group)

dept_pie_group.add_to(m)

# ── Legend ────────────────────────────────────────────────────────────────
legend_items = "".join(
    f'<div style="display:flex;align-items:center;margin:3px 0;">'
    f'<span style="display:inline-block;width:14px;height:14px;background:{c};'
    f'border-radius:3px;margin-right:8px;border:1px solid #333;"></span>'
    f'<span style="font-size:12px;">{lbl}</span></div>'
    for lbl, c in zip(MAP_DEFAULT_LABELS, custom_colors)
)
legend_html = (
    f'<div style="position:fixed;top:15px;left:55px;z-index:9999;background:white;'
    f'padding:10px 12px;border:2px solid #333;border-radius:6px;'
    f'box-shadow:0 2px 6px rgba(0,0,0,0.3);font-family:Arial;max-width:220px;">'
    f'<div style="font-weight:bold;font-size:12px;margin-bottom:6px;'
    f'border-bottom:1px solid #ddd;padding-bottom:4px;">Catégories</div>'
    f'{legend_items}'
    f'<div id="zoom-indicator" style="margin-top:8px;padding-top:6px;'
    f'border-top:1px solid #eee;font-size:11px;color:#888;">'
    f'Vue : <span id="zoom-label" style="font-weight:bold;color:#333;">Régions</span>'
    f'</div>'
    f'</div>'
)
m.get_root().html.add_child(folium.Element(legend_html))

# ── Zoom-based toggle JS ──────────────────────────────────────────────────
# New variable: ZOOM_THRESHOLD drives the JS below.
# Layer names must exactly match the `name=` arguments used above.

zoom_js = f"""
<script>
(function () {{
    var THRESHOLD = {ZOOM_THRESHOLD};

    /* Wait until the Leaflet map object is ready */
    function init() {{
        /* st_folium renders into an iframe; the map variable is `map_<id>`.
           We iterate window keys to find the first L.Map instance. */
        var mapObj = null;
        Object.keys(window).forEach(function(k) {{
            if (window[k] && window[k]._leaflet_id !== undefined
                    && typeof window[k].getZoom === 'function') {{
                mapObj = window[k];
            }}
        }});

        if (!mapObj) {{
            setTimeout(init, 300);
            return;
        }}

        /* Collect the two FeatureGroup layers by their name attribute */
        var regionLayer = null;
        var deptLayer   = null;
        mapObj.eachLayer(function(l) {{
            if (l.options && l.options.name === "Camemberts \u2014 R\u00e9gions") {{
                regionLayer = l;
            }}
            if (l.options && l.options.name === "Camemberts \u2014 D\u00e9partements") {{
                deptLayer = l;
            }}
        }});

        if (!regionLayer || !deptLayer) {{
            setTimeout(init, 300);
            return;
        }}

        function applyZoom() {{
            var z = mapObj.getZoom();
            var label = document.getElementById('zoom-label');
            if (z >= THRESHOLD) {{
                if (!mapObj.hasLayer(deptLayer))   mapObj.addLayer(deptLayer);
                if (mapObj.hasLayer(regionLayer))  mapObj.removeLayer(regionLayer);
                if (label) {{ label.textContent = 'D\u00e9partements'; label.style.color='#1a6bb5'; }}
            }} else {{
                if (!mapObj.hasLayer(regionLayer)) mapObj.addLayer(regionLayer);
                if (mapObj.hasLayer(deptLayer))    mapObj.removeLayer(deptLayer);
                if (label) {{ label.textContent = 'R\u00e9gions'; label.style.color='#333'; }}
            }}
        }}

        mapObj.on('zoomend', applyZoom);
        applyZoom();   /* apply immediately on load */
    }}

    /* st_folium injects its iframe a bit after page load */
    setTimeout(init, 800);
}})();
</script>
"""
m.get_root().html.add_child(folium.Element(zoom_js))

folium.LayerControl(collapsed=False, position="topright").add_to(m)

# ── Render ────────────────────────────────────────────────────────────────
map_data = st_folium(
    m, height=700,
    returned_objects=["last_object_clicked"],
    key="folium_merged_map",
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