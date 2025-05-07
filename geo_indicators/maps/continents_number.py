import matplotlib.pyplot as plt
from coastal_length import create_contours

def filter_large_polygons(gdf, min_area_m2):
    """
    Filters polygons in the GeoDataFrame to keep only those with an area over the specified minimum area.

    Parameters:
        gdf (GeoDataFrame): A GeoDataFrame with polygon geometries.
        min_area_m2 (float): Minimum area in square meters.

    Returns:
        GeoDataFrame: Filtered GeoDataFrame with polygons having area over the specified minimum.
    """
    filtered_gdf = gdf[gdf.geometry.area >= min_area_m2]
    return filtered_gdf


if __name__ == "__main__":
    coastlines = create_contours()
    min_area_m2 = 7.5e12 # Approx. area of Australia in square meters
    large_polygons = filter_large_polygons(coastlines, min_area_m2)
    large_polygons.plot(edgecolor='black', facecolor='none', linewidth=0.5)
    plt.title("Continents")
    plt.xlabel("Longitude (in meters)")
    plt.ylabel("Latitude (in meters)")
    plt.show()
    print(f"Number of continents: {len(large_polygons)}")

