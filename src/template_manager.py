import json
import yaml
from typing import Dict, Any, List, Tuple
from jinja2 import Environment, BaseLoader

class SingboxTemplateManager:
    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self.env.filters['tojson'] = self._custom_json_filter

    def _custom_json_filter(self, value, indent=None):
        return json.dumps(value, indent=indent, ensure_ascii=False)

    def parse_template(self, template_path: str) -> Tuple[List[Dict[str, Any]], str]:
        """Parse template file with YAML front matter.

        Returns:
            (region_rules, template_string)
        """
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split front matter from template body
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                front_matter = yaml.safe_load(parts[1])
                template_string = parts[2].strip()
                region_rules = front_matter.get('regional_groups', [])
                return region_rules, template_string

        # No front matter, return empty rules and full content as template
        return [], content

    def render_config(self, template_string: str, **template_vars) -> Dict[str, Any]:
        """Render config from template string and variables."""
        template = self.env.from_string(template_string)
        rendered = template.render(**template_vars)
        return json.loads(rendered)
