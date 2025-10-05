# HEAT 视频转录翻译字幕工具

## 项目简介
HEAT 是一个基于 Flask 的本地化视频转录、翻译与字幕嵌入工具。支持通过本地 Whisper 模型进行语音识别，Argos Translate 进行离线翻译，并可自动调用 FFmpeg 将字幕嵌入视频。所有数据均在本地处理，无需联网。

## 功能特性
- 支持多种视频格式上传
- Whisper 本地模型高效转录
- Argos Translate 离线翻译（自动下载翻译包）
- 支持生成双语 SRT 字幕
- 一键嵌入字幕到视频
- 实时进度反馈，前端友好

## 环境准备
1. 安装 Python 3.8 及以上版本。
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 下载并解压 [FFmpeg Windows 版本](https://www.gyan.dev/ffmpeg/builds/)，将 `ffmpeg.exe` 放入 `ffmpeg-8.0-essentials_build/ffmpeg-8.0-essentials_build/bin/` 目录。
4. 准备 Whisper CTranslate2 格式模型（如 model.bin），放入 `assets/models/` 目录。

## 启动方式
### 1. 源码运行
```bash
python app.py
```
程序会自动打开浏览器，访问 http://127.0.0.1:5000

### 2. 打包为可执行文件
推荐使用 PyInstaller：
```bash
pyinstaller --onefile app.py --add-data "assets;assets" --add-data "uploads;uploads" --add-data "ffmpeg-8.0-essentials_build;ffmpeg-8.0-essentials_build"
```
打包后，将 index.html、assets、uploads、ffmpeg-8.0-essentials_build 等目录与可执行文件放在同一目录。

## 使用说明
1. 打开网页，上传视频文件，选择原始语言和目标翻译语言。
2. 点击开始，等待转录、翻译和字幕生成。
3. 下载生成的 SRT 字幕或带字幕的视频。

## 注意事项
- 所有处理均在本地完成，无需联网。
- Argos Translate 首次翻译时会自动下载所需语言包。
- 若遇到 404 或找不到资源，检查 index.html、assets/ 路径及 PyInstaller 打包参数。
- 仅支持本地模型推理，模型需提前准备好。

## 目录结构说明
- app.py                主程序入口
- index.html            前端页面
- assets/               静态资源与模型目录
- uploads/              上传及生成文件目录
- ffmpeg-8.0-essentials_build/  本地 FFmpeg 工具

## 常见问题
1. **404 页面找不到**：请确保 index.html 和 assets/ 与可执行文件同目录，或检查 BASE_PATH 路径处理。
2. **模型未找到**：请将 CTranslate2 格式的 Whisper 模型（model.bin）放入 assets/models/。
3. **FFmpeg 报错**：请确认 ffmpeg.exe 路径正确，且有执行权限。

## 致谢
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [Argos Translate](https://github.com/argosopentech/argos-translate)
- [moviepy](https://github.com/Zulko/moviepy)
- [FFmpeg](https://ffmpeg.org/)
