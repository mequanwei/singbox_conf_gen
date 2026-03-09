from typing import Dict, Any, List, Optional
from .subscription_fetcher import SubscriptionFetcher
from .route_extractor import RouteExtractor
from .template_manager import SingboxTemplateManager
import re
import json
import os

TEMPLATE_FILE = "singbox_default.j2"

class ConfigGenerator:
    def __init__(self):
        self.fetcher = SubscriptionFetcher()
        self.extractor = RouteExtractor()
        self.template_manager = SingboxTemplateManager()

    def generate_full_config(self,
                             subscription_url: Optional[str],
                             output_file: str,
                             use_cache: bool = True) -> Dict[str, Any]:

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
        )

        # Step 7: Save
        self._save_config(config, output_file)
        print()
        print(f"  Outbounds     {len(config.get('outbounds', []))} total")
        print(f"  Saved to      {output_file}")

        return config

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
