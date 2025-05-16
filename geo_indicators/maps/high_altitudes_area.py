import os
import numpy as np
from geo_indicators.visualization import plot_mask, plot_timeseries_simple
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_panalesis_maps,
    get_panalesis_age)



def get_high_altitudes_area(data, transform, plot=False):
    """
    Process the input raster to calculate high altitudes (>3000m) area after reprojection.

    Returns:
    - tuple: (area in square meters).
    """

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    high_altitude_mask = data[0] >= 3000  # Mask the pixels where the elevation is above 3000m
    if plot == True:
        plot_mask(high_altitude_mask, "High Altitude Regions (z >=3000m)")

    # Calculate area (count of pixels * pixel area)
    high_altitude_area = np.sum(high_altitude_mask) * pixel_area
    total_area = data[0].size * pixel_area


    return high_altitude_area, total_area

def process_high_altitude_area(source,version):
    if source == "ETOPO":
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        high_altitude_area, total_area = get_high_altitudes_area(data,transform,plot=True)
        high_altitude_percentage = high_altitude_area / total_area * 100
        print(f"Total high altitude area: {high_altitude_area:.2e} m²")
        print(f"Total raster area: {total_area:.2e} m²")
        print(f"Percentage of high altitude regions is {high_altitude_percentage}")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        ages = []
        high_altitudes_areas = []
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            high_altitude_area, total_area = get_high_altitudes_area(data, transform, plot=False)
            high_altitudes_areas.append(high_altitude_area)
            high_altitude_percentage = high_altitude_area / total_area * 100
            print(age)
            print(f"Total high altitude area: {high_altitude_area:.2e} m²")
            print(f"Total raster area: {total_area:.2e} m²")
            print(f"Percentage of high altitude regions is {high_altitude_percentage}")
        combined = list(zip(ages, high_altitudes_areas))
        combined.sort(key=lambda x: x[0])
        ages, high_altitudes_areas = zip(*combined)
        plot_timeseries_simple(ages, high_altitudes_areas, 'High Altitude Area (m²)',
                               'High Altitude Regions (z >=3000m)')
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    process_high_altitude_area(source,version)

