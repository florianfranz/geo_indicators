import os
import numpy as np
import pandas as pd
from rasterio.features import rasterize
from geo_indicators.visualization import plot_mask, plot_timeseries_simple
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_reproj_latitudes_bounds_path,
    load_reproj_latitudes_bounds,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
)

def get_tropical_mask(raster_meta, raster_shape):
    """
    Generate a binary mask where True indicates pixels between:
    - Subtropical_S and Subtropical_N
    """
    latitudes_path = get_reproj_latitudes_bounds_path()
    gdf = load_reproj_latitudes_bounds(latitudes_path)

    required_lines = ['Subtropical_N', 'Subtropical_S']
    if not all(name in gdf['name'].values for name in required_lines):
        raise ValueError("GeoJSON must contain all required latitude boundary lines.")

    line_rows = {}

    # Rasterize each line to find its row position
    for name in required_lines:
        geom = gdf[gdf['name'] == name].geometry
        if geom.empty:
            continue

        rasterized = rasterize(
            [(g, 1) for g in geom],
            out_shape=raster_shape,
            transform=raster_meta['transform'],
            fill=0,
            all_touched=True,
            dtype='uint8'
        )

        rows = np.where(rasterized == 1)[0]
        if rows.size > 0:
            line_rows[name] = rows.mean()  # average row if line spans multiple rows

    if len(line_rows) != 2:
        raise ValueError("Could not locate all required latitude boundaries in raster.")

    ys = np.indices(raster_shape)[0]
    tropical_mask = (ys >= line_rows['Subtropical_N']) & (ys <= line_rows['Subtropical_S'])

    return tropical_mask


def get_tropical_area(data, metadata, transform, plot=False):
    """
    Process the input raster to calculate total and tropical land areas after reprojection.

    Returns:
    - tuple: (land area m², total area m², tropical land area m²)
    """

    pixel_area = abs(transform[0] * transform[4])  # pixel width × height in meters
    elevation = data[0]

    # Land mask: elevation >= 0
    land_mask = elevation >= 0

    # Get tropical region mask
    tropical_mask = get_tropical_mask(metadata, elevation.shape)

    # Combined mask: land AND within tropical regions
    combined_mask = np.logical_and(land_mask, tropical_mask)
    if plot == True:
        plot_mask(combined_mask, "Tropical Land (23.5° < Latitude > 40° N/S)")

    # Area calculations
    total_area = elevation.size * pixel_area
    tropical_land_area = np.sum(combined_mask) * pixel_area

    return total_area, tropical_land_area


def process_tropical_land_area(source,version):
    ages = []
    tropical_land_areas = []
    if source == "ETOPO":
        if version != "ETOPO_2022":
            version = "ETOPO_2022"
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        age = 0
        ages.append(age)
        total_area, tropical_land_area = get_tropical_area(data, metadata, transform, plot=True)
        tropical_percentage = tropical_land_area / total_area * 100
        tropical_land_areas.append(tropical_land_area)
        print(f"Total raster area: {total_area:.2e} m²")
        print(f"Tropical land area: {tropical_land_area:.2e} m²")
        print(f"Percentage of tropical land: {tropical_percentage:.2f}%")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            total_area, tropical_land_area = get_tropical_area(data, metadata, transform, plot=False)
            tropical_land_areas.append(tropical_land_area)
            tropical_percentage = tropical_land_area / total_area * 100
            print(map)
            print(f"Total raster area: {total_area:.2e} m²")
            print(f"Tropical land area: {tropical_land_area:.2e} m²")
            print(f"Percentage of tropical land: {tropical_percentage:.2f}%")
        combined = list(zip(ages, tropical_land_areas))
        combined.sort(key=lambda x: x[0])
        ages, tropical_land_areas = zip(*combined)
        plot_timeseries_simple(ages, tropical_land_areas, 'Tropical Land Area (m²)',
                               'Tropical Land Area vs Age')
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")
    df = pd.DataFrame({
        'Age': ages,
        'Tropical_Land_Area': tropical_land_areas
    })
    stat_out(df, join_on='Age', version=version, source=source)


if __name__ == "__main__":
    source = "ETOPO"
    version = "v1"
    process_tropical_land_area(source,version)