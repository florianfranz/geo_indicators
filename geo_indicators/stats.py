from geo_indicators.maps import (
    land_area,
    polar_zones_land_area,
    temperate_zones_land_area,
    subtropical_zones_land_area,
    tropical_zone_land_area,
    hemispheres_symmetry,
    high_altitudes_area,
    continental_shelves_area,
    oceans_area_volume,
    coastal_length,
    continents_number,
    drainage_basins
)

def generate_stats(source,version):
    land_area.process_land_area(source,version)
    polar_zones_land_area.process_polar_land_area(source,version)
    temperate_zones_land_area.process_temperate_land_area(source,version)
    subtropical_zones_land_area.process_subtropical_land_area(source,version)
    tropical_zone_land_area.process_tropical_land_area(source,version)
    hemispheres_symmetry.process_hemispheres_area(source,version)
    high_altitudes_area.process_high_altitude_area(source,version)
    continental_shelves_area.process_shelves_area(source,version)
    oceans_area_volume.process_area_volume(source,version)
    coastal_length.process_coastal_length(source,version)
    continents_number.process_continents_number(source,version)
    drainage_basins.process_drainage_basins(source,version)

    print(f"Statistics exported for {version} of {source}")