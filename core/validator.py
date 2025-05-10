import pandas as pd
from pathlib import Path
from collections import defaultdict

class LotteryValidator:
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.analyzer = HistoricalAnalyzer(config_path)
    
    def _load_config(self, config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def validate_sets(self, sets=None, test_draws=None):
        test_draws = test_draws or self.config['validation']['test_draws']
        test_data = self.analyzer.historical.iloc[-test_draws:]
        num_cols = self.analyzer.num_cols
        
        results = []
        for numbers in sets or []:
            matches = []
            for _, draw in test_data.iterrows():
                match = len(set(numbers) & set(draw[num_cols]))
                matches.append(match)
            
            results.append({
                'numbers': numbers,
                'match_distribution': {
                    i: matches.count(i) 
                    for i in range(self.config['strategy']['numbers_to_select'] + 1)
                },
                'success_rate': sum(
                    1 for m in matches 
                    if m >= self.config['validation']['alert_threshold']
                ) / len(matches)
            })
        
        return results
    
    def get_overdue_report(self):
        if not self.config['analysis']['gap_analysis']['enabled']:
            return None
            
        gaps = self.analyzer._get_gap_stats(self.analyzer.historical)
        overdue = gaps['overdue_numbers']
        
        report = {
            'overdue_numbers': [],
            'common_gaps': gaps['common_gaps']
        }
        
        for num in overdue:
            mask = self.analyzer.historical[self.analyzer.num_cols].eq(num).any(axis=1)
            last_seen = len(self.analyzer.historical) - self.analyzer.historical[mask].index.max() - 1
            report['overdue_numbers'].append({
                'number': num,
                'draws_since_last': int(last_seen),
                'average_gap': sum(gaps['common_gaps'].get(abs(num - n), 0) 
                              for n in self.analyzer.number_pool) / len(self.analyzer.number_pool)
            })
        
        return report
    
    def check_latest_draw(self):
        if not Path(self.config['data']['latest_path']).exists():
            return None
            
        latest = pd.read_csv(self.config['data']['latest_path'])
        latest_numbers = set(latest.iloc[0][self.analyzer.num_cols])
        
        analysis = {
            'hot_numbers': self.analyzer._get_temperature_stats(self.analyzer.historical)['hot'],
            'cold_numbers': self.analyzer._get_temperature_stats(self.analyzer.historical)['cold']
        }
        
        return {
            'numbers': sorted(latest_numbers),
            'analysis': {
                num: {
                    'status': 'hot' if num in analysis['hot_numbers'] else 
                             'cold' if num in analysis['cold_numbers'] else 'neutral',
                    'frequency': self.analyzer._get_frequency_stats(self.analyzer.historical)['all'].get(num, 0)
                }
                for num in latest_numbers
            }
        }