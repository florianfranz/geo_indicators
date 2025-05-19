import os
from geo_indicators.visualization import plot_gdf_simple, plot_timeseries_simple
from coastal_length import create_contours
from geo_indicators.utils import load_tiff, reproject_raster, get_input_raster_path, get_reprojected_raster_path,get_panalesis_maps,get_panalesis_age


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

def process_continents_number(source,version):
    min_area_m2 = 7.5e12  # Approx. area of Australia in square meters
    if source == "ETOPO":
        input_raster = get_input_raster_path()
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        transform = metadata['transform']
        coastlines = create_contours(data,transform)
        large_polygons = filter_large_polygons(coastlines, min_area_m2)
        plot_gdf_simple(large_polygons, "Continents")
        print(f"Number of continents: {len(large_polygons)}")
    elif source == "PANALESIS":
        panalesis_maps = get_panalesis_maps(version)
        ages = []
        continents_numbers = []
        for map in panalesis_maps:
            age = get_panalesis_age(map)
            ages.append(age)
            data, metadata = load_tiff(map)
            transform = metadata['transform']
            coastlines = create_contours(data, transform)
            large_polygons = filter_large_polygons(coastlines, min_area_m2)
            continents = len(large_polygons)
            continents_numbers.append(continents)
        combined = list(zip(ages, continents_numbers))
        combined.sort(key=lambda x: x[0])
        ages, continents_numbers = zip(*combined)
        plot_timeseries_simple(ages, continents_numbers, "Number of Continents", "Number of Continents vs Age")


if __name__ == "__main__":
    source = "PANALESIS"
    version = "v0"
    process_continents_number(source, version)




