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



def set_background(image_source: str, overlay_opacity: float = 0.0, position: str = "cover"):
    """
    Apply a background image to the Streamlit app.

    Parameters
    ----------
    image_source : str
        Local path ("images/bg.jpg") or URL ("https://...").
    overlay_opacity : float
        White overlay opacity (0–1) on top of the image to keep text readable.
        0 = no overlay, 0.3 = light wash, 0.6 = strong wash.
    position : str
        CSS background-size: "cover", "contain", or "auto".
    """
    import base64
    from pathlib import Path

    # Build the CSS `url(...)` value (local file → base64 data URI, URL → used as-is)
    if Path(image_source).is_file():
        ext = Path(image_source).suffix.lower().lstrip(".")
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png",
                "gif": "gif", "webp": "webp"}.get(ext, "jpeg")
        with open(image_source, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        src = f"data:image/{mime};base64,{data}"
    else:
        src = image_source  # assume URL

    overlay_css = ""
    if overlay_opacity > 0:
        overlay_css = f"""
        .stApp::before {{
            content: "";
            position: fixed;
            inset: 0;
            background: rgba(255, 255, 255, {overlay_opacity});
            z-index: 0;
            pointer-events: none;
        }}
        .stApp > header {{
            background-color: transparent;
        }}
        .block-container {{
            position: relative;
            z-index: 1;
        }}
        """

    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("{src}");
            background-size: {position};
            background-position: center center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        {overlay_css}
        </style>
        """,
        unsafe_allow_html=True,
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
    "Quantité incinérée (tMS/an)": "qty_incineration",
    "Quantité mise en décharge (tMS/an)": "qty_landfill",


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
    "qty_incineration",
    "qty_landfill",
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
    "qty_landfill"
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



GEOJSON_DEPARTEMENTS = {
    "01","02","03","04","05","06","07","08","09","10","11","12","13","14","15",
    "16","17","18","19","2A","2B","21","22","23","24","25","26","27","28","29",
    "30","31","32","33","34","35","36","37","38","39","40","41","42","43","44",
    "45","46","47","48","49","50","51","52","53","54","55","56","57","58","59",
    "60","61","62","63","64","65","66","67","68","69","70","71","72","73","74",
    "75","76","77","78","79","80","81","82","83","84","85","86","87","88","89",
    "90","91","92","93","94","95"
}


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
        "logo-In-Extenso.png",
        use_container_width=True,
    )
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


# ── Landing page (no file uploaded yet) ───────────────────────────────────────
if not st.session_state["analyse_triggered"]:
    # Apply background ONLY for the landing screen
    set_background("2.svg", overlay_opacity=0.55)

    # Center the welcome message on top of the background
    st.markdown(
        """
        <style>
            .landing-hero {
                text-align: center;
                padding: 4rem 1rem 2rem 1rem;
            }
            .landing-hero h1 {
                font-size: 3rem;
                color: #1D3557;
                margin-bottom: 0.5rem;
            }
            .landing-hero p {
                font-size: 1.15rem;
                color: #333;
                max-width: 720px;
                margin: 0 auto 2rem auto;
            }
        </style>
        <div class="landing-hero">
            <h1>🌊 STEU – Boues &amp; Épandage</h1>
            <p>
                Bienvenue. Importez votre fichier Excel dans le panneau de gauche,
                puis cliquez sur <b>« Analyser le document »</b> pour explorer vos données
                de stations d'épuration et d'épandage.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info("📥 Veuillez importer un fichier Excel pour commencer.", icon="ℹ️")
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
MAP_QTY_COLS = ["unite_methanisation", "qty_epandage", "qty_compostage", "qty_incineration", "qty_landfill"]
MAP_DEFAULT_COLORS = ["#E63946", "#1D3557", "#2A9D8F", "#F4A261", "#8338EC"]
MAP_DEFAULT_LABELS = ["Méthanisation", "Épandage", "Compostage", "Incinération", "Mise en décharge"]

GEOJSON_REGIONS = {
    "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
    "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
    "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
    "Pays de la Loire", "Provence-Alpes-Côte d'Azur",
}

# ── Helper functions (add once, near the other helpers) ──────────────────────

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


# ── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs([
    "Dashboard",
    "Analyse détaillée",
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
    st.title("Répartition selon type de traitement et localisation")

    # ══════════════════════════════════════════════════════════════════════════════
    # VIEW TOGGLE — just update session_state (Streamlit reruns automatically)
    # ══════════════════════════════════════════════════════════════════════════════
    if "map_view" not in st.session_state:
        st.session_state["map_view"] = "Région"  # default view

 

    is_dept_view = st.session_state["map_view"] == "department"

    # ══════════════════════════════════════════════════════════════════════════════
    # CUSTOMIZATION
    # ══════════════════════════════════════════════════════════════════════════════
    with st.expander("Personnalisation de la carte", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            pie_size = st.slider(
                "Taille des diagrammes (px)", 40, 220,
                80 if is_dept_view else 80, 10,
            )
            show_center = st.checkbox("Afficher le total au centre", value=True)
        with c2:
            st.markdown("**Couleurs des catégories**")
            custom_colors = []
            for i, default in enumerate(MAP_DEFAULT_COLORS):
                c = st.color_picker(f"Couleur : {MAP_DEFAULT_LABELS[i]}", default)
                custom_colors.append(c)

    # ══════════════════════════════════════════════════════════════════════════════
    # PREPARE REGION DATA
    # ══════════════════════════════════════════════════════════════════════════════
    df_map = df_filtered.copy()
    df_map[MAP_REGION_COL] = df_map[MAP_REGION_COL].apply(_normalize_region_name)

    unmatched = sorted(set(df_map[MAP_REGION_COL].dropna()) - GEOJSON_REGIONS - {None})
    if unmatched:
        with st.expander(f"⚠️ Régions non reconnues ({len(unmatched)})"):
            st.write("Ces noms seront exclus de la carte :")
            st.code(", ".join(unmatched))

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

    # ══════════════════════════════════════════════════════════════════════════════
    # PREPARE DEPARTMENT DATA
    # ══════════════════════════════════════════════════════════════════════════════
    df_dept = df_filtered.copy()
    df_dept["Departement"] = df_dept["Departement"].astype(str).apply(normalize_dept_code)
    df_dept = df_dept[df_dept["Departement"].isin(GEOJSON_DEPARTEMENTS)].copy()

    df_dept_grouped = pd.DataFrame()
    if not df_dept.empty:
        df_dept_grouped = (
            df_dept.groupby("Departement", as_index=False)[MAP_QTY_COLS].sum()
        )
        df_dept_grouped["Total"] = df_dept_grouped[MAP_QTY_COLS].sum(axis=1)

    # ══════════════════════════════════════════════════════════════════════════════
    # LOAD GEOJSONs — CACHED so heavy I/O runs once
    # ══════════════════════════════════════════════════════════════════════════════
    @st.cache_resource
    def _load_geo_resources():
        regions_geojson = load_regions_geojson()
        depts_geojson = load_departements_geojson()
        region_centroids = _compute_region_centroids(regions_geojson)
        region_bounds = compute_region_bounds(regions_geojson)
        dept_centroids, dept_bounds, dept_name_to_code = compute_geo_index(depts_geojson)
        return (regions_geojson, depts_geojson,
                region_centroids, region_bounds,
                dept_centroids, dept_bounds, dept_name_to_code)

    (regions_geojson, depts_geojson,
    region_centroids, region_bounds,
    dept_centroids, dept_bounds, dept_name_to_code) = _load_geo_resources()

    # ══════════════════════════════════════════════════════════════════════════════
    # CLICK-TO-ZOOM STATE
    # ══════════════════════════════════════════════════════════════════════════════
    if "map_selected_region" not in st.session_state:
        st.session_state["map_selected_region"] = None
    selected_region = st.session_state["map_selected_region"]

  
    # ══════════════════════════════════════════════════════════════════════════════
    # HEADER
    # ══════════════════════════════════════════════════════════════════════════════
    h_l, h_r = st.columns([6, 1])
    with h_l:
        view_label = "Départements" if is_dept_view else "Régions"
        count = len(df_dept_grouped) if is_dept_view else len(df_map_grouped)
        st.caption(f"🗺️ {count} {view_label.lower()} — {len(df_filtered):,} lignes au total")
    with h_r:
        if st.button("🔄 Reset", key="reset_map", width="stretch"):
            st.session_state["map_selected_region"] = None
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════════
    # BUILD THE MAP — both layers always present; visibility toggled via `show`
    # ══════════════════════════════════════════════════════════════════════════════
    
    m = folium.Map(
        location=[46.6, 2.3],
        zoom_start=5,
        control_scale=True,
    )


    # Click-to-zoom applies only when a region was clicked AND we are in region view
    if selected_region and not is_dept_view and selected_region in region_bounds:
        m.fit_bounds(region_bounds[selected_region], padding=[30, 30])
    # ── GeoJSON overlay (always visible) ────────────────────────────────────────
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
            style="background:#fff;border:1px solid #333;padding:4px 8px;"
                "font-family:Arial;font-size:12px;",
        ),
    ).add_to(m)

    # ── REGION pies (always added — visibility via `show`) ──────────────────────
    regions_group = folium.FeatureGroup(
        name=f"📊 Régions ({len(df_map_grouped)})",
        show=not is_dept_view,
    )

    for _, row in df_map_grouped.iterrows():
        region = row[MAP_REGION_COL]
        if region not in region_centroids:
            continue
        values = [row[c] for c in MAP_QTY_COLS]
        if sum(values) == 0:
            continue

        lat, lon = region_centroids[region]
        pie_html = _build_pie_html(values, custom_colors, size=80, show_center=show_center)

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
                icon_size=(pie_size, pie_size),
                icon_anchor=(pie_size // 2, pie_size // 2),
            ),
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{region} — Total : {sum(values):,.0f}",
        ).add_to(regions_group)

    regions_group.add_to(m)

    # ── DEPARTMENT pies (always added — visibility via `show`) ──────────────────
    depts_group = folium.FeatureGroup(
        name=f"📊 Départements ({len(df_dept_grouped)})",
        show=is_dept_view,
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
        pie_html = _build_pie_html(values, custom_colors, size=60, show_center=show_center)

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
                icon_size=(pie_size, pie_size),
                icon_anchor=(pie_size // 2, pie_size // 2),
            ),
            popup=folium.Popup(popup_html, max_width=320),
            tooltip=f"{dept_name} — Total : {sum(values):,.0f}",
        ).add_to(depts_group)

    depts_group.add_to(m)

    # ── Legend ───────────────────────────────────────────────────────────────────
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
        f'<div style="margin-top:8px;padding-top:6px;border-top:1px solid #eee;'
        f'font-size:11px;color:#888;">'
        f'Vue : <span style="font-weight:bold;color:#333;">{"Départements" if is_dept_view else "Régions"}</span>'
        f'</div>'
        f'</div>'
    )
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── LayerControl — user can also toggle layers manually from the map ─────────
# Layer control
    layer_control = folium.LayerControl(
        collapsed=False,
        position="topright",
    )
    layer_control.add_to(m)

    from folium import Element

    script = f"""
    <script>

    setTimeout(function() {{

        var map = {m.get_name()};

        map.on('overlayadd', function(e) {{

            if (e.name.startsWith("📊 Régions")) {{

                map.eachLayer(function(layer) {{
                    if (
                        layer !== e.layer &&
                        layer.options &&
                        layer.options.name &&
                        layer.options.name.startsWith("📊 Départements")
                    ) {{
                        map.removeLayer(layer);
                    }}
                }});

            }}

            if (e.name.startsWith("📊 Départements")) {{

                map.eachLayer(function(layer) {{
                    if (
                        layer !== e.layer &&
                        layer.options &&
                        layer.options.name &&
                        layer.options.name.startsWith("📊 Régions")
                    ) {{
                        map.removeLayer(layer);
                    }}
                }});

            }}

        }});

    }}, 300);

    </script>
    """

    m.get_root().html.add_child(Element(script))

    # ── Render with the SAME key (streamlit-folium preserves component state) ────
    map_data = st_folium(
        m,
        height=700,
        returned_objects=["last_object_clicked"],
        key="folium_pie_map_tab2",
        width="stretch",
    )

    # ── Persist view state for the next rerun ───────────────────────────────────
    if map_data and map_data.get("center") and map_data.get("zoom") is not None:
        c = map_data["center"]
        


    # -----------------
    # BARCHART : the following plot is a bar chart that shows the distribution of quantities by region. 
    # -----------------

        # --- Constants ---
    REGION_COL = "region"
    QTY_COLS = [
        "unite_methanisation",
        "qty_epandage",
        "qty_compostage",
        "qty_incineration",
        "qty_landfill"
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
  

    df = df[[c for c in REQUIRED_COLS if c in df.columns]]

    # --- Validate Columns ---
    missing_cols = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing_cols:
        st.error(f"❌ Missing required columns: {missing_cols}")
        st.stop()

    # --- Display Raw Data ---
    with st.expander("📋 View Raw Data"):
        st.dataframe(df, use_container_width=True)

    # --- Sidebar Customization ---
    st.sidebar.header("🎨 Chart Customization")
    color1 = st.sidebar.selectbox(f"Color: Méthanisation", list(COLORS_OPTIONS), index=0, key="c1")
    color2 = st.sidebar.selectbox(f"Color: Épandage", list(COLORS_OPTIONS), index=1, key="c2")
    color3 = st.sidebar.selectbox(f"Color: Compostage", list(COLORS_OPTIONS), index=2, key="c3")
    color4 = st.sidebar.selectbox(f"Color: Incinération", list(COLORS_OPTIONS), index=3, key="c4")
    color5 = st.sidebar.selectbox(f"Color: Décharge", list(COLORS_OPTIONS), index=4, key="c5")

    colors = [COLORS_OPTIONS[color1], COLORS_OPTIONS[color2], COLORS_OPTIONS[color3], COLORS_OPTIONS[color4], COLORS_OPTIONS[color5]]

    fig_width = st.sidebar.slider("Figure Width", 8, 20, 12)
    fig_height = st.sidebar.slider("Figure Height", 4, 12, 6)
    show_grid = st.sidebar.checkbox("Show Grid", value=False)
    show_values = st.sidebar.checkbox("Show Values on Bars", value=False)
    show_total = st.sidebar.checkbox("Show Total on Top", value=False)

    st.sidebar.header("🔃 Trier")
    sort_options = [REGION_COL, "Total"] + QTY_COLS
    sort_by = st.sidebar.selectbox("Sort by", sort_options)
    sort_asc = st.sidebar.checkbox("Ascending order", value=True)

    # --- Process Data (Cached) ---
    @st.cache_data
    def process_data(data: pd.DataFrame, sort_col: str, ascending: bool) -> pd.DataFrame:
        grouped = data.groupby(REGION_COL, as_index=False)[QTY_COLS].sum()
        if sort_col == "Total":
            grouped["__total__"] = grouped[QTY_COLS].sum(axis=1)
            grouped = grouped.sort_values("__total__", ascending=ascending).drop(columns="__total__")
        else:
            grouped = grouped.sort_values(sort_col, ascending=ascending)
        return grouped.reset_index(drop=True)

    df_grouped = process_data(df, sort_by, sort_asc)

    DISPLAY_COLS = {"unite_methanisation": "Méthanisation",
                     "qty_epandage": "Épandage",
                     "qty_compostage": "Compostage",
                     "qty_incineration": "Incinération", 
                     "qty_landfill": "Décharge"}
    
    # --- Build Chart ---
    fig = go.Figure()
    for i, (col, name) in enumerate(DISPLAY_COLS.items()):
        text_vals = df_grouped[col].astype(int).astype(str) if show_values else None
        fig.add_trace(go.Bar(
            name=name,
            x=df_grouped[REGION_COL],
            y=df_grouped[col],
            marker_color=colors[i],
            text=text_vals,
            textposition='inside' if show_values else None,
        ))

    # Add totals on top
    if show_total:
        totals = df_grouped[QTY_COLS].sum(axis=1)
        fig.add_trace(go.Scatter(
            x=df_grouped[REGION_COL],
            y=totals,
            mode='text',
            text=totals.astype(int).astype(str),
            textposition='top center',
            showlegend=False,
            hoverinfo='skip'
        ))

    fig.update_layout(
        barmode='stack',
        xaxis_title="Region",
        yaxis_title="Quantity Level",
        width=fig_width * 100,  # convert slider units to px (rough)
        height=fig_height * 100,
        hovermode="x unified",
        xaxis=dict(showgrid=show_grid),
        yaxis=dict(showgrid=show_grid),
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Summary Metrics ---
    st.subheader("📈 Summary Statistics")
    totals = df_grouped[QTY_COLS].sum()
    cols = st.columns(len(QTY_COLS) + 1)
    for i, col_name in enumerate(QTY_COLS):
        cols[i].metric(col_name, f"{totals[col_name]:.0f}")
    cols[-1].metric("Grand Total", f"{totals.sum():.0f}")
