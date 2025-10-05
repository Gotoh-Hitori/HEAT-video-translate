const transcriptionTable = document.getElementById('transcription-table');
const transcriptionTableBody = transcriptionTable.querySelector('tbody');
let transcriptionSegments = [];

const uploadForm = document.getElementById('upload-form');
const progressContainer = document.getElementById('progress-container');
const transcribeProgressBar = document.getElementById('transcribe-progress-bar');
const transcribeProgressText = document.getElementById('transcribe-progress-text');
const translateProgressBar = document.getElementById('translate-progress-bar');
const translateProgressText = document.getElementById('translate-progress-text');
const videoPreview = document.getElementById('video-preview');
const previewPlayer = document.getElementById('preview-player');
const resultDiv = document.getElementById('result');


const transcriptionConsole = document.getElementById('transcription-console');


uploadForm.addEventListener('submit', function (e) {
    e.preventDefault();
    resultDiv.innerHTML = '';
    progressContainer.style.display = 'block';
    transcribeProgressBar.value = 0;
    transcribeProgressText.textContent = '';
    // 已删除翻译进度条相关逻辑
    transcriptionConsole.value = '';

    const fileInput = document.getElementById('video-file');
    const file = fileInput.files[0];
    const sourceLang = document.getElementById('source-lang').value;
    if (!sourceLang) {
        alert('请先选择原视频语言！');
        return;
    }
    const formData = new FormData();
    formData.append('video-file', file);
    formData.append('source-lang', sourceLang);
    const targetLang = document.getElementById('target-lang').value;
    formData.append('target-lang', targetLang);

    // 预览原视频（上传后立即显示）
    if (file) {
        videoPreview.style.display = 'block';
        previewPlayer.src = URL.createObjectURL(file);
    }

    // 使用 XMLHttpRequest 解析 SSE流
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/transcribe', true);
    xhr.responseType = 'text';

    let lastIndex = 0;
    xhr.onreadystatechange = function () {
        if (xhr.readyState === 3 || xhr.readyState === 4) {
            // 解析SSE流
            let chunk = xhr.responseText.substring(lastIndex);
            lastIndex = xhr.responseText.length;
            let events = chunk.split(/\n\n/);
            events.forEach(ev => {
                if (ev.trim().startsWith('data:')) {
                    try {
                        let jsonStr = ev.trim().replace(/^data:\s*/, '');
                        let data = JSON.parse(jsonStr);
                        if (data.progress === 'transcribe') {
                            // 转录开始，进度条显示
                            transcribeProgressBar.value = data.percent || 0;
                            transcribeProgressText.textContent = data.msg || '';
                        }
                        if (data.progress === 'transcription_ready' && data.transcription) {
                            // 转录完成，显示内容
                            transcriptionConsole.value = data.transcription;
                            transcribeProgressBar.value = data.percent || 0;
                            transcribeProgressText.textContent = data.msg || '';
                            if (data.segments) {
                                transcriptionSegments = data.segments;
                                renderTranscriptionTable(transcriptionSegments);
                                document.getElementById('edit-area').style.display = 'block';
                                // 初始化翻译控制台内容
                                renderTranslationTable(data.segments);
                            } else {
                                transcriptionTableBody.innerHTML = `<tr><td colspan='3'>无详细分段信息</td></tr>`;
                            }
                        }
                        // 已删除翻译进度条相关逻辑
                        if (data.progress === 'done') {
                            transcribeProgressBar.value = 100;
                            transcribeProgressText.textContent = '转录完成';
                            if (data.subtitle && data.video) {
                                resultDiv.innerHTML = `
                                    <h2>字幕文件：</h2>
                                    <a href="${data.subtitle}" download>下载字幕</a>
                                    <h2>带字幕的视频：</h2>
                                    <a href="${data.video}" download>下载视频</a>
                                    <video src="${data.video}" controls style="max-width:100%;margin-top:10px;"></video>
                                `;
                            }
                            // 自动保存 srt_path
                            if (data.srt_path) window.lastSrtPath = data.srt_path;
                            if (data.segments) {
                                transcriptionSegments = data.segments;
                                renderTranscriptionTable(transcriptionSegments);
                                document.getElementById('edit-area').style.display = 'block';
                            }
                        }
function renderTranscriptionTable(segments) {
    transcriptionTableBody.innerHTML = '';
    segments.forEach((seg, idx) => {
        const tr = document.createElement('tr');
        // 时间戳
        const tdTime = document.createElement('td');
        tdTime.innerHTML = `<input type='text' value='${seg.timestart} --> ${seg.timestop}' style='width:98%;'>`;
        // 原文
        const tdText = document.createElement('td');
        tdText.innerHTML = `<input type='text' value="${seg.text.replace(/"/g,'&quot;')}" style='width:98%;'>`;
        tr.appendChild(tdTime);
        tr.appendChild(tdText);
        transcriptionTableBody.appendChild(tr);
    });
}

function renderTranslationTable(segments) {
    const translationTableBody = document.getElementById('translation-table').querySelector('tbody');
    translationTableBody.innerHTML = '';
    segments.forEach((seg, idx) => {
        const tr = document.createElement('tr');
        // 原文
        const tdText = document.createElement('td');
        tdText.innerHTML = `<input type='text' value="${seg.text.replace(/"/g,'&quot;')}" style='width:98%;'>`;
        // 翻译
        const tdTrans = document.createElement('td');
        tdTrans.innerHTML = `<input type='text' value="${seg.translated ? seg.translated.replace(/"/g,'&quot;') : ''}" style='width:98%;'>`;
        tr.appendChild(tdText);
        tr.appendChild(tdTrans);
        translationTableBody.appendChild(tr);
    });
}
document.getElementById('save-transcription-btn').onclick = function() {
// 翻译控制台保存按钮
document.getElementById('save-translation-btn').onclick = function() {
    // 先获取翻译表格中的最新内容
    const translationTableBody = document.getElementById('translation-table').querySelector('tbody');
    const rows = translationTableBody.querySelectorAll('tr');
    rows.forEach((tr, idx) => {
        const inputs = tr.querySelectorAll('input');
        if (inputs.length === 2) {
            const text = inputs[0].value;
            const translated = inputs[1].value;
            if (transcriptionSegments[idx]) {
                transcriptionSegments[idx].text = text;
                transcriptionSegments[idx].translated = translated;
            }
        }
    });
    // 生成 SRT 字幕内容
    let srt = '';
    transcriptionSegments.forEach((seg, idx) => {
        srt += `${idx+1}\n`;
        srt += `${seg.timestart} --> ${seg.timestop}\n`;
        srt += `${seg.text}\n`;
        if (seg.translated) srt += `${seg.translated}\n`;
        srt += `\n`;
    });
    // 触发浏览器下载
    const blob = new Blob([srt], {type: 'text/srt'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'subtitles.srt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    document.getElementById('translate-result').innerHTML = '<span style="color:green;">SRT字幕已下载！</span>';
};

// 生成字幕并嵌入视频按钮
document.getElementById('generate-subtitle-btn').onclick = async function() {
    document.getElementById('subtitle-result').innerHTML = '正在生成字幕并嵌入视频...';
    try {
        // 获取 srt_path 和 video_path
        const srtPath = window.lastSrtPath || '';
        const fileName = document.getElementById('video-file').files[0].name;
        const videoPath = 'uploads/' + fileName;
        const resp = await fetch('/generate-subtitled-video', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({srt_path: srtPath, video_path: videoPath})
        });
        const data = await resp.json();
        let srtDownload = '';
        if (srtPath) {
            const srtUrl = '/download/subtitle/' + encodeURIComponent(srtPath.split(/[/\\]/).pop());
            srtDownload = `<h2>字幕文件：</h2><a href="${srtUrl}" download>下载SRT字幕</a>`;
        }
        if (data.video) {
            document.getElementById('subtitle-result').innerHTML = `
                ${srtDownload}
                <h2>带字幕的视频：</h2>
                <a href="${data.video}" download>下载视频</a>
                <video src="${data.video}" controls style="max-width:100%;margin-top:10px;"></video>
            `;
        } else {
            document.getElementById('subtitle-result').innerHTML = '<span style="color:red;">生成失败</span>';
        }
    } catch(e) {
        document.getElementById('subtitle-result').innerHTML = '<span style="color:red;">生成失败</span>';
    }
};
    // 保存用户更改到 transcriptionSegments
    const rows = transcriptionTableBody.querySelectorAll('tr');
    rows.forEach((tr, idx) => {
        const inputs = tr.querySelectorAll('input');
        if (inputs.length === 3) {
            const [time, text, translated] = inputs;
            const [timestart, timestop] = time.value.split('-->').map(s=>s.trim());
            transcriptionSegments[idx].timestart = timestart;
            transcriptionSegments[idx].timestop = timestop;
            transcriptionSegments[idx].text = text.value;
            transcriptionSegments[idx].translated = translated.value;
        }
    });
    alert('已保存更改！');
};
document.getElementById('translate-btn').onclick = async function() {
    // 翻译所有分段
    document.getElementById('translate-result').innerHTML = '正在翻译...';
    // 先保存用户更改
    document.getElementById('save-transcription-btn').onclick();
    const targetLang = document.getElementById('target-lang').value || 'zh';
    try {
        const resp = await fetch('/translate-text', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({segments: transcriptionSegments, target_lang: targetLang})
        });
        const data = await resp.json();
        if (data.segments) {
            // 更新表格翻译列
            transcriptionSegments = data.segments;
            renderTranscriptionTable(transcriptionSegments);
            renderTranslationTable(transcriptionSegments);
            document.getElementById('translate-result').innerHTML = '<span style="color:green;">翻译完成，可继续修改！</span>';
        } else {
            document.getElementById('translate-result').innerHTML = '<span style="color:red;">翻译失败</span>';
        }
    } catch(e) {
        document.getElementById('translate-result').innerHTML = '<span style="color:red;">翻译失败</span>';
    }
};
                    } catch(e) {}
                }
            });
        }
    };
    xhr.onerror = function () {
        transcribeProgressText.textContent = '上传或处理失败';
        resultDiv.innerHTML = '<span style="color:red;">网络错误，请重试。</span>';
    };
    xhr.send(formData);
});
