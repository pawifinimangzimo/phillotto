import yaml
from typing import List, Dict
from pathlib import Path
from .analysis import HistoricalAnalyzer

class LotteryValidator:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.analyzer = HistoricalAnalyzer(config_path)

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def validate_draw(self, numbers: List[int]) -> Dict[str, Dict]:
        """Comprehensive validation with both gap types"""
        if len(numbers) != self.config['lottery']['numbers_to_draw']:
            raise ValueError("Incorrect number of balls drawn")

        results = {
            'basic': {
                'count': len(numbers),
                'unique': len(set(numbers)) == len(numbers),
                'in_range': all(1 <= n <= self.config['lottery']['number_pool'] for n in numbers)
            }
        }
        
        # Standard gap validation
        if self.config['analysis']['overdue']['enabled']:
            overdue = self.analyzer.get_overdue_numbers()
            results['overdue'] = {
                'count': sum(1 for n in numbers if n in overdue),
                'valid': (
                    self.config['generation']['gap_constraints']['overdue']['min_include'] <= 
                    sum(1 for n in numbers if n in overdue) <= 
                    self.config['generation']['gap_constraints']['overdue']['max_include']
                )
            }

        # Inter-number gap validation
        if self.config['analysis']['inter_number_gaps']['enabled']:
            gap_stats = self.analyzer.analyze_inter_number_gaps(numbers)
            results['inter_number_gaps'] = {
                **gap_stats,
                'valid': gap_stats['is_valid']
            }

        # Number properties
        if self.config['analysis']['primes']['enabled']:
            results['primes'] = self.analyzer.analyze_primes(numbers)
            
        if self.config['analysis']['even_odd']['enabled']:
            results['even_odd'] = self.analyzer.analyze_even_odd(numbers)
            
        # Sum validation
        total = sum(numbers)
        results['sum'] = {
            'total': total,
            'valid': self.config['lottery']['min_sum'] <= total <= self.config['lottery']['max_sum']
        }
            
        # Overall validation
        results['is_valid'] = all(
            v['valid'] for k, v in results.items() 
            if k != 'is_valid' and 'valid' in v
        ) and results['basic']['unique'] and results['basic']['in_range']
        
        return results