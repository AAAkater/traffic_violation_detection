# 交通违法判定服务 (Traffic Violation Detection)

基于 YOLO 目标检测 + LLM 判定的交通违法检测流水线，支持 NVIDIA CUDA GPU 环境。

## 目录结构

```
traffic_violation_detection/
├── main.py                  # FastAPI 服务入口
├── detector/                # 检测 & 判定核心逻辑
│   ├── detect.py            # YOLO 目标检测
│   ├── filter.py            # 检测结果过滤
│   ├── draw.py              # 标注绘制
│   └── api/                 # FastAPI 路由 & 生命周期
├── docker/
│   └── cuda/                # NVIDIA GPU 部署
│       ├── Dockerfile
│       └── docker-compose.yaml
└── models/                  # 模型权重目录（自动从 ModelScope 下载）
```

---

## Docker 部署

### 前置条件

- **Docker** >= 20.10
- **NVIDIA GPU**：安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

### 1. 准备模型权重（可选）

启动时如果 `volume/models/` 目录下没有模型权重文件，服务会**自动从 ModelScope 下载**，无需手动准备。

如需使用自己的模型，放入 `docker/cuda/volume/models/` 即可。

### 2. 配置环境变量

复制并编辑环境变量文件：

```bash
cp docker/cuda/.env.example docker/cuda/.env
vim docker/cuda/.env
```

必须填写的变量：

| 变量             | 说明                                |
| ---------------- | ----------------------------------- |
| `JUDGE_API_KEY`  | LLM 判定接口的 API Key（必填）      |
| `JUDGE_BASE_URL` | LLM API 地址                        |
| `JUDGE_MODEL`    | 判定模型名称（默认 `qwen3.7-plus`） |

`YOLO_MODEL_PATH` 等其余变量已有默认值，一般无需修改。

### 3. 启动服务

```bash
cd docker/cuda
docker compose up -d
```

首次运行会自动构建镜像（约 5-10 分钟），后续启动直接复用已有镜像。

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:4321/v1/health

# 上传图片进行违法判定
curl -X POST http://localhost:4321/v1/judge \
  -F "file=@/path/to/image.jpg"

# 返回示例
{
    "code": 0,
    "msg": "success",
    "data": {
        "filename": "2132978.jpg",
        "violated": true,
        "reason": "1. 观察第4张嫌疑车辆图及前几张图的车道标线，嫌疑车辆（消防车）位于最左侧车道，地面标线显示为左转箭头，判定车辆正在左转。2. 分析三张检测图，左侧横杆上的信号灯（对应左转）始终标注为red（红色左转箭头），中间横杆上的信号灯（对应直行）标注为green。3. 车辆为左转，应参考左转信号灯。4. 在车辆通过路口（越过停止线进入路口）的过程中，对应的左转信号灯始终为red，因此判定为闯红灯。"
    }
}
```

### 5. 查看日志

```bash
cd docker/cuda && docker compose logs -f
```

### 6. 停止服务

```bash
cd docker/cuda && docker compose down
```

---