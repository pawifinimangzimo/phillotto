import sys
from pathlib import Path
from .analysis import HistoricalAnalyzer
from .optimizer import LotteryOptimizer
from .validator import LotteryValidator

# Package version
__version__ = "1.0.0"

# Verify data directory exists
def _verify_data_dir():
    required_dirs = ['data/stats', 'data/results']
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)

# Expose main classes
__all__ = ['HistoricalAnalyzer', 'LotteryOptimizer', 'LotteryValidator']

# Initialize on import
_verify_data_dir()