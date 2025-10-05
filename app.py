import os
import subprocess
import json
import time
from flask import Flask, request, jsonify, send_from_directory, Response
from moviepy import VideoFileClip
 # 已移除requests，全部翻译走本地Argos Translate
from faster_whisper import WhisperModel
import argostranslate.package
import argostranslate.translate
import ffmpeg
import sys
if getattr(sys, 'frozen', False):
    # PyInstaller环境
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.abspath('.')
app = Flask(__name__, static_folder=os.path.join(BASE_PATH, 'assets'))
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def extract_audio_from_video(video_path, audio_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    audio.write_audiofile(audio_path)
    audio.close()
    video.close()

def transcribe_audio(audio_path):
    # 直接加载本地模型文件 model.bin
    model_dir = "assets/models"
    if not os.path.exists(os.path.join(model_dir, "model.bin")):
        raise FileNotFoundError("assets/models/model.bin 不存在，请确认模型已转换为CTranslate2格式并放置在assets/models目录下。")
    model = WhisperModel(model_dir, device="cpu", compute_type="float32", local_files_only=True)
    segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
    return segments, info.language

def argos_translate_text(text, target_lang):
    """
    使用 Argos Translate 进行英文到目标语言的翻译。
    自动安装所需包，优先本地，无则下载。
    """
    import argostranslate.package
    import argostranslate.translate

    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == 'en'), None)
    to_lang = next((lang for lang in installed_languages if lang.code == target_lang), None)
    if from_lang and to_lang:
        translation = from_lang.get_translation(to_lang)
        return translation.translate(text)
    try:
        argostranslate.package.update_package_index()
        available_packages = argostranslate.package.get_available_packages()
        package_to_install = next(
            (pkg for pkg in available_packages if pkg.from_code == 'en' and pkg.to_code == target_lang), None
        )
        if package_to_install:
            package_path = package_to_install.download()
            argostranslate.package.install_from_path(package_path)
            installed_languages = argostranslate.translate.get_installed_languages()
            from_lang = next((lang for lang in installed_languages if lang.code == 'en'), None)
            to_lang = next((lang for lang in installed_languages if lang.code == target_lang), None)
            if from_lang and to_lang:
                translation = from_lang.get_translation(to_lang)
                return translation.translate(text)
    except Exception as e:
        print(f"自动下载翻译包失败: {e}")
    print(f"未找到 {target_lang} 的翻译包或模型")
    return text

def generate_bilingual_srt(segments, translate=False):
    srt_content = []
    for idx, segment in enumerate(segments, 1):
        srt_content.append(f"{idx}")
        srt_content.append(f"{segment['timestart']} --> {segment['timestop']}")
        srt_content.append(segment['text'])
        if translate:
            translated = argos_translate_text(segment['text'])
            srt_content.append(translated)
        srt_content.append("")  # 空行分隔字幕
    return "\n".join(srt_content)

def embed_subtitles_in_video(video_path, srt_path, output_path):
    import shutil
    # 自动获取 ffmpeg.exe 绝对路径
    ffmpeg_bin_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'ffmpeg-8.0-essentials_build', 'ffmpeg-8.0-essentials_build', 'bin'))
    ffmpeg_path = os.path.join(ffmpeg_bin_dir, 'ffmpeg.exe')
    # 直接将 temp 文件存到 ffmpeg.exe 所在目录
    temp_video = os.path.join(ffmpeg_bin_dir, 'temp.mp4')
    temp_srt = os.path.join(ffmpeg_bin_dir, 'temp.srt')
    temp_output = os.path.join(ffmpeg_bin_dir, 'temp_out.mp4')
    shutil.copy(video_path, temp_video)
    shutil.copy(srt_path, temp_srt)
    print(f"[DEBUG] ffmpeg_path: {ffmpeg_path}")
    print(f"[DEBUG] temp_video: {temp_video}, exists: {os.path.exists(temp_video)}")
    print(f"[DEBUG] temp_srt: {temp_srt}, exists: {os.path.exists(temp_srt)}")
    print(f"[DEBUG] temp_output: {temp_output}")
    print(f"[DEBUG] output_path: {output_path}")
    # ffmpeg-python 处理 Windows 路径转义
    if not os.path.exists(temp_srt):
        raise FileNotFoundError(f"字幕文件不存在: {temp_srt}")
    if not os.path.exists(temp_video):
        raise FileNotFoundError(f"视频文件不存在: {temp_video}")
    # Windows 路径转义：反斜杠，盘符冒号转 \:，整体单引号包裹
    def win_ffmpeg_sub_path(path):
        p = os.path.abspath(path)
        # 先全部转为单反斜杠，再转为双反斜杠
        p = p.replace('/', '\\')
        p = p.replace('\\', '\\\\')
        if p[1] == ':':
            p = p[0] + '\\\\:' + p[2:]
        return f"'{p}'"

    srt_path_ffmpeg = win_ffmpeg_sub_path(temp_srt)
    old_cwd = os.getcwd()
    os.chdir(ffmpeg_bin_dir)
    try:
        (
            ffmpeg
            .input('temp.mp4')
            .output('temp_out.mp4', vf=f"subtitles={srt_path_ffmpeg}", vcodec='libx264', acodec='aac', strict='experimental')
            .run(overwrite_output=True, cmd=ffmpeg_path)
        )
    finally:
        os.chdir(old_cwd)
    if not os.path.exists(temp_output):
        raise FileNotFoundError(f"FFmpeg 输出文件不存在: {temp_output}")
    shutil.copy(temp_output, output_path)

@app.route('/')
def index():
    return send_from_directory(BASE_PATH, 'index.html')

# 处理静态资源访问
@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(os.path.join(BASE_PATH, 'assets'), filename)


# 新增流式进度接口
import json
import time


@app.route('/transcribe', methods=['POST'])
def transcribe():
    # 先处理 request 相关内容
    video_file = request.files['video-file']
    target_lang = request.form.get('target-lang', '')
    translate = bool(target_lang)
    source_lang = request.form.get('source-lang', None)
    if not source_lang or source_lang == 'auto':
        return jsonify({'error': '请在前端选择原视频语言，不能使用自动识别！'}), 400

    # 直接使用本地模型，无需检测和下载

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    video_file.save(video_path)

    audio_path = video_path.rsplit('.', 1)[0] + '.wav'
    extract_audio_from_video(video_path, audio_path)

    def generate():
        yield f"data: {json.dumps({'progress': 'transcribe', 'percent': 10, 'msg': '正在转录...'})}\n\n"
        segments, language = transcribe_audio(audio_path)
        segments = list(segments)
        yield f"data: {json.dumps({'progress': 'transcribe', 'percent': 60, 'msg': '转录完成'})}\n\n"

        # 输出转录内容（带时间戳）
        segment_dicts = []
        for segment in segments:
            seg_dict = {
                'timestart': f"{segment.start:.2f}",
                'timestop': f"{segment.end:.2f}",
                'text': segment.text,
                'translated': ''
            }
            segment_dicts.append(seg_dict)
        transcription_with_timestamps = [f"[{seg['timestart']} --> {seg['timestop']}] {seg['text']}" for seg in segment_dicts]
        transcription_text = "\n".join(transcription_with_timestamps)
        yield f"data: {json.dumps({'progress': 'transcription_ready', 'percent': 65, 'msg': '转录内容已输出', 'transcription': transcription_text, 'segments': segment_dicts})}\n\n"

        # 翻译
        if translate:
            total = len(segment_dicts)
            for idx, seg_dict in enumerate(segment_dicts, 1):
                seg_dict['translated'] = argos_translate_text(seg_dict['text'], target_lang)
                percent = int(65 + 30 * idx / total)
                yield f"data: {json.dumps({'progress': 'translate', 'percent': percent, 'msg': f'翻译 {idx}/{total}'})}\n\n"
        else:
            yield f"data: {json.dumps({'progress': 'translate', 'percent': 95, 'msg': '无需翻译'})}\n\n"

        # 生成 SRT 内容并保存
        srt_content = []
        for idx, seg in enumerate(segment_dicts, 1):
            srt_content.append(f"{idx}")
            srt_content.append(f"{seg['timestart']} --> {seg['timestop']}")
            srt_content.append(seg['text'])
            if translate:
                srt_content.append(seg['translated'])
            srt_content.append("")
        srt_content = "\n".join(srt_content)

        subtitle_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'subtitles')
        os.makedirs(subtitle_dir, exist_ok=True)
        srt_filename = os.path.basename(video_path).rsplit('.', 1)[0] + '.srt'
        srt_path = os.path.join(subtitle_dir, srt_filename)
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        subtitle_url = '/download/subtitle/' + srt_filename
        yield f"data: {json.dumps({'progress': 'done', 'percent': 100, 'msg': '字幕已生成', 'subtitle': subtitle_url, 'srt_path': srt_path, 'video_path': video_path})}\n\n"

    return Response(generate(), mimetype='text/event-stream')
# 新增生成嵌入字幕视频接口
@app.route('/generate-subtitled-video', methods=['POST'])
def generate_subtitled_video():
    data = request.get_json() or request.form
    video_path = data.get('video_path')
    srt_path = data.get('srt_path')
    if not video_path or not srt_path:
        return jsonify({'error': '参数缺失'}), 400
    output_video_path = video_path.rsplit('.', 1)[0] + '_subtitled.mp4'
    try:
        embed_subtitles_in_video(video_path, srt_path, output_video_path)
    except Exception as e:
        import traceback
        print('字幕嵌入异常详细信息:')
        traceback.print_exc()
        return jsonify({'error': f'字幕嵌入失败: {e}'})
    video_url = '/download/video/' + os.path.basename(output_video_path)
    return jsonify({'video': video_url, 'output_video_path': output_video_path})


# 新增下载接口
@app.route('/download/subtitle/<filename>')
def download_subtitle(filename):
    subtitle_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'subtitles')
    return send_from_directory(subtitle_dir, filename, as_attachment=True)

@app.route('/download/video/<filename>')
def download_video(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


# 新增翻译接口，支持前端 POST 文本和目标语言
@app.route('/translate-text', methods=['POST'])
def translate_text_api():
    # 支持批量分段翻译
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    segments = data.get('segments')
    target_lang = data.get('target_lang', 'zh')
    # segments 可能是字符串，需要解析
    if isinstance(segments, str):
        import ast
        segments = ast.literal_eval(segments)
    if not segments or not isinstance(segments, list):
        return jsonify({'error': '参数缺失或格式错误'}), 400
    # 批量翻译
    for seg in segments:
        text = seg.get('text', '')
        seg['translated'] = argos_translate_text(text, target_lang) if text else ''
    return jsonify({'segments': segments})

import webbrowser

if __name__ == '__main__':
    import threading
    def open_browser():
        import time
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000')
    threading.Thread(target=open_browser).start()
    app.run(debug=True, use_reloader=False)
