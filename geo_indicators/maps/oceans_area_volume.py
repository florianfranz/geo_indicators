import os
import numpy as np
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path, get_panalesis_maps, get_panalesis_age
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


def process_area_volume(source, version):
    if source == "ETOPO":
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        area, volume = oceans_area_volume(data[0], transform)
        print(f"Area below sea level: {area:.2e} m²")
        print(f"Volume below sea level: {volume:.2e} m³")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        ages = []
        areas = []
        volumes = []
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            area, volume = oceans_area_volume(data[0], transform)
            areas.append(area)
            volumes.append(volume)
            print(map)
            print(f"Area below sea level: {area:.2e} m²")
            print(f"Volume below sea level: {volume:.2e} m³")
        combined = list(zip(ages, areas, volumes))
        combined.sort(key=lambda x: x[0])
        ages, areas, volumes = zip(*combined)
        plot_timeseries_simple(ages,areas, "Oceanic Area (m²)", "Oceanic Area vs Age")
        plot_timeseries_simple(ages,volumes, "Oceanic Volume (m³)", "Oceanic Volume vs Age")
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v0"
    process_area_volume(source,version)