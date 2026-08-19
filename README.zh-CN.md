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

Server 使用 STDIO：协议消息写入 stdout，日志写入 stderr。CLI 参数优先于 `DETECTION_MCP_*` 环境变量，环境变量优先于内置默认值。

### 配置参考

| 用途 | CLI | 环境变量 | 默认值 |
|---|---|---|---|
| SQLite 文件 | `--db-path` | `DETECTION_MCP_DB_PATH` | 平台用户数据目录 |
| 数据集根目录 | 可重复使用 `--allowed-dataset-root` | `DETECTION_MCP_ALLOWED_DATASET_ROOTS` | 不限制 |
| 导出根目录 | 可重复使用 `--allowed-export-root` | `DETECTION_MCP_ALLOWED_EXPORT_ROOTS` | 不限制 |
| 随机排序种子 | `--random-seed` | `DETECTION_MCP_RANDOM_SEED` | `42` |
| 预览宽度 | `--preview-max-width` | `DETECTION_MCP_PREVIEW_MAX_WIDTH` | `768` |
| 预览高度 | `--preview-max-height` | `DETECTION_MCP_PREVIEW_MAX_HEIGHT` | `768` |
| 旋转框校正 | `--rotated-correction-enabled` / `--no-rotated-correction` | `DETECTION_MCP_ROTATED_CORRECTION_ENABLED` | 启用 |
| 校正阈值 | `--rotated-correction-threshold` | `DETECTION_MCP_ROTATED_CORRECTION_THRESHOLD` | `0.01` |
| 拒绝阈值 | `--rotated-error-threshold` | `DETECTION_MCP_ROTATED_ERROR_THRESHOLD` | `0.05` |
| 日志 | `--log-level` | `DETECTION_MCP_LOG_LEVEL` | `INFO` |

环境变量中的根目录列表使用操作系统路径分隔符。空的允许根目录列表会保留便于移植的默认行为，但部署时应显式配置根目录。数据集权限不会自动授予导出权限。运行 `detection-mcp --version` 不会启动 MCP 会话。

## 标注流程

1. 登记数据集根目录并定义类别。
2. 按状态或确定性的随机顺序列出图片。
3. 预览经过方向校正的图片。
4. 以原子批次添加归一化水平框或旋转框。
5. 通过叠加预览复核并修正标注，再将图片标记为完成。
6. 将已完成图片导出为 AutoTrain 或扩展 JSONL。

## 安装 Agent Skills

面向 detection-mcp 使用者安装的 Agent Skills 位于仓库根目录的 `skills/` 中，不包含在 Python wheel、源码分发包或容器镜像内。使用 [skills CLI](https://github.com/vercel-labs/skills) 可以直接从 GitHub 安装：

```bash
npx skills add ryan-minato/detection-mcp --skill object-detection-annotation
npx skills add ryan-minato/detection-mcp --skill detection-mcp-setup
```

默认安装到当前项目；需要在多个项目中使用时，可添加 `--global`。

## Tool 分组

| 范围 | Tools |
|---|---|
| 数据集 | `create_dataset`、`delete_dataset`、`restore_dataset`、`list_datasets`、`get_dataset` |
| 类别 | `add_categories`、`edit_category`、`delete_category`、`restore_category`、`list_categories`、`get_category` |
| 图片与复核 | `list_images`、`set_image_status`、`preview_image`、`preview_annotations` |
| 标注 | `list_annotations`、三个水平框 Tool、三个旋转框 Tool |
| 导出 | `export_metadata_jsonl` |

常规成功响应为 `{ "ok": true, "data": ... }`。领域错误以 MCP 错误结果返回 `{ "ok": false, "error": { "code": ..., "message": ... } }`。预览 Tool 返回 PNG 图像内容及相同的结构化响应。`list_tools` 返回的 schema 是机器可读契约。

## 导出格式

`export_metadata_jsonl` 只导出状态为 `completed` 的图片。它会写入临时文件、刷新内容，并在持有独占锁文件时原子替换目标文件。

### AutoTrain 模式

AutoTrain 模式要求平铺数据集根目录中至少有五张已完成图片。文件必须使用 `.jpg`、`.jpeg` 或 `.png`。每个 JSONL 对象包含 `file_name` 和 `objects`；bbox 使用像素坐标 `[x, y, width, height]`，类别使用从零开始的导出索引。

AutoTrain 的 bbox schema 无法表达旋转框。它们会计入 `ignored_rotated_annotations` 并被省略。没有标注的图片会作为带空数组的负样本保留。

### Extended 模式

Extended 模式还会输出 `polygon` 和 `polygon_category` 数组。每个 polygon 为按规范点顺序排列的八个像素坐标。该模式允许嵌套的可移植图片路径和 WebP 图片。

已删除类别的标注会被排除并报告。除非 `overwrite=true`，否则已有导出文件会被拒绝；并发锁也会作为已有输出错误报告。

## 开发命令

仓库统一使用 `just` 执行命令：

```bash
just sync       # 同步锁定的开发环境
just test       # 运行常规测试
just quality-control # 运行不含测试的 CI 质量检查
just quality    # 运行完整本地提交门禁
just hooks      # 对全部跟踪文件运行仓库 hooks
just check      # 依次运行 quality 和 hooks
```

任何情况下都不得绕过 Git hooks。每次提交前必须通过完整质量门禁以及暂存内容的机密信息和个人信息扫描。具体规则见 [CONTRIBUTING.md](CONTRIBUTING.md)、[SECURITY.md](SECURITY.md) 和 [AGENTS.md](AGENTS.md)。

## 容器

生产镜像使用非 root 的 `detection-mcp` 系统用户运行，并直接启动 STDIO Server。设置两个宿主机路径后运行示例：

```bash
export DETECTION_MCP_DATASET_PATH=/srv/datasets
export DETECTION_MCP_OUTPUT_PATH=/srv/detection-mcp-output
docker compose -f docker-compose.example.yml run --rm detection-mcp
```

示例将 `/datasets` 以只读方式挂载，将 `/output` 设为可写，并为 `/state` 使用命名持久卷。向 MCP Tool 传入容器路径，例如 `/datasets/coco-subset` 和 `/output/metadata.jsonl`；容器内不能访问宿主机路径。

MCP 桌面客户端可以使用带相同挂载的 `docker run --interactive` 作为 STDIO 命令。不要挂载主目录或文件系统根目录。数据库不能与只读数据集挂载共用位置。应分别备份状态卷和导出文件；原始图片不归此 Server 管理。

## 许可证

Apache-2.0，见 [LICENSE](LICENSE)。
