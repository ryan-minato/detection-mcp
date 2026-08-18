# detection-mcp

[English](README.md)

`detection-mcp` 是一个通过 STDIO 运行的本地 Model Context Protocol Server，用于物体检测标注。它在 SQLite 中保存工作流状态和标注，在内存中渲染复核预览，并在不修改原始图片的前提下导出 JSONL。

## 项目状态

v1 实现已可进入审查。项目提供 23 个 Tool，覆盖数据集、类别、图片、水平框、旋转框、预览和导出。包要求 Python 3.12 或更新版本，并使用 `fastmcp>=3.4.7,<4.0.0`，因此可以接收兼容的 FastMCP 3.x 安全更新。

## 从本仓库安装

安装 [uv](https://docs.astral.sh/uv/) 后运行：

```bash
uv tool install .
detection-mcp --version
```

如果要参与仓库开发：

```bash
uv sync --locked --all-groups
uv run pre-commit install --install-hooks --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
```

## 配置 MCP 客户端

使用已安装的命令，并且只授权任务实际需要的目录：

```json
{
  "mcpServers": {
    "detection-mcp": {
      "command": "detection-mcp",
      "args": [
        "--db-path", "/var/lib/detection-mcp/annotations.db",
        "--allowed-dataset-root", "/srv/datasets",
        "--allowed-export-root", "/srv/exports"
      ]
    }
  }
}
```

Server 使用 STDIO：协议消息写入 stdout，日志写入 stderr。CLI 参数优先于 `DETECTION_MCP_*` 环境变量。全部设置见[配置文档](docs/configuration.md)。

## 标注流程

1. 登记数据集根目录并定义类别。
2. 按状态或确定性的随机顺序列出图片。
3. 预览经过方向校正的图片。
4. 以原子批次添加归一化水平框或旋转框。
5. 通过叠加预览复核并修正标注，再将图片标记为完成。
6. 将已完成图片导出为 AutoTrain 或扩展 JSONL。

安装后可运行 `detection-mcp --skills-path`，找到随包提供的 `object-detection-annotation` 和 `detection-mcp-setup` Agent Skills。

## Tool 分组

| 范围 | Tools |
|---|---|
| 数据集 | `create_dataset`、`delete_dataset`、`restore_dataset`、`list_datasets`、`get_dataset` |
| 类别 | `add_categories`、`edit_category`、`delete_category`、`restore_category`、`list_categories`、`get_category` |
| 图片与复核 | `list_images`、`set_image_status`、`preview_image`、`preview_annotations` |
| 标注 | `list_annotations`、三个水平框 Tool、三个旋转框 Tool |
| 导出 | `export_metadata_jsonl` |

完整说明见 [Tool 参考](docs/tool-reference.md)和[导出格式](docs/export-format.md)。

## 开发命令

仓库统一使用 `just` 执行命令：

```bash
just sync       # 同步锁定的开发环境
just test       # 运行常规测试
just quality    # 运行完整本地提交门禁
just hooks      # 对全部跟踪文件运行仓库 hooks
just check      # 依次运行 quality 和 hooks
```

任何情况下都不得绕过 Git hooks。每次提交前必须通过完整质量门禁以及暂存内容的机密信息和个人信息扫描。具体规则见 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和 [AGENTS.md](AGENTS.md)。

## 容器

生产镜像使用非 root 用户运行。数据集必须只读挂载，状态和导出目录则使用相互独立的可写挂载。详见 [Docker 部署](docs/docker.md)和 `docker-compose.example.yml`。

## 许可证

Apache-2.0，见 [LICENSE](LICENSE)。
