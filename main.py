# main.py

from geo_indicators.stats import generate_stats

if __name__ == "__main__":
    source = "PANALESIS"
    version = "v1"
    generate_stats(source,version)

