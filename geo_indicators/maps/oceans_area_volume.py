import os
import numpy as np
import pandas as pd
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
    )
from geo_indicators.visualization import plot_timeseries_simple


def oceans_area_volume(data, transform):
    """
    Calculate the area and volume of pixels below sea level (elevation < 0).

    Parameters:
    - data (numpy.ndarray): The raster data array.
    - transform (Affine): The affine transformation of the raster (from rasterio).

    Returns:
    - tuple: (area in square meters, volume in cubic meters).
    """
    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    mask = data < 0  # Mask the pixels where the elevation is below sea level

    # Calculate area (count of pixels * pixel area)
    area = np.sum(mask) * pixel_area

    # Calculate volume (sum of absolute elevation values * pixel area)
    volume = np.sum(np.abs(data[mask])) * pixel_area

    return area, volume


def process_area_volume(source, version,verbose=False):
    ages = []
    areas = []
    volumes = []
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
        area, volume = oceans_area_volume(data[0], transform)
        areas.append(area)
        volumes.append(volume)
        if verbose:
            print(f"Area below sea level: {area:.2e} m²")
            print(f"Volume below sea level: {volume:.2e} m³")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            area, volume = oceans_area_volume(data[0], transform)
            areas.append(area)
            volumes.append(volume)
            if verbose:
                print(map)
                print(f"Area below sea level: {area:.2e} m²")
                print(f"Volume below sea level: {volume:.2e} m³")
        combined = list(zip(ages, areas, volumes))
        combined.sort(key=lambda x: x[0])
        ages, areas, volumes = zip(*combined)
        if verbose:
            plot_timeseries_simple(ages,areas, "Oceanic Area (m²)", "Oceanic Area vs Age")
            plot_timeseries_simple(ages,volumes, "Oceanic Volume (m³)", "Oceanic Volume vs Age")
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")
    df = pd.DataFrame({
        'Age': ages,
        'Ocean_Area': areas,
        'Ocean_Volume': volumes
    })
    stat_out(df, join_on='Age', version=version, source=source)


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    process_area_volume(source,version)