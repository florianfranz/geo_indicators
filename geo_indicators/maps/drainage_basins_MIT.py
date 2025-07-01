import os
import geojson
import geopandas as gpd
import gc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pysheds.grid import Grid
import rasterio
from rasterio.features import rasterize
from rasterio.transform import xy, rowcol
from scipy.spatial import cKDTree
from skimage import measure
from shapely.geometry import Polygon
from shapely.errors import GEOSException
from shapely.ops import unary_union

from geo_indicators.maps.coastal_length import close_contour
from geo_indicators.utils import (
    load_tiff,
    reproject_raster,
    get_input_raster_path,
    get_reprojected_raster_path,
    get_reproj_MITgcm_nodes,
    get_out_dir_path,
    get_panalesis_maps,
    get_panalesis_age,
    stat_out
)
from geo_indicators.visualization import plot_gdf_simple

def safe_buffer_zero(geom):
    try:
        return geom.buffer(0)
    except GEOSException:
        return None  # Or log it if needed


def trace_clipped_flow_path(clipped_fdir, start_coord, transform):
    # Convert starting coordinates to grid indices
    start_row, start_col = rowcol(transform, *start_coord)
    # Direction map for D8 flow
    dirmap = {
        1: (0, 1),  # East
        2: (1, 1),  # Southeast
        4: (1, 0),  # South
        8: (1, -1),  # Southwest
        16: (0, -1),  # West
        32: (-1, -1),  # Northwest
        64: (-1, 0),  # North
        128: (-1, 1)  # Northeast
    }
    # Initialize path and starting point
    path = [(start_row, start_col)]
    current_row, current_col = start_row, start_col
    # Trace the flow
    while True:
        # Get the flow direction value at the current cell
        flow_dir = clipped_fdir[current_row, current_col]
        # Check if the flow direction is valid
        if np.isnan(flow_dir) or flow_dir not in dirmap:
            break  # End of flow (e.g., invalid cell, outlet, or boundary)
        # Get the next step based on the flow direction
        step = dirmap[flow_dir]
        next_row, next_col = current_row + step[0], current_col + step[1]
        # Check if the next cell is out of bounds
        if (next_row < 0 or next_row >= clipped_fdir.shape[0] or
                next_col < 0 or next_col >= clipped_fdir.shape[1]):
            break  # End of flow (e.g., domain boundary)
        # Add the next cell to the path
        path.append((next_row, next_col))
        current_row, current_col = next_row, next_col
    return path

def process_drainage_basins_MITgcm(source, version):
    ages = []
    contour_levels = [0,-2000]
    if source == "ETOPO":
        polygons = []
        if version != "ETOPO_2022":
            version = "ETOPO_2022"
        input_raster = get_input_raster_path()
        filled_raster_path = input_raster.replace('.tif','_filled.tif')
        reprojected_raster = get_reprojected_raster_path()
        if os.path.exists(reprojected_raster):
            data, metadata = load_tiff(reprojected_raster)
        else:
            reproject_raster(input_raster, reprojected_raster)
            data, metadata = load_tiff(reprojected_raster)
        band = data[0]
        transform = metadata['transform']
        raster_crs = metadata['crs']
        age = 0
        ages.append(age)
        reproj_MITgcm_nodes_path = get_reproj_MITgcm_nodes()
        out_dir_path = get_out_dir_path(source,version)
        out_reproj_MITgcm_nodes_path = os.path.join(out_dir_path, f"{version}", f"out_MITgcm_nodes_{age}.geojson" )
        start_end_geojson_path = os.path.join(out_dir_path, f"{version}", f"start_end_points_{age}.geojson")
        flow_paths_geojson_path = os.path.join(out_dir_path, f"{version}", f"flow_paths_{age}.geojson")
        for level in contour_levels:
            contours = measure.find_contours(band, level)
            for contour in contours:
                transformed_contour = []
                for point in contour:
                    x, y = transform * (point[1], point[0])  # Transform to geographic coordinates
                    transformed_contour.append((x, y))

                closed_contour = close_contour(transformed_contour)
                if closed_contour:
                    polygon = Polygon(closed_contour)
                    if polygon.is_valid:
                        polygons.append({'geometry': polygon, 'level': level})

        gdf = gpd.GeoDataFrame(polygons)
        gdf.set_crs(raster_crs, allow_override=True)
        #gdf.to_file(output_contours, driver='GeoJSON')
        level_0_polygons = gdf[gdf['level'] == 0]
        nested_polygons = []
        for _, parent_row in level_0_polygons.iterrows():
            parent_polygon = parent_row['geometry']
            # Check for both level 0 and level -2000 polygons contained in the parent polygon
            for _, child_row in gdf.iterrows():
                child_polygon = child_row['geometry']
                child_level = child_row['level']
                # Ensure child is strictly contained within the parent and is not the parent itself
                if parent_polygon.contains(child_polygon) and not parent_polygon.equals(child_polygon):
                    nested_polygons.append({'geometry': child_polygon, 'level': child_level})
        # Create a GeoDataFrame for the nested polygons
        nested_gdf = gpd.GeoDataFrame(nested_polygons)
        nested_gdf.set_crs(gdf.crs, inplace=True)
        nested_with_flag = []
        nested_without_flag = []
        # Iterate through each polygon in the nested_gdf to check if it contains a level -2000 polygon
        for _, parent_row in nested_gdf.iterrows():
            parent_polygon = parent_row['geometry']
            parent_level = parent_row['level']
            parent_flag = 0  # Default FLAG value is 0
            if parent_level == 0:  # Only process level 0 polygons
                # Check if this level 0 polygon contains any level -2000 polygons
                for _, child_row in nested_gdf.iterrows():
                    child_polygon = child_row['geometry']
                    child_level = child_row['level']
                    if parent_polygon.contains(child_polygon) and child_level == -2000:
                        parent_flag = 1  # Set FLAG to 1 if a level -2000 polygon is contained
                # Append the nested polygon with the FLAG value
                nested_with_flag.append({
                    'geometry': parent_polygon,
                    'level': parent_level,
                    'FLAG': parent_flag
                })
        # Create a new GeoDataFrame with the FLAG property
        nested_with_flag_gdf = gpd.GeoDataFrame(nested_with_flag)
        nested_with_flag_gdf.set_crs(nested_gdf.crs, inplace=True)
        nested_flag_1_gdf = nested_with_flag_gdf[nested_with_flag_gdf['FLAG'] == 1]
        # Filter out only level 0 polygons from the original contours (exclude level -2000 polygons)
        level_0_contours_gdf = gdf[gdf['level'] == 0]
        # Create an empty list to hold the resulting difference polygons
        diff_polygons = []
        # Iterate through each level 0 contour polygon and subtract nested FLAG=1 polygons
        for _, contour_row in level_0_contours_gdf.iterrows():
            contour_polygon = contour_row['geometry']
            # Subtract each nested FLAG=1 polygon from the contour polygon
            result_polygon = contour_polygon
            for _, nested_row in nested_flag_1_gdf.iterrows():
                nested_polygon = nested_row['geometry']
                result_polygon = result_polygon.difference(nested_polygon)
            # Only append the result if it is valid
            if result_polygon.is_valid and not result_polygon.is_empty:
                diff_polygons.append({'geometry': result_polygon, 'level': contour_row['level']})
        # Create a GeoDataFrame for the resulting difference polygons
        diff_gdf = gpd.GeoDataFrame(diff_polygons)
        diff_gdf.set_crs(gdf.crs, inplace=True)
        dissolved_geometry = unary_union(diff_gdf.geometry)
        # If you want the result as a new GeoDataFrame
        dissolved_gdf = gpd.GeoDataFrame(geometry=[dissolved_geometry], crs=diff_gdf.crs)
        #plot_gdf_simple(dissolved_gdf, "Dissolved contours")
        gdf_points = gpd.read_file(reproj_MITgcm_nodes_path)
        gdf_polygons = dissolved_gdf
        dissolved_polygon = gdf_polygons.geometry.union_all()
        # Check if each point is inside the dissolved polygon
        gdf_points['CONT'] = gdf_points.geometry.apply(
            lambda point: 1 if dissolved_polygon.contains(point) else 0).astype(int)

        polygons = nested_with_flag_gdf
        polygons = polygons[polygons['FLAG'] == 0]

        # Only set the CRS if it's missing
        if polygons.crs is None:
            polygons = polygons.set_crs(metadata['crs'])

        # Now you can safely reproject if needed
        if polygons.crs != metadata['crs']:
            polygons = polygons.to_crs(metadata['crs'])

        polygons['geometry'] = polygons['geometry'].apply(safe_buffer_zero)

        # Drop any resulting None, invalid, or empty geometries
        polygons = polygons.dropna(subset=['geometry'])
        polygons = polygons[polygons.is_valid & ~polygons.is_empty]

        # Apply a 0.25 buffer around the cleaned polygons
        buffered_polygons = polygons.copy()
        buffered_polygons['geometry'] = buffered_polygons['geometry'].apply(
            lambda geom: geom.buffer(25) if geom.is_valid else None
        )

        # Drop any failures again (should be rare after cleaning)
        buffered_polygons = buffered_polygons.dropna(subset=['geometry'])
        buffered_polygons = buffered_polygons[buffered_polygons.is_valid & ~buffered_polygons.is_empty]

        polygon_mask = rasterize(
            [(geom, 1) for geom in buffered_polygons.geometry],
            out_shape=band.shape,
            transform=metadata['transform'],
            fill=0,
            dtype='uint8'
        )

        new_value = 444  # Dummy value, we can change this later.
        band[polygon_mask == 1] = new_value

        # Save the modified raster
        with rasterio.open(filled_raster_path, 'w', **metadata) as dst:
            dst.write(band, 1)
        grid = Grid.from_raster(filled_raster_path)
        dem = grid.read_raster(filled_raster_path)

        # Process the filtered DEM
        pit_filled_dem = grid.fill_pits(dem, epsilon=1e-3)
        flooded_dem = grid.fill_depressions(pit_filled_dem, epsilon=1e-3)
        inflated_dem = grid.resolve_flats(flooded_dem)
        dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
        fdir = grid.flowdir(inflated_dem, dirmap=dirmap, nodata_out=np.int64(0))
        # Load the original raster to check values
        with rasterio.open(filled_raster_path) as src:
            original_dem = src.read(1)  # Read the first band (assumes single-band raster)
            transform = src.transform  # Get the affine transform of the raster
        # Create a mask for values > 0 in the original DEM
        valid_mask = original_dem > 0
        clipped_fdir = np.where(valid_mask, fdir, np.nan)
        ocean_gdf = gdf_points[gdf_points['CONT'] == 0]
        ocean_coords = np.array([[geom.x, geom.y] for geom in ocean_gdf.geometry])
        ocean_ids = ocean_gdf['ID'].to_numpy()

        ocean_points = np.column_stack((ocean_coords, ocean_ids))  # if you need IDs later

        # Build the KDTree
        tree = cKDTree(ocean_coords)
        geojson_features = []
        start_end_features = []
        # Process each point in the CSV with CONT=1
        out_ids = []
        for idx, row in gdf_points.iterrows():
            if row['CONT'] == 1:
                # Start point coordinates
                start_point = (row.geometry.x, row.geometry.y)
                # Trace the flow path
                flow_path = trace_clipped_flow_path(clipped_fdir, start_point, transform)
                # Convert the flow path grid indices to coordinates
                flow_path_coords = [xy(transform, r, c) for r, c in flow_path]
                last_point_coords = flow_path_coords[-1] if flow_path_coords else start_point
                # Find the nearest ocean point to the last point in the flow path
                _, nearest_idx = tree.query(last_point_coords)  # Find nearest ocean point
                nearest_id = ocean_points[nearest_idx, 2]
                out_ids.append(nearest_id)
                # Add flow path to GeoJSON features
                if flow_path_coords:
                    geojson_features.append(geojson.Feature(
                        geometry=geojson.LineString(flow_path_coords),
                        properties={'ID': row['ID'], 'OUT_ID': nearest_id}
                    ))
                # Add start and end points to GeoJSON
                start_end_features.append(geojson.Feature(
                    geometry=geojson.Point(start_point),
                    properties={'Type': 'Start', 'ID': row['ID'], 'OUT_ID': nearest_id}
                ))
                start_end_features.append(geojson.Feature(
                    geometry=geojson.Point(last_point_coords),
                    properties={'Type': 'End', 'ID': row['ID'], 'OUT_ID': nearest_id}
                ))
            else:
                # OUT_ID for ocean points (CONT=0) is their own ID
                out_ids.append(row['ID'])
        gdf_points['OUT_ID'] = out_ids
        os.makedirs(os.path.dirname(out_reproj_MITgcm_nodes_path), exist_ok=True)
        gdf_points.to_file(out_reproj_MITgcm_nodes_path)
        with open(flow_paths_geojson_path, 'w') as f:
            geojson.dump(geojson.FeatureCollection(geojson_features), f)
        print(f"Flow paths GeoJSON file saved to {flow_paths_geojson_path}")
        with open(start_end_geojson_path, 'w') as f:
            geojson.dump(geojson.FeatureCollection(start_end_features), f)
        cell_width = abs(grid.affine.a)
        cell_height = abs(grid.affine.e)
        cell_area = cell_width * cell_height
        xmin, ymin, xmax, ymax = grid.bbox
        buffer_x = 2 * cell_width
        buffer_y = 2 * cell_height

        print(f"cell area is {cell_area}")
        acc = grid.accumulation(fdir, dirmap=dirmap, nodata_out=np.int64(0))
        threshold = 100

        start_end_points_gdf = gpd.read_file(start_end_geojson_path)
        outlets = start_end_points_gdf[start_end_points_gdf['Type'] == 'End']
        outlets = outlets.reset_index()  # Retain original index for later mapping
        print(len(outlets))

        catchment_areas = []

        for i, row in outlets.iterrows():
            idx = row['index']  # original index in start_end_points_gdf
            x, y = row.geometry.x, row.geometry.y
            if (
                    x <= xmin + buffer_x or x >= xmax - buffer_x or
                    y <= ymin + buffer_y or y >= ymax - buffer_y
            ):
                print(f"Outlet {idx} skipped: too close to raster edge.")
                catchment_areas.append((idx, np.nan))
                continue

            try:
                x_snap, y_snap = grid.snap_to_mask(acc > threshold, (x, y))
                if (
                        x_snap <= xmin + buffer_x or x_snap >= xmax - buffer_x or
                        y_snap <= ymin + buffer_y or y_snap >= ymax - buffer_y
                ):
                    print(f"Outlet {idx} skipped after snapping: snapped point too close to raster edge.")
                    catchment_areas.append((idx, np.nan))
                    continue

                catch = grid.catchment(
                    x=x_snap, y=y_snap,
                    fdir=fdir, dirmap=dirmap,
                    xytype='coordinate'
                )
                catch_array = catch.view()
                num_cells = np.count_nonzero(catch_array)
                catchment_area = num_cells * cell_area
                catchment_areas.append((idx, catchment_area))

                del catch, catch_array
                gc.collect()
            except Exception as e:
                print(f"Outlet {idx} failed during catchment extraction: {e}")
                catchment_areas.append((idx, np.nan))
                continue

        # Create a Series with catchment_area values mapped by index
        catchment_series = pd.Series(dict(catchment_areas))

        # Add the column to the original GeoDataFrame, aligning by index
        start_end_points_gdf['catchment_area'] = start_end_points_gdf.index.map(catchment_series)
        start_end_points_gdf.to_file(start_end_geojson_path, driver="GeoJSON")

    return catchment_areas


if __name__ == "__main__":
    source = "ETOPO"
    version = "2022"
    catchment_areas = process_drainage_basins_MITgcm(source, version)




