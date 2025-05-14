import pandas as pd
from pathlib import Path
from collections import defaultdict
import yaml
import numpy as np
import json
from typing import Dict, List, Optional, Union
from .analysis import HistoricalAnalyzer

class LotteryValidator:
    def __init__(self, config_path: str = "config.yaml") -> None:
        """Initialize validator with configuration and data checks."""
        self.config = self._load_config(config_path)
        self.analyzer = HistoricalAnalyzer(config_path)
        self._validate_initial_data()

    def _load_config(self, config_path: str) -> Dict:
        """Load and validate configuration file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found at {config_path}")
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config.get('data'):
            raise ValueError("Invalid config: Missing 'data' section")
        return config

    def _validate_initial_data(self) -> None:
        """Verify required data files exist at initialization."""
        required_files = [
            Path(self.config['data']['historical_path']),
            Path(self.config['data']['latest_path'])
        ]
        for file in required_files:
            if not file.exists():
                raise FileNotFoundError(f"Required data file not found: {file}")

    def validate_sets(self, sets: List[List[int]], test_draws: Optional[int] = None) -> List[Dict]:
        """Validate generated number sets against historical draws."""
        test_draws = test_draws or self.config['validation']['test_draws']
        test_data = self.analyzer.historical.iloc[-test_draws:]
        
        if test_data.empty:
            raise ValueError("No historical data available for validation")

        results = []
        for numbers in sets:
            clean_numbers = [int(num) for num in numbers]
            matches = []
            
            for _, draw in test_data.iterrows():
                draw_numbers = [draw[f'n{i+1}'] for i in range(self.config['strategy']['numbers_to_select'])]
                matches.append(len(set(clean_numbers) & set(draw_numbers)))

            results.append({
                'numbers': clean_numbers,
                'match_distribution': self._count_matches(matches),
                'success_rate': self._calculate_success_rate(
                    matches, 
                    self.config['validation']['alert_threshold']
                )
            })
        return results

    def _count_matches(self, matches: List[int]) -> Dict[int, int]:
        """Convert match list to distribution dictionary."""
        distribution = defaultdict(int)
        for count in matches:
            distribution[count] += 1
        return dict(sorted(distribution.items()))

    def _calculate_success_rate(self, matches: List[int], threshold: int) -> float:
        """
        Calculate percentage of draws meeting or exceeding threshold.
        
        Args:
            matches: List of match counts (e.g., [3, 4, 2])
            threshold: Minimum matches to consider successful
            
        Returns:
            Success rate between 0.0 and 1.0
        """
        if not matches:
            return 0.0
        successful = sum(1 for m in matches if m >= threshold)
        return successful / len(matches)

    def check_latest_draw(self) -> Optional[Dict]:
        """Analyze numbers from the latest draw."""
        latest_path = Path(self.config['data']['latest_path'])
        if not latest_path.exists():
            raise FileNotFoundError(f"Latest draw file not found at {latest_path}")

        try:
            latest = pd.read_csv(
                latest_path,
                header=None if not self.config['data']['has_header'] else 0,
                names=['date', 'numbers'],
                dtype={'date': str, 'numbers': str},
                on_bad_lines='error'
            )
            
            if latest.empty:
                raise ValueError("Latest draw file is empty")

            latest_numbers = [int(n) for n in latest.iloc[0]['numbers'].split('-')]
            
            return {
                'numbers': sorted(latest_numbers),
                'analysis': {
                    num: {
                        'status': 'hot' if num in self.analyzer._get_temperature_stats(self.analyzer.historical)['hot'] else 
                                 'cold' if num in self.analyzer._get_temperature_stats(self.analyzer.historical)['cold'] else 'neutral',
                        'frequency': int(self.analyzer._get_frequency_stats(self.analyzer.historical)['all'].get(num, 0))
                    }
                    for num in latest_numbers
                }
            }
        except Exception as e:
            raise ValueError(f"Failed to parse latest draw: {str(e)}")

    def get_overdue_report(self) -> Dict:
        """Generate report on overdue numbers with gap analysis."""
        if not self.config['analysis']['gap_analysis']['enabled']:
            return {'status': 'gap_analysis_disabled'}

        gaps = self.analyzer._get_gap_stats(self.analyzer.historical)
        report = {
            'overdue_numbers': [],
            'common_gaps': {int(k): int(v) for k, v in gaps['common_gaps'].items()},
            'metadata': {
                'total_draws': len(self.analyzer.historical),
                'gap_threshold': self.config['analysis']['gap_analysis']['threshold']
            }
        }

        for num in gaps['overdue_numbers']:
            last_seen = len(self.analyzer.historical) - \
                       self.analyzer.historical[
                           self.analyzer.historical[self.analyzer.num_cols].eq(num).any(axis=1)
                       ].index.max() - 1
            
            report['overdue_numbers'].append({
                'number': int(num),
                'draws_since_last': int(last_seen),
                'average_gap': float(np.mean([
                    abs(num - n) for n in self.analyzer.number_pool
                    if n != num
                ]))
            })
        return report

    def save_validation_report(self, results: List[Dict], filename: str = "validation_report.json") -> Path:
        """Save validation results to JSON with proper serialization."""
        report_path = Path(self.config['data']['stats_dir']) / filename
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        def serialize(obj):
            if isinstance(obj, (np.integer, np.int64)):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=serialize)
        return report_path