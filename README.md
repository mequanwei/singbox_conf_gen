# Sing-box Configuration Generator

A Python tool to convert Clash subscription configurations to sing-box format.

## Features

- ✅ **Jinja2 Template System** - 动态模板支持，方便自定义配置
- ✅ Fetch Clash configurations from subscription URLs (with caching)
- ✅ Convert Clash format to sing-box configuration
- ✅ Sanitize node names (remove emojis, ensure UTF-8 compatibility)
- ✅ Generate routes from Clash rules
- ✅ Support selective updates (nodes only)
- ✅ Configurable inbound modes (mixed or tun)
- ✅ CLI interface with multiple commands
- ✅ Template management (create, list, switch templates)
- ✅ Backward compatibility with JSON templates

## Installation

1. Clone this repository
2. Install dependencies using uv:
   ```bash
   uv pip install -r requirements.txt
   ```

## Usage

### Generate Complete Configuration

```bash
# Generate with default Jinja2 template (mixed inbound)
uv run python main.py generate --output config.json

# Generate with tun inbound using Jinja2 template
uv run python main.py generate --inbound tun --output config.json

# Generate using custom template
uv run python main.py generate --template my_custom.j2 --output config.json

# Generate from specific URL
uv run python main.py generate --url "your-subscription-url" --output config.json

# Generate without sanitizing names (keep emojis)
uv run python main.py generate --no-sanitize --output config.json

# Use legacy JSON template system
uv run python main.py generate --legacy-template --template singbox_config.json --output config.json
```

### Update Nodes Only

```bash
# Update only proxy nodes in existing config
uv run python main.py update --current config.json --output updated_config.json
```

### Get Subscription Information

```bash
# Show subscription info without generating config
uv run python main.py info
```

### Template Management

```bash
# List available templates
uv run python main.py list-templates

# Create a new template
uv run python main.py create-template --name my_template.j2
```

### Other Commands

```bash
# Clear subscription cache
uv run python main.py clear-cache

# Show version
uv run python main.py version

# Show help
uv run python main.py --help
```

## Configuration Files

- `url`: Contains your Clash subscription URL
- `templates/`: Directory containing Jinja2 template files
  - `singbox_default.j2`: Default sing-box template
- `singbox_config.json`: Legacy JSON template (for backward compatibility)
- `clash.yaml`: Example Clash configuration (for reference)

## Project Structure

```
├── src/
│   ├── subscription_fetcher.py  # Fetch and cache subscriptions
│   ├── route_extractor.py       # Extract routes from Clash config
│   ├── singbox_config.py        # Sing-box configuration management
│   ├── template_manager.py      # Jinja2 template management
│   └── config_generator.py      # Main configuration generator
├── templates/
│   └── singbox_default.j2       # Default Jinja2 template
├── main.py                      # CLI interface
├── example_usage.py             # Usage examples
├── requirements.txt             # Dependencies
├── TEMPLATE_GUIDE.md            # Template editing guide
└── README.md                    # This file
```

## Requirements

- Python 3.8+
- uv (recommended) or pip
- Dependencies: requests, pyyaml, click, rich, jinja2

## Features Implemented

1. ✅ **Jinja2 Template System**: Dynamic template rendering with full customization
2. ✅ **Subscription Fetching**: Fetches from URL with caching support
3. ✅ **Route Extraction**: Converts Clash proxies and rules to sing-box format
4. ✅ **Configuration Generation**: Creates structured sing-box configurations
5. ✅ **Name Sanitization**: Removes emojis and ensures UTF-8 compatibility
6. ✅ **Selective Updates**: Update only nodes without changing other settings
7. ✅ **Inbound Selection**: Choose between mixed-in and tun modes
8. ✅ **Template Management**: Create, list, and switch between templates
9. ✅ **CLI Interface**: Easy-to-use command-line interface
10. ✅ **Backward Compatibility**: Legacy JSON template support

## Example Workflow

```bash
# 1. Check subscription info
uv run python main.py info

# 2. List available templates
uv run python main.py list-templates

# 3. Create custom template (optional)
uv run python main.py create-template --name my_custom.j2

# 4. Generate initial configuration using Jinja2 template
uv run python main.py generate --template my_custom.j2 --output my_config.json

# 5. Later update only nodes (preserving other settings)
uv run python main.py update --current my_config.json --output updated_config.json
```

## Template Customization

The new Jinja2 template system allows you to easily customize your sing-box configuration:

1. **Edit templates directly**: Modify files in `templates/` directory
2. **Dynamic configuration**: Templates support variables and conditional logic
3. **Easy maintenance**: No need to modify code, just edit template files

See `TEMPLATE_GUIDE.md` for detailed template editing instructions.

## What's New in v2.0

- 🆕 **Jinja2 Template System**: Replace static JSON with dynamic templates
- 🆕 **Template Management**: CLI commands to create and manage templates
- 🆕 **Enhanced Flexibility**: Easy customization without code changes
- 🆕 **Better UX**: Cleaner separation between logic and configuration
- ✅ **Backward Compatible**: Legacy JSON templates still supported

This tool successfully converts Clash subscription configurations to sing-box format while providing maximum flexibility for customization through the new template system.