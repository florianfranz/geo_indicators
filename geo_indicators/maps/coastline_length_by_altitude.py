import os
from geo_indicators.maps.coastal_length import create_contours, get_total_length
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
)
import matplotlib.pyplot as plt

def process_coastlines_by_alt(source,version,verbose=False):
    levels = list(range(-11000, 9001, 100))
    ages = []
    if source == "ETOPO":
        total_coastline_lengths = []
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
        for level in levels:
            print(f"Processing level {level}")
            coastlines = create_contours(data,transform,level)
            total_coastline_length = get_total_length(coastlines)
            total_coastline_lengths.append(total_coastline_length)

        if verbose:
            plt.figure(figsize=(8, 6))
            plt.plot(levels, total_coastline_lengths, label=f'Coastline Length of {version}')
            plt.axvline(x=0, color="red")
            plt.xlabel('Elevation Level [m]')
            plt.ylabel('Total Coastline Length [m]')
            plt.xlim(-11000, 8000)
            plt.grid(False)
            plt.legend()
            plt.tight_layout()
            plt.show()
    elif source == "PANALESIS":
        plt.figure(figsize=(8, 6))
        panalesis_maps = get_panalesis_maps(version)
        for map in panalesis_maps:
            total_coastline_lengths = []
            age = get_panalesis_age(map)
            print(f"Processing age {age}")

            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            for level in levels:
                coastlines = create_contours(data, transform, level)
                total_coastline_length = get_total_length(coastlines)
                total_coastline_lengths.append(total_coastline_length)

            plt.plot(levels, total_coastline_lengths, label=f' {age}')
        plt.axvline(x=320, color="red")
        plt.xlabel('Elevation Level [m]')
        plt.ylabel('Total Coastline Length [m]')
        plt.xlim(-11000, 8000)
        plt.grid(False)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v0_3"
    process_coastlines_by_alt(source, version)