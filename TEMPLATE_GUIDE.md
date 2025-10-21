# Sing-box Jinja2 模板编辑指南

## 概述

现在sing-box配置支持Jinja2模板系统，您可以轻松自定义配置而无需修改代码。

## 模板文件位置

所有模板文件存储在 `templates/` 目录中，文件扩展名通常为 `.j2`。

## 可用变量

在模板中，您可以使用以下变量：

### 主要变量

- `outbounds` - 所有出站配置的列表（从订阅解析得到）
- `route_rules` - 路由规则列表（从Clash规则转换得到）
- `inbound_mode` - 入站模式 ("mixed" 或 "tun")
- `proxy_names` - 所有代理名称的列表

### 模板语法示例

#### 1. 条件判断（入站模式）

```jinja2
"inbounds": [
  {% if inbound_mode == "tun" -%}
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
  {%- else -%}
  {
    "tag": "mixed-in",
    "type": "mixed",
    "listen": "0.0.0.0",
    "listen_port": 7890,
    "set_system_proxy": false
  }
  {%- endif %}
]
```

#### 2. 插入动态数据

```jinja2
"outbounds": {{ outbounds | tojson(2) }},
"route": {
  "rules": {{ route_rules | tojson(2) }}
}
```

#### 3. 循环遍历代理名称

```jinja2
"proxy-groups": [
  {
    "name": "Auto",
    "type": "url-test",
    "proxies": [
      {% for name in proxy_names -%}
      "{{ name }}"{% if not loop.last %},{% endif %}
      {% endfor %}
    ]
  }
]
```

## 常用过滤器

- `tojson(indent)` - 将Python对象转换为JSON格式
- `length` - 获取列表长度
- `first` - 获取列表第一个元素
- `last` - 获取列表最后一个元素

## 模板管理命令

### 列出可用模板
```bash
uv run python main.py list-templates
```

### 创建新模板
```bash
uv run python main.py create-template --name my_template.j2
```

### 使用指定模板生成配置
```bash
uv run python main.py generate --template my_template.j2 --output config.json
```

## 模板示例

### 简化版模板

创建一个只包含基本功能的简化模板：

```jinja2
{
  "log": { "level": "info" },
  "inbounds": [
    {% if inbound_mode == "tun" -%}
    { "type": "tun", "tag": "tun-in" }
    {%- else -%}
    { "type": "mixed", "tag": "mixed-in", "listen_port": 7890 }
    {%- endif %}
  ],
  "outbounds": {{ outbounds | tojson(2) }},
  "route": {
    "rules": {{ route_rules | tojson(2) }},
    "final": "direct"
  }
}
```

### 高级模板

包含更多自定义选项的模板：

```jinja2
{
  "log": {
    "level": "{{ log_level | default('info') }}",
    "timestamp": true
  },
  "dns": {
    "servers": [
      { "tag": "local", "server": "{{ local_dns | default('223.5.5.5') }}" },
      { "tag": "remote", "server": "{{ remote_dns | default('8.8.8.8') }}" }
    ]
  },
  "inbounds": [
    {% if inbound_mode == "tun" -%}
    {
      "type": "tun",
      "tag": "tun-in",
      "inet4_address": "{{ tun_address | default('172.19.0.1/30') }}",
      "auto_route": true
    }
    {%- else -%}
    {
      "type": "mixed",
      "tag": "mixed-in",
      "listen": "{{ listen_ip | default('0.0.0.0') }}",
      "listen_port": {{ listen_port | default(7890) }}
    }
    {%- endif %}
  ],
  "outbounds": {{ outbounds | tojson(2) }},
  "route": {
    "rules": {{ route_rules | tojson(2) }},
    "final": "{{ final_outbound | default('direct') }}"
  }
}
```

## 自定义变量

您可以在生成配置时传递自定义变量：

```python
config = generator.template_manager.render_config(
    template_name="my_template.j2",
    outbounds=outbounds,
    route_rules=route_rules,
    inbound_mode="mixed",
    # 自定义变量
    log_level="debug",
    listen_port=8080,
    local_dns="119.29.29.29"
)
```

## 注意事项

1. **JSON语法**: 确保生成的内容是有效的JSON格式
2. **空白处理**: 使用 `{%-` 和 `-%}` 来控制空白字符
3. **转义**: 对于特殊字符，确保正确转义
4. **测试**: 修改模板后，使用测试命令验证配置的正确性

## 故障排除

如果模板渲染失败，检查：

1. 模板语法是否正确
2. 变量名是否拼写正确
3. JSON格式是否有效
4. 文件路径是否正确

## 向后兼容

系统仍然支持传统的JSON模板模式，使用 `--legacy-template` 选项即可切换。