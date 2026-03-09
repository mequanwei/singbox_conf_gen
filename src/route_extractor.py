from typing import Dict, Any, List, Optional

class RouteExtractor:
    def extract_outbounds(self, clash_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract proxy node outbounds from Clash config (ss/vmess/trojan only)"""
        outbounds = []

        for proxy in clash_config.get('proxies', []):
            outbound = self._convert_proxy_to_outbound(proxy)
            if outbound:
                outbounds.append(outbound)

        return outbounds

    def _convert_proxy_to_outbound(self, proxy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        outbound = {
            "tag": proxy.get('name', 'unnamed'),
            "type": "shadowsocks",
            "server": proxy.get('server', ''),
            "server_port": proxy.get('port', 443),
            "method": proxy.get('cipher', 'aes-128-gcm'),
            "password": proxy.get('password', '')
        }

        if proxy.get('plugin') == 'obfs':
            plugin_opts = proxy.get('plugin-opts', {})
            mode = plugin_opts.get('mode', '')
            host = plugin_opts.get('host', '')
            if mode:
                outbound["plugin"] = "obfs-local"
                opts = f"obfs={mode}"
                if host:
                    opts += f";obfs-host={host}"
                outbound["plugin_opts"] = opts

        return outbound

    def _convert_vmess(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
        outbound = {
            "tag": proxy.get('name', 'unnamed'),
            "type": "vmess",
            "server": proxy.get('server', ''),
            "server_port": proxy.get('port', 443),
            "uuid": proxy.get('uuid', ''),
            "security": proxy.get('cipher', 'auto'),
            "alter_id": proxy.get('alterId', 0)
        }

        network = proxy.get('network', 'tcp')
        if network == 'ws':
            outbound["transport"] = {
                "type": "ws",
                "path": proxy.get('ws-opts', {}).get('path', '/'),
                "headers": proxy.get('ws-opts', {}).get('headers', {})
            }

        return outbound

    def _convert_trojan(self, proxy: Dict[str, Any]) -> Dict[str, Any]:
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
