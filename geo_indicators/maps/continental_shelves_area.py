import os
import numpy as np
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path, get_panalesis_maps, get_panalesis_age
from geo_indicators.visualization import plot_mask, plot_timeseries_simple


def get_shelves_area(data, transform, plot=False):
    """
    Process the input raster to calculate continental shelves area after reprojection.

    Returns:
    - tuple: (area in square meters, volume in cubic meters).
    """

    pixel_area = abs(transform[0] * transform[4])  # width * height of a pixel in meters
    shelves_mask = (data[0] >= -300) & (data[0] < 0)  # Mask the pixels where the elevation is between -300 and 0m
    if plot == True:
        plot_mask(shelves_mask, "Continental Shelves (-300m >= z > 0m)")

    # Calculate area (count of pixels * pixel area)
    shelves_area = np.sum(shelves_mask) * pixel_area
    total_area = data[0].size * pixel_area

    return shelves_area, total_area

def process_shelves_area(source,version):
    if source == "ETOPO":
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        shelves_area, total_area = get_shelves_area(data, transform, plot=True)
        shelves_percentage = shelves_area/total_area*100
        print(f"Total shelves area: {shelves_area:.2e} m²")
        print(f"Total raster area: {total_area:.2e} m²")
        print(f"Percentage of shelves is {shelves_percentage}")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        ages = []
        shelves_areas = []
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            shelves_area, total_area = get_shelves_area(data, transform, plot=False)
            shelves_areas.append(shelves_area)
            shelves_percentage = shelves_area / total_area * 100
            print(map)
            print(f"Total shelves area: {shelves_area:.2e} m²")
            print(f"Total raster area: {total_area:.2e} m²")
            print(f"Percentage of shelves is {shelves_percentage}")
        combined = list(zip(ages, shelves_areas))
        combined.sort(key=lambda x: x[0])
        ages, shelves_areas = zip(*combined)
        plot_timeseries_simple(ages,shelves_areas, 'Shelves Area (m²)', 'Shelves Area vs Age')
    else:
        print(f"Incorrect source value, must be either PANALESIS or ETOPO")


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    process_shelves_area(source,version)
