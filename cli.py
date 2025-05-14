#!/usr/bin/env python3
import click
from core.analysis import HistoricalAnalyzer
from core.optimizer import LotteryOptimizer
from core.validator import LotteryValidator
from pathlib import Path
import json
import sys
import yaml
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

class NaturalOrderGroup(click.Group):
    def list_commands(self, ctx):
        return self.commands.keys()

def _show_file_debug(ctx, filepath: Path, required: bool = True) -> None:
    """Display detailed file information in debug mode."""
    if ctx.obj['DEBUG']:
        status = "✅ FOUND" if filepath.exists() else "❌ MISSING"
        details = ""
        if filepath.exists():
            if filepath.is_file():
                details = f" ({filepath.stat().st_size/1024:.1f}KB)"
            else:
                details = f" ({len(list(filepath.glob('*')))} files)"
        click.echo(f"DEBUG: {status} {filepath}{details}", err=True)
    if required and not filepath.exists():
        raise click.FileError(str(filepath), hint="Check config.yaml paths")

def _validate_data_paths(ctx, config: Dict[str, Any]) -> None:
    """Validate all required data paths exist."""
    if ctx.obj['DEBUG']:
        click.secho("\n🔍 DATA PATH VALIDATION:", fg='cyan', bold=True)
    
    paths = {
        'historical': Path(config['data']['historical_path']),
        'latest': Path(config['data']['latest_path']),
        'stats_dir': Path(config['data']['stats_dir']),
        'results_dir': Path(config['data']['results_dir'])
    }

    for name, path in paths.items():
        if ctx.obj['DEBUG']:
            status = "✅" if path.exists() else "❌"
            details = ""
            if path.exists():
                if path.is_file():
                    details = f" ({path.stat().st_size/1024:.1f}KB)"
                else:
                    details = f" ({len(list(path.glob('*')))} files)"
            click.echo(f"{status} {name.upper():<12}: {path}{details}")
        
        if name in ['historical', 'latest'] and not path.exists():
            raise click.FileError(str(path), 
                               hint=f"Create file or update config.yaml [data:{name}_path]")

@click.group(cls=NaturalOrderGroup, invoke_without_command=True, 
             help="🎰 Lottery Number Optimizer CLI\nGenerate statistically optimized lottery numbers")
@click.option('--config', default='config.yaml', show_default=True,
              help="📄 Path to config file")
@click.option('--debug', is_flag=True, help="🐛 Show debug information")
@click.version_option("1.0", message="%(prog)s v%(version)s")
@click.pass_context
def cli(ctx, config: str, debug: bool) -> None:
    """Main CLI entry point."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug

@cli.command(help="📊 Analyze historical draw patterns")
@click.option('--test-draws', type=int, help="🔢 Number of historical draws to analyze")
@click.option('--show-all', is_flag=True, help="🌈 Show all analysis sections")
@click.option('--hide', multiple=True, type=click.Choice([
    'frequency', 'temperature', 'odd_even', 'sums', 
    'high_low', 'primes', 'gaps', 'combinations'
]), help="🚫 Sections to hide")
@click.option('--save', is_flag=True, help="💾 Save full report to JSON")
@click.pass_context
def analyze(ctx, test_draws: int, show_all: bool, hide: List[str], save: bool) -> None:
    """Run comprehensive lottery analysis."""
    try:
        config_path = Path(ctx.parent.params['config'])
        _show_file_debug(ctx, config_path)
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        _validate_data_paths(ctx, config)
        analyzer = HistoricalAnalyzer(str(config_path))
        
        display_config = analyzer.config['display'].copy()
        if show_all:
            for key in display_config:
                if key.startswith('show_'):
                    display_config[key] = True
        for section in hide:
            display_config[f'show_{section}'] = False
        analyzer.config['display'] = display_config
        
        stats = analyzer.run(test_draws)
        
        click.secho("\n⚡ ANALYSIS REPORT ⚡", fg='blue', bold=True)
        click.echo(f"Analyzed {stats['metadata']['draws_analyzed']} draws "
                  f"from {stats['metadata']['date_range']['start']} to {stats['metadata']['date_range']['end']}")
        click.echo("="*60)
        
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
            if not analyzer.config['display'].get(f'show_{section}', True):
                continue
                
            click.secho(f"\n{title}", fg=color, bold=True)
            
            if section == 'frequency':
                freq = stats['frequency']
                click.echo(f"Top {analyzer.config['display']['frequency']['top_range']} numbers:")
                for num, count in freq['top'].items():
                    if count >= analyzer.config['display']['frequency']['highlight_over']:
                        click.secho(f"  #{num}: {count} (Hot)", fg='yellow', bold=True)
                    else:
                        click.echo(f"  #{num}: {count}")
            
            elif section == 'temperature':
                temp = stats['temperature']
                click.echo(f"Hot (last {analyzer.config['analysis']['recency_bins']['hot']} draws):")
                click.echo("  " + ", ".join(map(str, temp['hot'][:analyzer.config['display']['temperature']['max_hot_display']])))
                if len(temp['hot']) > analyzer.config['display']['temperature']['max_hot_display']:
                    click.echo(f"  ...and {len(temp['hot'])-analyzer.config['display']['temperature']['max_hot_display']} more")
                
                if temp['cold']:
                    click.echo(f"\nCold (> {analyzer.config['analysis']['recency_bins']['cold']} draws):")
                    click.echo("  " + ", ".join(map(str, temp['cold'])))
            
            elif section == 'primes':
                primes = stats['primes']
                click.echo(f"Prime numbers in pool ({primes['prime_percentage']:.1%}):")
                for p in primes['primes_in_pool']:
                    freq = primes['prime_frequency'][p]
                    if freq >= analyzer.config['display']['primes']['highlight_over']:
                        click.secho(f"  #{p}: {freq} (Hot)", fg='yellow')
                    else:
                        click.echo(f"  #{p}: {freq}")
            
            elif section == 'gaps' and stats['gaps']:
                gaps = stats['gaps']
                click.echo("Most common gaps:")
                for gap, count in sorted(gaps['common_gaps'].items(), key=lambda x: -x[1])[:analyzer.config['display']['gaps']['top_gaps_to_show']]:
                    click.echo(f"  {gap}: {count} times")
                if gaps['overdue_numbers']:
                    click.secho("\n🚨 Overdue Numbers:", fg='red')
                    for num in gaps['overdue_numbers']:
                        click.echo(f"  #{num}")
            
            elif section == 'combinations' and stats['combinations']:
                for size, combos in stats['combinations'].items():
                    click.echo(f"\nTop {size}-number combinations:")
                    max_combos = analyzer.config['display']['combinations'].get(f'max_{"pairs" if size==2 else "triplets" if size==3 else "quads"}', 5)
                    for combo, count in sorted(combos.items(), key=lambda x: -x[1])[:max_combos]:
                        click.echo(f"  {combo}: {count} occurrences")
        
        if save:
            report_path = Path(analyzer.config['data']['stats_dir']) / 'analysis_report.json'
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                json.dump(stats, f, indent=2)
            click.secho(f"\n💾 Report saved to {report_path}", fg='green')

    except Exception as e:
        if ctx.obj['DEBUG']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Analysis failed: {str(e)}")

@cli.command(help="🎲 Generate optimized number sets")
@click.option('--sets', type=click.IntRange(1,100), default=4,
              show_default=True, help="🔢 Number of sets to generate")
@click.option('--strategy', type=click.Choice(['weighted', 'high_low', 'prime', 'auto']),
              default='auto', show_default=True,
              help="📊 Generation strategy")
@click.option('--save', is_flag=True,
              help="💾 Save to generated_sets.csv")
@click.pass_context
def generate(ctx, sets: int, strategy: str, save: bool) -> None:
    """Generate optimized lottery number sets."""
    try:
        config_path = Path(ctx.parent.params['config'])
        _show_file_debug(ctx, config_path)
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        _validate_data_paths(ctx, config)
        opt = LotteryOptimizer(str(config_path))
        
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
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                f.write("numbers\n")
                for nums in generated_sets:
                    f.write(f"{'-'.join(map(str, nums))}\n")
            click.secho(f"Saved to {save_path}", fg='green')

    except Exception as e:
        if ctx.obj['DEBUG']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Generation failed: {str(e)}")

@cli.command(help="✅ Validate generated sets")
@click.option('--against-latest', is_flag=True,
              help="🆚 Compare against latest draw")
@click.option('--test-draws', type=click.IntRange(10,1000), default=120,
              show_default=True, help="📅 Draws to test against")
@click.option('--threshold', type=click.IntRange(1,6), default=4,
              show_default=True, help="🎯 Match threshold")
@click.pass_context
def validate(ctx, against_latest: bool, test_draws: int, threshold: int) -> None:
    """Validate lottery number sets."""
    try:
        config_path = Path(ctx.parent.params['config'])
        _show_file_debug(ctx, config_path)
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        _validate_data_paths(ctx, config)
        val = LotteryValidator(str(config_path))
        
        if against_latest:
            latest_path = Path(val.config['data']['latest_path'])
            _show_file_debug(ctx, latest_path)
            
            result = val.check_latest_draw()
            if not result:
                click.secho("No latest draw found at configured path:", fg='yellow')
                click.echo(f"  {latest_path}")
                return
                
            click.secho(f"\nLatest Draw Analysis ({result['numbers']}):", fg='blue')
            for num, stats in result['analysis'].items():
                status_color = 'green' if stats['status'] == 'hot' else 'red' if stats['status'] == 'cold' else 'white'
                click.echo(f"  #{num}: ", nl=False)
                click.secho(f"{stats['status'].upper()}", fg=status_color, nl=False)
                click.echo(f" (appeared {stats['frequency']} times)")
        else:
            opt = LotteryOptimizer(str(config_path))
            analyzer = HistoricalAnalyzer(str(config_path))
            sets = opt.generate_sets()
            results = val.validate_sets(sets, test_draws)
            freq_stats = analyzer._get_frequency_stats(analyzer.historical)
            
            click.secho(f"\nValidation Results (last {test_draws} draws):", fg='blue')
            for i, res in enumerate(results, 1):
                click.echo(f"\nSet {i}: {res['numbers']}")
                success_color = 'green' if res['success_rate'] > 0.3 else 'yellow' if res['success_rate'] > 0.1 else 'red'
                click.echo(f"Success Rate ({threshold}+ matches): ", nl=False)
                click.secho(f"{res['success_rate']:.1%}", fg=success_color)
                click.echo("Match Distribution:")
                for matches, count in sorted(res['match_distribution'].items()):
                    click.echo(f"  {matches} matches: {count} times")
                
                click.echo("\nNumber Insights:")
                for num in sorted(res['numbers']):
                    count = freq_stats['all'].get(num, 0)
                    if count >= analyzer.config['display']['frequency']['highlight_over']:
                        click.secho(f"  #{num}: {count} (Hot)", fg='yellow')
                    elif count >= analyzer.config['display']['frequency']['min_frequency']:
                        click.echo(f"  #{num}: {count}")
                    else:
                        click.secho(f"  #{num}: {count} (Rare)", fg='cyan')

    except Exception as e:
        if ctx.obj['DEBUG']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Validation failed: {str(e)}")

@cli.command(help="⚙️ Show current configuration")
@click.pass_context
def config(ctx) -> None:
    """Display current configuration."""
    try:
        config_path = Path(ctx.parent.params['config'])
        _show_file_debug(ctx, config_path)
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        click.secho("\n⚙️ CURRENT CONFIGURATION", fg='blue', bold=True)
        click.echo(yaml.dump(config, sort_keys=False))
        
    except Exception as e:
        if ctx.obj['DEBUG']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Config display failed: {str(e)}")

@cli.command(help="🛠️ Show data configuration and paths")
@click.pass_context
def datainfo(ctx) -> None:
    """Inspect data configuration and paths."""
    try:
        config_path = Path(ctx.parent.params['config'])
        _show_file_debug(ctx, config_path)
        
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        click.secho("\n📂 ACTIVE DATA PATHS", fg='green', bold=True)
        _validate_data_paths(ctx, config)
        
        click.secho("\n⚙️ DATA CONFIGURATION", fg='blue', bold=True)
        click.echo(yaml.dump(config['data'], sort_keys=False))
        
        if ctx.obj['DEBUG']:
            click.secho("\n🐛 DEBUG INFO", fg='yellow')
            click.echo(f"Working Directory: {Path.cwd()}")
            click.echo(f"Config Last Modified: {datetime.fromtimestamp(config_path.stat().st_mtime)}")
            click.echo(f"Python Version: {sys.version}")
        
    except Exception as e:
        if ctx.obj['DEBUG']:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(f"Data info failed: {str(e)}")

if __name__ == "__main__":
    try:
        cli()
    except Exception as e:
        click.secho(f"❌ Error: {e}", fg='red')
        sys.exit(1)