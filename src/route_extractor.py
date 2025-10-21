from typing import Dict, Any, List, Optional

class RouteExtractor:
    def __init__(self):
        pass

    def extract_outbounds(self, clash_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract outbound configurations from Clash config

        Args:
            clash_config: Parsed Clash configuration

        Returns:
            List of sing-box compatible outbound configurations
        """
        outbounds = []

        # Add direct outbound
        outbounds.append({
            "tag": "direct",
            "type": "direct"
        })

        # Convert Clash proxies to sing-box outbounds
        proxies = clash_config.get('proxies', [])
        for proxy in proxies:
            outbound = self._convert_proxy_to_outbound(proxy)
            if outbound:
                outbounds.append(outbound)

        # Add selector groups
        proxy_groups = clash_config.get('proxy-groups', [])
        for group in proxy_groups:
            group_outbound = self._convert_group_to_outbound(group)
            if group_outbound:
                outbounds.append(group_outbound)

        return outbounds

    def extract_route_rules(self, clash_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract and convert Clash rules to sing-box route rules

        Args:
            clash_config: Parsed Clash configuration

        Returns:
            List of sing-box compatible route rules
        """
        rules = []
        clash_rules = clash_config.get('rules', [])

        for rule in clash_rules:
            if isinstance(rule, str):
                converted_rule = self._convert_clash_rule(rule)
                if converted_rule:
                    rules.append(converted_rule)

        return rules

    def _convert_proxy_to_outbound(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Clash proxy to sing-box outbound"""
        proxy_type = proxy.get('type', '').lower()

        if proxy_type == 'ss':
            return self._convert_shadowsocks(proxy)
        elif proxy_type == 'vmess':
            return self._convert_vmess(proxy)
        elif proxy_type == 'trojan':
            return self._convert_trojan(proxy)
        else:
            print(f"Unsupported proxy type: {proxy_type}")
            return None

    def _convert_shadowsocks(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Shadowsocks proxy to sing-box format"""
        outbound = {
            "tag": proxy.get('name', 'unnamed'),
            "type": "shadowsocks",
            "server": proxy.get('server', ''),
            "server_port": proxy.get('port', 443),
            "method": proxy.get('cipher', 'aes-128-gcm'),
            "password": proxy.get('password', '')
        }

        # Handle plugin (obfs)
        if proxy.get('plugin') == 'obfs':
            plugin_opts = proxy.get('plugin-opts', {})
            if plugin_opts.get('mode') == 'http':
                outbound["plugin"] = "obfs-local"
                outbound["plugin_opts"] = {
                    "mode": "http",
                    "host": plugin_opts.get('host', '')
                }

        return outbound

    def _convert_vmess(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
        """Convert VMess proxy to sing-box format"""
        outbound = {
            "tag": proxy.get('name', 'unnamed'),
            "type": "vmess",
            "server": proxy.get('server', ''),
            "server_port": proxy.get('port', 443),
            "uuid": proxy.get('uuid', ''),
            "security": proxy.get('cipher', 'auto'),
            "alter_id": proxy.get('alterId', 0)
        }

        # Handle transport
        network = proxy.get('network', 'tcp')
        if network == 'ws':
            outbound["transport"] = {
                "type": "ws",
                "path": proxy.get('ws-opts', {}).get('path', '/'),
                "headers": proxy.get('ws-opts', {}).get('headers', {})
            }

        return outbound

    def _convert_trojan(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Trojan proxy to sing-box format"""
        return {
            "tag": proxy.get('name', 'unnamed'),
            "type": "trojan",
            "server": proxy.get('server', ''),
            "server_port": proxy.get('port', 443),
            "password": proxy.get('password', ''),
            "tls": {
                "enabled": True,
                "server_name": proxy.get('sni', proxy.get('server', ''))
            }
        }

    def _convert_group_to_outbound(self, group: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert Clash proxy group to sing-box outbound"""
        group_type = group.get('type', '').lower()

        if group_type == 'select':
            return {
                "tag": group.get('name', 'unnamed'),
                "type": "selector",
                "outbounds": group.get('proxies', [])
            }
        elif group_type == 'url-test':
            return {
                "tag": group.get('name', 'unnamed'),
                "type": "urltest",
                "outbounds": group.get('proxies', []),
                "url": group.get('url', 'http://www.gstatic.com/generate_204'),
                "interval": group.get('interval', 300)
            }
        else:
            print(f"Unsupported group type: {group_type}")
            return None

    def _convert_clash_rule(self, rule_str: str) -> Optional[Dict[str, Any]]:
        """Convert Clash rule string to sing-box rule"""
        parts = rule_str.split(',')
        if len(parts) < 2:
            return None

        rule_type = parts[0].strip()
        outbound = parts[-1].strip()

        if len(parts) == 3:
            rule_value = parts[1].strip()
        else:
            rule_value = ','.join(parts[1:-1]).strip()

        # Convert rule types
        if rule_type == 'DOMAIN':
            return {
                "domain": [rule_value],
                "outbound": outbound
            }
        elif rule_type == 'DOMAIN-SUFFIX':
            return {
                "domain_suffix": [rule_value],
                "outbound": outbound
            }
        elif rule_type == 'DOMAIN-KEYWORD':
            return {
                "domain_keyword": [rule_value],
                "outbound": outbound
            }
        elif rule_type == 'IP-CIDR':
            return {
                "ip_cidr": [rule_value],
                "outbound": outbound
            }
        elif rule_type == 'GEOIP':
            return {
                "geoip": rule_value,
                "outbound": outbound
            }
        elif rule_type == 'GEOSITE':
            return {
                "geosite": rule_value,
                "outbound": outbound
            }
        elif rule_type == 'MATCH':
            return {
                "outbound": outbound
            }
        else:
            print(f"Unsupported rule type: {rule_type}")
            return None

    def get_proxy_names(self, clash_config: Dict[str, Any]) -> List[str]:
        """Get list of all proxy names from Clash config"""
        names = []

        # Add proxy names
        for proxy in clash_config.get('proxies', []):
            names.append(proxy.get('name', 'unnamed'))

        # Add group names
        for group in clash_config.get('proxy-groups', []):
            names.append(group.get('name', 'unnamed'))

        return names