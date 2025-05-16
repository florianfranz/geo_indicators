import os
import re
import numpy as np
import matplotlib.pyplot as plt
from geo_indicators.utils import load_tiff, get_input_raster_path, get_panalesis_maps

def get_additional_raster_paths(directory, pattern):
    # List all files in the directory
    all_files = os.listdir(directory)
    # Filter files based on the naming convention pattern
    raster_files = [os.path.join(directory, f) for f in all_files if re.match(pattern, f)]
    return raster_files

def hypsometric_curve():
    # Load the primary raster file
    input_raster = get_input_raster_path()
    data, metadata = load_tiff(input_raster)

    # Flatten the elevation data to a 1D array
    elevations = data.flatten()

    # Calculate the histogram of elevation data
    hist, bin_edges = np.histogram(elevations, bins=500)

    # Calculate the cumulative distribution
    cumulative_distribution = np.cumsum(hist)
    cumulative_fraction = cumulative_distribution / cumulative_distribution[-1]

    # Initialize lists to store cumulative distributions from additional rasters
    all_cumulative_distributions = []

    panalesis_maps = get_panalesis_maps("v1")
    for map in panalesis_maps:
        data, _ = load_tiff(map)
        elevations = data.flatten()
        hist, _ = np.histogram(elevations, bins=500)
        cumulative_distribution = np.cumsum(hist)
        cumulative_fraction = cumulative_distribution / cumulative_distribution[-1]
        all_cumulative_distributions.append(cumulative_fraction)

    # Convert list to numpy array for easier manipulation
    all_cumulative_distributions = np.array(all_cumulative_distributions)

    # Calculate the minimum and maximum cumulative distributions at each bin
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
    hypsometric_curve()
