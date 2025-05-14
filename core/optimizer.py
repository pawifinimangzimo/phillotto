import random
import numpy as np
from typing import List
from pathlib import Path
import yaml
from .analysis import HistoricalAnalyzer
from .validator import LotteryValidator

class LotteryOptimizer:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.analyzer = HistoricalAnalyzer(config_path)
        self.validator = LotteryValidator(config_path)
        self.number_pool = list(range(1, self.config['lottery']['number_pool'] + 1))

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def generate_set(self, max_attempts: int = 1000) -> List[int]:
        """Generate numbers with all constraints"""
        strategies = [
            self._generate_weighted,
            self._generate_balanced,
            self._generate_random
        ]
        
        for attempt in range(max_attempts):
            numbers = random.choice(strategies)()
            if self.validator.validate_draw(numbers)['is_valid']:
                return sorted(numbers)
                
        raise ValueError(f"Failed to generate valid set after {max_attempts} attempts")

    def _generate_weighted(self) -> List[int]:
        """Weighted by frequency and gap properties"""
        weights = np.ones(len(self.number_pool))
        freq = self._get_frequency_weights()
        overdue = self.analyzer.get_overdue_numbers()
        
        for i, num in enumerate(self.number_pool):
            # Frequency weighting
            weights[i] *= freq.get(num, 1.0)
            
            # Overdue boost
            if num in overdue:
                weights[i] *= 1.5
                
            # Gap penalty
            for n in self.number_pool:
                if abs(num - n) > self.config['generation']['gap_constraints']['inter_number']['max_single_gap']:
                    weights[i] *= 0.7
                    
        return random.choices(
            population=self.number_pool,
            weights=weights,
            k=self.config['lottery']['numbers_to_draw']
        )

    def _generate_balanced(self) -> List[int]:
        """Balanced gap distribution approach"""
        # Start with overdue numbers
        overdue = list(self.analyzer.get_overdue_numbers().keys())
        selected = random.sample(
            overdue,
            k=random.randint(
                self.config['generation']['gap_constraints']['overdue']['min_include'],
                self.config['generation']['gap_constraints']['overdue']['max_include']
            )
        )
        
        # Fill remaining with gap-balancing numbers
        while len(selected) < self.config['lottery']['numbers_to_draw']:
            candidates = [n for n in self.number_pool if n not in selected]
            next_num = min(
                candidates,
                key=lambda x: self._calculate_gap_score(selected + [x])
            )
            selected.append(next_num)
            
        return selected

    def _calculate_gap_score(self, numbers: List[int]) -> float:
        """Score based on gap distribution (lower is better)"""
        gaps = self.analyzer.analyze_inter_number_gaps(numbers)
        cfg = self.config['generation']['gap_constraints']['inter_number']
        
        score = 0
        if gaps['average'] > cfg['max_avg_gap']:
            score += (gaps['average'] - cfg['max_avg_gap']) * 10
        if gaps['max'] > cfg['max_single_gap']:
            score += (gaps['max'] - cfg['max_single_gap']) * 20
        return score

    def _get_frequency_weights(self) -> Dict[int, float]:
        """Get frequency-based weights for all numbers"""
        freq = defaultdict(int)
        for _, row in self.analyzer.historical.iterrows():
            for num in row[self.analyzer.num_cols]:
                freq[num] += 1
        max_freq = max(freq.values()) if freq else 1
        return {num: count/max_freq for num, count in freq.items()}

    def _generate_random(self) -> List[int]:
        """Fallback random generation"""
        return random.sample(self.number_pool, k=self.config['lottery']['numbers_to_draw'])