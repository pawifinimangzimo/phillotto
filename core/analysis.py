import yaml
import pandas as pd
import numpy as np
import sympy
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict, Counter

class HistoricalAnalyzer:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.historical = self._load_historical_data()
        self.number_pool = list(range(1, self.config['lottery']['number_pool'] + 1))
        self.num_cols = [f'n{i+1}' for i in range(self.config['lottery']['numbers_to_draw'])]

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        Path(config['data']['stats_dir']).mkdir(parents=True, exist_ok=True)
        return config

    def _load_historical_data(self) -> pd.DataFrame:
        try:
            df = pd.read_csv(
                self.config['data']['historical_path'],
                header=None if not self.config['data']['has_header'] else 0,
                names=['date'] + self.num_cols,
                parse_dates=['date'],
                date_format=self.config['data']['date_format']
            )
            return df.sort_values('date')
        except Exception as e:
            raise ValueError(f"Failed to load historical data: {str(e)}")

    # =====================
    # Gap Analysis Methods
    # =====================
    
    def get_overdue_numbers(self) -> Dict[int, int]:
        if not self.config['analysis']['overdue']['enabled']:
            return {}
            
        last_seen = {}
        for idx, row in self.historical.iterrows():
            for num in row[self.num_cols]:
                last_seen[num] = idx
                
        threshold = self.config['analysis']['overdue']['threshold']
        return {
            num: len(self.historical) - pos - 1
            for num, pos in last_seen.items()
            if (len(self.historical) - pos - 1) >= threshold
        }

    def analyze_inter_number_gaps(self, numbers: List[int]) -> Dict:
        if not self.config['analysis']['inter_number_gaps']['enabled']:
            return {}
            
        sorted_nums = sorted(numbers)
        gaps = [sorted_nums[i] - sorted_nums[i-1] for i in range(1, len(sorted_nums))]
        
        return {
            'average': float(np.mean(gaps)),
            'max': max(gaps),
            'min': min(gaps),
            'histogram': dict(Counter(gaps)),
            'is_valid': (
                np.mean(gaps) <= self.config['analysis']['inter_number_gaps']['max_avg'] and
                max(gaps) <= self.config['analysis']['inter_number_gaps']['max_single'] and
                len(set(gaps)) >= self.config['analysis']['inter_number_gaps']['min_variety']
            )
        }

    # =====================
    # Pattern Analysis
    # =====================
    
    def analyze_primes(self, numbers: List[int]) -> Dict:
        if not self.config['analysis']['primes']['enabled']:
            return {}
            
        primes = [n for n in numbers if sympy.isprime(n)]
        return {
            'primes': primes,
            'count': len(primes),
            'is_valid': len(primes) >= self.config['analysis']['primes']['min_primes']
        }

    def analyze_even_odd(self, numbers: List[int]) -> Dict:
        if not self.config['analysis']['even_odd']['enabled']:
            return {}
            
        odds = sum(1 for n in numbers if n % 2 != 0)
        ratio = odds / len(numbers)
        target = self.config['analysis']['even_odd']['target_ratio']
        tolerance = self.config['analysis']['even_odd']['tolerance']
        
        return {
            'odds': odds,
            'ratio': ratio,
            'is_valid': abs(ratio - target) <= tolerance
        }

    def full_analysis(self, numbers: List[int]) -> Dict:
        """Run all enabled analyses"""
        return {
            'overdue': self.get_overdue_numbers(),
            'inter_number_gaps': self.analyze_inter_number_gaps(numbers),
            'primes': self.analyze_primes(numbers),
            'even_odd': self.analyze_even_odd(numbers),
            'sum': sum(numbers),
            'sum_valid': (
                self.config['lottery']['min_sum'] <= sum(numbers) <= self.config['lottery']['max_sum']
            )
        }