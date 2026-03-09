# singbox_conf_gen

将 Clash 订阅转换为 sing-box 配置的 Python 工具。地区分组规则写在模板文件头部，模板文件自包含，无需额外配置。

## 安装

```bash
uv pip install -r requirements.txt
```

## 用法

```bash
# 从 url 文件读取订阅地址，生成配置
uv run python main.py

# 指定订阅地址
uv run python main.py --url "your-subscription-url"

# 不使用缓存（重新拉取订阅）
uv run python main.py --no-cache

# 指定输出文件
uv run python main.py --output config.json
```

### 选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `--url`, `-u` | — | Clash 订阅地址（不填则读缓存） |
| `--url-file`, `-f` | `url` | 包含订阅地址的文件 |
| `--output`, `-o` | `output_config.json` | 输出文件 |
| `--no-cache` | — | 不使用缓存，重新拉取订阅 |

## 模板格式

模板文件由两部分组成，用 `---` 分隔：

1. **YAML front matter**：定义地区分组规则
2. **Jinja2 模板体**：定义完整的 sing-box 配置结构

```
---
regional_groups:
  - name: "HK Game"
    include: ["HK", "香港"]
    require: ["游戏"]
  - name: "HK"
    include: ["HK", "香港"]
    exclude: ["游戏"]
  - name: "JP"
    include: ["JP", "日本"]
  - name: "US"
    include: ["US", "美国"]
---
{
  "outbounds": [
    ...
    {% for name, nodes in regional_groups.items() %}
    {"tag": "{{ name }}", "type": "urltest", "outbounds": {{ nodes | tojson }}},
    {% endfor %}
    {% for node in outbounds %}
    {{ node | tojson }}{% if not loop.last %},{% endif %}
    {% endfor %}
  ]
}
```

### 分组匹配规则

| 字段 | 逻辑 | 说明 |
|------|------|------|
| `include` | OR | 节点名包含任一关键词 |
| `require` | AND | 节点名必须包含所有关键词 |
| `exclude` | NOT | 节点名不能包含任一关键词 |

- 按顺序匹配，第一个命中即分配
- 未匹配的节点归入 `Others` 组

### 模板变量

| 变量 | 类型 | 说明 |
|------|------|------|
| `outbounds` | `list` | 转换后的代理节点（sing-box 格式） |
| `regional_groups` | `dict[str, list[str]]` | 地区分组，key 为组名，value 为节点名列表 |
| `all_proxy_names` | `list[str]` | 所有节点名 |

服务分组（AI/Google/Streaming 等）直接在模板体中定义，按需修改。

## 规则集

默认模板使用 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat/tree/sing/geo) 提供的规则集，涵盖广告过滤、常用服务（OpenAI、YouTube、Netflix 等）和国内外地址段。所有规则集在 sing-box 启动时自动下载并缓存到本地。

规则集分为两类：

- **`geo/geosite/`**：基于域名的规则，如 `geosite-google`、`geosite-netflix`
- **`geo/geoip/`**：基于 IP 段的规则，如 `geoip-cn`、`geoip-telegram`

如需替换规则集来源，直接修改模板中 `rule_set` 数组里各条目的 `url` 字段。

## 项目结构

```
├── src/
│   ├── subscription_fetcher.py  # 订阅拉取与缓存
│   ├── route_extractor.py       # Clash 代理节点转换
│   ├── template_manager.py      # 模板解析与渲染
│   └── config_generator.py      # 主流程
├── templates/
│   └── singbox_default.j2       # 默认模板（含地区分组规则）
├── cache/                        # 订阅缓存（自动创建）
├── main.py                       # CLI 入口
├── requirements.txt
└── url                           # 订阅地址文件（自行创建）
```

## 支持的代理协议

从 Clash 订阅中提取以下类型的节点：

- Shadowsocks（含 obfs 插件）
- VMess（含 WebSocket 传输）
- Trojan
