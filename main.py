#!/usr/bin/env python3

import click
import os
from src.config_generator import ConfigGenerator

@click.command()
@click.option('--url', '-u', default=None, help='Clash subscription URL')
@click.option('--url-file', '-f', default='url', help='File containing subscription URL (default: url)')
@click.option('--output', '-o', default='output_config.json', help='Output file (default: output_config.json)')
@click.option('--no-cache', is_flag=True, help='Do not use cached subscription')
def generate(url, url_file, output, no_cache):
    """Sing-box Configuration Generator - Convert Clash subscriptions to sing-box format"""

    subscription_url = None
    if url:
        subscription_url = url
    elif os.path.exists(url_file):
        with open(url_file, 'r') as f:
            subscription_url = f.read().strip()

    try:
        generator = ConfigGenerator()
        config = generator.generate_full_config(
            subscription_url=subscription_url,
            output_file=output,
            use_cache=not no_cache
        )
        click.echo(f"\nDone! {len(config.get('outbounds', []))} outbounds -> {output}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)

if __name__ == '__main__':
    generate()
