import json
from typing import Dict, Any, List, Optional
from copy import deepcopy

class SingboxConfigManager:
    def __init__(self, template_file: Optional[str] = None):
        self.template = {}
        if template_file:
            self.load_template(template_file)

    def load_template(self, template_file: str):
        """Load sing-box configuration template"""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                self.template = json.load(f)
            print(f"Template loaded from {template_file}")
        except Exception as e:
            raise Exception(f"Failed to load template: {e}")

    def create_config(self,
                     outbounds: List[Dict[str, Any]],
                     route_rules: List[Dict[str, Any]],
                     inbound_mode: str = "mixed") -> Dict[str, Any]:
        """
        Create complete sing-box configuration

        Args:
            outbounds: List of outbound configurations
            route_rules: List of route rules
            inbound_mode: "mixed" or "tun"

        Returns:
            Complete sing-box configuration
        """
        config = deepcopy(self.template)

        # Update inbounds based on mode
        config["inbounds"] = self._create_inbounds(inbound_mode)

        # Set outbounds
        config["outbounds"] = outbounds

        # Create route configuration
        config["route"] = self._create_route_config(route_rules, outbounds)

        return config

    def update_outbounds_only(self,
                             current_config: Dict[str, Any],
                             new_outbounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update only outbounds in existing configuration

        Args:
            current_config: Current sing-box configuration
            new_outbounds: New outbound configurations

        Returns:
            Updated configuration with new outbounds
        """
        config = deepcopy(current_config)

        # Keep existing non-proxy outbounds (direct, reject, etc.)
        existing_system_outbounds = []
        for outbound in config.get("outbounds", []):
            if outbound.get("type") in ["direct", "block", "dns"]:
                existing_system_outbounds.append(outbound)

        # Find proxy outbounds in new list
        proxy_outbounds = []
        for outbound in new_outbounds:
            if outbound.get("type") not in ["direct", "block", "dns"]:
                proxy_outbounds.append(outbound)

        # Combine system and proxy outbounds
        config["outbounds"] = existing_system_outbounds + new_outbounds

        # Update selector outbounds to include new proxy names
        self._update_selector_outbounds(config, proxy_outbounds)

        return config

    def _create_inbounds(self, mode: str) -> List[Dict[str, Any]]:
        """Create inbound configuration based on mode"""
        if mode.lower() == "tun":
            return [
                {
                    "tag": "tun-in",
                    "type": "tun",
                    "interface_name": "tun0",
                    "inet4_address": "172.19.0.1/30",
                    "auto_route": True,
                    "strict_route": False,
                    "sniff": True,
                    "sniff_override_destination": True
                }
            ]
        else:  # mixed mode (default)
            return [
                {
                    "tag": "mixed-in",
                    "type": "mixed",
                    "listen": "0.0.0.0",
                    "listen_port": 7890,
                    "set_system_proxy": False
                }
            ]

    def _create_route_config(self,
                           rules: List[Dict[str, Any]],
                           outbounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create route configuration"""
        route_config = {
            "rules": rules,
            "final": "Proxy",
            "auto_detect_interface": True
        }

        # Add rule sets if available in template
        if "route" in self.template and "rule_set" in self.template["route"]:
            route_config["rule_set"] = self.template["route"]["rule_set"]

        return route_config

    def _update_selector_outbounds(self, config: Dict[str, Any], proxy_outbounds: List[Dict[str, Any]]):
        """Update selector-type outbounds with new proxy names"""
        proxy_names = [outbound.get("tag", "") for outbound in proxy_outbounds if outbound.get("tag")]

        for outbound in config.get("outbounds", []):
            if outbound.get("type") == "selector":
                # Keep system outbounds and add new proxy names
                current_outbounds = outbound.get("outbounds", [])
                system_outbounds = [name for name in current_outbounds
                                  if name in ["direct", "block", "DIRECT", "REJECT"]]

                outbound["outbounds"] = system_outbounds + proxy_names

    def save_config(self, config: Dict[str, Any], output_file: str):
        """Save configuration to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved to {output_file}")
        except Exception as e:
            raise Exception(f"Failed to save configuration: {e}")

    def load_config(self, config_file: str) -> Dict[str, Any]:
        """Load existing sing-box configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load configuration: {e}")

    def get_template_info(self) -> Dict[str, Any]:
        """Get information about loaded template"""
        if not self.template:
            return {"status": "No template loaded"}

        info = {
            "status": "Template loaded",
            "sections": list(self.template.keys()),
            "inbounds": len(self.template.get("inbounds", [])),
            "outbounds": len(self.template.get("outbounds", [])),
            "route_rules": len(self.template.get("route", {}).get("rules", [])) if "route" in self.template else 0
        }

        # Check inbound types
        inbound_types = []
        for inbound in self.template.get("inbounds", []):
            inbound_types.append(inbound.get("type", "unknown"))
        info["inbound_types"] = inbound_types

        return info