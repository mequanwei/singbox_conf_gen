from typing import Dict, Any, List, Optional
from .subscription_fetcher import SubscriptionFetcher
from .route_extractor import RouteExtractor
from .singbox_config import SingboxConfigManager
from .template_manager import SingboxTemplateManager
import re
import json
import os

class ConfigGenerator:
    def __init__(self, template_file: str = None, use_jinja_template: bool = True):
        self.fetcher = SubscriptionFetcher()
        self.extractor = RouteExtractor()
        self.use_jinja_template = use_jinja_template

        if use_jinja_template:
            # Use new Jinja2 template system
            self.template_manager = SingboxTemplateManager()
            self.template_name = template_file or "singbox_default.j2"

            # Create default template if it doesn't exist
            template_path = os.path.join("templates", self.template_name)
            if not os.path.exists(template_path):
                print(f"Template {self.template_name} not found, creating default template...")
                self.template_manager.create_default_template(template_path)

        else:
            # Use legacy JSON template system for backward compatibility
            self.config_manager = SingboxConfigManager(template_file)
            self.template_manager = None

    def generate_full_config(self,
                           subscription_url: str,
                           output_file: str,
                           inbound_mode: str = "mixed",
                           sanitize_names: bool = False,
                           use_cache: bool = True) -> Dict[str, Any]:
        """
        Generate complete sing-box configuration from Clash subscription

        Args:
            subscription_url: Clash subscription URL
            output_file: Output file path
            inbound_mode: "mixed" or "tun"
            sanitize_names: Whether to sanitize proxy names
            use_cache: Whether to use cached subscription

        Returns:
            Generated configuration
        """
        print("Generating full sing-box configuration...")

        # Step 1: Fetch subscription
        print("1. Fetching subscription...")
        clash_config = self.fetcher.fetch_subscription(subscription_url, use_cache)

        # Step 2: Process names (always remove emojis, optionally full sanitize)
        print("2. Processing proxy names...")
        if sanitize_names:
            print("   - Full sanitization (remove emojis and special characters)")
            clash_config = self._sanitize_proxy_names(clash_config)
        else:
            print("   - Removing emojis only (keep Chinese/English/symbols)")
            clash_config = self._remove_emojis_only(clash_config)

        # Step 3: Extract routes
        print("3. Extracting routes...")
        outbounds = self.extractor.extract_outbounds(clash_config)
        route_rules = self.extractor.extract_route_rules(clash_config)

        print(f"   - Extracted {len(outbounds)} outbounds")
        print(f"   - Extracted {len(route_rules)} route rules")

        # Step 4: Create proxy groups
        print("4. Creating proxy groups...")
        group_data = self._create_proxy_groups(outbounds)
        print(f"   - Created {len(group_data['proxy_groups'])} proxy groups")
        print(f"   - Created {len(group_data['regional_groups'])} regional groups")

        # Step 5: Generate configuration
        print("5. Generating configuration...")
        if self.use_jinja_template:
            # Use Jinja2 template system
            config = self.template_manager.render_config(
                template_name=self.template_name,
                outbounds=outbounds,
                route_rules=route_rules,
                inbound_mode=inbound_mode,
                proxy_groups=group_data['proxy_groups'],
                regional_groups=group_data['regional_groups'],
                all_proxy_names=group_data['all_proxy_names']
            )
        else:
            # Use legacy JSON template system
            config = self.config_manager.create_config(
                outbounds=outbounds,
                route_rules=route_rules,
                inbound_mode=inbound_mode
            )

        # Step 6: Save configuration
        print("6. Saving configuration...")
        self._save_config(config, output_file)

        print(f"✅ Configuration generated successfully: {output_file}")
        return config

    def update_nodes_only(self,
                         subscription_url: str,
                         current_config_file: str,
                         output_file: str,
                         sanitize_names: bool = True,
                         use_cache: bool = True) -> Dict[str, Any]:
        """
        Update only proxy nodes in existing configuration

        Args:
            subscription_url: Clash subscription URL
            current_config_file: Current sing-box config file
            output_file: Output file path
            sanitize_names: Whether to sanitize proxy names
            use_cache: Whether to use cached subscription

        Returns:
            Updated configuration
        """
        print("Updating proxy nodes only...")

        # Step 1: Load current configuration
        print("1. Loading current configuration...")
        current_config = self._load_config(current_config_file)

        # Step 2: Fetch subscription
        print("2. Fetching subscription...")
        clash_config = self.fetcher.fetch_subscription(subscription_url, use_cache)

        # Step 3: Process names (always remove emojis, optionally full sanitize)
        print("3. Processing proxy names...")
        if sanitize_names:
            print("   - Full sanitization (remove emojis and special characters)")
            clash_config = self._sanitize_proxy_names(clash_config)
        else:
            print("   - Removing emojis only (keep Chinese/English/symbols)")
            clash_config = self._remove_emojis_only(clash_config)

        # Step 4: Extract new outbounds
        print("4. Extracting new outbounds...")
        new_outbounds = self.extractor.extract_outbounds(clash_config)
        print(f"   - Extracted {len(new_outbounds)} outbounds")

        # Step 5: Update configuration
        print("5. Updating configuration...")
        if self.use_jinja_template:
            # For Jinja2 templates, we need to regenerate the full config with new outbounds
            # but preserve other settings from current config
            route_rules = current_config.get("route", {}).get("rules", [])
            inbound_mode = "tun" if current_config.get("inbounds", [{}])[0].get("type") == "tun" else "mixed"

            updated_config = self.template_manager.render_config(
                template_name=self.template_name,
                outbounds=new_outbounds,
                route_rules=route_rules,
                inbound_mode=inbound_mode
            )
        else:
            # Use legacy JSON template system
            updated_config = self.config_manager.update_outbounds_only(
                current_config, new_outbounds
            )

        # Step 6: Save configuration
        print("6. Saving updated configuration...")
        self._save_config(updated_config, output_file)

        print(f"✅ Nodes updated successfully: {output_file}")
        return updated_config

    def _sanitize_proxy_names(self, clash_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize proxy names to remove emojis and ensure UTF-8 compatibility

        Args:
            clash_config: Clash configuration

        Returns:
            Configuration with sanitized names
        """
        def sanitize_name(name: str) -> str:
            if not name:
                return "Unnamed"

            # Remove emoji patterns
            # Unicode emoji ranges
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002702-\U000027B0"
                "\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE)

            # Remove emojis
            clean_name = emoji_pattern.sub('', name)

            # Remove extra spaces
            clean_name = ' '.join(clean_name.split())

            # If name becomes empty after cleaning, use fallback
            if not clean_name or clean_name.isspace():
                clean_name = f"Node_{hash(name) % 10000}"

            return clean_name

        # Create mapping of old names to new names
        name_mapping = {}

        # Sanitize proxy names
        for proxy in clash_config.get('proxies', []):
            old_name = proxy.get('name', '')
            new_name = sanitize_name(old_name)

            # Ensure uniqueness
            counter = 1
            original_new_name = new_name
            while new_name in name_mapping.values():
                new_name = f"{original_new_name}_{counter}"
                counter += 1

            name_mapping[old_name] = new_name
            proxy['name'] = new_name

        # Sanitize group names and update proxy references
        for group in clash_config.get('proxy-groups', []):
            old_name = group.get('name', '')
            new_name = sanitize_name(old_name)

            # Ensure uniqueness
            counter = 1
            original_new_name = new_name
            while new_name in name_mapping.values():
                new_name = f"{original_new_name}_{counter}"
                counter += 1

            name_mapping[old_name] = new_name
            group['name'] = new_name

            # Update proxy references in group
            if 'proxies' in group:
                group['proxies'] = [name_mapping.get(proxy_name, proxy_name)
                                  for proxy_name in group['proxies']]

        print(f"   - Sanitized {len(name_mapping)} proxy/group names")
        return clash_config

    def _remove_emojis_only(self, clash_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove emojis from proxy names but keep Chinese/English/symbols

        Args:
            clash_config: Clash configuration

        Returns:
            Configuration with emoji-free names
        """
        def remove_emojis(name: str) -> str:
            if not name:
                return "Unnamed"

            # Remove only flag emojis and common emojis, but keep special symbols
            emoji_pattern = re.compile(
                "["
                "\U0001F1E0-\U0001F1FF"  # flags (iOS) - this is what we mainly want to remove
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F32F"  # misc symbols
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "]+", flags=re.UNICODE)

            # Remove emojis
            cleaned = emoji_pattern.sub('', name)

            # Clean up extra spaces but preserve the structure
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            return cleaned if cleaned else "Unnamed"

        name_mapping = {}

        # Process proxies
        for proxy in clash_config.get('proxies', []):
            old_name = proxy.get('name', '')
            new_name = remove_emojis(old_name)

            # Ensure uniqueness
            counter = 1
            original_new_name = new_name
            while new_name in name_mapping.values():
                new_name = f"{original_new_name}_{counter}"
                counter += 1

            name_mapping[old_name] = new_name
            proxy['name'] = new_name

        # Process proxy groups
        for group in clash_config.get('proxy-groups', []):
            old_name = group.get('name', '')
            new_name = remove_emojis(old_name)

            # Ensure uniqueness
            counter = 1
            original_new_name = new_name
            while new_name in name_mapping.values():
                new_name = f"{original_new_name}_{counter}"
                counter += 1

            name_mapping[old_name] = new_name
            group['name'] = new_name

            # Update proxy references in group
            if 'proxies' in group:
                group['proxies'] = [name_mapping.get(proxy_name, proxy_name)
                                  for proxy_name in group['proxies']]

        print(f"   - Removed emojis from {len(name_mapping)} proxy/group names")
        return clash_config

    def get_subscription_info(self, subscription_url: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get information about subscription without generating config"""
        clash_config = self.fetcher.fetch_subscription(subscription_url, use_cache)

        proxy_names = self.extractor.get_proxy_names(clash_config)
        outbounds = self.extractor.extract_outbounds(clash_config)
        rules = self.extractor.extract_route_rules(clash_config)

        return {
            "total_proxies": len(clash_config.get('proxies', [])),
            "total_groups": len(clash_config.get('proxy-groups', [])),
            "total_rules": len(clash_config.get('rules', [])),
            "extracted_outbounds": len(outbounds),
            "extracted_rules": len(rules),
            "proxy_names": proxy_names[:10],  # First 10 names
            "has_emojis": any('🇭🇰' in name or '🇺🇸' in name or '🇸🇬' in name
                            for name in proxy_names[:20])
        }

    def clear_cache(self):
        """Clear subscription cache"""
        self.fetcher.clear_cache()

    def _save_config(self, config: Dict[str, Any], output_file: str):
        """Save configuration to file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved to {output_file}")
        except Exception as e:
            raise Exception(f"Failed to save configuration: {e}")

    def _create_proxy_groups(self, outbounds: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create proxy groups from outbounds

        Args:
            outbounds: List of outbound configurations

        Returns:
            Dictionary containing proxy groups and regional groups
        """
        # Get all proxy nodes (exclude system outbounds)
        proxy_nodes = []
        for outbound in outbounds:
            if outbound.get("type") not in ["direct", "block", "dns"]:
                proxy_nodes.append(outbound.get("tag", ""))

        # Create regional groups
        regional_groups = self._group_nodes_by_region(proxy_nodes)

        # Create service-specific groups
        service_groups = self._create_service_groups(regional_groups)

        return {
            "proxy_groups": service_groups,
            "regional_groups": regional_groups,
            "all_proxy_names": proxy_nodes
        }

    def _group_nodes_by_region(self, proxy_nodes: List[str]) -> Dict[str, List[str]]:
        """Group proxy nodes by region based on their names"""
        regions = {
            "HongKong": ["香港", "HK", "Hong Kong"],
            "TaiWan": ["台湾", "TW", "Taiwan"],
            "Japan": ["日本", "JP", "Japan"],
            "America": ["美国", "US", "United States", "亚美尼亚"]
        }

        grouped = {region: [] for region in regions.keys()}
        ungrouped = []

        for node in proxy_nodes:
            if not node:
                continue

            assigned = False
            for region, keywords in regions.items():
                if any(keyword in node for keyword in keywords):
                    grouped[region].append(node)
                    assigned = True
                    break

            if not assigned:
                ungrouped.append(node)

        # Remove empty groups
        grouped = {k: v for k, v in grouped.items() if v}

        # Add ungrouped nodes to "Others" if any
        if ungrouped:
            grouped["Others"] = ungrouped

        return grouped

    def _create_service_groups(self, regional_groups: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Create service-specific proxy groups"""
        groups = []

        # Main Proxy group with all nodes
        all_nodes = []
        for nodes in regional_groups.values():
            all_nodes.extend(nodes)

        groups.append({
            "tag": "Proxy",
            "type": "selector",
            "outbounds": ["direct"] + all_nodes
        })

        # Get available regions for reference
        available_regions = [region for region in ["HongKong", "TaiWan", "Japan", "America"]
                           if region in regional_groups and regional_groups[region]]

        # OpenAI group (prefer America, TaiWan, Japan)
        openai_outbounds = ["direct", "Proxy"]
        for region in ["America", "TaiWan", "Japan"]:
            if region in available_regions:
                openai_outbounds.append(region)

        groups.append({
            "tag": "OpenAI",
            "type": "selector",
            "outbounds": openai_outbounds,
            "default": "America" if "America" in available_regions else "Proxy"
        })

        # Claude group (same as OpenAI)
        groups.append({
            "tag": "Claude",
            "type": "selector",
            "outbounds": openai_outbounds,
            "default": "America" if "America" in available_regions else "Proxy"
        })

        # Google group (all regions)
        google_outbounds = []
        for region in ["HongKong", "TaiWan", "Japan", "America"]:
            if region in available_regions:
                google_outbounds.append(region)

        groups.append({
            "tag": "Google",
            "type": "selector",
            "outbounds": google_outbounds if google_outbounds else ["Proxy"]
        })

        # Netflix group (same as Google)
        groups.append({
            "tag": "Netflix",
            "type": "selector",
            "outbounds": google_outbounds if google_outbounds else ["Proxy"]
        })

        # Apple group (with direct option first)
        apple_outbounds = ["direct"] + (google_outbounds if google_outbounds else ["Proxy"])

        groups.append({
            "tag": "Apple",
            "type": "selector",
            "outbounds": apple_outbounds
        })

        # Microsoft group (with direct option first)
        groups.append({
            "tag": "Microsoft",
            "type": "selector",
            "outbounds": apple_outbounds
        })

        # Games group (with direct option first)
        groups.append({
            "tag": "Games",
            "type": "selector",
            "outbounds": apple_outbounds
        })

        # Streaming group (same as Google)
        groups.append({
            "tag": "Streaming",
            "type": "selector",
            "outbounds": google_outbounds if google_outbounds else ["Proxy"]
        })

        # Global group (all regions + direct at end)
        global_outbounds = (google_outbounds if google_outbounds else ["Proxy"]) + ["direct"]

        groups.append({
            "tag": "Global",
            "type": "selector",
            "outbounds": global_outbounds
        })

        # China group
        groups.append({
            "tag": "China",
            "type": "selector",
            "outbounds": ["direct", "Proxy"]
        })

        # Add regional selector groups
        for region, nodes in regional_groups.items():
            if nodes:  # Only add if there are nodes
                groups.append({
                    "tag": region,
                    "type": "selector",
                    "outbounds": nodes
                })

        return groups

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load existing configuration"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load configuration: {e}")

    def list_templates(self) -> List[str]:
        """List available templates"""
        if self.use_jinja_template:
            return self.template_manager.list_templates()
        else:
            return ["Legacy JSON template system"]

    def switch_template(self, template_name: str):
        """Switch to a different template"""
        if self.use_jinja_template:
            template_path = os.path.join("templates", template_name)
            if os.path.exists(template_path):
                self.template_name = template_name
                print(f"Switched to template: {template_name}")
            else:
                raise Exception(f"Template {template_name} not found")
        else:
            raise Exception("Template switching is only available in Jinja2 mode")