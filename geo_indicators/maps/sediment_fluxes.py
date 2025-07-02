import os
import geopandas as gpd
import pandas as pd
from geo_indicators.utils import (
    get_out_dir_path,
    get_panalesis_nodes,
    get_panalesis_age)


def calculate_tss(A):
    if pd.isna(A):
        return None
    A_km2 = A / 1_000_000
    w = 0.0006
    Ag = 0.5  # ice cover in catchment: 0 (0%) to 10 (100%)
    I = 1 + (0.09 * Ag)
    L = 1.5  # soft_mixed lithologies
    B = I * L
    k = 0.075
    m = 0.8
    convert_m3ps_to_km3py = 0.000031536
    R = 4.6
    T = 10
    Q = k * (A_km2 ** m) * convert_m3ps_to_km3py
    return w * B * (Q ** 0.31) * (A_km2 ** 0.5) * R * T


def get_TSS_for_MITgcm_nodes(source, version, age):
    out_dir_path = get_out_dir_path(source, version)
    start_end_geojson_path = os.path.join(out_dir_path, f"{source}_{version}", f"start_end_points_{age}.geojson")

    print(f"Reading GeoJSON from: {start_end_geojson_path}")

    MITgcm_nodes_gdf = gpd.read_file(start_end_geojson_path)

    print("Calculating TSS...")
    MITgcm_nodes_gdf['TSS'] = MITgcm_nodes_gdf['catchment_area'].apply(calculate_tss)

    print("Preview of calculated TSS values:")
    print(MITgcm_nodes_gdf[['catchment_area', 'TSS']].head())

    # Overwrite the file safely
    try:
        if os.path.exists(start_end_geojson_path):
            os.remove(start_end_geojson_path)
            print(f"Old file deleted: {start_end_geojson_path}")

        MITgcm_nodes_gdf.to_file(start_end_geojson_path, driver="GeoJSON")
        print(f"Updated GeoJSON saved to: {start_end_geojson_path}")
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")


def process_sediment_fluxes(source, version):
    if source == "ETOPO":
        if version != "2022":
            version = "2022"
        age = 0
        get_TSS_for_MITgcm_nodes(source, version, age)
    elif source == "PANALESIS":
        panalesis_nodes = get_panalesis_nodes(version)
        for node in panalesis_nodes:
            age = get_panalesis_age(node)
            get_TSS_for_MITgcm_nodes(source, version, age)

if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    process_sediment_fluxes(source, version)
