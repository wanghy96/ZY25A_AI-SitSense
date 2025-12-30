# PosePro-for-AI-Fitness-Coach

一个基于计算机视觉和姿态识别的智能深蹲训练系统，使用MediaPipe和Streamlit构建，能够实时监测用户的深蹲动作并提供即时反馈。

## 🎯 项目特色

- **实时姿态检测**：使用MediaPipe进行高精度的人体姿态识别
- **智能动作分析**：自动检测深蹲动作的各个阶段（站立、下蹲、最低点、起身）
- **即时反馈系统**：提供实时的动作纠正建议和语音提示
- **动作计数**：自动统计正确和错误的深蹲次数
- **Web界面**：基于Streamlit的现代化Web界面，支持实时视频流
- **多角度支持**：支持侧面和正面角度的动作监测

## 🚀 功能特性

### 动作监测
- **深蹲阶段识别**：自动识别深蹲的5个阶段（s1→s2→s3→s2→s1）
- **角度分析**：监测膝盖、髋部、脚踝等关键关节角度
- **姿势纠正**：检测并提示身体前倾、后仰、膝盖过脚尖等问题
- **深度控制**：监测下蹲深度，避免过深或过浅

### 智能反馈
- **实时提示**：屏幕显示实时的动作指导信息
- **语音提醒**：支持音频反馈（需要音频文件）
- **计数统计**：分别统计正确和错误的深蹲次数
- **状态重置**：长时间无活动时自动重置计数

### 用户界面
- **实时视频流**：支持摄像头实时视频流处理
- **视频录制**：可录制训练过程并下载
- **响应式设计**：适配不同屏幕尺寸
- **中文界面**：完全中文化的用户界面

## 📋 系统要求

- Python 3.7+
- 摄像头设备
- Windows/Linux/macOS

## 🛠️ 安装指南

### 1. 克隆项目
```bash
git clone <repository-url>
cd PosePro-for-AI-Fitness-Coach
```

### 2. 创建虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 运行应用
```bash
# 使用批处理文件（Windows）
start.bat

# 或直接运行
streamlit run AI-Fitness-Coach.py
```

## 📦 项目结构

```
PosePro-for-AI-Fitness-Coach/
├── AI-Fitness-Coach.py        # 主应用入口
├── frame_instance.py          # 帧处理类
├── state_tracker.py           # 状态跟踪器
├── process.py                 # 图像处理流程
├── utils.py                   # 工具函数
├── trainer_process_example.py # 深蹲训练逻辑
├── pages/                     # Streamlit页面
│   └── _开始锻炼.py           # 锻炼页面
├── requirements.txt           # 依赖包列表
├── start.bat                  # 启动脚本
├── Dockerfile                 # Docker配置
├── incorrect.wav             # 错误提示音频
├── reset_counters.wav        # 重置计数音频
└── docs/                     # 文档目录
    ├── frame_instance.md
    └── state_tracker.md
```

## 🔧 核心组件

### FrameInstance类
- 处理单帧图像和姿态检测
- 计算关键点坐标和角度
- 提供绘图和文本显示功能

### StateTracker类
- 跟踪深蹲动作的状态序列
- 管理动作计数和错误检测
- 处理长时间无活动的重置逻辑

### 训练器模块
- 实现深蹲动作的检测算法
- 提供实时的动作反馈
- 管理音频提示系统

## 🎮 使用方法

1. **启动应用**：运行`start.bat`或直接执行Streamlit命令
2. **选择页面**：在Web界面中选择"开始锻炼"
3. **调整位置**：确保摄像头能清晰看到你的侧面轮廓
4. **开始训练**：按照屏幕提示进行深蹲动作
5. **查看反馈**：注意屏幕上的实时提示和计数

## ⚙️ 配置选项

### 角度阈值
- **膝盖角度**：0-32°（站立），35-65°（下蹲），70-95°（最低点）
- **髋部角度**：检测身体前倾/后仰
- **脚踝角度**：检测膝盖是否超过脚尖

### 状态序列
```python
COMPLETE_STATE_SEQUENCE = ['s1', 's2', 's3', 's2', 's1']
```

### 超时设置
```python
INACTIVE_THRESH = 60.0  # 60秒无活动自动重置
```

## 🐳 Docker部署

```bash
# 构建镜像
docker build -t ai-squat-trainer .

# 运行容器
docker run -p 8501:8080 ai-squat-trainer
```

## 📝 依赖包

- `streamlit` - Web应用框架
- `opencv-python-headless` - 计算机视觉处理
- `mediapipe` - 姿态识别
- `numpy` - 数值计算
- `simpleaudio` - 音频播放
- `av` - 音视频处理
- `streamlit-webrtc` - WebRTC支持

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [MediaPipe](https://mediapipe.dev/) - 姿态识别框架
- [Streamlit](https://streamlit.io/) - Web应用框架
- [OpenCV](https://opencv.org/) - 计算机视觉库

---

**注意**：使用前请确保摄像头权限已开启，并在光线充足的环境下进行训练以获得最佳效果。
