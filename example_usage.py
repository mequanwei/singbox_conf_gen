#!/usr/bin/env python3
"""
示例：如何使用 Sing-box Configuration Generator

这个脚本展示了如何使用该工具的主要功能。
"""

from src.config_generator import ConfigGenerator

def main():
    print("=== Sing-box Configuration Generator 使用示例 ===\n")

    # 读取订阅URL
    try:
        with open('url', 'r') as f:
            subscription_url = f.read().strip()
        print(f"✓ 从 'url' 文件读取订阅地址")
    except FileNotFoundError:
        print("❌ 请确保 'url' 文件存在并包含您的订阅地址")
        return

    # 初始化配置生成器
    try:
        generator = ConfigGenerator("singbox_config.json")
        print("✓ 配置生成器初始化成功")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    print("\n--- 示例 1: 查看订阅信息 ---")
    try:
        info = generator.get_subscription_info(subscription_url)
        print(f"代理数量: {info['total_proxies']}")
        print(f"代理组数量: {info['total_groups']}")
        print(f"包含emoji: {'是' if info['has_emojis'] else '否'}")
        print(f"示例代理名称: {info['proxy_names'][:3]}")
    except Exception as e:
        print(f"❌ 获取信息失败: {e}")

    print("\n--- 示例 2: 生成完整配置 (mixed模式) ---")
    try:
        config = generator.generate_full_config(
            subscription_url=subscription_url,
            output_file="example_mixed_config.json",
            inbound_mode="mixed",
            sanitize_names=True
        )
        print(f"✓ 生成成功，包含 {len(config.get('outbounds', []))} 个出站配置")
    except Exception as e:
        print(f"❌ 生成失败: {e}")

    print("\n--- 示例 3: 生成TUN模式配置 ---")
    try:
        config = generator.generate_full_config(
            subscription_url=subscription_url,
            output_file="example_tun_config.json",
            inbound_mode="tun",
            sanitize_names=True
        )
        print(f"✓ TUN配置生成成功")
    except Exception as e:
        print(f"❌ TUN配置生成失败: {e}")

    print("\n--- 示例 4: 仅更新节点 ---")
    try:
        updated_config = generator.update_nodes_only(
            subscription_url=subscription_url,
            current_config_file="example_mixed_config.json",
            output_file="example_updated_config.json",
            sanitize_names=True
        )
        print(f"✓ 节点更新成功")
    except Exception as e:
        print(f"❌ 节点更新失败: {e}")

    print("\n=== 使用完成 ===")
    print("生成的文件:")
    print("- example_mixed_config.json (mixed模式完整配置)")
    print("- example_tun_config.json (tun模式完整配置)")
    print("- example_updated_config.json (仅更新节点)")

if __name__ == "__main__":
    main()