
![](images/logo3.png)

# A Python Package to Create Indices Characterizing the Geography of the Earth for Climate Modelling

## Introduction

This package creates indices that describe the Earth's geography in the context of climate modelling. 

Geography plays a crucial role in climate modelling for several reasons:
1. **Spatial variability:** Different geographic regions have unique characteristics such as elevation, vegetation, and proximity to bodies of water, which significantly influence local climate conditions.
2. **Energy balance:** The Earth's energy balance, which is essential for climate prediction, varies across different geographic locations. Factors like solar radiation, albedo (reflectivity), and heat exchange between land, ocean, and atmosphere are geographically dependent.
3. **Atmospheric circulation:** Geographic features such as mountains and valleys affect atmospheric circulation patterns, which in turn influence weather and climate. For example, mountain ranges can block or redirect air flow, leading to distinct climatic zones on either side.
4. **Ocean currents:** The geography of the ocean floor and coastlines shapes ocean currents, which are vital for distributing heat and moisture around the globe. These currents play a key role in regulating climate.
5. **Land surface processes:** eographic factors determine land surface processes like soil moisture, vegetation cover, and snow accumulation, all of which impact climate models. These processes affect the exchange of heat, water, and carbon between the land and atmosphere.

We base our indices on maps (raster format) and plate tectonics models (vector format). These indices can be generated 
for the present-day Earth but are most useful for maps of the Earth past (palaeogeographic maps), 
which changed through time due to movement of tectonic plates.

### Indices derived from palaeogeographic maps

1. Oceans
- N/S marine passage
- W/E marine passage
- Total oceans area and volume
2. Coastal
- Coastal length
- Area of continental shelves (with depths between -300 and 0m)
- River fluxes
- Sediment fluxes
3. Land
- Total land area and percentage
- Land area in polar zones (from 60° to 90° latitude N/S)
- Land area in temperate zones (from 40° to 60° N/S)
- Land area in subtropical zones (from 23.5° to 40° N/S)
- Land area in tropical zone (from 23.5°S to 23.5°N)
- Land distribution: hemispheres symmetry
- Number of continents
- Land area with high altitude (<3000m)
- Area and volume of large inland water bodies
- Drainage basins area

### Indices derived from plate tectonics models
1. Oceans
- Subduction zones length
- Hot-spots volume
2. Land
- Suture zone length in tropical zone
3. Global
- Latitudinal distribution of features (line vertices and points)


