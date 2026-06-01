from typing import Dict, Any, List, Optional, Tuple
from .subscription_fetcher import SubscriptionFetcher
from .route_extractor import RouteExtractor
from .template_manager import SingboxTemplateManager
import ipaddress
import re
import json
import os
from urllib.parse import urlparse

TEMPLATE_FILE = "singbox_default.j2"
UPSTREAM_DNS_TAG_PREFIX = "upstream-policy-dns"
PROVIDER_HOST_DOH_TAG = "provider-host-doh"
PROVIDER_HOST_DOH_URL = "https://anycast.jllyzx.com/5428ab28"
PROVIDER_HOST_PATTERNS = {
    "*.sankuaei.com",
    "*.aixifan7498.com",
    "*.afdiancdn.org",
}

class ConfigGenerator:
    def __init__(self):
        self.fetcher = SubscriptionFetcher()
        self.extractor = RouteExtractor()
        self.template_manager = SingboxTemplateManager()

    def generate_full_config(self,
                             subscription_url: Optional[str],
                             output_file: str,
                             use_cache: bool = True,
                             platform: str = 'default') -> Dict[str, Any]:

        print(f"[sing-box] Generating config  output={output_file}")
        print()

        # Step 1: Fetch subscription
        clash_config = self.fetcher.fetch_subscription(subscription_url, use_cache)
        total_proxies = len(clash_config.get('proxies', []))
        print(f"  Subscription  {total_proxies} proxies found")

        # Step 2: Remove emojis from proxy names
        clash_config = self._remove_emojis_only(clash_config)

        # Step 3: Extract proxy nodes
        outbounds = self.extractor.extract_outbounds(clash_config)
        print(f"  Nodes         {len(outbounds)} converted (ss/vmess/trojan)")

        # Step 4: Parse template
        template_path = os.path.join("templates", TEMPLATE_FILE)
        region_rules, template_string = self.template_manager.parse_template(template_path)
        print(f"  Template      {TEMPLATE_FILE}  ({len(region_rules)} region rules)")

        # Step 5: Group nodes by region
        proxy_names = [ob.get('tag', '') for ob in outbounds]
        regional_groups = self._group_nodes_by_region(proxy_names, region_rules)
        print(f"  Region groups")
        for name, nodes in regional_groups.items():
            print(f"    {name:<16} {len(nodes)} nodes")

        # Step 6: Render
        config = self.template_manager.render_config(
            template_string,
            outbounds=outbounds,
            regional_groups=regional_groups,
            all_proxy_names=proxy_names,
            platform=platform,
        )
        upstream_resolver_count = self._apply_upstream_dns_policies(config, clash_config)
        if upstream_resolver_count:
            print(f"  Upstream DNS  {upstream_resolver_count} outbounds via Clash nameserver-policy")

        # Step 7: Save
        self._save_config(config, output_file)
        print()
        print(f"  Outbounds     {len(config.get('outbounds', []))} total")
        print(f"  Saved to      {output_file}")

        return config

    def _apply_upstream_dns_policies(self, config: Dict[str, Any], clash_config: Dict[str, Any]) -> int:
        """Convert upstream Clash nameserver-policy entries for proxy server domains."""
        policy = (clash_config.get("dns") or {}).get("nameserver-policy") or {}
        if not isinstance(policy, dict):
            return 0

        dns_config = config.setdefault("dns", {})
        dns_servers = dns_config.setdefault("servers", [])
        dns_rules = dns_config.setdefault("rules", [])

        entries = self._upstream_policy_entries(policy)
        if not entries:
            return 0

        affected = 0
        used_entries: List[Dict[str, Any]] = []
        target_tags: Dict[Tuple[Any, ...], str] = {}
        for outbound in config.get("outbounds", []):
            server = outbound.get("server")
            for entry in entries:
                if not self._matches_policy_host(server, entry):
                    continue
                target_key = self._dns_target_key(entry["target"])
                tag = target_tags.get(target_key)
                if tag is None:
                    tag = self._next_upstream_dns_tag(
                        dns_servers,
                        len(target_tags) + 1,
                        entry.get("tag_hint"),
                    )
                    target_tags[target_key] = tag
                    self._upsert_dns_server(dns_servers, tag, entry["target"])
                outbound["domain_resolver"] = tag
                affected += 1
                if entry not in used_entries:
                    used_entries.append(entry)
                break

        self._insert_upstream_dns_rules(dns_rules, used_entries, target_tags)
        return affected

    def _upstream_policy_entries(self, policy: Dict[str, Any]) -> List[Dict[str, Any]]:
        entries = []
        for pattern, nameservers in policy.items():
            matcher = self._policy_pattern_matcher(str(pattern))
            if matcher is None:
                continue
            target = self._provider_host_doh_target(str(pattern))
            tag_hint = PROVIDER_HOST_DOH_TAG if target is not None else None
            if target is None:
                target = self._first_supported_dns_target(nameservers)
            if target is None:
                continue
            entries.append({**matcher, "target": target, "tag_hint": tag_hint})
        return entries

    def _policy_pattern_matcher(self, pattern: str) -> Optional[Dict[str, str]]:
        pattern = pattern.strip().lower().rstrip(".")
        if pattern.startswith("*.") or pattern.startswith("+."):
            suffix = pattern[2:]
            return {
                "kind": "domain_suffix",
                "value": f".{suffix}",
                "match": suffix,
            }
        if not pattern or ":" in pattern:
            return None
        return {
            "kind": "domain",
            "value": pattern,
            "match": pattern,
        }

    def _first_supported_dns_target(self, nameservers: Any) -> Optional[Dict[str, Any]]:
        if isinstance(nameservers, str):
            candidates = [nameservers]
        elif isinstance(nameservers, list):
            candidates = [candidate for candidate in nameservers if isinstance(candidate, str)]
        else:
            return None

        for candidate in candidates:
            target = self._parse_dns_target(candidate)
            if target is not None:
                return target
        return None

    def _provider_host_doh_target(self, pattern: str) -> Optional[Dict[str, Any]]:
        normalized = pattern.strip().lower().rstrip(".")
        if normalized not in PROVIDER_HOST_PATTERNS:
            return None
        return self._parse_dns_target(PROVIDER_HOST_DOH_URL)

    def _parse_dns_target(self, target: str) -> Optional[Dict[str, Any]]:
        target = target.strip()
        if not target:
            return None

        parsed = urlparse(target)
        if parsed.scheme:
            if parsed.scheme not in {"udp", "tcp", "tls", "https", "quic"} or not parsed.hostname:
                return None
            server = {
                "type": parsed.scheme,
                "server": parsed.hostname,
            }
            if parsed.port:
                server["server_port"] = parsed.port
            if parsed.scheme == "https":
                server["path"] = parsed.path or "/dns-query"
            return server

        host, port = self._split_host_port(target, default_port=53)
        if not host:
            return None
        server = {
            "type": "udp",
            "server": host,
        }
        if port != 53:
            server["server_port"] = port
        return server

    def _split_host_port(self, value: str, default_port: int) -> Tuple[str, int]:
        if value.startswith("[") and "]" in value:
            host, _, rest = value[1:].partition("]")
            if rest.startswith(":") and rest[1:].isdigit():
                return host, int(rest[1:])
            return host, default_port
        if ":" in value:
            host, port = value.rsplit(":", 1)
            if port.isdigit():
                return host, int(port)
        return value, default_port

    def _upsert_dns_server(self, dns_servers: List[Dict[str, Any]], tag: str, target: Dict[str, Any]) -> None:
        server = {"tag": tag, **target}
        if server["type"] in {"https", "tls", "quic"} and not self._is_ip_address(server["server"]):
            bootstrap_tag = self._bootstrap_dns_tag(dns_servers)
            if bootstrap_tag:
                server["domain_resolver"] = bootstrap_tag
        dns_servers.append(server)

    def _insert_upstream_dns_rules(self, dns_rules: List[Dict[str, Any]],
                                   entries: List[Dict[str, Any]],
                                   target_tags: Dict[Tuple[Any, ...], str]) -> None:
        grouped: Dict[str, Dict[str, List[str]]] = {}
        for entry in entries:
            tag = target_tags[self._dns_target_key(entry["target"])]
            grouped.setdefault(tag, {}).setdefault(entry["kind"], [])
            if entry["value"] not in grouped[tag][entry["kind"]]:
                grouped[tag][entry["kind"]].append(entry["value"])

        for tag, fields in reversed(list(grouped.items())):
            rule = {"server": tag}
            if fields.get("domain_suffix"):
                rule["domain_suffix"] = fields["domain_suffix"]
            if fields.get("domain"):
                rule["domain"] = fields["domain"]
            if not any(existing.get("server") == tag and
                       existing.get("domain_suffix") == rule.get("domain_suffix") and
                       existing.get("domain") == rule.get("domain")
                       for existing in dns_rules):
                dns_rules.insert(self._after_leading_clash_mode_rules(dns_rules), rule)

    def _after_leading_clash_mode_rules(self, dns_rules: List[Dict[str, Any]]) -> int:
        index = 0
        while index < len(dns_rules) and "clash_mode" in dns_rules[index]:
            index += 1
        return index

    def _bootstrap_dns_tag(self, dns_servers: List[Dict[str, Any]]) -> Optional[str]:
        for server in dns_servers:
            if server.get("tag") == "ali":
                return "ali"
        for server in dns_servers:
            tag = server.get("tag")
            if tag and not tag.startswith(f"{UPSTREAM_DNS_TAG_PREFIX}-"):
                return tag
        return None

    def _next_upstream_dns_tag(self, dns_servers: List[Dict[str, Any]], index: int,
                               preferred: Optional[str] = None) -> str:
        existing_tags = {server.get("tag") for server in dns_servers}
        if preferred and preferred not in existing_tags:
            return preferred
        while True:
            tag = f"{UPSTREAM_DNS_TAG_PREFIX}-{index}"
            if tag not in existing_tags:
                return tag
            index += 1

    def _matches_policy_host(self, server: Optional[str], entry: Dict[str, Any]) -> bool:
        if not server:
            return False
        hostname = server.lower().rstrip(".")
        match = entry["match"]
        if entry["kind"] == "domain_suffix":
            return hostname == match or hostname.endswith(f".{match}")
        return hostname == match

    def _dns_target_key(self, target: Dict[str, Any]) -> Tuple[Any, ...]:
        return tuple(sorted(target.items()))

    def _is_ip_address(self, value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _group_nodes_by_region(self, proxy_names: List[str],
                                region_rules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {rule['name']: [] for rule in region_rules}
        assigned: set = set()

        for name in proxy_names:
            if not name:
                continue
            for rule in region_rules:
                include = rule.get('include', [])
                require = rule.get('require', [])
                exclude = rule.get('exclude', [])
                if not any(kw in name for kw in include):
                    continue
                if require and not all(kw in name for kw in require):
                    continue
                if exclude and any(kw in name for kw in exclude):
                    continue
                groups[rule['name']].append(name)
                assigned.add(name)
                break

        others = [n for n in proxy_names if n and n not in assigned]
        if others:
            groups["Others"] = others

        return {k: v for k, v in groups.items() if v}

    def _remove_emojis_only(self, clash_config: Dict[str, Any]) -> Dict[str, Any]:
        def remove_emojis(name: str) -> str:
            if not name:
                return "Unnamed"
            pattern = re.compile(
                "["
                "\U0001F1E0-\U0001F1FF"
                "\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F32F"
                "\U0001F680-\U0001F6FF"
                "]+", flags=re.UNICODE)
            cleaned = pattern.sub('', name)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned if cleaned else "Unnamed"

        name_mapping: Dict[str, str] = {}
        for proxy in clash_config.get('proxies', []):
            old_name = proxy.get('name', '')
            new_name = remove_emojis(old_name)
            counter = 1
            original = new_name
            while new_name in name_mapping.values():
                new_name = f"{original}_{counter}"
                counter += 1
            name_mapping[old_name] = new_name
            proxy['name'] = new_name

        return clash_config

    def _save_config(self, config: Dict[str, Any], output_file: str):
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
