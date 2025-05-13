#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from core.optimizer import LotteryOptimizer
from core.validator import LotteryValidator
from pathlib import Path
import yaml
import json

@click.group()
def cli():
    """Lottery Number Optimizer CLI"""
    pass

@cli.command()
@click.option('--test-draws', default=None, type=int, help='Number of historical draws to analyze')
@click.option('--show-gaps', is_flag=True, help='Show gap analysis')
@click.option('--save', is_flag=True, help='Save report to file')
def analyze(test_draws, show_gaps, save):
    """Run historical analysis"""
    analyzer = HistoricalAnalyzer()
    stats = analyzer.run(test_draws)
    
    if show_gaps:
        validator = LotteryValidator()
        gap_report = validator.get_overdue_report()
        if gap_report:
            click.echo("\nGap Analysis Report:")
            click.echo(f"Overdue Numbers (Avg Gap >{analyzer.config['analysis']['gap_analysis']['threshold']}):")
            for num in gap_report['overdue_numbers']:
                click.echo(f"  #{num['number']}: Last seen {num['draws_since_last']} draws ago")
    
    if save:
        report_path = Path(analyzer.config['data']['stats_dir']) / 'cli_analysis.json'
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=2)
        click.echo(f"\nReport saved to {report_path}")
    
    click.echo("\nAnalysis Summary:")
    click.echo(f"- Top Numbers: {list(stats['frequency']['top'].keys())}")
    click.echo(f"- Hot Numbers: {stats['temperature']['hot']}")
    click.echo(f"- Cold Numbers: {stats['temperature']['cold']}")

@cli.command()
@click.option('--sets', default=None, type=int, help='Number of sets to generate')
@click.option('--strategy', 
              type=click.Choice(['weighted', 'high_low', 'prime', 'balanced']),
              help='Generation strategy')
@click.option('--save', is_flag=True, help='Save sets to file')
def generate(sets, strategy, save):
    """Generate number sets"""
    opt = LotteryOptimizer()
    num_sets = sets or opt.config['output']['sets_to_select']
    
    strategies = {
        'weighted': opt._generate_weighted_random,
        'high_low': opt._generate_high_low_mix,
        'prime': opt._generate_prime_balanced,
        'balanced': opt.generate_valid_set
    }
    
    if strategy:
        sets = [strategies[strategy]() for _ in range(num_sets)]
    else:
        sets = opt.generate_sets(num_sets)
    
    click.echo("\nGenerated Number Sets:")
    for i, nums in enumerate(sets, 1):
        click.echo(f"Set {i}: {nums}")
    
    if save:
        save_path = Path(opt.config['data']['results_dir']) / 'generated_sets.csv'
        with open(save_path, 'w') as f:
            f.write("numbers\n")
            for nums in sets:
                f.write(f"{'-'.join(map(str, nums))}\n")
        click.echo(f"\nSets saved to {save_path}")

@cli.command()
@click.option('--against-latest', is_flag=True, help='Validate against latest draw')
@click.option('--test-draws', default=None, type=int, help='Number of historical draws to test against')
@click.option('--threshold', default=None, type=int, help='Match threshold for alerts')
def validate(against_latest, test_draws, threshold):
    """Validate generated sets"""
    val = LotteryValidator()
    
    if against_latest:
        result = val.check_latest_draw()
        if not result:
            click.echo("No latest draw found!")
            return
            
        click.echo(f"\nLatest Draw Analysis ({result['numbers']}):")
        for num, stats in result['analysis'].items():
            click.echo(f"  #{num}: {stats['status'].upper()} (appeared {stats['frequency']} times historically)")
    else:
        opt = LotteryOptimizer()
        sets = opt.generate_sets()
        test_draws = test_draws or val.config['validation']['test_draws']
        threshold = threshold or val.config['validation']['alert_threshold']
        
        results = val.validate_sets(sets, test_draws)
        
        click.echo(f"\nValidation Results (last {test_draws} draws):")
        for i, res in enumerate(results, 1):
            click.echo(f"\nSet {i}: {res['numbers']}")
            click.echo(f"Success Rate ({threshold}+ matches): {res['success_rate']:.1%}")
            click.echo("Match Distribution:")
            for matches, count in sorted(res['match_distribution'].items()):
                click.echo(f"  {matches} matches: {count} times")

@cli.command()
@click.argument('action', type=click.Choice(['setup', 'migrate']))
def utils(action):
    """Helper utilities"""
    if action == 'setup':
        if not Path('scripts/setup_env.sh').exists():
            click.echo("Error: setup script not found!")
            return
            
        click.echo("Running setup...")
        import subprocess
        subprocess.run(['./scripts/setup_env.sh'], shell=True)
    elif action == 'migrate':
        if not Path('scripts/migrate.sh').exists():
            click.echo("Error: migrate script not found!")
            return
            
        click.echo("Packaging project...")
        import subprocess
        subprocess.run(['./scripts/migrate.sh'], shell=True)

if __name__ == "__main__":
    cli()