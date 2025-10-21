#!/usr/bin/env python3

import click
import os
from src.config_generator import ConfigGenerator

@click.group()
def cli():
    """Sing-box Configuration Generator - Convert Clash subscriptions to sing-box format"""
    pass

@cli.command()
@click.option('--url', '-u', help='Clash subscription URL')
@click.option('--url-file', '-f', default='url', help='File containing subscription URL (default: url)')
@click.option('--template', '-t', default='singbox_default.j2', help='Template file (default: singbox_default.j2)')
@click.option('--output', '-o', default='output_config.json', help='Output configuration file (default: output_config.json)')
@click.option('--inbound', '-i', type=click.Choice(['mixed', 'tun']), default='mixed', help='Inbound mode (default: mixed)')
@click.option('--sanitize', is_flag=True, help='Sanitize proxy names (remove emojis and special characters)')
@click.option('--no-cache', is_flag=True, help='Do not use cached subscription')
@click.option('--legacy-template', is_flag=True, help='Use legacy JSON template system instead of Jinja2')
def generate(url, url_file, template, output, inbound, sanitize, no_cache, legacy_template):
    """Generate complete sing-box configuration from Clash subscription"""

    # Get subscription URL
    if url:
        subscription_url = url
    elif os.path.exists(url_file):
        with open(url_file, 'r') as f:
            subscription_url = f.read().strip()
        click.echo(f"Using URL from {url_file}")
    else:
        click.echo(f"Error: No URL provided and {url_file} does not exist", err=True)
        return

    # Check template file for legacy mode
    if legacy_template and not os.path.exists(template):
        click.echo(f"Error: Template file {template} does not exist", err=True)
        return

    try:
        generator = ConfigGenerator(template, use_jinja_template=not legacy_template)

        click.echo(f"Generating sing-box configuration...")
        click.echo(f"  Subscription URL: {subscription_url}")
        click.echo(f"  Template: {template}")
        click.echo(f"  Output: {output}")
        click.echo(f"  Inbound mode: {inbound}")
        click.echo(f"  Sanitize names: {sanitize}")
        click.echo(f"  Use cache: {not no_cache}")
        click.echo()

        config = generator.generate_full_config(
            subscription_url=subscription_url,
            output_file=output,
            inbound_mode=inbound,
            sanitize_names=sanitize,
            use_cache=not no_cache
        )

        click.echo(f"\n🎉 Configuration generated successfully!")
        click.echo(f"📁 Output file: {output}")
        click.echo(f"📊 Generated {len(config.get('outbounds', []))} outbounds")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)

@cli.command()
@click.option('--url', '-u', help='Clash subscription URL')
@click.option('--url-file', '-f', default='url', help='File containing subscription URL (default: url)')
@click.option('--current', '-c', required=True, help='Current sing-box configuration file')
@click.option('--output', '-o', default='updated_config.json', help='Output configuration file (default: updated_config.json)')
@click.option('--template', '-t', default='singbox_default.j2', help='Template file for Jinja2 mode (default: singbox_default.j2)')
@click.option('--sanitize', is_flag=True, help='Sanitize proxy names (remove emojis and special characters)')
@click.option('--no-cache', is_flag=True, help='Do not use cached subscription')
@click.option('--legacy-template', is_flag=True, help='Use legacy JSON template system instead of Jinja2')
def update(url, url_file, current, output, template, sanitize, no_cache, legacy_template):
    """Update only proxy nodes in existing sing-box configuration"""

    # Get subscription URL
    if url:
        subscription_url = url
    elif os.path.exists(url_file):
        with open(url_file, 'r') as f:
            subscription_url = f.read().strip()
        click.echo(f"Using URL from {url_file}")
    else:
        click.echo(f"Error: No URL provided and {url_file} does not exist", err=True)
        return

    # Check current config file
    if not os.path.exists(current):
        click.echo(f"Error: Current configuration file {current} does not exist", err=True)
        return

    try:
        generator = ConfigGenerator(template, use_jinja_template=not legacy_template)

        click.echo(f"Updating proxy nodes...")
        click.echo(f"  Subscription URL: {subscription_url}")
        click.echo(f"  Current config: {current}")
        click.echo(f"  Output: {output}")
        click.echo(f"  Sanitize names: {sanitize}")
        click.echo(f"  Use cache: {not no_cache}")
        click.echo()

        config = generator.update_nodes_only(
            subscription_url=subscription_url,
            current_config_file=current,
            output_file=output,
            sanitize_names=sanitize,
            use_cache=not no_cache
        )

        click.echo(f"\n🎉 Nodes updated successfully!")
        click.echo(f"📁 Output file: {output}")
        click.echo(f"📊 Updated {len(config.get('outbounds', []))} outbounds")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)

@cli.command()
@click.option('--url', '-u', help='Clash subscription URL')
@click.option('--url-file', '-f', default='url', help='File containing subscription URL (default: url)')
@click.option('--no-cache', is_flag=True, help='Do not use cached subscription')
def info(url, url_file, no_cache):
    """Show information about Clash subscription without generating configuration"""

    # Get subscription URL
    if url:
        subscription_url = url
    elif os.path.exists(url_file):
        with open(url_file, 'r') as f:
            subscription_url = f.read().strip()
        click.echo(f"Using URL from {url_file}")
    else:
        click.echo(f"Error: No URL provided and {url_file} does not exist", err=True)
        return

    try:
        # Use default Jinja2 template for info command
        generator = ConfigGenerator(use_jinja_template=True)

        if generator:
            click.echo(f"Fetching subscription information...")
            click.echo(f"  URL: {subscription_url}")
            click.echo()

            info_data = generator.get_subscription_info(subscription_url, not no_cache)

            click.echo(f"📊 Subscription Information:")
            click.echo(f"  Total proxies: {info_data['total_proxies']}")
            click.echo(f"  Total groups: {info_data['total_groups']}")
            click.echo(f"  Total rules: {info_data['total_rules']}")
            click.echo(f"  Extractable outbounds: {info_data['extracted_outbounds']}")
            click.echo(f"  Extractable rules: {info_data['extracted_rules']}")
            click.echo(f"  Contains emojis: {'Yes' if info_data['has_emojis'] else 'No'}")

            click.echo(f"\n📝 Sample proxy names:")
            for i, name in enumerate(info_data['proxy_names'][:5], 1):
                click.echo(f"  {i}. {name}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)

@cli.command()
def clear_cache():
    """Clear subscription cache"""
    try:
        from src.subscription_fetcher import SubscriptionFetcher
        fetcher = SubscriptionFetcher()
        fetcher.clear_cache()
        click.echo("✅ Cache cleared successfully")
    except Exception as e:
        click.echo(f"❌ Error clearing cache: {e}", err=True)

@cli.command()
def list_templates():
    """List available Jinja2 templates"""
    try:
        from src.template_manager import SingboxTemplateManager
        manager = SingboxTemplateManager()
        templates = manager.list_templates()

        if templates:
            click.echo("📋 Available templates:")
            for i, template in enumerate(templates, 1):
                click.echo(f"  {i}. {template}")
        else:
            click.echo("No templates found in templates/ directory")
            click.echo("Use 'create-template' command to create a default template")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)

@cli.command()
@click.option('--name', '-n', default='custom.j2', help='Template name (default: custom.j2)')
def create_template(name):
    """Create a new default template"""
    try:
        from src.template_manager import SingboxTemplateManager
        manager = SingboxTemplateManager()

        template_path = os.path.join("templates", name)
        if os.path.exists(template_path):
            if not click.confirm(f"Template {name} already exists. Overwrite?"):
                return

        manager.create_default_template(template_path)
        click.echo(f"✅ Template created: {template_path}")
        click.echo(f"You can now edit this template file to customize your configuration")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)

@cli.command()
def version():
    """Show version information"""
    click.echo("Sing-box Configuration Generator v2.0.0")
    click.echo("Convert Clash subscriptions to sing-box format")
    click.echo("Now with Jinja2 template support!")

if __name__ == '__main__':
    cli()