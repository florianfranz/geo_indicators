import os
import geopandas as gpd
import pandas as pd
from geo_indicators.utils import (
    get_out_dir_path,
    get_panalesis_nodes,
    get_panalesis_age
)
from geo_indicators.visualization import (
    plot_scatter_from_gdf_ref,
    plot_scatter_from_gdf
)


def calculate_tss(A, R, T):
    if pd.isna(A) or pd.isna(R):
        return None
    elif R <= 0:
        return None
    A_km2 = A / 1_000_000
    R_km = R / 1000
    w = 0.0006
    Ag = 0.5  # ice cover in catchment: 0 (0%) to 10 (100%)
    I = 1 + (0.09 * Ag)
    L = 1.5  # soft_mixed lithologies
    B = I * L
    k = 0.075
    m = 0.8
    convert_m3ps_to_km3py = 0.000031536
    Q = k * (A_km2 ** m) * convert_m3ps_to_km3py
    TSS = w * B * (Q ** 0.31) * (A_km2 ** 0.5) * R_km * T
    return TSS, Q


def get_TSS_for_MITgcm_nodes(source, version, age):
    out_dir_path = get_out_dir_path(source, version)
    print(out_dir_path)
    MITgcm_nodes_path = os.path.join(out_dir_path, f"{source}_{version}", f"out_MITgcm_nodes_{age}.geojson")

    MITgcm_nodes_gdf = gpd.read_file(MITgcm_nodes_path)

    MITgcm_nodes_gdf[['TSS', 'Qw']] = MITgcm_nodes_gdf.apply(
        lambda row: pd.Series(calculate_tss(row['catchment_area'], row['max_elevation'],row['mean_temperature'])),
        axis=1
    )

    try:
        if os.path.exists(MITgcm_nodes_path):
            os.remove(MITgcm_nodes_path)
        MITgcm_nodes_gdf.to_file(MITgcm_nodes_path, driver="GeoJSON")
    except Exception as e:
        print(f"Error saving GeoJSON: {e}")
    if source == "PANALESIS":
        plot_scatter_from_gdf_ref(MITgcm_nodes_gdf,'catchment_area','TSS',age,version,True)
    else:
        plot_scatter_from_gdf(MITgcm_nodes_gdf, 'catchment_area','TSS',True)


def process_sediment_fluxes(source, version):
    if source == "ETOPO":
        if version != "2022":
            version = "2022"
        age = 0
        get_TSS_for_MITgcm_nodes(source, version, age)
    elif source == "PANALESIS":
        panalesis_nodes = get_panalesis_nodes(version)
        print(panalesis_nodes)
        for node in panalesis_nodes:
            age = get_panalesis_age(node)
            if age < 100:
                get_TSS_for_MITgcm_nodes(source, version, age)


if __name__ == "__main__":
    source = "ETOPO"
    version = "2022"
    process_sediment_fluxes(source, version)
