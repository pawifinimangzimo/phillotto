#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from pathlib import Path
import json
import sys
from typing import List

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
              help="🔢 Number of historical draws to analyze")
@click.option('--show-all', is_flag=True, 
              help="🌈 Display all analysis sections")
@click.option('--hide', multiple=True, type=click.Choice([
    'frequency', 'temperature', 'odd_even', 'sums', 
    'high_low', 'primes', 'gaps', 'combinations'
]), help="🚫 Sections to hide")
@click.option('--save', is_flag=True,
              help="💾 Save full report to JSON")
def analyze(test_draws, show_all, hide, save):
    """Run comprehensive historical analysis"""
    analyzer = HistoricalAnalyzer()
    
    # Override display config if needed
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
    click.echo(f"Analyzed {stats['metadata']['draws_analyzed']} draws from "
              f"{stats['metadata']['date_range']['start']} to {stats['metadata']['date_range']['end']}")
    click.echo("=" * 60)
    
    # Dynamic section display
    sections = [
        ('frequency', "🔢 NUMBER FREQUENCY", 'green'),
        ('temperature', "🌡️ NUMBER TEMPERATURE", 'yellow'),
        ('odd_even', "⚖️ ODD/EVEN BALANCE", 'magenta'),
        ('sums', "🧮 SUM RANGE STATISTICS", 'cyan'),
        ('high_low', "⬇️⬆️ HIGH/LOW DISTRIBUTION", 'blue'),
        ('primes', "🔢 PRIME NUMBERS ANALYSIS", 'red'),
        ('gaps', "📊 GAP ANALYSIS", 'white'),
        ('combinations', "🃏 NUMBER COMBINATIONS", 'green')
    ]
    
    for section, title, color in sections:
        if not analyzer._should_display(section):
            continue
            
        click.secho(f"\n{title}", fg=color, bold=True)
        
        if section == 'frequency':
            top_nums = stats['frequency']['top']
            min_freq = analyzer._get_display_config('frequency', 'min_frequency', 0)
            click.echo(f"Top {len(top_nums)} numbers (min {min_freq} appearances):")
            highlight_freq = analyzer._get_display_config('frequency', 'highlight_over', 50)
            for num, count in top_nums.items():
                if count > highlight_freq:
                    click.secho(f"  #{num:>2}: {count:>3}", bold=True)
                else:
                    click.echo(f"  #{num:>2}: {count:>3}")
        
        elif section == 'temperature':
            temp = stats['temperature']
            max_hot = analyzer._get_display_config('temperature', 'max_hot_display', 15)
            
            click.echo(f"Hot (last {analyzer.config['analysis']['recency_bins']['hot']} draws):")
            click.echo("  " + ", ".join(map(str, temp['hot'][:max_hot])))
            if len(temp['hot']) > max_hot:
                click.echo(f"  ...and {len(temp['hot'])-max_hot} more")
            
            if analyzer._get_display_config('temperature', 'show_warm', False):
                click.echo(f"\nWarm (last {analyzer.config['analysis']['recency_bins']['warm']} draws):")
                click.echo("  " + ", ".join(map(str, temp['warm'])))
            
            if temp['cold']:
                click.echo(f"\nCold (> {analyzer.config['analysis']['recency_bins']['cold']} draws):")
                highlight_cold = analyzer._get_display_config('temperature', 'highlight_cold_over', 30)
                for num in temp['cold']:
                    last_seen = next(d for d in stats['frequency']['all'].items() if d[0] == num)
                    if last_seen[1] > highlight_cold:
                        click.secho(f"  #{num}: {last_seen[1]} draws ago", fg='red', bold=True)
                    else:
                        click.echo(f"  #{num}: {last_seen[1]} draws ago")
        
        # ... (similar blocks for other sections)
    
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