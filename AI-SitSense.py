import av
import os
import sys
import time
import threading
import traceback
import subprocess
import platform
import requests
import streamlit as st
from typing import Optional
from aiortc.contrib.media import MediaRecorder
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer

BASE_DIR = os.path.abspath(os.path.join(__file__, '../../'))
sys.path.append(BASE_DIR)

from utils import get_mediapipe_pose
from process import process, state_tracker
from frame_instance import FrameInstance

# 初始化 MediaPipe 姿态模型（全局共用，降低加载开销）
pose = get_mediapipe_pose()
output_video_file = "output_live.flv"

# DeepSeek API 配置
DEEPSEEK_API_KEY = "sk-17391aedc9a54cdfb23ec38744989584"  # TODO: 放入安全存储
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

# 系统通知支持
NOTIFICATION_AVAILABLE = False
notification = None
win10toast = None

try:
    from plyer import notification
    NOTIFICATION_AVAILABLE = True
except ImportError:
    try:
        import win10toast
        NOTIFICATION_AVAILABLE = True
    except ImportError:
        NOTIFICATION_AVAILABLE = False
        print("提示: 未安装系统通知库，请运行 'pip install plyer win10toast' 以启用系统通知功能")

_system_notification_lock = threading.Lock()
_last_system_notification_ts = 0.0
SYSTEM_NOTIFICATION_INTERVAL = 5.0
BAD_POSTURE_ALERT_THRESHOLD = 10.0  # 任一不良姿势持续10秒触发
POSTURE_LABELS = {
    'forward_head': "头部前倾",
    'head_tilt': "歪头",
    'spinal_curvature': "脊柱侧弯",
}


def show_system_notification(duration: float, posture_key: Optional[str]) -> None:
    """显示系统右下角通知"""
    posture_label = POSTURE_LABELS.get(posture_key, "不良坐姿")
    message = f"⚠️ {posture_label}已持续 {duration:.1f} 秒，请立刻调整。"

    if notification is not None:
        try:
            notification.notify(
                title="⚠️ 坐姿不良提醒",
                message=f"检测到{posture_label} {duration:.1f} 秒，请抬头挺胸，保持背部挺直。",
                app_name="坐姿监测系统",
                timeout=10,
            )
            print(f"✓ 系统通知已发送 (plyer): {message}")
            return
        except Exception as exc:
            print(f"✗ plyer通知失败: {exc}")

    if win10toast is not None:
        try:
            toaster = win10toast.ToastNotifier()
            toaster.show_toast(
                "⚠️ 坐姿不良提醒",
                f"{posture_label} {duration:.1f} 秒，请调整坐姿！",
                duration=10,
                threaded=True,
            )
            print(f"✓ 系统通知已发送 (win10toast): {message}")
            return
        except Exception as exc:
            print(f"✗ win10toast通知失败: {exc}")

    if platform.system() == "Windows":
        try:
            subprocess.Popen(
                ['msg', '%username%', message],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(f"✓ 系统通知已发送 (msg命令): {message}")
        except Exception as exc:
            print(f"✗ Windows命令通知失败: {exc}")


def _trigger_system_notification(duration: float, posture_key: Optional[str]) -> None:
    """节流触发系统通知"""
    global _last_system_notification_ts
    now = time.time()
    with _system_notification_lock:
        if now - _last_system_notification_ts < SYSTEM_NOTIFICATION_INTERVAL:
            return
        _last_system_notification_ts = now

    threading.Thread(target=show_system_notification, args=(duration, posture_key), daemon=True).start()


def call_deepseek_api(stats_data: dict) -> str:
    """调用 DeepSeek API 生成坐姿分析报告"""
    try:
        prompt = f"""
        你是一个专业的坐姿矫正师，请你依据坐姿检测数据说明用户存在的坐姿问题并且给出建议。

        坐姿检测数据：
        - 检测总时长：{stats_data['detection_duration']:.1f}秒
        - 头部前倾：发生了{stats_data['forward_head_count']}次，平均每次持续{stats_data['forward_head_avg_duration']:.1f}秒
        - 头部歪斜：发生了{stats_data['head_tilt_count']}次，平均每次持续{stats_data['head_tilt_avg_duration']:.1f}秒
        - 脊柱侧弯：发生了{stats_data['spinal_curvature_count']}次，平均每次持续{stats_data['spinal_curvature_avg_duration']:.1f}秒

        详细记录：
        {stats_data['detailed_records']}

        请用专业但易懂的语言，以200-300字分析问题、给出建议、指出注意事项。
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的坐姿矫正师，专注于帮助用户改善坐姿问题，预防颈椎和脊柱疾病。"
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']
    except requests.exceptions.RequestException as exc:
        return f"API调用失败: {exc}"
    except Exception as exc:
        return f"处理响应时出错: {exc}"


def video_frame_callback(frame: av.VideoFrame) -> av.VideoFrame:
    """webrtc 视频帧回调：处理画面并触发后台通知"""
    try:
        ndarray = frame.to_ndarray(format="rgb24")
        processed = process(FrameInstance(ndarray, pose))

        alert_needed, posture_key, alert_duration = state_tracker.should_trigger_alert(
            BAD_POSTURE_ALERT_THRESHOLD
        )
        if alert_needed:
            _trigger_system_notification(alert_duration, posture_key)

        return av.VideoFrame.from_ndarray(processed, format="rgb24")
    except Exception as exc:
        traceback.print_exc()
        raise exc


def out_recorder_factory() -> MediaRecorder:
    return MediaRecorder(output_video_file)


def render_live_status(ctx) -> None:
    """展示融合自“开始锻炼”页面的实时姿态状态与调试信息"""
    st.subheader("实时坐姿状态")
    status_placeholder = st.empty()

    if ctx.state.playing:
        current_state = state_tracker.get_state()
        durations = {
            "forward_head": state_tracker.get_forward_head_duration(),
            "head_tilt": state_tracker.get_head_tilt_duration(),
            "spinal_curvature": state_tracker.get_spinal_curvature_duration(),
        }
        alert_needed, alert_key, alert_duration = state_tracker.should_trigger_alert(
            BAD_POSTURE_ALERT_THRESHOLD
        )

        with status_placeholder.container():
            st.markdown("---")
            if current_state == 'bad_posture':
                st.markdown("""
                <div style='background-color:#ff4444;color:white;padding:15px;border-radius:10px;
                            text-align:center;font-size:20px;font-weight:bold;margin:10px 0;'>
                    🔴 检测到不良坐姿 - 请立即调整！
                </div>
                """, unsafe_allow_html=True)

                warning_parts = []
                if durations["forward_head"] > 0:
                    warning_parts.append(f"头部前倾 {durations['forward_head']:.1f} 秒")
                if durations["head_tilt"] > 0:
                    warning_parts.append(f"歪头 {durations['head_tilt']:.1f} 秒")
                if durations["spinal_curvature"] > 0:
                    warning_parts.append(f"肩膀不平 {durations['spinal_curvature']:.1f} 秒")

                if warning_parts:
                    st.warning(" / ".join(warning_parts))
            elif current_state == 'no_posture':
                st.info("📹 无法识别关键点，请正对摄像头并确保光线充足。")
            else:
                st.success("🟢 姿态良好，请保持！")

            with st.expander("📝 详细调试信息", expanded=False):
                st.metric("当前状态", current_state or "未识别")
                cols = st.columns(3)
                cols[0].metric("前倾持续", f"{durations['forward_head']:.1f} 秒")
                cols[1].metric("歪头持续", f"{durations['head_tilt']:.1f} 秒")
                cols[2].metric("肩膀不平", f"{durations['spinal_curvature']:.1f} 秒")
                status_text = "已触发" if alert_needed else "等待阈值"
                st.caption(f"系统通知监控：{status_text} (阈值 {BAD_POSTURE_ALERT_THRESHOLD:.0f}s)")

            if alert_needed:
                label = POSTURE_LABELS.get(alert_key, "不良坐姿")
                st.error(f"⚠️ {label} 已持续 {alert_duration:.1f} 秒，后台系统通知正在提醒。")
            else:
                st.info(f"系统通知守护已开启，任一不良坐姿持续 {BAD_POSTURE_ALERT_THRESHOLD:.0f} 秒将提醒。")
    else:
        with status_placeholder.container():
            st.info("等待启动摄像头... 点击上方“实时检测”中的按钮以开始。")


def render_detection_dashboard(ctx):
    """原 AI 页面中的检测统计与 DeepSeek 评估逻辑"""
    st.subheader("检测统计")

    if ctx.state.playing:
        if st.session_state['detection_start_time'] is None:
            st.session_state['detection_start_time'] = time.time()
            state_tracker.reset_stats()
            st.session_state['detection_completed'] = False
            st.session_state['deepseek_response'] = None

        detection_duration = time.time() - st.session_state['detection_start_time']
        current_stats = state_tracker.get_all_stats()

        st.metric("检测时长", f"{detection_duration:.1f} 秒")
        st.caption("检测到不良坐姿时会自动记录持续时间，超过 15 秒会计数，超过 10 秒触发系统提醒。")

        col1, col2, col3 = st.columns(3)
        col1.metric("头部前倾次数", current_stats['forward_head']['count'])
        col1.metric("平均持续", f"{current_stats['forward_head']['avg_duration']:.1f} 秒")
        col2.metric("歪头次数", current_stats['head_tilt']['count'])
        col2.metric("平均持续", f"{current_stats['head_tilt']['avg_duration']:.1f} 秒")
        col3.metric("脊柱侧弯次数", current_stats['spinal_curvature']['count'])
        col3.metric("平均持续", f"{current_stats['spinal_curvature']['avg_duration']:.1f} 秒")

        total_bad_postures = (
            current_stats['forward_head']['count'] +
            current_stats['head_tilt']['count'] +
            current_stats['spinal_curvature']['count']
        )

        if total_bad_postures > 0:
            with st.expander("实时详细记录", expanded=False):
                if current_stats['forward_head']['count'] > 0:
                    st.write("**头部前倾记录：**")
                    for i, duration in enumerate(current_stats['forward_head']['durations'], 1):
                        st.write(f"第{i}次: {duration:.1f} 秒")
                if current_stats['head_tilt']['count'] > 0:
                    st.write("**歪头记录：**")
                    for i, duration in enumerate(current_stats['head_tilt']['durations'], 1):
                        st.write(f"第{i}次: {duration:.1f} 秒")
                if current_stats['spinal_curvature']['count'] > 0:
                    st.write("**脊柱侧弯记录：**")
                    for i, duration in enumerate(current_stats['spinal_curvature']['durations'], 1):
                        st.write(f"第{i}次: {duration:.1f} 秒")
    else:
        if st.session_state['detection_start_time'] is not None and not st.session_state['detection_completed']:
            detection_duration = time.time() - st.session_state['detection_start_time']
            st.session_state['detection_duration'] = detection_duration
            st.session_state['detection_completed'] = True
            st.session_state['final_stats'] = state_tracker.get_all_stats()
            st.session_state['detection_start_time'] = None

        if st.session_state['detection_completed'] and st.session_state['final_stats']:
            final_stats = st.session_state['final_stats']
            detection_duration = st.session_state['detection_duration']

            st.success("检测已结束，可查看总结与AI评估。")
            st.metric("总检测时长", f"{detection_duration:.1f} 秒")

            col1, col2, col3 = st.columns(3)
            forward_head_count = final_stats['forward_head']['count']
            head_tilt_count = final_stats['head_tilt']['count']
            spinal_curvature_count = final_stats['spinal_curvature']['count']

            col1.metric("头部前倾次数", forward_head_count)
            col1.metric("平均持续", f"{final_stats['forward_head']['avg_duration']:.1f} 秒")
            col2.metric("歪头次数", head_tilt_count)
            col2.metric("平均持续", f"{final_stats['head_tilt']['avg_duration']:.1f} 秒")
            col3.metric("脊柱侧弯次数", spinal_curvature_count)
            col3.metric("平均持续", f"{final_stats['spinal_curvature']['avg_duration']:.1f} 秒")

            total_bad_postures = forward_head_count + head_tilt_count + spinal_curvature_count
            if total_bad_postures == 0:
                st.success("🎉 优秀！检测期间未发现任何不良姿势。")
            elif total_bad_postures <= 3:
                st.warning(f"⚠️ 良好！发现 {total_bad_postures} 次不良姿势，请继续保持。")
            else:
                st.error(f"❌ 需要注意！发现 {total_bad_postures} 次不良姿势，请重点纠正。")

            with st.expander("查看详细记录与AI建议", expanded=False):
                detailed_records = []
                if forward_head_count > 0:
                    st.write("**头部前倾记录：**")
                    for i, duration in enumerate(final_stats['forward_head']['durations'], 1):
                        record = f"第{i}次: {duration:.1f} 秒"
                        st.write(record)
                        detailed_records.append(record)
                if head_tilt_count > 0:
                    st.write("**歪头记录：**")
                    for i, duration in enumerate(final_stats['head_tilt']['durations'], 1):
                        record = f"第{i}次: {duration:.1f} 秒"
                        st.write(record)
                        detailed_records.append(record)
                if spinal_curvature_count > 0:
                    st.write("**脊柱侧弯记录：**")
                    for i, duration in enumerate(final_stats['spinal_curvature']['durations'], 1):
                        record = f"第{i}次: {duration:.1f} 秒"
                        st.write(record)
                        detailed_records.append(record)

                st.markdown("---")
                st.subheader("AI 坐姿评估")

                if st.button("生成坐姿评估报告", type="primary"):
                    with st.spinner("正在调用AI完成坐姿评估，请稍候..."):
                        stats_data = {
                            'detection_duration': detection_duration,
                            'forward_head_count': forward_head_count,
                            'forward_head_avg_duration': final_stats['forward_head']['avg_duration'],
                            'head_tilt_count': head_tilt_count,
                            'head_tilt_avg_duration': final_stats['head_tilt']['avg_duration'],
                            'spinal_curvature_count': spinal_curvature_count,
                            'spinal_curvature_avg_duration': final_stats['spinal_curvature']['avg_duration'],
                            'detailed_records': "\n".join(detailed_records) or "检测期间未记录详细问题。",
                        }
                        st.session_state['deepseek_response'] = call_deepseek_api(stats_data)

                if st.session_state['deepseek_response']:
                    st.markdown("### 坐姿评估报告")
                    st.info(st.session_state['deepseek_response'])
        else:
            st.info("点击上方“开始”按钮即可开启新一轮检测。")


def render_download_section():
    st.markdown("---")
    download_button = st.empty()

    if os.path.exists(output_video_file):
        with open(output_video_file, 'rb') as op_vid:
            download = download_button.download_button(
                '下载检测视频', data=op_vid, file_name='output_live.flv'
            )
            if download:
                st.session_state['download'] = True

    if os.path.exists(output_video_file) and st.session_state.get('download'):
        os.remove(output_video_file)
        st.session_state['download'] = False
        download_button.empty()


def render_app():
    st.set_page_config(page_title="坐姿监测", layout="centered", page_icon="🪑")
    st.title('🪑 坐伴——AI智能坐姿检测系统')

    # 初始化会话状态
    st.session_state.setdefault('download', False)
    st.session_state.setdefault('detection_start_time', None)
    st.session_state.setdefault('deepseek_response', None)
    st.session_state.setdefault('detection_completed', False)
    st.session_state.setdefault('final_stats', None)
    st.session_state.setdefault('detection_duration', 0.0)

    with st.expander("使用说明", expanded=True):
        st.markdown("""
        **检测规则：**
        - 头部前倾 / 歪头 / 脊柱侧弯持续超过 15 秒计为 1 次
        - 任一不良姿势持续 10 秒会自动触发系统右下角提醒
        - 实时显示坐姿状态、持续时间和统计信息
        - 检测结束后可调用 AI 生成个性化建议
        """)

    st.subheader("实时检测")
    ctx = webrtc_streamer(
        key="posture-monitor",
        video_frame_callback=video_frame_callback,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={
            "video": {
                "width": {'min': 640, 'ideal': 960},
                "height": {'min': 480, 'ideal': 720},
            },
            "audio": True,
        },
        video_html_attrs=VideoHTMLAttributes(
            autoPlay=True,
            controls=False,
            muted=True,
            style={"width": "960px", "maxWidth": "100%"},
        ),
        out_recorder_factory=out_recorder_factory,
    )

    render_live_status(ctx)
    render_detection_dashboard(ctx)
    render_download_section()


if __name__ == "__main__":
    render_app()