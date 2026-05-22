# Jinja2 MCP Server

> **🚀 生产就绪的MCP协议Jinja2模板渲染服务器**  
> 为AI应用提供强大的模板处理能力，支持复杂JSON参数和安全沙箱执行

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)](https://github.com/WW-AI-Lab/jinja2-mcp-server)

---

## 🎯 核心特性

### 🔧 MCP协议完整支持
- **双传输协议**: 同时支持stdio和StreamableHttp传输
- **标准兼容**: 完全兼容MCP官方协议规范
- **AI集成**: 与Claude、GPT等AI模型无缝集成
- **调试友好**: 支持MCP Inspector可视化调试

### 🛡️ 安全与性能
- **安全沙箱**: 多层安全验证，防止恶意模板执行
- **异步处理**: 基于FastMCP的高性能异步架构
- **智能缓存**: 模板解析缓存，提升渲染性能
- **资源限制**: 执行超时、循环限制等安全机制

### 🎨 功能完整性
- **Jinja2 3.1+**: 支持最新版本的所有特性
- **复杂数据**: 完整的JSON数据结构支持
- **文件模板**: 支持模板文件系统和继承
- **调试工具**: 模板验证、语法检查、性能分析

---

## 🚀 快速开始

### 📋 环境要求

- **Python**: 3.8+ (推荐3.12+)
- **系统**: macOS / Linux / Windows
- **内存**: 最低512MB，推荐1GB+

### ⚡ 一键安装

```bash
# 克隆项目
git clone https://github.com/WW-AI-Lab/jinja2-mcp-server.git
cd jinja2-mcp-server

# 推荐：使用 uv（无需手动安装依赖）
uv sync

# 本地运行（stdio，适合 Claude Desktop / Cursor 等 MCP 客户端）
uv run jinja2-mcp-server --transport stdio

# 或从当前目录通过 uvx 运行
uvx --from . jinja2-mcp-server --transport stdio

# 直接 HTTP（适合本地调试）
uv run jinja2-mcp-server --transport streamable-http --port 8123
```

### 🌐 通过 mcp-proxy 暴露 Streamable HTTP

当需要让浏览器、MCP Inspector 或其它 HTTP 客户端访问本服务时，可用 [mcp-proxy](https://github.com/modelcontextprotocol/mcp-proxy) 把 **stdio 子进程** 转成 **Streamable HTTP**：

```bash
# 在项目根目录执行
uv tool install mcp-proxy

uv tool run mcp-proxy \
  --host 0.0.0.0 \
  --port 8087 \
  --allow-origin "*" \
  --transport=streamablehttp \
  -- uvx --from . jinja2-mcp-server --transport stdio
```

- MCP 端点：`http://127.0.0.1:8087/mcp`
- 子进程必须使用 `--transport stdio`；日志会写到 **stderr**，不会污染 stdout 上的 JSON-RPC。

**stdio 注意事项**：MCP 规定 stdout 仅用于 JSON-RPC。请勿将 `LOGGING_LEVEL=DEBUG` 或把日志重定向到 stdout，否则会出现 `Failed to parse JSONRPC message from server`。

### 🎮 快速体验

```bash
# 方式 A：MCP Inspector + mcp-proxy（见上一节命令，端口 8087）

# 方式 B：内置 Streamable HTTP
uv run jinja2-mcp-server --transport streamable-http --port 8123
# 连接到 http://localhost:8123/mcp
```

---

## 🛠️ 核心工具

### 1️⃣ render_template - 模板渲染
```json
{
  "template": "Hello {{ user.name }}! You have {{ messages | length }} messages.",
  "variables": {
    "user": {"name": "Alice"},
    "messages": [{"id": 1}, {"id": 2}]
  }
}
```
**输出**: `"Hello Alice! You have 2 messages."`

### 2️⃣ render_template_file - 文件模板
```json
{
  "template_path": "examples/templates/email.html",
  "variables": {
    "user": {"name": "Bob", "email": "bob@example.com"},
    "items": [{"name": "Product A", "price": 29.99}]
  }
}
```

### 3️⃣ validate_template - 模板验证
```json
{
  "template": "{% for item in items %}{{ item.name }}{% endfor %}"
}
```
**输出**: `{"valid": true, "variables_used": ["items"], "complexity": "low"}`

### 4️⃣ list_filters - 过滤器列表
获取所有可用的Jinja2过滤器（54个内置过滤器）

### 5️⃣ get_template_info - 模板分析
获取模板的详细信息和性能分析

---

## 📁 项目架构

```
jinja2-mcp-server/
├── 🏗️ src/jinja_mcp_server/        # 核心代码
│   ├── mcp_server.py               # FastMCP服务器实现
│   ├── server.py                   # 启动入口
│   ├── jinja/environment.py        # Jinja2环境管理
│   ├── config/settings.py          # 配置系统
│   ├── tools/registry.py           # MCP工具注册
│   └── utils/                      # 工具库
├── 📄 examples/templates/           # 示例模板
│   ├── basic.html                  # 基础HTML模板
│   ├── email.html                  # 邮件模板
│   └── config.yaml                 # 配置模板
├── 🧪 tests/                       # 测试用例
├── 📚 docs/                        # 项目文档
└── 🚀 run_server.py                # 启动脚本
```

---

## 🎨 使用场景

### 🤖 AI应用集成
```python
# 与Claude/GPT集成
# AI模型可以通过MCP协议调用模板渲染功能
# 支持动态生成邮件、报告、配置文件等
```

### 📧 邮件模板系统
```html
<!-- examples/templates/email.html -->
<html>
<body>
  <h1>Hello {{ user.name }}!</h1>
  <p>Your order summary:</p>
  <ul>
  {% for item in items %}
    <li>{{ item.name }} - ${{ item.price }}</li>
  {% endfor %}
  </ul>
</body>
</html>
```

### ⚙️ 配置文件生成
```yaml
# examples/templates/config.yaml
server:
  name: {{ server.name }}
  port: {{ server.port }}
  environment: {{ env }}
  
features:
{% for feature in features %}
  - {{ feature }}
{% endfor %}
```

### 📊 报告生成
```html
<!-- 动态报告模板 -->
<div class="report">
  <h2>{{ report.title }}</h2>
  <p>Generated on: {{ now() | strftime('%Y-%m-%d') }}</p>
  
  {% if metrics %}
  <table>
    {% for metric in metrics %}
    <tr>
      <td>{{ metric.name }}</td>
      <td>{{ metric.value | round(2) }}</td>
    </tr>
    {% endfor %}
  </table>
  {% endif %}
</div>
```

---

## ⚙️ 高级配置

### 环境变量配置
```bash
# 复制配置文件
cp env.example .env

# 编辑配置
JINJA_AUTOESCAPE=true
JINJA_CACHE_SIZE=400
SECURITY_MAX_LOOP_ITERATIONS=10000
LOGGING_LEVEL=WARNING
```

### JSON配置文件
```json
{
  "jinja": {
    "template_dirs": ["templates", "examples/templates"],
    "autoescape": true,
    "cache_size": 400,
    "strict_undefined": false
  },
  "security": {
    "enable_sandbox": true,
    "max_template_size": 1048576,
    "execution_timeout": 30,
    "max_loop_iterations": 10000
  },
  "logging": {
    "level": "INFO",
    "enable_structlog": true,
    "format": "json"
  },
  "mcp": {
    "server_name": "jinja2-mcp-server",
    "version": "1.0.0"
  }
}
```

---

## 🧪 开发与测试

### 开发环境搭建
```bash
# 克隆并进入项目
git clone https://github.com/WW-AI-Lab/jinja2-mcp-server.git
cd jinja2-mcp-server

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v

# 代码格式化
black src/ tests/
isort src/ tests/

# 类型检查
mypy src/
```

### 性能测试
```bash
# 基础功能测试
python test_server.py

# MCP协议测试
python test_mcp_tools.py

# 模板文件测试
python test_template_files.py

# HTTP协议测试
python test_mcp_http.py
```

---

## 📊 性能指标

### 🚀 基准性能
- **启动时间**: < 2秒
- **内存占用**: 初始 ~50MB，运行时 < 256MB
- **响应延迟**: 平均 < 10ms
- **并发处理**: > 200 requests/second
- **模板渲染**: 简单模板 < 1ms，复杂模板 < 50ms

### 📈 扩展性
- **模板缓存**: 支持400个模板缓存
- **文件大小**: 单模板最大1MB
- **并发连接**: 理论无限制（受系统资源限制）
- **传输协议**: stdio + StreamableHttp双协议支持

---

## 🔧 技术实现

### 核心技术栈
```python
# 基于现代Python生态
FastMCP          # MCP协议框架
Jinja2 3.1+      # 模板引擎
Pydantic v2      # 数据验证
structlog        # 结构化日志
asyncio          # 异步处理
MarkupSafe       # 安全转义
```

### 架构设计
```
┌─────────────────────────────────────────┐
│           MCP Clients                   │
│    ┌─────────────┐  ┌─────────────┐    │
│    │ AI Models   │  │ MCP Inspector│    │
│    └─────────────┘  └─────────────┘    │
└─────────┬─────────────────┬─────────────┘
          │ MCP Protocol    │
          │                 │
┌─────────▼─────────────────▼─────────────┐
│         jinja2-mcp-server               │
│  ┌─────────────────────────────────┐   │
│  │        FastMCP Core             │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │       MCP Tools (5个)           │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │    Jinja2 Service Layer         │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │      Infrastructure             │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 安全机制
```python
# 多层安全防护
1. AST语法解析验证
2. 沙箱环境执行
3. 资源使用限制
4. 执行超时控制
5. 循环次数限制
6. 危险函数过滤
```

---

## 🛠️ 扩展方向

### 已实现功能 ✅
- [x] 完整的MCP协议支持
- [x] Jinja2 3.1+ 全功能支持
- [x] 双传输协议 (stdio/HTTP)
- [x] 安全沙箱执行
- [x] 异步高性能处理
- [x] 模板文件系统支持
- [x] 详细的错误诊断
- [x] 结构化日志记录

---

## 📚 文档资源

### 📖 核心文档
- **[开发规划](docs/开发规划.md)** - 详细的开发历程和技术决策
- **[快速开始](#-快速开始)** - 5分钟上手指南
- **[API参考](#️-核心工具)** - 完整的工具API文档
- **[配置指南](#️-高级配置)** - 高级配置选项

### 🎯 使用示例
- **[基础模板](examples/templates/basic.html)** - HTML模板示例
- **[邮件模板](examples/templates/email.html)** - 邮件模板示例
- **[配置模板](examples/templates/config.yaml)** - YAML配置示例

### 🔧 开发指南
- **[贡献指南](#-开发与测试)** - 如何参与项目开发
- **[测试指南](#-开发与测试)** - 测试用例编写
- **[性能优化](docs/performance.md)** - 性能调优建议

---

## 🤝 贡献指南

### 🚀 参与开发
1. **Fork** 本仓库
2. 创建特性分支: `git checkout -b feature/amazing-feature`
3. 提交更改: `git commit -m 'Add amazing feature'`
4. 推送分支: `git push origin feature/amazing-feature`
5. 提交 **Pull Request**

### 🐛 问题报告
- [Issues](https://github.com/WW-AI-Lab/jinja2-mcp-server/issues) - Bug报告和功能请求
- [Discussions](https://github.com/WW-AI-Lab/jinja2-mcp-server/discussions) - 社区讨论

### 📋 开发规范
- **代码风格**: 遵循PEP 8，使用black格式化
- **类型提示**: 使用mypy进行类型检查
- **测试覆盖**: 新功能必须包含测试用例
- **文档更新**: 重要更改需要更新文档

---

## 📄 开源协议

**MIT License** — 随意商用、改造，欢迎贡献代码！

如果这个项目对你有帮助，请给个 ⭐ **Star** 支持一下！

---

## 🤖 关于 WW-AI-Lab

这是 **WW-AI-Lab** 的开源项目，我们专注于：

- 🔄 **企业自动化解决方案** - 浏览器自动化、AI工作流
- 🤖 **Agentic Workflow** - 端到端的AI业务流程  
- 🖼️ **生成式AI应用** - 多模态模型、图像处理
- 📊 **数据洞察工具** - AI驱动的数据分析

### 💡 项目特点

- **AI辅助开发**: 本项目完全由 Cursor IDE + Claude 协作完成
- **生产就绪**: 虽是开源项目，但代码质量达到生产标准
- **开源共享**: 包含完整的开发过程文档和最佳实践
- **学习友好**: 详细的技术实现说明，便于学习和改进

### 🚀 从开源到企业

当开源项目在实践中证明有效时，我们会将其升级为企业级方案：  
👉 **YFGaia** - 提供更严谨的测试、文档与长期维护

### 📞 联系我们

| 渠道 | 地址 | 用途 |
|------|------|------|
| 📧 **Email** | [toxingwang@gmail.com](mailto:toxingwang@gmail.com) | 合作 / 业务咨询 |
| 🐦 **X (Twitter)** | [@WW_AI_Lab](https://x.com/WW_AI_Lab) | 最新动态、技术分享 |
| 💬 **微信** | toxingwang | 深度交流，添加请注明来源 |

---

**免责声明**: 本项目基于MIT协议开源，仅供学习和研究使用。如需商业支持，请通过上述渠道联系。

**Built with ❤️ using Python, Jinja2, FastMCP and Cursor IDE**