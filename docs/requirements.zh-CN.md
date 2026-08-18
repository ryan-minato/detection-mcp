# 物体检测数据集标注 MCP v1 项目需求文档

**工作项目名：** `detection-mcp`
**建议 CLI：** `detection-mcp`
**文档版本：** v1.0 Requirements Baseline
**日期：** 2026-08-18

> 本文档是项目创建、实现、测试、打包和验收的需求基线。除非通过后续版本化变更明确修改，否则 v1 实现应以本文档的行为定义为准。

## 1. 项目目标

本项目创建一个面向 AI Agent 的本地 Model Context Protocol（MCP）Server，用于管理和执行物体检测数据集标注。Server 必须允许 Agent 在不修改原始图片文件的前提下完成数据集注册、类别定义、图片任务状态管理、普通轴对齐 bbox 标注、旋转 bbox 标注、图片/标注预览以及 `metadata.jsonl` 导出。

项目必须满足以下核心目标：

1. 以 **FastMCP** 作为 MCP Server 实现框架。
2. v1 以 **STDIO 本地进程**作为运行方式，不以 HTTP/SSE/Streamable HTTP 作为主部署形态。
3. 支持 **PyPI 安装**和**Docker 镜像安装/运行**两种方式。
4. Docker 运行时数据集目录必须只读挂载；数据库状态与导出目录必须使用独立可写挂载。
5. 原始图片文件对 MCP 永远只读；任何工具均不得修改、重命名、移动或删除原始图片。
6. 标注数据库持久化保存数据集、类别、图片状态和 annotation。
7. 普通 bbox 内部使用归一化 `xyxy`；旋转框内部使用归一化 8 点 polygon。
8. 对写入操作进行即时合法性检查；导出前进行全数据集最终 preflight 检查。
9. 提供与 MCP 配套的 **Agent Skills**，指导 Agent 正确安装、配置和使用本 MCP。
10. Tool 输入输出必须结构化、稳定、对 Agent 友好，并尽量避免依赖自然语言解析结果。

## 2. 非目标与边界

v1 明确不负责以下事项：

- 不负责原始图片文件生命周期管理。
- 不自动追踪外部对图片内容的替换、修改或删除。
- 不保存图片 SHA256、mtime 或文件指纹用于一致性验证。
- 不提供 GUI 标注客户端；预览通过 MCP image content 返回给 Agent/Host。
- 不以 HTTP 远程服务作为 v1 的部署目标。
- 不实现多租户、用户鉴权或远程权限体系。
- 不要求 annotation 审计历史、撤销栈或软删除；annotation 删除为硬删除。
- 不提供独立 `validate_dataset` tool；合法性检查由写入阶段和导出阶段承担。
- 不承诺扩展 `polygon` 字段可直接被 Hugging Face AutoTrain 用于旋转框训练；该字段属于本项目扩展格式。

## 3. 技术基线

### 3.1 实现框架

- MCP Server 必须使用 Python **FastMCP** 实现。
- 项目应依赖 FastMCP 当前稳定版本，不默认依赖 beta/rc 等预发布版本。
- Python 目标版本建议为 **3.11+**；`pyproject.toml` 应明确 `requires-python`。
- 所有 Tool 使用 Python 类型标注/Pydantic 兼容模型定义输入输出，使 FastMCP 自动生成明确 schema 并执行输入验证。
- Preview Tool 应返回 MCP 原生 image content，同时返回结构化尺寸/缩放元数据。

### 3.2 Transport

v1 Server 必须支持并默认使用 **STDIO**：

```text
MCP Host / Agent
      │ stdin/stdout
      ▼
detection-mcp
      │
      ├─ SQLite state
      └─ read-only image filesystem
```

禁止将协议内容以外的普通日志写入 stdout，避免破坏 STDIO MCP 通信。运行日志必须写入 stderr 或专用日志设施。

### 3.3 持久化

v1 使用 **SQLite** 保存 MCP 自身状态。数据库路径必须可通过 CLI 和环境变量覆盖。

数据库至少保存：

- dataset registry 与 soft-delete 状态
- category registry 与 soft-delete 状态
- image annotation status
- bbox / rotated bbox annotations
- schema version / migration version

必须启用外键约束，并保证批量写操作具备事务原子性。

## 4. 安装与分发要求

### 4.1 PyPI 安装

项目必须发布 wheel 和 sdist，使用户可以通过类似方式安装：

```bash
pip install detection-mcp
```

安装后必须提供 console entry point：

```bash
detection-mcp
```

该命令默认启动 STDIO MCP Server。

推荐同时兼容 `uvx` / `uv tool` 等基于 PyPI 包的运行方式，但这不是 v1 的硬性依赖。

本地安装的默认数据库应位于平台用户数据目录中，不应写入数据集目录。必须支持：

```text
--db-path PATH
```

覆盖默认位置。

### 4.2 Docker 安装/运行

项目必须提供可发布的 Docker 镜像。容器默认 ENTRYPOINT 应启动 STDIO MCP Server，不暴露或要求 TCP 端口。

典型运行模型：

```bash
docker run --rm -i \
  -v /host/datasets:/datasets:ro \
  -v /host/od-mcp-state:/state \
  -v /host/od-mcp-output:/output \
  <image>
```

容器必须满足：

- `/datasets`：只读数据集挂载根目录。
- `/state`：可写持久化状态目录，默认 SQLite 位于 `/state/annotations.db`。
- `/output`：可写导出目录。
- 容器内不得尝试对 `/datasets` 执行写操作。
- `create_dataset` 接收的是容器内路径，例如 `/datasets/coco-subset`。
- Docker 镜像应以非 root 用户运行。
- 容器重建后，只要 `/state` 挂载保持不变，dataset/category/status/annotation 状态必须完整保留。
- 镜像必须支持 `--version` 或等价方式输出版本，便于诊断。

### 4.3 文件系统边界

所有 image path 必须经过路径标准化和 resolve。任何 resolve 后逃逸 dataset root 的路径必须拒绝，包括 `..` 和 symlink escape。

Server 应支持“允许的数据集根”和“允许的导出根”配置：

- Docker 默认强制 dataset 只允许位于 `/datasets` 下，导出只允许位于 `/output` 下。
- PyPI 本地安装允许通过 CLI/环境变量配置一个或多个 allowed roots；若启用，则必须严格执行。

## 5. 全局配置

所有 Server 级配置采用以下优先级：

```text
CLI 参数 > 环境变量 > 内置默认值
```

至少应提供：

| 配置 | 默认/要求 |
|---|---|
| 数据库路径 | 本地平台数据目录；Docker `/state/annotations.db` |
| 全局随机种子 | `42` |
| Preview 默认最大宽 | `768` |
| Preview 默认最大高 | `768` |
| Rotated bbox 自动纠正 | 默认开启 |
| Rotated bbox correction threshold | 必须提供明确内置默认值并在发布文档中记录 |
| Rotated bbox error threshold | 必须提供明确内置默认值并在发布文档中记录 |
| 日志级别 | `INFO` 建议 |
| Allowed dataset roots | Docker 强制 `/datasets`；本地可配置 |
| Allowed export roots | Docker 强制 `/output`；本地可配置 |

建议环境变量统一使用项目名前缀，例如：

```text
DETECTION_MCP_DB_PATH
DETECTION_MCP_RANDOM_SEED
DETECTION_MCP_PREVIEW_MAX_WIDTH
DETECTION_MCP_PREVIEW_MAX_HEIGHT
DETECTION_MCP_ROTATED_CORRECTION_ENABLED
DETECTION_MCP_ROTATED_CORRECTION_THRESHOLD
DETECTION_MCP_ROTATED_ERROR_THRESHOLD
DETECTION_MCP_ALLOWED_DATASET_ROOTS
DETECTION_MCP_ALLOWED_EXPORT_ROOTS
DETECTION_MCP_LOG_LEVEL
```

具体数值阈值必须在 v1 发布前冻结，不能以未记录的 magic number 散落在实现代码中。

## 6. 文件与图片处理规则

### 6.1 原始图片只读原则

MCP 可以：

- 扫描目录
- 打开/解码图片
- 读取 EXIF
- 在内存中缩放
- 在内存中绘制 preview overlay
- 读取图片尺寸

MCP 永远不可以：

- 覆盖图片
- 删除图片
- 移动图片
- 重命名图片
- 在 dataset root 生成缓存/缩略图/临时文件
- 修改图片 EXIF 或编码

任何缓存或临时文件如确有需要，只能写入 MCP 自身 state/cache 或系统临时目录。

### 6.2 图片发现

`list_images` 必须从 dataset root **递归扫描**受支持图片。

v1 发现层支持：

```text
.jpg
.jpeg
.png
.webp
```

返回给 Agent 的 `image_path` 始终是 dataset root 相对路径，并统一使用可移植的相对路径表示。

### 6.3 EXIF Orientation

图片解码、preview、annotation 坐标以及 export 所使用的坐标系，必须统一基于**应用 EXIF orientation 后的视觉图像**。

Agent 看到的图片方向必须与 annotation 坐标方向一致。

## 7. Dataset 模型与生命周期

### 7.1 Dataset 创建

`create_dataset` 至少输入：

- `root_path`
- `name`（可选）

Server 应将 root 解析为 canonical path 并保存。创建成功返回稳定、不可重用的 `dataset_id`。

后续所有 dataset 相关工具显式传入 `dataset_id`，不得依赖“当前 dataset”或 session 隐式状态。

同一 root 是否被多个 dataset 记录使用不作为 v1 禁止条件；不同 dataset 可以形成独立 annotation namespace。

### 7.2 Dataset 删除/恢复

Dataset 删除为**软删除**：

- 标记 `deleted_at` 或等价状态。
- 不删除 categories。
- 不删除 image states。
- 不删除 annotations。
- 绝不修改原始图片。

默认列表不包含已删除 dataset；通过 `include_deleted=true` 可列出。

已删除 dataset 除读取其元数据、列出和恢复外，其他标注类写操作必须返回 `DATASET_DELETED`。

`restore_dataset` 只恢复数据库状态，不负责修复或重建外部图片目录。

## 8. Category 模型与生命周期

每个 category 至少包含：

```text
category_id
name
description
deleted_at
created_at
updated_at
```

要求：

- `category_id` 稳定、永不复用。
- active category 的 `name` 在同一 dataset 内必须唯一。
- annotation 内部只引用 `category_id`，不得只保存类别名。
- `description` 是该类别当前的单一权威定义文本，供 Agent 后续重新获取标注标准。

### 8.1 Category 添加

一次调用允许添加一组或多组 category，每项包含：

```text
name
description?
```

批量添加必须原子化：全部合法才提交，否则全部回滚。

### 8.2 Category 编辑

允许：

- rename
- 修改 description
- 同时修改二者

至少一个可编辑字段必须被提供。

### 8.3 Category 删除

删除为**软删除**。

软删除后：

- 历史 annotations 保留。
- 默认 `list_categories` 不返回该 category。
- 不能用于新增 annotation。
- 不能作为 annotation edit 的新 category。
- 默认 `list_annotations` 不返回引用该 category 的 annotation。
- export 排除该 category 及引用它的 annotations。

### 8.4 Category 恢复

`restore_category` 允许提供 `new_name`，从而在恢复时就地重命名。

若最终名称与 active category 重复，则返回 `CATEGORY_NAME_CONFLICT`，并保持原 deleted 状态不变。

## 9. 图片标注状态

每张图片只有三种状态：

```text
unannotated
in_progress
completed
```

定义：

- `unannotated`：尚未开始。
- `in_progress`：已经开始但尚未确认完成。
- `completed`：已经确认完成。

状态与 annotation 数量严格独立。

因此：

```text
completed + 0 annotations
```

是合法且重要的负样本表达。

没有 image state 数据库记录的图片默认视为 `unannotated`。

`set_image_status` 只写 MCP 数据库，不修改图片文件。

## 10. list_images 行为

Tool 输入至少包含：

```text
dataset_id
status = all | unannotated | in_progress | completed
order_by = name | random
random_seed?
offset = 0
max_results
```

默认：

```text
status = all
order_by = name
offset = 0
random_seed = server global seed (42)
```

### 10.1 name 排序

按 dataset-relative path 进行稳定排序。大小写和 Unicode 正规化策略必须在实现中保持一致并通过测试固定。

### 10.2 random 排序

随机顺序必须是**确定性的**：同一 dataset、同一当前图片集合、同一 seed 必须产生同一顺序。

实现不得依赖 Python 进程随机化的 `hash()`。推荐使用稳定哈希（例如 seed + relative path 的 SHA-256）生成排序键，再应用 `offset` / `max_results`。

## 11. 普通 bbox 规范

内部和 Tool 输入统一使用归一化 `xyxy`：

```text
[x1, y1, x2, y2]
```

要求：

```text
0 <= x1 < x2 <= 1
0 <= y1 < y2 <= 1
```

并且：

- 全部值必须 finite。
- 禁止 NaN。
- 禁止 ±Infinity。

归一化定义：

```text
normalized_x = pixel_x / image_width
normalized_y = pixel_y / image_height
```

`0.0` 表示左/上视觉边界，`1.0` 表示右/下视觉边界。

## 12. Rotated bbox / polygon 规范

内部和 Tool 输入使用：

```text
[x1, y1, x2, y2, x3, y3, x4, y4]
```

所有坐标均归一化到 `[0.0, 1.0]`。

Server 至少验证：

- 恰好四个顶点。
- 所有值 finite。
- 顶点不重复。
- polygon 不自交。
- polygon 为凸四边形。
- 面积大于 0。
- 邻边关系接近矩形。
- 对边接近平行。
- 对边长度关系合理。
- 坐标不越界。

### 12.1 Canonical ordering

Server 接收合法的循环顶点顺序后，应统一 canonicalize：

1. 按图像坐标系的顺时针顺序排列。
2. 起点选择 y 最小的顶点；若并列，则选择 x 最小的顶点。

不得接受明显自交的“蝴蝶结”顺序并静默重排为另一含义。

### 12.2 自动纠正

Rotated bbox 自动纠正默认开启，由 Server 全局参数控制。

行为分为：

```text
small deviation  -> 自动纠正
medium deviation -> 自动纠正 + warning
large deviation  -> error / reject
```

correction threshold 和 error threshold 必须有内置默认值，并允许 CLI/环境变量覆盖。

发生纠正时 Tool 结果必须返回：

- `submitted_geometry`
- `stored_geometry`
- `corrected: true`
- deviation/correction 相关结构化信息
- warning（如属于中等误差区间）

不得静默改变 geometry 而不向 Agent 报告。

## 13. Annotation 数据模型

所有 annotation 使用统一稳定 `annotation_id`。

至少保存：

```text
annotation_id
dataset_id
image_path
type = bbox | rotated_bbox
category_id
geometry
created_at
updated_at
```

要求：

- `annotation_id` 删除后不重新编号、不复用。
- annotation 删除为**硬删除**。
- bbox 与 rotated_bbox 不允许通过 edit 直接互相转换；类型转换通过 delete + add 完成。

## 14. Annotation 写入事务

批量 add 工具必须执行：

```text
BEGIN
  validate entire request
  validate all categories
  validate image
  validate every geometry
  insert all annotations
COMMIT
```

任意一个 annotation 无效：

```text
ROLLBACK
```

不得出现部分成功。

v1 不要求提供 idempotency key。虽然本地 STDIO 场景仍可能发生调用重试，但该问题不进入 v1 范围。

## 15. Preview 规范

### 15.1 preview_image

输入至少包括：

```text
dataset_id
image_path
max_width?
max_height?
allow_upscale? = false
```

Server 默认每边最大不超过 `768` 像素。每次调用给出的 requested max 不能突破 Server 全局 preview 上限；若请求超过上限，Server 可 clamp 到上限，但必须在 structured result 中返回实际尺寸和 `clamped=true`。

缩放保持纵横比，默认不放大小图。

返回：

- MCP image content
- original width/height
- preview width/height
- scale
- clamped / orientation-applied 等必要元数据

### 15.2 preview_annotations

输入至少包括：

```text
dataset_id
image_path
annotation_type = bbox | rotated_bbox | all
annotation_ids?
include_deleted_categories = false
max_width?
max_height?
```

渲染要求：

- 显示 `[annotation_id] category_name`。
- category 颜色由 `category_id` 确定性映射，不能每次随机。
- bbox 与 rotated_bbox 必须视觉可区分。
- 默认隐藏引用 deleted category 的 annotations。
- 渲染只发生在内存中，不在 dataset root 创建修改后的图片。

## 16. Export 规则

Tool：`export_metadata_jsonl`。

输入至少包括：

```text
dataset_id
output_path
export_mode = autotrain | extended
overwrite = false
```

### 16.1 导出图片范围

默认且固定只导出：

```text
image status == completed
```

`unannotated` 和 `in_progress` 不进入最终文件。

因此负样本必须显式标记为：

```text
completed + 0 annotations
```

### 16.2 Category 导出映射

导出时：

1. 排除软删除 category。
2. 排除引用软删除 category 的 annotations。
3. active category 按内部 `category_id ASC` 排序。
4. 映射为连续 `0..N-1` export category ID。

Exporter 结果必须返回 category mapping 和排除统计。

### 16.3 普通 bbox 导出

内部 normalized xyxy 转换为像素 COCO-style：

```text
[x, y, width, height]
```

计算：

```text
x      = x1 * W
y      = y1 * H
width  = (x2 - x1) * W
height = (y2 - y1) * H
```

### 16.4 Rotated bbox 导出

extended 模式下增加：

```text
objects.polygon
objects.polygon_category
```

polygon 输出像素 DOTA 8-point 格式：

```text
[x1, y1, x2, y2, x3, y3, x4, y4]
```

由归一化坐标乘视觉图像 W/H 得到。

对应关系：

```text
bbox[i]    <-> category[i]
polygon[i] <-> polygon_category[i]
```

### 16.5 export_mode = autotrain

只输出官方普通物体检测字段：

```json
{"file_name":"0001.png","objects":{"bbox":[],"category":[]}}
```

rotated annotations 不作为旋转框训练数据输出；Exporter 必须返回被忽略 rotated annotation 数量，不能无提示静默丢弃。

为了保持严格 AutoTrain 上传兼容性，preflight 必须检查至少：

- 导出图片为 JPEG/JPG/PNG。
- 导出路径为 flat layout；`file_name` 不含嵌套目录。
- 至少具有 AutoTrain 当前要求的最小图片数量。
- 输出 JSONL 的 bbox 为像素 COCO `[x,y,width,height]`。

若 dataset 的 completed 图片包含 nested path 或 WebP 等不兼容项，则 autotrain 模式失败并返回明确错误，而不是复制/移动原始图片来“修复”目录结构。

### 16.6 export_mode = extended

输出稳定对象 schema：

```json
{
  "file_name": "nested/0001.webp",
  "objects": {
    "bbox": [],
    "category": [],
    "polygon": [],
    "polygon_category": []
  }
}
```

不存在某种 annotation 时仍输出对应空数组。

该模式属于本项目扩展格式；`polygon` / `polygon_category` 不是当前 AutoTrain 官方旋转框字段。

### 16.7 原子文件写入

默认：

```text
overwrite = false
```

目标文件已存在时返回 `OUTPUT_ALREADY_EXISTS`。

导出必须：

1. 完成全数据集 preflight。
2. 写入同目录临时文件。
3. flush/close 成功。
4. 通过原子 rename/replace 生成最终 `metadata.jsonl`。

失败时不得留下一个看似有效但内容不完整的最终文件。

## 17. MCP Tools 清单（v1）

v1 共 **23 个 Tool**。

### 17.1 Dataset（5）

1. `create_dataset`
   - 输入：`root_path`, `name?`
   - 输出：dataset 基本信息、`dataset_id`
2. `delete_dataset`
   - 输入：`dataset_id`
   - 行为：软删除
3. `restore_dataset`
   - 输入：`dataset_id`
4. `list_datasets`
   - 输入：`include_deleted=false`
5. `get_dataset`
   - 输入：`dataset_id`

### 17.2 Category（6）

6. `add_categories`
   - 输入：`dataset_id`, `categories[]`
   - 原子批量添加
7. `edit_category`
   - 输入：`dataset_id`, `category_id`, `name?`, `description?`
8. `delete_category`
   - 软删除
9. `restore_category`
   - 输入允许 `new_name?`
10. `list_categories`
    - `include_deleted=false`
11. `get_category`
    - 可以读取 deleted category

### 17.3 Image（4）

12. `list_images`
    - 支持 status、name/random、seed、offset、max_results
13. `set_image_status`
    - `unannotated | in_progress | completed`
14. `preview_image`
15. `preview_annotations`

### 17.4 Annotation（7）

16. `list_annotations`
    - `image_path?`
    - `annotation_type?`
    - `category_ids?`
    - `annotation_ids?`
    - `include_deleted_categories=false`
    - `offset`
    - `max_results`
17. `add_bbox_annotations`
18. `edit_bbox_annotation`
19. `delete_bbox_annotation`
    - 实现允许一次删除一个或多个 annotation ID
20. `add_rotated_bbox_annotations`
21. `edit_rotated_bbox_annotation`
22. `delete_rotated_bbox_annotation`
    - 实现允许一次删除一个或多个 annotation ID

### 17.5 Export（1）

23. `export_metadata_jsonl`

## 18. Tool 输出与错误规范

### 18.1 Structured output

除 preview 图片本体外，Tool 应尽量返回结构化对象，不使用仅供人阅读的字符串作为唯一结果。

典型成功结果应包含相关 ID、最终存储 geometry、状态和统计。

### 18.2 错误对象

Tool 可修复的业务错误应返回稳定错误码，示例：

```json
{
  "code": "INVALID_BBOX",
  "message": "annotations[2].bbox requires x1 < x2",
  "field": "annotations[2].bbox",
  "details": {
    "received": [0.7, 0.2, 0.4, 0.8]
  }
}
```

至少定义：

```text
DATASET_NOT_FOUND
DATASET_DELETED
CATEGORY_NOT_FOUND
CATEGORY_DELETED
CATEGORY_NAME_CONFLICT
IMAGE_NOT_FOUND
IMAGE_ROOT_UNAVAILABLE
UNSUPPORTED_IMAGE_FORMAT
IMAGE_DECODE_FAILED
PATH_OUTSIDE_DATASET_ROOT
PATH_NOT_ALLOWED
ANNOTATION_NOT_FOUND
INVALID_BBOX
INVALID_ROTATED_BBOX
ROTATED_BBOX_CORRECTION_EXCEEDED
INVALID_ARGUMENT
OUTPUT_ALREADY_EXISTS
OUTPUT_PATH_NOT_ALLOWED
AUTOTRAIN_LAYOUT_INCOMPATIBLE
EXPORT_VALIDATION_FAILED
STORAGE_ERROR
TRANSACTION_FAILED
```

批量失败必须指出失败元素的 index/field，方便 Agent 修正后重试。

## 19. SQLite 数据模型要求

推荐最少表：

### `datasets`

```text
id INTEGER PRIMARY KEY
name TEXT
root_path TEXT NOT NULL
deleted_at TEXT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

### `categories`

```text
id INTEGER PRIMARY KEY
dataset_id INTEGER NOT NULL
name TEXT NOT NULL
description TEXT NULL
deleted_at TEXT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

active category 名称唯一约束可以通过 partial unique index 或事务级验证实现。

### `image_states`

```text
dataset_id INTEGER NOT NULL
image_path TEXT NOT NULL
status TEXT NOT NULL
updated_at TEXT NOT NULL
PRIMARY KEY(dataset_id, image_path)
```

无记录即 `unannotated`。

### `annotations`

```text
id INTEGER PRIMARY KEY
dataset_id INTEGER NOT NULL
image_path TEXT NOT NULL
type TEXT NOT NULL
category_id INTEGER NOT NULL
geometry_json TEXT NOT NULL
created_at TEXT NOT NULL
updated_at TEXT NOT NULL
```

geometry 必须由领域层再次验证，不能只依赖 JSON 数据存在。

### Schema migration

数据库必须具有明确 schema version，并提供向前迁移机制。升级 package/container 不应要求用户手工重建 annotation 数据库。

## 20. 服务内部架构要求

Tool 定义层不应直接堆积所有业务逻辑。推荐分层：

```text
FastMCP tools
    ↓
service / domain layer
    ├─ dataset service
    ├─ category service
    ├─ image scan/status service
    ├─ annotation service
    ├─ geometry validation/correction
    ├─ preview renderer
    └─ exporter
    ↓
SQLite repository + filesystem read layer
```

路径安全、geometry 校验、category active 状态、事务等规则必须由领域层集中实现，避免多个 Tool 出现不一致行为。

## 21. Agent Skills 要求

项目必须随仓库发布对应的 Agent Skills，用于帮助 AI Agent 正确安装、配置和操作 MCP。

Skills 应遵守开放的 Agent Skills `SKILL.md` 目录结构和 frontmatter 规范。不得依赖实验性的 `allowed-tools` 字段才能正常工作。

v1 至少提供两个 Skill：

### 21.1 `object-detection-annotation`

用途：指导 Agent 实际进行数据集标注。

必须覆盖：

- 如何发现/选择 dataset。
- 标注前如何 `list_categories` / `get_category` 获取权威类别定义。
- 如何选择 `unannotated` / `in_progress` 图片。
- 如何先设置 `in_progress`。
- 如何 preview 图片。
- 修改前如何 `list_annotations` 避免重复或覆盖错误。
- normalized xyxy 输入规范。
- rotated polygon 输入与纠正规则。
- 如何 add/edit/delete annotation。
- 如何通过 `preview_annotations` 检查结果。
- 如何正确处理负样本。
- 完成后如何设置 `completed`。
- 如何执行 export 及理解 autotrain/extended 区别。
- 常见错误及恢复流程。

建议目录：

```text
skills/object-detection-annotation/
├── SKILL.md
└── references/
    ├── tool-reference.md
    ├── annotation-rules.md
    ├── workflow.md
    ├── export-format.md
    └── troubleshooting.md
```

`SKILL.md` 保持精炼，通过 references 渐进式加载详细信息，避免每次触发都占用过多上下文。

### 21.2 `detection-mcp-setup`

用途：指导 Agent/用户安装和连接本 MCP。

必须覆盖：

- PyPI 安装。
- console entry point。
- MCP Host 的 STDIO 配置思路。
- Docker `-i` STDIO 运行。
- `/datasets:ro`、`/state:rw`、`/output:rw` 挂载。
- 容器内 dataset path 与宿主机 path 的映射概念。
- CLI/environment 配置优先级。
- 数据库持久化。
- 常见路径/权限/挂载错误诊断。

建议目录：

```text
skills/detection-mcp-setup/
├── SKILL.md
└── references/
    ├── pypi-install.md
    ├── docker-install.md
    ├── client-config.md
    └── configuration.md
```

### 21.3 Skills 发布要求

- 仓库根目录保留 `skills/`。
- Skills 只通过仓库根目录发布，不包含在 wheel、sdist 或 Docker 镜像中。
- README 必须提供从 GitHub 仓库直接安装 Skills 的命令。
- CI 必须校验每个 `SKILL.md` frontmatter、目录名一致性、内部 reference 链接完整性。

## 22. 推荐仓库结构

```text
detection-mcp/
├── pyproject.toml
├── README.md
├── LICENSE
├── Dockerfile
├── docker-compose.example.yml
├── src/
│   └── detection_mcp/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── server.py
│       ├── config.py
│       ├── models.py
│       ├── errors.py
│       ├── db/
│       │   ├── connection.py
│       │   ├── migrations.py
│       │   └── repositories.py
│       ├── tools/
│       │   ├── datasets.py
│       │   ├── categories.py
│       │   ├── images.py
│       │   ├── annotations.py
│       │   └── export.py
│       └── services/
│           ├── paths.py
│           ├── image_scan.py
│           ├── geometry.py
│           ├── preview.py
│           ├── annotations.py
│           └── exporter.py
├── skills/
│   ├── object-detection-annotation/
│   │   ├── SKILL.md
│   │   └── references/
│   └── detection-mcp-setup/
│       ├── SKILL.md
│       └── references/
├── docs/
│   ├── requirements.md
│   ├── tool-reference.md
│   ├── configuration.md
│   ├── export-format.md
│   └── docker.md
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    └── golden/
```

## 23. 测试要求

### 23.1 Unit tests

至少覆盖：

- bbox 边界值与非法值。
- NaN/Infinity 拒绝。
- rotated polygon 自交、凸性、矩形误差。
- canonical ordering。
- small/medium/large correction 行为。
- category soft delete / restore / rename conflict。
- dataset soft delete / restore。
- deleted category annotation 默认隐藏。
- deterministic random list_images。
- offset/max_results。
- path traversal 与 symlink escape。
- EXIF orientation 后坐标和尺寸。
- category export 0-based 连续映射。
- completed-only export。
- autotrain 与 extended schema。

### 23.2 Transaction tests

必须证明：

- 一批 annotation 中任意一项失败时，没有任何一项落库。
- 一批 category 中任意一项冲突时，没有任何一项落库。
- restore category 重名时不改变 deleted 状态。

### 23.3 MCP integration tests

使用 FastMCP Client 或等价测试方式验证：

- 可以列出 23 个 Tool。
- Tool schema 符合预期。
- 真实 STDIO 子进程可以连接。
- preview 返回 image content。
- structured error 可被客户端读取。

### 23.4 Packaging tests

CI 必须验证：

1. clean virtualenv 中构建并安装 wheel。
2. `detection-mcp --version` 正常。
3. PyPI 安装形态能够启动 STDIO Server。
4. Docker image 构建成功。
5. Docker 挂载只读数据集后可以 preview/annotate。
6. 容器重启后 `/state` 中 annotation 状态仍存在。
7. export 能写到 `/output`。
8. 不存在对 `/datasets` 的写入要求。

### 23.5 Skills tests

- `SKILL.md` YAML frontmatter 可解析。
- `name` 与父目录相同。
- `name` 满足小写字母/数字/连字符约束。
- description 非空且包含明确触发场景。
- references 均存在。
- Skill 中列出的 Tool 名称与 Server 实际 Tool 名称一致。

## 24. 日志与可诊断性

日志必须发送到 stderr，不污染 STDIO stdout。

建议记录：

- Server/version 启动信息。
- DB path（敏感路径可适度处理）。
- dataset register/delete/restore。
- export 结果摘要。
- rotated bbox correction warning。
- 可诊断的 filesystem/SQLite 错误。

Tool 返回中不得泄漏无必要的 Python traceback；详细 traceback 放日志，Tool 返回稳定错误码与可操作 message。

## 25. Agent 推荐工作流

标准标注流程：

```text
list/create dataset
        ↓
list_categories
        ↓
get_category
读取权威类别定义
        ↓
list_images(status=unannotated/in_progress)
        ↓
set_image_status(in_progress)
        ↓
preview_image
        ↓
list_annotations
        ↓
add / edit / delete annotations
        ↓
preview_annotations
        ↓
必要时继续修正
        ↓
set_image_status(completed)
        ↓
下一张
        ↓
export_metadata_jsonl
```

Skill 必须引导 Agent 遵循该流程，而不是在未读取类别定义和已有 annotations 的情况下盲目写入。

## 26. 验收标准（Definition of Done）

v1 可以发布的最低标准：

1. FastMCP Server 通过 STDIO 稳定运行。
2. 23 个 Tool 全部实现，并与文档名称/语义一致。
3. Dataset/category soft delete 和 restore 行为通过自动化测试。
4. Annotation add/edit/delete/list 完整可用。
5. 普通 bbox 与 rotated bbox 验证、纠正和结构化 warning/error 完成。
6. Batch 写入具有原子事务保证。
7. list_images 支持递归发现、status filter、稳定 random seed、offset 和 max_results。
8. Preview 最大边默认受 768 配置控制，并返回 MCP image content。
9. 原始图片无任何写操作代码路径。
10. `completed + 0 annotations` 可以正确导出为负样本。
11. export 排除 deleted category 及其 annotations，并生成连续 0-based category IDs。
12. autotrain 模式执行严格 preflight；extended 模式输出 DOTA 8-point polygon 扩展。
13. export 使用临时文件 + 原子替换，不产生半成品最终文件。
14. SQLite schema migration 机制存在并测试。
15. PyPI wheel/sdist 构建与安装通过。
16. Docker image 能以只读 dataset + 可写 state/output 挂载方式工作。
17. 至少两个 Agent Skills 创建完成并通过结构/链接检查。
18. README 提供 PyPI、Docker、MCP client 连接和 Skills 使用说明。
19. CI 覆盖 unit、integration、packaging、Docker、Skills validation。
20. 项目需求文档、Tool reference、configuration 和 export format 与实现保持一致。

## 27. v1 之后可考虑但当前不实现

- Annotation 操作历史、undo/redo、软删除或 audit log。
- 多 Agent 并发 revision / optimistic locking。
- Idempotency key。
- 图片 hash / external modification detection。
- 自动生成 AutoTrain flat archive（复制/重命名图片）。
- 远程 HTTP/Streamable HTTP 部署。
- 用户鉴权、多租户。
- segmentation mask / arbitrary polygon / keypoints。
- dataset split 管理。
- Web UI。
- 交互式 MCP App 标注界面。

## 28. 外部规范基线

实现与文档应参考以下上游规范，并在依赖升级时重新验证：

1. FastMCP 官方文档 / GitHub：FastMCP 用于通过 Python 函数定义 MCP tools，并生成 schema/validation；当前稳定安装可通过 `pip install fastmcp`。
2. Model Context Protocol 2026-07-28 Tools 规范：Tool 可以返回结构化内容以及 image content。
3. Hugging Face AutoTrain Object Detection：普通 bbox 使用像素 COCO `[x, y, width, height]`；上传格式要求 JPEG/JPG/PNG、flat archive 等。
4. Agent Skills Specification：每个 Skill 至少包含一个带 YAML frontmatter 的 `SKILL.md`；可使用 `references/`、`scripts/`、`assets/` 做渐进式组织。

本项目的 `objects.polygon` / `objects.polygon_category` 是自定义扩展，不应在文档中表述为 AutoTrain 官方 rotated bbox schema。
