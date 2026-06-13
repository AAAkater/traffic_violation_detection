# 交通违法检测系统 (Traffic Violation Detection)

基于 YOLO 目标检测 + 多模态 LLM 判定的交通违法检测流水线。

## 架构

```txt
浏览器 → nginx (web) → /api/v1/* → FastAPI (server-cuda)
                       → /traffic/* → RustFS (对象存储)

PostgreSQL ─┘                           └─ RustFS
```

## Docker 一键部署

```bash
cd docker/cuda

# 0. 修复 rustfs 数据目录权限（首次部署需要）
sudo chown -R 10001:10001 ./volumes/rustfs

# 1. 准备模型权重（可选，不设置时首次启动自动下载）
mkdir -p volume/models
# 可选：提前放置模型文件以加速首次启动
# cp /path/to/yolo.pt volume/models/v1.pt

# 2. 复制环境变量配置
cp .env.example .env
# 编辑 .env 设置 S3_PUBLIC_ENDPOINT 等

# 3. 构建并启动
docker compose up -d --build
```

首次启动会自动创建数据库表。

### 环境变量

| 变量                   | 默认值     | 说明                                              |
| ---------------------- | ---------- | ------------------------------------------------- |
| `IS_DEV`               | `false`    | 开发模式：`true` 时输出 DEBUG 日志 + 保存调试图片 |
| `YOLO_MODEL_PATH`      | 空         | YOLO 模型权重路径，不设置时自动下载               |
| `POSTGRES_SERVER`      | `postgres` | 数据库主机                                        |
| `S3_SERVER`            | `rustfs`   | 对象存储主机                                      |
| `S3_PUBLIC_ENDPOINT`   | 空         | 公网访问地址（nginx 域名），用于生成图片外链      |
| `S3_PRESIGNED_EXPIRES` | `600`      | 图片外链有效期（秒）                              |

---

后端开发见 [server/README.md](server/README.md)，前端开发见 [web/README.md](web/README.md)。
