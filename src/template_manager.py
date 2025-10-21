import json
import os
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, Template

class SingboxTemplateManager:
    def __init__(self, template_dir: str = "templates"):
        """
        Initialize template manager

        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = template_dir
        os.makedirs(template_dir, exist_ok=True)

        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters['tojson'] = self._custom_json_filter

    def _custom_json_filter(self, value, indent=None):
        """Custom JSON filter for Jinja2"""
        return json.dumps(value, indent=indent, ensure_ascii=False)

    def render_config(self,
                     template_name: str,
                     outbounds: List[Dict[str, Any]],
                     route_rules: List[Dict[str, Any]],
                     inbound_mode: str = "mixed",
                     **kwargs) -> Dict[str, Any]:
        """
        Render sing-box configuration from template

        Args:
            template_name: Name of template file
            outbounds: List of outbound configurations
            route_rules: List of route rules
            inbound_mode: Inbound mode (mixed or tun)
            **kwargs: Additional template variables

        Returns:
            Rendered configuration as dictionary
        """
        try:
            template = self.env.get_template(template_name)
        except Exception as e:
            raise Exception(f"Failed to load template {template_name}: {e}")

        # Prepare template variables
        template_vars = {
            'outbounds': outbounds,
            'route_rules': route_rules,
            'inbound_mode': inbound_mode,
            'proxy_names': [ob.get('tag', '') for ob in outbounds if ob.get('tag')],
            'proxy_groups': kwargs.get('proxy_groups', []),
            'regional_groups': kwargs.get('regional_groups', {}),
            'all_proxy_names': kwargs.get('all_proxy_names', []),
            **kwargs
        }

        try:
            rendered = template.render(**template_vars)
            return json.loads(rendered)
        except Exception as e:
            raise Exception(f"Failed to render template: {e}")

    def create_default_template(self, template_path: str):
        """Create default sing-box template"""
        template_content = '''{
  "log": {
    "level": "info",
    "timestamp": true
  },
  "experimental": {
    "clash_api": {
      "external_controller": "0.0.0.0:9090",
      "external_ui": "ui",
      "secret": "",
      "external_ui_download_url": "https://mirror.ghproxy.com/https://github.com/MetaCubeX/metacubexd/archive/refs/heads/gh-pages.zip",
      "external_ui_download_detour": "direct",
      "default_mode": "Enhanced"
    }
  },
  "dns": {
    "servers": [
      {
        "tag": "google",
        "type": "udp",
        "server": "8.8.8.8",
        "detour": "Google"
      },
      {
        "tag": "ali",
        "type": "https",
        "server": "223.5.5.5"
      }
    ],
    "rules": [
      {
        "clash_mode": "Direct",
        "server": "ali"
      },
      {
        "clash_mode": "Global",
        "server": "google"
      },
      {
        "rule_set": "geosite-geolocation-cn",
        "server": "ali"
      },
      {
        "type": "logical",
        "mode": "and",
        "rules": [
          {
            "rule_set": "geosite-geolocation-!cn",
            "invert": true
          },
          {
            "rule_set": "geoip-cn"
          }
        ],
        "server": "google",
        "client_subnet": "163.125.229.25/24"
      }
    ],
    "independent_cache": true,
    "reverse_mapping": true,
    "strategy": "ipv4_only"
  },
  "inbounds": [
    {% if inbound_mode == "tun" %}
    {
      "tag": "tun-in",
      "type": "tun",
      "interface_name": "tun0",
      "inet4_address": "172.19.0.1/30",
      "auto_route": true,
      "strict_route": false,
      "sniff": true,
      "sniff_override_destination": true
    }
    {% else %}
    {
      "tag": "mixed-in",
      "type": "mixed",
      "listen": "0.0.0.0",
      "listen_port": 7890,
      "set_system_proxy": false
    }
    {% endif %}
  ],
  "outbounds": {{ outbounds | tojson(2) }},
  "route": {
    "rules": {{ route_rules | tojson(2) }},
    "rule_set": [
      {
        "tag": "geosite-geolocation-cn",
        "type": "remote",
        "format": "binary",
        "url": "https://mirror.ghproxy.com/https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-geolocation-cn.srs",
        "download_detour": "direct"
      },
      {
        "tag": "geosite-geolocation-!cn",
        "type": "remote",
        "format": "binary",
        "url": "https://mirror.ghproxy.com/https://raw.githubusercontent.com/SagerNet/sing-geosite/rule-set/geosite-geolocation-!cn.srs",
        "download_detour": "direct"
      },
      {
        "tag": "geoip-cn",
        "type": "remote",
        "format": "binary",
        "url": "https://mirror.ghproxy.com/https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/sing/geo/geoip/cn.srs",
        "download_detour": "direct"
      }
    ],
    "final": "Proxy",
    "auto_detect_interface": true
  }
}'''

        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(template_content)

    def list_templates(self) -> List[str]:
        """List available templates"""
        if not os.path.exists(self.template_dir):
            return []

        templates = []
        for file in os.listdir(self.template_dir):
            if file.endswith('.j2') or file.endswith('.jinja') or file.endswith('.template'):
                templates.append(file)
        return templates

    def validate_template(self, template_name: str) -> bool:
        """Validate template syntax"""
        try:
            self.env.get_template(template_name)
            return True
        except Exception:
            return False

    def get_template_variables(self, template_name: str) -> List[str]:
        """Get variables used in template"""
        try:
            template = self.env.get_template(template_name)
            return list(template.new_context().get_exported())
        except Exception:
            return []