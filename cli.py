#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from core.optimizer import LotteryOptimizer
from core.validator import LotteryValidator
from pathlib import Path
import yaml
import json
import sys

class NaturalOrderGroup(click.Group):
    """Preserve command order in help output"""
    def list_commands(self, ctx):
        return self.commands.keys()

@click.group(cls=NaturalOrderGroup, invoke_without_command=True, 
             help="🎰 Lottery Number Optimizer CLI\n\nGenerate statistically optimized lottery numbers")
@click.option('--config', default='config.yaml', show_default=True,
              help="📄 Path to config file")
@click.version_option("1.0", message="%(prog)s v%(version)s")
@click.pass_context
def cli(ctx, config):
    """Main entry point"""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

# Analysis Commands
@cli.command(help="📊 Analyze historical draw patterns")
@click.option('--test-draws', type=click.IntRange(1,1000), 
              help="🔢 Analyze last N draws [1-1000]")
@click.option('--show-gaps', is_flag=True,
              help="📈 Display gap analysis")
@click.option('--save', is_flag=True,
              help="💾 Save report to JSON")
def analyze(test_draws, show_gaps, save):
    """Run historical analysis"""
    analyzer = HistoricalAnalyzer()
    stats = analyzer.run(test_draws)
    
    if show_gaps:
        validator = LotteryValidator()
        gap_report = validator.get_overdue_report()
        if gap_report:
            click.secho("\nGap Analysis:", fg='cyan')
            click.echo(f"Overdue Numbers (Avg Gap >{analyzer.config['analysis']['gap_analysis']['threshold']}):")
            for num in gap_report['overdue_numbers']:
                click.echo(f"  #{num['number']}: Last seen {num['draws_since_last']} draws ago")
    
    if save:
        report_path = Path(analyzer.config['data']['stats_dir']) / 'analysis.json'
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=2)
        click.secho(f"\nReport saved to {report_path}", fg='green')
    
    click.secho("\nAnalysis Summary:", fg='blue')
    click.echo(f"• Top Numbers: {list(stats['frequency']['top'].keys())}")
    click.echo(f"• Hot Numbers: {stats['temperature']['hot']}")
    click.echo(f"• Cold Numbers: {stats['temperature']['cold']}")

# Generation Commands
@cli.command(help="🎲 Generate optimized number sets")
@click.option('--sets', type=click.IntRange(1,100), default=4,
              show_default=True, help="🔢 Number of sets to generate")
@click.option('--strategy', type=click.Choice(['weighted', 'high_low', 'prime', 'auto']),
              default='auto', show_default=True,
              help="📊 Generation strategy:\n"
                   "weighted = Frequency-based\n"
                   "high_low = Balanced high/low\n"
                   "prime = Prime number focus\n"
                   "auto = Mixed strategies")
@click.option('--save', is_flag=True,
              help="💾 Save to generated_sets.csv")
def generate(sets, strategy, save):
    """Generate number sets"""
    opt = LotteryOptimizer()
    
    strategies = {
        'weighted': opt._generate_weighted_random,
        'high_low': opt._generate_high_low_mix,
        'prime': opt._generate_prime_balanced,
        'auto': opt.generate_valid_set
    }
    
    generated_sets = [strategies[strategy]() for _ in range(sets)]
    
    click.secho("\nGenerated Sets:", fg='blue')
    for i, nums in enumerate(generated_sets, 1):
        click.echo(f"Set {i}: {nums}")
    
    if save:
        save_path = Path(opt.config['data']['results_dir']) / 'generated_sets.csv'
        try:
            with open(save_path, 'w') as f:
                f.write("numbers\n")
                for nums in generated_sets:
                    f.write(f"{'-'.join(map(str, nums))}\n")
            click.secho(f"Saved to {save_path}", fg='green')
        except Exception as e:
            click.secho(f"Error saving: {e}", fg='red')

# Validation Commands
@cli.command(help="✅ Validate generated sets")
@click.option('--against-latest', is_flag=True,
              help="🆚 Compare against latest draw")
@click.option('--test-draws', type=click.IntRange(10,1000), default=120,
              show_default=True, help="📅 Draws to test against")
@click.option('--threshold', type=click.IntRange(1,6), default=4,
              show_default=True, help="🎯 Match threshold")
def validate(against_latest, test_draws, threshold):
    """Validate number sets"""
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

# Utility Commands
@cli.command(help="⚙️ Initialize system")
def setup():
    """Initialize directories"""
    from bootstrap import setup_dirs
    setup_dirs()
    click.secho("System ready!", fg='green')

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        click.secho(f"Error: {e}", fg='red')
        sys.exit(1)