# main.py

from geo_indicators.stats import generate_stats
from geo_indicators.visualization import heatmap_chart, radar_chart

if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    #generate_stats(source,version)
    heatmap_chart(source,version)
    radar_chart(source,version)


