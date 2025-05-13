#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from core.optimizer import LotteryOptimizer
from core.validator import LotteryValidator
from pathlib import Path
import json
import sys

class NaturalOrderGroup(click.Group):
    """Preserve command order in help output"""
    def list_commands(self, ctx):
        return self.commands.keys()

@click.group(cls=NaturalOrderGroup, invoke_without_command=True, 
             help="🎰 Lottery Number Optimizer CLI\nGenerate statistically optimized lottery numbers")
@click.option('--config', default='config.yaml', show_default=True,
              help="📄 Path to config file")
@click.version_option("1.0", message="%(prog)s v%(version)s")
@click.pass_context
def cli(ctx, config):
    """Main entry point"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Analysis Command
@cli.command(help="📊 Analyze historical draw patterns")
@click.option('--test-draws', type=int, 
              help="🔢 Number of historical draws to analyze")
@click.option('--show-all', is_flag=True,
              help="🌈 Show all analysis sections")
@click.option('--hide', multiple=True, type=click.Choice([
    'frequency', 'temperature', 'odd_even', 'sums', 
    'high_low', 'primes', 'gaps', 'combinations'
]), help="🚫 Sections to hide")
@click.option('--save', is_flag=True,
              help="💾 Save full report to JSON")
def analyze(test_draws, show_all, hide, save):
    analyzer = HistoricalAnalyzer()
    
    # Temporary config override
    if show_all or hide:
        display_config = analyzer.config['display'].copy()
        if show_all:
            for key in display_config:
                if key.startswith('show_'):
                    display_config[key] = True
        for section in hide:
            display_config[f'show_{section}'] = False
        analyzer.config['display'] = display_config
    
    stats = analyzer.run(test_draws)
    
    # Display header
    click.secho("\n⚡ ANALYSIS REPORT ⚡", fg='blue', bold=True)
    click.echo(f"Analyzed {stats['metadata']['draws_analyzed']} draws")
    click.echo("="*50)
    
    # Dynamic section display (same as previous version)
    # ... [include all the analysis display code from earlier] ...

# Generate Command (FULLY PRESERVED)
@cli.command(help="🎲 Generate optimized number sets")
@click.option('--sets', type=click.IntRange(1,100), default=4,
              show_default=True, help="🔢 Number of sets to generate")
@click.option('--strategy', type=click.Choice(['weighted', 'high_low', 'prime', 'auto']),
              default='auto', show_default=True,
              help="📊 Generation strategy")
@click.option('--save', is_flag=True,
              help="💾 Save to generated_sets.csv")
def generate(sets, strategy, save):
    opt = LotteryOptimizer()
    strategies = {
        'weighted': opt._generate_weighted_random,
        'high_low': opt._generate_high_low_mix,
        'prime': opt._generate_prime_balanced,
        'auto': opt.generate_valid_set
    }
    
    generated_sets = [strategies[strategy]() for _ in range(sets)]
    
    click.secho("\nGenerated Sets:", fg='green', bold=True)
    for i, nums in enumerate(generated_sets, 1):
        click.echo(f"Set {i}: {nums}")
    
    if save:
        save_path = Path(opt.config['data']['results_dir']) / 'generated_sets.csv'
        with open(save_path, 'w') as f:
            f.write("numbers\n")
            for nums in generated_sets:
                f.write(f"{'-'.join(map(str, nums))}\n")
        click.secho(f"Saved to {save_path}", fg='green')

# Validate Command (FULLY PRESERVED)
@cli.command(help="✅ Validate generated sets")
@click.option('--against-latest', is_flag=True,
              help="🆚 Compare against latest draw")
@click.option('--test-draws', type=click.IntRange(10,1000), default=120,
              show_default=True, help="📅 Draws to test against")
@click.option('--threshold', type=click.IntRange(1,6), default=4,
              show_default=True, help="🎯 Match threshold")
def validate(against_latest, test_draws, threshold):
    val = LotteryValidator()
    
    if against_latest:
        result = val.check_latest_draw()
        if not result:
            click.secho("No latest draw found!", fg='red')
            return
            
        click.secho(f"\nLatest Draw Analysis ({result['numbers']}):", fg='blue')
        for num, stats in result['analysis'].items():
            status_color = 'green' if stats['status'] == 'hot' else 'red' if stats['status'] == 'cold' else 'white'
            click.echo(f"  #{num}: ", nl=False)
            click.secho(f"{stats['status'].upper()}", fg=status_color, nl=False)
            click.echo(f" (appeared {stats['frequency']} times)")
    else:
        opt = LotteryOptimizer()
        sets = opt.generate_sets()
        results = val.validate_sets(sets, test_draws)
        
        click.secho(f"\nValidation Results (last {test_draws} draws):", fg='blue')
        for i, res in enumerate(results, 1):
            click.echo(f"\nSet {i}: {res['numbers']}")
            success_color = 'green' if res['success_rate'] > 0.3 else 'yellow' if res['success_rate'] > 0.1 else 'red'
            click.echo(f"Success Rate ({threshold}+ matches): ", nl=False)
            click.secho(f"{res['success_rate']:.1%}", fg=success_color)
            click.echo("Match Distribution:")
            for matches, count in sorted(res['match_distribution'].items()):
                click.echo(f"  {matches} matches: {count} times")

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')
        sys.exit(1)