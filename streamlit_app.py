from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from spectra_core import (
    SITE_AMPLIFICATION,
    USER_CITY_LABEL,
    ZONE_FACTORS,
    calculate_spectra,
    load_city_coordinates,
    load_hazard_data,
    results_rows,
)


st.set_page_config(
    page_title="RTGM and IS Code Spectra Calculator",
    layout="wide",
)


@st.cache_resource(show_spinner="Loading hazard dataset...")
def cached_hazard_data():
    return load_hazard_data()


@st.cache_data(show_spinner=False)
def cached_city_coordinates():
    return load_city_coordinates()


def build_plot(city, results):
    fig, ax = plt.subplots(figsize=(8.5, 5.0))
    ax.plot(results["periods"], results["mce"], c="r", ls="--", label="PSHA-2475yrs")
    ax.plot(results["periods"], results["is_2475"], c="r", ls="-", label="IS-2475yrs")
    ax.plot(results["periods"], results["dbe"], c="b", ls="--", label="PSHA-475yrs")
    ax.plot(results["periods"], results["is_475"], c="b", ls="-", label="IS-475yrs")
    ax.plot(results["periods"], results["rtgm"], c="k", ls="-", label="RTGM")
    ax.set_ylim(bottom=0)
    ax.set_xlim(0, 5)
    ax.grid(which="major", linestyle="-", alpha=0.5)
    ax.legend(fontsize=10)
    ax.set_xlabel("Time period (s)")
    ax.set_ylabel("Sa (g)")
    ax.set_title(city)
    fig.tight_layout()
    return fig


def dataframe_to_tsv(dataframe):
    return dataframe.to_csv(sep="\t", index=False, float_format="%.3f")


def dataframe_to_csv(dataframe):
    return dataframe.to_csv(index=False, float_format="%.3f").encode("utf-8")


def figure_to_png(fig):
    image = BytesIO()
    fig.savefig(image, format="png", dpi=300, bbox_inches="tight")
    image.seek(0)
    return image


def safe_filename(name):
    safe = "".join(char for char in name if char.isalnum() or char in (" ", "_", "-")).strip()
    return safe or "Selected_location"


city_coordinates, city_source = cached_city_coordinates()
hazard_data = cached_hazard_data()

st.title("RTGM and IS Code Spectra Calculator")

with st.sidebar:
    st.header("Inputs")

    city_options = [USER_CITY_LABEL] + sorted(city for city in city_coordinates if city != USER_CITY_LABEL)
    city = st.selectbox("City", city_options, index=0)
    city_data = city_coordinates.get(city, {})
    is_user_location = city == USER_CITY_LABEL

    if is_user_location:
        latitude_text = st.text_input("Latitude", value="")
        longitude_text = st.text_input("Longitude", value="")
        zone = st.selectbox("Zone factor", [""] + list(ZONE_FACTORS.keys()), index=0)
    else:
        latitude_text = "" if city_data.get("latitude") is None else f"{city_data['latitude']:.4f}"
        longitude_text = "" if city_data.get("longitude") is None else f"{city_data['longitude']:.4f}"
        zone = city_data["zone"] or ""
        st.text_input("Latitude", value=latitude_text, disabled=True)
        st.text_input("Longitude", value=longitude_text, disabled=True)
        zone_options = [""] + list(ZONE_FACTORS.keys())
        st.selectbox("Zone factor", zone_options, index=zone_options.index(zone), disabled=True)

    soil_type = st.selectbox("Site soil type", list(SITE_AMPLIFICATION.keys()), index=1)
    beta = st.number_input("Beta", min_value=0.001, value=0.6, step=0.05, format="%.3f")

    run = st.button("Run", type="primary", use_container_width=True)

    st.caption(f"City lookup source: {city_source}")
    st.divider()
    st.caption(
        "Developed by Aditya Jhunjhunwala (arj@purdue.edu).\n\n"
        "Hazard data provided by Prof. STG Raghukanth (IIT Madras).\n\n"
        "For details on RTGM calculations, please refer Luco, N., "
        "Ellingwood, B. R., Hamburger, R. O., Hooper, J. D., "
        "Kimball, J. K., & Kircher, C. A. (2007). Risk-targeted versus "
        "current seismic design maps for the conterminous United States.\n\n"
        "For educational purposes only."
    )


if run:
    try:
        if not latitude_text.strip() or not longitude_text.strip():
            raise ValueError("Please enter latitude and longitude.")
        if zone not in ZONE_FACTORS:
            raise ValueError("Please select a zone factor.")

        latitude = float(latitude_text)
        longitude = float(longitude_text)
        site_amp = SITE_AMPLIFICATION[soil_type]
        zone_values = ZONE_FACTORS[zone]

        with st.spinner("Calculating spectra..."):
            results = calculate_spectra(
                hazard_data,
                latitude,
                longitude,
                site_amp,
                zone_values["Z_475"],
                zone_values["Z_2475"],
                beta,
            )

        st.session_state["results"] = results
        st.session_state["city"] = city
    except Exception as exc:
        st.error(str(exc))


if "results" not in st.session_state:
    st.info("Select a city or choose User, provide the inputs, and click Run.")
else:
    results = st.session_state["results"]
    city = st.session_state["city"]
    table = pd.DataFrame(results_rows(results)).round(3)
    fig = build_plot(city, results)
    png = figure_to_png(fig)
    csv_data = dataframe_to_csv(table)
    tsv_data = dataframe_to_tsv(table)
    filename = safe_filename(city)

    st.success(
        "Done. Nearest hazard grid point: "
        f"{results['nearest_lat']:.3f}, {results['nearest_lon']:.3f}"
    )

    plot_col, download_col = st.columns([3, 1])
    with plot_col:
        st.pyplot(fig, clear_figure=True)
    with download_col:
        st.download_button(
            "Download plot",
            data=png,
            file_name=f"{filename}-RTGM.png",
            mime="image/png",
            use_container_width=True,
        )
        st.download_button(
            "Download table CSV",
            data=csv_data,
            file_name=f"{filename}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.subheader("Plot Data")
    st.dataframe(table, hide_index=True, use_container_width=True)

    with st.expander("Copy-friendly table"):
        st.text_area("Tab-separated values", value=tsv_data, height=240)
