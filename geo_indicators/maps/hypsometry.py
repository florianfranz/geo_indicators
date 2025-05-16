import os
import re
import numpy as np
import matplotlib.pyplot as plt
from geo_indicators.utils import load_tiff, get_input_raster_path, get_panalesis_maps

def get_additional_raster_paths(directory, pattern):
    all_files = os.listdir(directory)
    raster_files = [os.path.join(directory, f) for f in all_files if re.match(pattern, f)]
    return raster_files

def hypsometric_curve(version):
    input_raster = get_input_raster_path()
    data, metadata = load_tiff(input_raster)
    elevations = data.flatten()
    hist, bin_edges = np.histogram(elevations, bins=500)
    cumulative_distribution = np.cumsum(hist)
    cumulative_fraction = cumulative_distribution / cumulative_distribution[-1]
    all_cumulative_distributions = []

    panalesis_maps = get_panalesis_maps(version)
    for map in panalesis_maps:
        data, _ = load_tiff(map)
        elevations = data.flatten()
        hist, _ = np.histogram(elevations, bins=500)
        cumulative_distribution = np.cumsum(hist)
        cumulative_fraction = cumulative_distribution / cumulative_distribution[-1]
        all_cumulative_distributions.append(cumulative_fraction)
    all_cumulative_distributions = np.array(all_cumulative_distributions)
    min_cumulative_fraction = np.min(all_cumulative_distributions, axis=0)
    max_cumulative_fraction = np.max(all_cumulative_distributions, axis=0)

    plt.figure(figsize=(10, 6))
    plt.plot(cumulative_fraction, bin_edges[:-1], label='ETOPO 2022 resampled at 0.1°')
    plt.fill_betweenx(bin_edges[:-1], min_cumulative_fraction, max_cumulative_fraction, color='gray', alpha=0.5, label='Sea-level corrected PANALESIS v1 maps (330-550 Ma)')
    plt.xlabel('Cumulative Fraction of Earth Surface')
    plt.ylabel('Elevation (m)')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    version = "v1"
    hypsometric_curve(version)
