import click
import yaml
from pathlib import Path
from typing import List
from .analysis import HistoricalAnalyzer
from .optimizer import LotteryOptimizer
from .validator import LotteryValidator

@click.group()
@click.option('--config', default='config.yaml', help='Path to config file')
@click.pass_context
def cli(ctx, config):
    """Lottery Number Optimizer CLI"""
    ctx.ensure_object(dict)
    with open(config, 'r') as f:
        ctx.obj['config'] = yaml.safe_load(f)
    Path(ctx.obj['config']['data']['stats_dir']).mkdir(parents=True, exist_ok=True)

@cli.command()
@click.option('--show-gaps', is_flag=True, help="Show gap analysis")
@click.pass_context
def analyze(ctx, show_gaps):
    """Analyze historical patterns"""
    analyzer = HistoricalAnalyzer(ctx.obj['config'])
    latest = analyzer.historical.iloc[-1][analyzer.num_cols].tolist()
    
    results = analyzer.full_analysis(latest)
    
    click.secho("\n=== ANALYSIS REPORT ===", bold=True)
    click.echo(f"Latest Draw: {sorted(latest)}")
    
    # Overdue numbers display
    if analyzer.config['analysis']['overdue']['enabled']:
        click.secho("\n🔴 Overdue Numbers:", fg='red')
        overdue = results['overdue']
        for num, draws in list(overdue.items())[:analyzer.config['display']['overdue']['max_display']]:
            status = "COLD" if draws >= analyzer.config['analysis']['overdue']['cold_threshold'] else "OVERDUE"
            click.echo(f"#{num}: {draws} draws ({status})")
    
    # Inter-number gap display
    if show_gaps and analyzer.config['analysis']['inter_number_gaps']['enabled']:
        gaps = results['inter_number_gaps']
        click.secho("\n📏 Inter-Number Gaps:", fg='cyan')
        click.echo(f"Average: {gaps['average']:.1f} (Max allowed: {analyzer.config['analysis']['inter_number_gaps']['max_avg']})")
        click.echo(f"Max Gap: {gaps['max']} (Max allowed: {analyzer.config['analysis']['inter_number_gaps']['max_single']})")
        
        if gaps['histogram']:
            click.echo("Gap Distribution:")
            for gap, count in sorted(gaps['histogram'].items()):
                highlight = "!" if gap > analyzer.config['display']['gaps']['large_threshold'] else ""
                click.echo(f"  {gap}: {count}x{highlight}")

@cli.command()
@click.option('--strategy', type=click.Choice(['weighted', 'balanced', 'random']), 
              default='weighted', help='Generation strategy')
@click.pass_context
def generate(ctx, strategy):
    """Generate optimized numbers"""
    optimizer = LotteryOptimizer(ctx.obj['config'])
    
    if strategy == 'weighted':
        numbers = optimizer._generate_weighted()
    elif strategy == 'balanced':
        numbers = optimizer._generate_balanced()
    else:
        numbers = optimizer._generate_random()
    
    validator = LotteryValidator(ctx.obj['config'])
    validation = validator.validate_draw(numbers)
    
    click.secho(f"\nGenerated Numbers: {sorted(numbers)}", bold=True)
    
    if validation['is_valid']:
        click.secho("✅ VALID", fg='green')
    else:
        click.secho("❌ INVALID", fg='red')
        
    # Show validation details
    if validation.get('inter_number_gaps'):
        gaps = validation['inter_number_gaps']
        click.echo(f"\nGap Analysis:")
        click.echo(f"  Avg: {gaps['average']:.1f} | Max: {gaps['max']} | Valid: {gaps['valid']}")

if __name__ == '__main__':
    cli()