#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from core.validator import LotteryValidator
from pathlib import Path
import json
import sys
from typing import Optional

class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()

@click.group(cls=NaturalOrderGroup, invoke_without_command=True, 
             help="🎰 Lottery Number Optimizer CLI\nGenerate statistically optimized lottery numbers")
@click.option('--config', default='config.yaml', show_default=True,
              help="📄 Path to config file")
@click.version_option("1.0", message="%(prog)s v%(version)s")
@click.pass_context
def cli(ctx, config):
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command(help="📊 Analyze historical draw patterns")
@click.option('--test-draws', type=int, 
              help=f"🔢 Number of historical draws to analyze (default from config)")
@click.option('--show-gaps', is_flag=True,
              help="📈 Display gap analysis details")
@click.option('--show-combos', is_flag=True,
              help="🃏 Show number combination stats")
@click.option('--save', is_flag=True,
              help="💾 Save full report to JSON")
def analyze(test_draws, show_gaps, show_combos, save):
    """Run comprehensive historical analysis"""
    analyzer = HistoricalAnalyzer()
    stats = analyzer.run(test_draws)
    
    # Header
    click.secho("\n⚡ COMPREHENSIVE ANALYSIS REPORT ⚡", fg='blue', bold=True)
    click.echo(f"Analyzed last {test_draws or analyzer.config['validation']['test_draws']} draws")
    click.echo("="*50)
    
    # 1. Frequency Analysis
    click.secho("\n🔢 TOP NUMBERS (BY FREQUENCY)", fg='green', bold=True)
    top_nums = stats['frequency']['top']
    min_freq = analyzer.config['analysis'].get('min_frequency', 0)
    click.echo(f"Showing top {len(top_nums)} numbers (min {min_freq} appearances):")
    for num, count in top_nums.items():
        click.echo(f"  #{num:>2}: {count:>3} appearances")
    
    # 2. Temperature Analysis
    click.secho("\n🌡️ NUMBER TEMPERATURE", fg='yellow', bold=True)
    temp = stats['temperature']
    click.echo(f"Hot (last {analyzer.config['analysis']['recency_bins']['hot']} draws):")
    click.echo("  " + ", ".join(map(str, temp['hot'][:15])))
    if len(temp['hot']) > 15:
        click.echo(f"  ...and {len(temp['hot'])-15} more")
    
    if temp['cold']:
        click.echo(f"\nCold (> {analyzer.config['analysis']['recency_bins']['cold']} draws since last appearance):")
        click.echo("  " + ", ".join(map(str, temp['cold'])))
    else:
        click.echo("\n❄️ No cold numbers - all have appeared recently")
    
    # 3. Odd/Even Balance
    click.secho("\n⚖️ ODD/EVEN DISTRIBUTION", fg='magenta', bold=True)
    total_draws = sum(stats['odd_even'].values())
    for odds, count in stats['odd_even'].items():
        evens = analyzer.config['strategy']['numbers_to_select'] - odds
        click.echo(f"  {odds} odd + {evens} even: {count:>3} draws ({count/total_draws:.1%})")
    
    # 4. Sum Range Analysis
    click.secho("\n🧮 SUM RANGE STATISTICS", fg='cyan', bold=True)
    sums = stats['sums']
    click.echo(f"Minimum sum: {sums['min']}")
    click.echo(f"Maximum sum: {sums['max']}")
    click.echo(f"Average sum: {sums['mean']:.1f} ± {sums['std_dev']:.1f}")
    
    # 5. High/Low Distribution
    hl = stats['high_low']
    click.secho("\n⬇️⬆️ HIGH/LOW DISTRIBUTION", fg='blue', bold=True)
    click.echo(f"Low numbers (≤{analyzer.config['strategy']['low_number_max']}): {len(hl['low_numbers'])} numbers")
    click.echo(f"High numbers: {len(hl['high_numbers'])} numbers")
    click.echo(f"Avg low numbers per draw: {hl['avg_low_per_draw']:.1f}")
    
    # 6. Prime Numbers
    primes = stats['primes']
    click.secho("\n🔢 PRIME NUMBERS ANALYSIS", fg='red', bold=True)
    click.echo(f"Prime numbers in pool ({primes['prime_percentage']:.1%}):")
    click.echo("  " + ", ".join(map(str, primes['primes_in_pool'])))
    
    # 7. Gap Analysis (if enabled)
    if show_gaps and stats.get('gaps'):
        click.secho("\n📊 GAP ANALYSIS DETAILS", fg='red', bold=True)
        gaps = stats['gaps']
        click.echo("Most common gaps between numbers:")
        for gap, count in sorted(gaps['common_gaps'].items(), key=lambda x: -x[1])[:10]:
            click.echo(f"  {gap:>2}: {count:>3} times")
        click.echo(f"\nAverage gap size: {gaps['avg_gap_size']:.1f}")
        
        if gaps['overdue_numbers']:
            click.secho("\n🚨 OVERDUE NUMBERS", fg='red', bold=True)
            for num in gaps['overdue_numbers']:
                click.echo(f"  #{num}")
    
    # 8. Combinations (if requested)
    if show_combos and stats['combinations']:
        click.secho("\n🃏 NUMBER COMBINATIONS", fg='green', bold=True)
        for size, combos in stats['combinations'].items():
            click.echo(f"\nTop {size}-number combinations:")
            for combo, count in sorted(combos.items(), key=lambda x: -x[1])[:5]:
                click.echo(f"  {combo}: {count} occurrences")
    
    # Save full report
    if save:
        report_path = Path(analyzer.config['data']['stats_dir']) / 'analysis_report.json'
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=2)
        click.secho(f"\n💾 Full report saved to {report_path}", fg='green')

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')
        sys.exit(1)