import os
import numpy as np
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path,get_panalesis_maps, get_panalesis_age
from geo_indicators.visualization import plot_mask, plot_timeseries_simple


def get_land_area(data,transform, plot=False):
    """
    Process the input raster to calculate an area after reprojection.

    Returns:
    - tuple: (area in square meters, volume in cubic meters).
    """

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    land_mask = data[0] >= 0  # Mask the pixels where the elevation is above or equal to sea level
    if plot == True:
        plot_mask(land_mask, "Land (z >= 0m)")

    # Calculate area (count of pixels * pixel area)
    land_area = np.sum(land_mask) * pixel_area
    total_area = data[0].size * pixel_area

    return land_area, total_area

def process_land_area(source):
    if source == "ETOPO":
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        land_area, total_area = get_land_area(data,transform, plot=True)
        land_percentage = land_area / total_area * 100
        print(f"Total land area: {land_area:.2e} m²")
        print(f"Total raster area: {total_area:.2e} m²")
        print(f"Percentage of land is {land_percentage}%")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps("v1")
        ages = []
        land_areas = []
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            land_area, total_area = get_land_area(data, transform, plot=False)
            land_areas.append(land_area)
            land_percentage = land_area / total_area * 100
            print(map)
            print(f"Total land area: {land_area:.2e} m²")
            print(f"Total raster area: {total_area:.2e} m²")
            print(f"Percentage of land is {land_percentage}%")
        plot_timeseries_simple(ages, land_areas, 'Land Area (m²)', 'Land Area vs Age')
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")


if __name__ == "__main__":
    source = "PANALESIS"
    process_land_area(source)
