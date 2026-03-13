import requests
import yaml
import json
import os
import base64
from datetime import datetime
from typing import Dict, Any, Optional

class SubscriptionFetcher:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def fetch_subscription(self, url: Optional[str], use_cache: bool = True) -> Dict[str, Any]:
        """Fetch Clash subscription from URL with optional caching.

        If url is None, reads from cache. If cache is missing, raises an error.
        """
        cache_file = os.path.join(self.cache_dir, "clash_subscription.yaml")
        cache_meta_file = os.path.join(self.cache_dir, "cache_meta.json")

        # No URL provided — must use cache
        if url is None:
            if os.path.exists(cache_file):
                try:
                    if os.path.exists(cache_meta_file):
                        with open(cache_meta_file, 'r') as f:
                            meta = json.load(f)
                        print(f"No URL provided, using cache (saved {meta['timestamp']})")
                    else:
                        print("No URL provided, using cache")
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    raise Exception(f"Failed to read cache: {e}")
            else:
                raise Exception("No subscription URL provided and no cache found. "
                                "Pass --url or create a 'url' file.")

        # Check if cache exists and is valid
        if use_cache and os.path.exists(cache_file) and os.path.exists(cache_meta_file):
            try:
                with open(cache_meta_file, 'r') as f:
                    meta = json.load(f)
                print(f"Using cached subscription (saved {meta['timestamp']})")

                with open(cache_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            except Exception as e:
                print(f"Cache read error: {e}, fetching from URL...")

        # Fetch from URL
        print(f"Fetching subscription from: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Check if this is a subscription URL list (starts with protocol://)
            if response.text.strip().startswith(('ss://', 'vmess://', 'trojan://', 'vless://')):
                # Parse subscription URLs directly
                config = self._parse_subscription_urls(response.text)
            else:
                # Try to parse as YAML first, if fails try base64 decode
                try:
                    config = yaml.safe_load(response.text)
                    if config is None or isinstance(config, str):
                        # Might be base64 encoded
                        raise yaml.YAMLError("Not valid YAML, try base64")
                except yaml.YAMLError:
                    # Try base64 decode
                    try:
                        decoded_text = base64.b64decode(response.text).decode('utf-8')
                        if decoded_text.strip().startswith(('ss://', 'vmess://', 'trojan://', 'vless://')):
                            config = self._parse_subscription_urls(decoded_text)
                        else:
                            config = yaml.safe_load(decoded_text)
                            if config is None:
                                config = self._parse_subscription_urls(decoded_text)
                    except Exception:
                        # If base64 fails, try parsing as subscription URLs
                        config = self._parse_subscription_urls(response.text)

            # Save to cache
            with open(cache_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            # Save cache metadata
            meta = {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "response_size": len(response.text)
            }
            with open(cache_meta_file, 'w') as f:
                json.dump(meta, f, indent=2)

            print(f"Subscription cached successfully ({len(response.text)} bytes)")
            return config

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch subscription: {e}")
        except yaml.YAMLError as e:
            raise Exception(f"Failed to parse YAML: {e}")



    def _parse_subscription_urls(self, content: str) -> Dict[str, Any]:
        """Parse base64-encoded subscription URLs into Clash format"""
        import urllib.parse
        import re

        lines = content.strip().split('\n')
        proxies = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            try:
                # Handle ss:// URLs
                if line.startswith('ss://'):
                    proxy = self._parse_ss_url(line)
                    if proxy:
                        proxies.append(proxy)
                # Handle vmess:// URLs
                elif line.startswith('vmess://'):
                    proxy = self._parse_vmess_url(line)
                    if proxy:
                        proxies.append(proxy)
                # Handle trojan:// URLs
                elif line.startswith('trojan://'):
                    proxy = self._parse_trojan_url(line)
                    if proxy:
                        proxies.append(proxy)
            except Exception as e:
                print(f"Failed to parse line: {line[:50]}... Error: {e}")
                continue

        # Create a basic Clash configuration structure
        config = {
            'proxies': proxies,
            'proxy-groups': [
                {
                    'name': 'Proxy',
                    'type': 'select',
                    'proxies': ['DIRECT'] + [p['name'] for p in proxies]
                }
            ],
            'rules': [
                'MATCH,Proxy'
            ]
        }

        return config

    def _parse_ss_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse Shadowsocks URL"""
        import urllib.parse
        import re

        try:
            # ss://base64(method:password)@server:port/?plugin=xxx#name
            if '/?' in url:
                base_url, params = url.split('/?', 1)
            else:
                base_url, params = url, ""

            # Extract base64 part
            base64_part = base_url[5:]  # Remove 'ss://'
            if '@' in base64_part:
                auth_part, server_part = base64_part.split('@', 1)
            else:
                # Decode the whole thing and split
                decoded = base64.b64decode(base64_part + '==').decode('utf-8')
                if '@' in decoded:
                    auth_part, server_part = decoded.rsplit('@', 1)
                else:
                    return None

            # Parse auth part (method:password)
            if ':' in auth_part:
                method, password = auth_part.split(':', 1)
            else:
                try:
                    auth_decoded = base64.b64decode(auth_part + '==').decode('utf-8')
                    method, password = auth_decoded.split(':', 1)
                except:
                    return None

            # Parse server and port
            if ':' in server_part:
                server, port = server_part.rsplit(':', 1)
                port = int(port)
            else:
                return None

            # Parse fragment (name)
            name = "Unnamed"
            if '#' in params:
                params, name = params.split('#', 1)
                name = urllib.parse.unquote(name)

            # Parse query parameters
            query_params = {}
            if params:
                for param in params.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        query_params[key] = urllib.parse.unquote(value)

            proxy = {
                'name': name,
                'type': 'ss',
                'server': server,
                'port': port,
                'cipher': method,
                'password': password
            }

            # Handle plugin
            if 'plugin' in query_params:
                plugin_info = query_params['plugin']
                if 'simple-obfs' in plugin_info or 'obfs' in plugin_info:
                    proxy['plugin'] = 'obfs'
                    proxy['plugin-opts'] = {}
                    if 'obfs=http' in plugin_info:
                        proxy['plugin-opts']['mode'] = 'http'
                    if 'obfs-host=' in plugin_info:
                        host_part = plugin_info.split('obfs-host=')[1].split(';')[0]
                        proxy['plugin-opts']['host'] = urllib.parse.unquote(host_part)

            return proxy

        except Exception as e:
            print(f"Error parsing SS URL: {e}")
            return None

    def _parse_vmess_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse VMess URL"""
        # VMess parsing would go here
        return None

    def _parse_trojan_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse Trojan URL"""
        # Trojan parsing would go here
        return None