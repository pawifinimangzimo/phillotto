import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path
import yaml
import sympy
from typing import Dict, List, Any

class HistoricalAnalyzer:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.historical = None
        self.number_pool = None
        self.num_cols = None
        self._load_data()
    
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _validate_data_file(self, path):
        """Thorough file validation before pandas attempts reading"""
        path = Path(path)
        
        # 1. File existence
        if not path.exists():
            raise ValueError(f"File does not exist: {path}")
        
        # 2. File size check
        if path.stat().st_size == 0:
            raise ValueError(f"File is empty: {path}")
        
        # 3. Read first line for content check
        with open(path, 'r') as f:
            first_line = f.readline().strip()
            if not first_line:
                raise ValueError(f"First line is empty in: {path}")
            
            # 4. Verify delimiter
            if ',' not in first_line:
                raise ValueError(f"No comma delimiter found in first line: {first_line}")
        
        return True

    def _load_data(self):
        num_select = self.config['strategy']['numbers_to_select']
        self.num_cols = [f'n{i+1}' for i in range(num_select)]
        
        try:
            self._validate_data_file(self.config['data']['historical_path'])
            
            self.historical = pd.read_csv(
                self.config['data']['historical_path'],
                header=None if not self.config['data']['has_header'] else 0,
                names=['date', 'numbers'],
                on_bad_lines='error'    
            )
            
            if len(self.historical) == 0:
                raise ValueError("File has header but no data rows")

            self.historical[self.num_cols] = self.historical['numbers'].str.split('-', expand=True).astype(int)
            self.historical['date'] = pd.to_datetime(
                self.historical['date'], 
                format=self.config['data']['date_format']
            )
            self.number_pool = list(range(1, self.config['strategy']['number_pool'] + 1))

        except Exception as e:
        # Enhanced error context
        raise ValueError(
            f"Failed to load {self.config['data']['historical_path']}\n"
            f"Error: {str(e)}\n"
            f"File must be:\n"
            f"- Comma-delimited\n"
            f"- First column: dates\n"
            f"- Second column: numbers as 1-2-3-4-5-6\n"
            f"Example:\n01/01/2020,5-10-15-20-25-30"
        )
Debugging Steps:




    def run(self, test_draws=None):
        test_draws = test_draws or self.config['validation']['test_draws']
        test_data = self.historical.iloc[-test_draws:] if test_draws else self.historical
        
        stats = {
            'metadata': {
                'draws_analyzed': len(test_data),
                'date_range': {
                    'start': test_data['date'].min().strftime('%Y-%m-%d'),
                    'end': test_data['date'].max().strftime('%Y-%m-%d')
                }
            },
            'frequency': self._get_frequency_stats(test_data),
            'temperature': self._get_temperature_stats(test_data),
            'combinations': self._get_serializable_combinations(test_data),
            'primes': self._get_prime_stats(test_data),
            'gaps': self._get_gap_stats(test_data) if self.config['analysis']['gap_analysis']['enabled'] else None,
            'odd_even': self._get_odd_even_stats(test_data),
            'sums': self._get_sum_stats(test_data),
            'high_low': self._get_high_low_stats(test_data)
        }
        
        self._save_report(stats)
        return stats
    
    def _should_display(self, section):
        """Check if a section should be displayed"""
        return self.config['display'].get(f'show_{section}', False)
    
    def _get_display_config(self, section, key, default=None):
        """Get display configuration value"""
        return self.config['display'].get(section, {}).get(key, default)

    def _get_frequency_stats(self, data):
        freq = data[self.num_cols].stack().value_counts()
        min_freq = self._get_display_config('frequency', 'min_frequency', 0)
        filtered = freq[freq >= min_freq]
        return {
            'top': filtered.head(self._get_display_config('frequency', 'top_range', 10)).to_dict(),
            'all': freq.to_dict(),
            'min_frequency': min_freq
        }
    
    def _get_temperature_stats(self, data):
        recency = {}
        for num in self.number_pool:
            mask = data[self.num_cols].eq(num).any(axis=1)
            last_idx = data[mask].index.max()
            recency[num] = len(data) - last_idx - 1 if not pd.isna(last_idx) else float('inf')
        
        return {
            'hot': [n for n,r in recency.items() if r <= self.config['analysis']['recency_bins']['hot']],
            'warm': [n for n,r in recency.items() if 
                    self.config['analysis']['recency_bins']['hot'] < r <= self.config['analysis']['recency_bins']['warm']],
            'cold': [n for n,r in recency.items() if r > self.config['analysis']['recency_bins']['cold']]
        }
    
    def _get_prime_stats(self, data):
        primes = [n for n in self.number_pool if sympy.isprime(n)]
        freq = self._get_frequency_stats(data)['all']
        return {
            'primes_in_pool': primes,
            'prime_frequency': {p: freq.get(p, 0) for p in primes},
            'prime_percentage': len(primes) / len(self.number_pool),
            'highlight_threshold': self._get_display_config('primes', 'highlight_over', 10)
        }
    
    def _get_high_low_stats(self, data):
        low_max = self.config['strategy']['low_number_max']
        return {
            'low_numbers': [n for n in self.number_pool if n <= low_max],
            'high_numbers': [n for n in self.number_pool if n > low_max],
            'avg_low_per_draw': data[self.num_cols].apply(
                lambda x: sum(1 for n in x if n <= low_max), axis=1).mean(),
            'low_cutoff': low_max
        }
    
    def _get_serializable_combinations(self, data):
        if not self._should_display('combinations'):
            return None
            
        combo_data = self._get_combination_stats(data)
        return {
            size: {'-'.join(map(str, combo)): count 
                  for combo, count in combinations_dict.items()}
            for size, combinations_dict in combo_data.items()
        }
    
    def _get_combination_stats(self, data):
        combo_data = defaultdict(int)
        for _, row in data.iterrows():
            nums = sorted(row[self.num_cols])
            for size in range(2, 7):
                if not self.config['analysis']['combination_analysis'].get(
                    {2:'pairs',3:'triplets',4:'quadruplets',5:'quintuplets',6:'sixtuplets'}[size], False):
                    continue
                for combo in combinations(nums, size):
                    combo_data[combo] += 1
        
        return {
            size: {k:v for k,v in combo_data.items() if len(k) == size}
            for size in [2,3,4,5,6]
            if self.config['analysis']['combination_analysis'].get(
                {2:'pairs',3:'triplets',4:'quadruplets',5:'quintuplets',6:'sixtuplets'}[size], False)
        }
    
    def _get_gap_stats(self, data):
        gap_counts = defaultdict(int)
        number_gaps = defaultdict(list)
        
        for _, row in data.iterrows():
            nums = sorted(row[self.num_cols])
            for i in range(1, len(nums)):
                gap = nums[i] - nums[i-1]
                gap_counts[gap] += 1
                number_gaps[nums[i]].append(gap)
        
        overdue = [
            num for num, gaps in number_gaps.items() 
            if sum(gaps)/len(gaps) > self.config['analysis']['gap_analysis']['threshold']
        ]
        
        return {
            'common_gaps': dict(sorted(gap_counts.items())),
            'overdue_numbers': overdue,
            'avg_gap_size': sum(k*v for k,v in gap_counts.items())/sum(gap_counts.values()),
            'threshold': self.config['analysis']['gap_analysis']['threshold']
        }
    
    def _get_odd_even_stats(self, data):
        odd_even = defaultdict(int)
        for _, row in data.iterrows():
            odds = sum(1 for n in row[self.num_cols] if n % 2 == 1)
            odd_even[odds] += 1
        return dict(sorted(odd_even.items()))
    
    def _get_sum_stats(self, data):
        sums = data[self.num_cols].sum(axis=1)
        return {
            'min': int(sums.min()),
            'max': int(sums.max()),
            'mean': float(sums.mean()),
            'std_dev': float(sums.std())
        }
    
    def _save_report(self, stats):
        def convert(o):
            if isinstance(o, (np.integer, np.int64)):
                return int(o)
            elif isinstance(o, (np.floating, np.float64)):
                return float(o)
            elif isinstance(o, np.ndarray):
                return o.tolist()
            elif isinstance(o, pd.Timestamp):
                return o.isoformat()
            raise TypeError(f"Object of type {type(o)} is not JSON serializable")

        Path(self.config['data']['stats_dir']).mkdir(parents=True, exist_ok=True)
        with open(Path(self.config['data']['stats_dir']) / 'analysis_report.json', 'w') as f:
            json.dump(stats, f, indent=2, default=convert)