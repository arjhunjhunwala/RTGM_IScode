# RTGM and IS Code Spectra Streamlit App

This Streamlit app calculates RTGM, PSHA 475-year, PSHA 2475-year, and IS code spectra for Indian cities or a user-defined latitude and longitude.

## Files Used

- `streamlit_app.py`: Streamlit user interface.
- `spectra_core.py`: Shared calculation and data-loading logic.
- `Hazard_curves_All_grid_points_in_India.mat`: Hazard-curve data.
- `Indian_cities_geocoded.csv`: City, zone, latitude, and longitude database.
- `requirements.txt`: Python dependencies.
- `.streamlit/config.toml`: Streamlit display settings.

## Run Locally

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the app:

```powershell
streamlit run streamlit_app.py
```

The app opens in a browser. For listed cities, latitude, longitude, and zone are filled automatically. Select `User` to enter custom location and zone values.
