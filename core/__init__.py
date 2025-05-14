# core/__init__.py
from core.analysis import HistoricalAnalyzer
from core.optimizer import LotteryOptimizer
from core.validator import LotteryValidator

__all__ = ['HistoricalAnalyzer', 'LotteryOptimizer', 'LotteryValidator']
__version__ = "1.0.0"

def init_package():
    """Initialize package resources"""
    from pathlib import Path
    import os
    
    # Create required data directories
    required_dirs = [
        'data/stats',
        'data/results'
    ]
    for dir_path in required_dirs:
        os.makedirs(dir_path, exist_ok=True)

# Initialize on first import
init_package()