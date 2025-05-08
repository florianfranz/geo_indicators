import numpy as np
import matplotlib.pyplot as plt
from geo_indicators.utils import load_tiff, get_input_raster_path

def hypsometric_curve():
    # Load the raster file using external functions
    input_raster = get_input_raster_path()
    data, metadata = load_tiff(input_raster)

    # Flatten the elevation data to a 1D array
    elevations = data.flatten()

    # Calculate the histogram of elevation data
    hist, bin_edges = np.histogram(elevations, bins=500)

    # Calculate the cumulative distribution
    cumulative_distribution = np.cumsum(hist)
    cumulative_fraction = cumulative_distribution / cumulative_distribution[-1]

    plt.figure(figsize=(10, 6))
    plt.plot(cumulative_fraction, bin_edges[:-1])
    plt.xlabel('Cummulative Fraction of Earth Surface')
    plt.ylabel('Elevation (m)')
    plt.title('Hypsometric Curve')
    plt.legend()
    plt.grid(True)
    plt.show()

if __name__ == "__main__":
    hypsometric_curve()
