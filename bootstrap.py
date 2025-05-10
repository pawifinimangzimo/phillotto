#!/usr/bin/env python3
import shutil
import os
from pathlib import Path

CONFIG_TEMPLATE = """
# Auto-generated config
data:
  historical_path: "data/historical.csv"
  results_dir: "data/results/"
  stats_dir: "data/stats/"
"""

def setup_dirs():
    Path("data").mkdir(exist_ok=True)
    for d in ["stats", "results", "archive"]:
        Path(f"data/{d}").mkdir(exist_ok=True)
    
    if not Path("config.yaml").exists():
        with open("config.yaml", "w") as f:
            f.write(CONFIG_TEMPLATE)
        print("ℹ️ Created default config.yaml")

if __name__ == "__main__":
    setup_dirs()
    print("🏁 Bootstrap complete! Edit config.yaml as needed")