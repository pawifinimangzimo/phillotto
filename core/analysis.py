import pandas as pd
import numpy as np
from collections import defaultdict
from itertools import combinations
import json
from pathlib import Path
import yaml

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
    
    def _load_data(self):
        num_select = self.config['strategy']['numbers_to_select']
        self.num_cols = [f'n{i+1}' for i in range(num_select)]
        
        try:
            self.historical = pd.read_csv(
                self.config['data']['historical_path'],
                header=None if not self.config['data']['has_header'] else 0,
                names=['date', 'numbers']
            )
            self.historical[self.num_cols] = self.historical['numbers'].str.split('-', expand=True).astype(int)
            self.historical['date'] = pd.to_datetime(
                self.historical['date'], 
                format=self.config['data']['date_format']
            )
            self.number_pool = list(range(1, self.config['strategy']['number_pool'] + 1))
        except Exception as e:
            raise ValueError(f"Data loading failed: {str(e)}")

    def run(self, test_draws=None):
        test_draws = test_draws or self.config['validation']['test_draws']
        test_data = self.historical.iloc[-test_draws:] if test_draws else self.historical
        
        stats = {
            'frequency': self._get_frequency_stats(test_data),
            'temperature': self._get_temperature_stats(test_data),
            'combinations': self._get_serializable_combinations(test_data),
            'gaps': self._get_gap_stats(test_data) if self.config['analysis']['gap_analysis']['enabled'] else None,
            'odd_even': self._get_odd_even_stats(test_data),
            'sums': self._get_sum_stats(test_data)
        }
        
        self._save_report(stats)
        return stats
    
    def _get_frequency_stats(self, data):
        freq = data[self.num_cols].stack().value_counts()
        return {
            'top': freq.head(self.config['analysis']['top_range']).to_dict(),
            'all': freq.to_dict()
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
    
    def _get_serializable_combinations(self, data):
        """Convert tuple keys to strings for JSON serialization"""
        combo_data = self._get_combination_stats(data)
        serializable = {}
        
        for size, combinations_dict in combo_data.items():
            serializable[size] = {
                '-'.join(map(str, combo)): count 
                for combo, count in combinations_dict.items()
            }
        
        return serializable
    
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
            'overdue_numbers': overdue
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
            'mean': float(sums.mean())
        }
    
    def _save_report(self, stats):
        Path(self.config['data']['stats_dir']).mkdir(parents=True, exist_ok=True)
        with open(Path(self.config['data']['stats_dir']) / 'analysis_report.json', 'w') as f:
            json.dump(stats, f, indent=2, default=str)