import numpy as np
import random
import sympy
from collections import defaultdict
from pathlib import Path

class LotteryOptimizer:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.analyzer = HistoricalAnalyzer(config_path)
        self.number_pool = list(range(1, self.config['strategy']['number_pool'] + 1))
        self.prime_numbers = [n for n in self.number_pool if sympy.isprime(n)]
        self.weights = None
        self._calculate_weights()
    
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _calculate_weights(self):
        # Frequency weights
        freq = self.analyzer._get_frequency_stats(self.analyzer.historical)['all']
        freq_weights = np.array([freq.get(n, 0) for n in self.number_pool])
        
        # Recency weights
        temp = self.analyzer._get_temperature_stats(self.analyzer.historical)
        recency_weights = np.array([
            3 if n in temp['hot'] else
            2 if n in temp['warm'] else
            1 for n in self.number_pool
        ])
        
        # Base weights
        self.weights = (
            self.config['strategy']['frequency_weight'] * freq_weights +
            self.config['strategy']['recent_weight'] * recency_weights +
            self.config['strategy']['random_weight'] * np.random.rand(len(self.number_pool))
        )
        self.weights /= self.weights.sum()
    
    def generate_sets(self, n_sets=None):
        n_sets = n_sets or self.config['output']['sets_to_generate']
        return [self.generate_valid_set() for _ in range(n_sets)]
    
    def generate_valid_set(self):
        strategies = [
            self._generate_weighted_random,
            self._generate_high_low_mix,
            self._generate_prime_balanced
        ]
        
        for _ in range(1000):
            nums = random.choice(strategies)()
            if (self._enforce_odd_even_balance(nums) and 
                self._validate_sum_range(nums)):
                return nums
        raise ValueError("Failed to generate valid set after 1000 attempts")
    
    def _generate_weighted_random(self):
        return sorted(np.random.choice(
            self.number_pool,
            size=self.config['strategy']['numbers_to_select'],
            replace=False,
            p=self.weights
        ))
    
    def _generate_high_low_mix(self):
        low_max = self.config['strategy']['low_number_max']
        low_nums = [n for n in self.number_pool if n <= low_max]
        high_nums = [n for n in self.number_pool if n > low_max]
        
        split = max(1, self.config['strategy']['numbers_to_select'] // 2)
        selected = (
            random.sample(low_nums, split) +
            random.sample(high_nums, self.config['strategy']['numbers_to_select'] - split)
        )
        return sorted(selected)
    
    def _generate_prime_balanced(self):
        num_primes = random.choice([1, 2])  # 1-2 primes per set
        primes = random.sample(
            [n for n in self.prime_numbers if n > self.config['strategy']['high_prime_min']],
            min(num_primes, len(self.prime_numbers))
        )
        non_primes = random.sample(
            [n for n in self.number_pool if n not in self.prime_numbers],
            self.config['strategy']['numbers_to_select'] - len(primes))
        )
        return sorted(primes + non_primes)
    
    def _enforce_odd_even_balance(self, numbers):
        odds = sum(1 for n in numbers if n % 2 == 1)
        return (
            self.config['analysis']['odd_even']['min_odds'] <= odds <= 
            self.config['analysis']['odd_even']['max_odds']
        )
    
    def _validate_sum_range(self, numbers):
        total = sum(numbers)
        return (
            self.config['analysis']['sum_range']['min'] <= total <= 
            self.config['analysis']['sum_range']['max']
        )