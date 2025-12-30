import cv2
import math
from frame_instance import FrameInstance
from state_tracker import StateTracker
import simpleaudio as sa
import threading

# 全局变量，用于跟踪音频的播放状态
is_playing = False

def play_sound(sound_file):
    global is_playing
    try:
        wave_obj = sa.WaveObject.from_wave_file(f"{sound_file}.wav")
        play_obj = wave_obj.play()
        play_obj.wait_done()
        is_playing = False  # 音频播放完成，更新状态
        print(f"音频播放完成: {sound_file}")
    except Exception as e:
        print(f"播放音频失败: {e}")
        is_playing = False

# 坐姿状态序列
COMPLETE_STATE_SEQUENCE = ['good_posture', 'bad_posture']

# 未活动监测的时长阈值，单位秒
INACTIVE_THRESH = 60.0

def calculate_head_tilt_angle(left_ear, right_ear):
    """计算头部倾斜角度（修正版）"""
    if left_ear is None or right_ear is None:
        return 0

    # 计算左右耳的连线与水平线的角度
    dx = right_ear[0] - left_ear[0]
    dy = right_ear[1] - left_ear[1]

    # 如果dx为0，避免除以零错误
    if dx == 0:
        return 90 if dy > 0 else -90

    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)

    # 将角度转换到0-360度范围
    if angle_deg < 0:
        angle_deg += 360

    return angle_deg

def calculate_shoulder_level(left_shldr, right_shldr):
    """计算肩膀水平度"""
    if left_shldr is None or right_shldr is None:
        return 0

    # 计算左右肩膀的Y坐标差异（垂直方向）
    y_diff = abs(left_shldr[1] - right_shldr[1])

    return y_diff

def trainer_process(frame_instance, state_tracker, frame_width, frame_height):
    global is_playing

    # 检测是否能够获取到鼻子、肩膀和耳朵的关键点
    nose_coord = frame_instance.get_coord('nose')
    left_shldr_coord = frame_instance.get_coord('left_shldr')
    right_shldr_coord = frame_instance.get_coord('right_shldr')
    left_ear_coord = frame_instance.get_coord('left_ear')
    right_ear_coord = frame_instance.get_coord('right_ear')

    # 检查关键点是否有效（不为None且不为[0,0]）
    has_nose = nose_coord is not None and not (nose_coord[0] == 0 and nose_coord[1] == 0)
    has_left_shldr = left_shldr_coord is not None and not (left_shldr_coord[0] == 0 and left_shldr_coord[1] == 0)
    has_right_shldr = right_shldr_coord is not None and not (right_shldr_coord[0] == 0 and right_shldr_coord[1] == 0)
    has_left_ear = left_ear_coord is not None and not (left_ear_coord[0] == 0 and left_ear_coord[1] == 0)
    has_right_ear = right_ear_coord is not None and not (right_ear_coord[0] == 0 and right_ear_coord[1] == 0)

    if not has_nose or not has_left_shldr or not has_right_shldr or not has_left_ear or not has_right_ear:
        # 无法检测到完整的关键点，提示用户正对屏幕
        state_tracker.set_state('no_posture')

        # 绘制已有的关键点
        if has_nose:
            frame_instance.circle('nose', radius=7, color='yellow')
        if has_left_shldr:
            frame_instance.circle('left_shldr', radius=7, color='yellow')
        if has_right_shldr:
            frame_instance.circle('right_shldr', radius=7, color='yellow')
        if has_left_ear:
            frame_instance.circle('left_ear', radius=7, color='yellow')
        if has_right_ear:
            frame_instance.circle('right_ear', radius=7, color='yellow')

        # 提示用户正对屏幕
        frame_instance.draw_text(
            text='请正对屏幕',
            pos=(40, frame_height - 90),
            text_color=(0, 255, 230),
            font_scale=0.65,
            bg_color=(255, 153, 0),
        )
        frame_instance.draw_text(
            text='确保摄像头能清晰看到您的头部和肩膀',
            pos=(40, frame_height - 40),
            text_color=(255, 255, 230),
            font_scale=0.65,
            bg_color=(255, 153, 0),
        )

    else:
        # 成功检测到所有关键点，计算头部前倾角度和歪头角度
        head_forward_angle = frame_instance.get_angle('left_shldr', 'nose', 'right_shldr')
        head_tilt_angle = calculate_head_tilt_angle(left_ear_coord, right_ear_coord)

        # 计算与水平线(180度)的偏差
        tilt_deviation = min(
            abs(head_tilt_angle - 180),  # 与180度的偏差
            abs(head_tilt_angle - 0)  # 与0度的偏差（考虑到360度循环）
        )

        # 计算肩膀水平度
        shoulder_level_diff = calculate_shoulder_level(left_shldr_coord, right_shldr_coord)

        # 绘制关键点和连线
        frame_instance.circle('nose', 'left_shldr', 'right_shldr', 'left_ear', 'right_ear', radius=7, color='yellow')
        frame_instance.line('nose', 'left_shldr', 'light_blue', 3)
        frame_instance.line('nose', 'right_shldr', 'light_blue', 3)
        frame_instance.line('left_shldr', 'right_shldr', 'light_blue', 2)
        frame_instance.line('left_ear', 'right_ear', 'pink', 2)  # 用粉色显示耳朵连线

        # 显示角度值
        cv2.putText(frame_instance.frame, f'{head_forward_angle}°',
                    (nose_coord[0] + 20, nose_coord[1]),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 230), 2)

        # 在耳朵连线中点显示歪头角度
        ear_mid_x = (left_ear_coord[0] + right_ear_coord[0]) // 2
        ear_mid_y = (left_ear_coord[1] + right_ear_coord[1]) // 2
        cv2.putText(frame_instance.frame, f'{tilt_deviation:.1f}°',
                    (ear_mid_x, ear_mid_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 192, 203), 2)

        # 在肩膀连线中点显示肩膀水平度
        shldr_mid_x = (left_shldr_coord[0] + right_shldr_coord[0]) // 2
        shldr_mid_y = (left_shldr_coord[1] + right_shldr_coord[1]) // 2
        cv2.putText(frame_instance.frame, f'{shoulder_level_diff:.0f}px',
                    (shldr_mid_x, shldr_mid_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # 判断坐姿状态
        has_forward_head = head_forward_angle > 107
        has_head_tilt = tilt_deviation > 15  # 歪头偏差阈值设为15度
        has_spinal_curvature = shoulder_level_diff > 20  # 脊柱侧弯阈值设为20像素

        # 绘制水平参考线（用于可视化肩膀水平度）
        if has_spinal_curvature:
            # 如果肩膀不平，绘制水平参考线
            ref_y = min(left_shldr_coord[1], right_shldr_coord[1]) + 20
            cv2.line(frame_instance.frame,
                     (left_shldr_coord[0] - 30, ref_y),
                     (right_shldr_coord[0] + 30, ref_y),
                     (0, 255, 255), 2, cv2.LINE_AA)

            # 标记较高的肩膀
            higher_shoulder = "左肩" if left_shldr_coord[1] < right_shldr_coord[1] else "右肩"
            cv2.putText(frame_instance.frame, f'{higher_shoulder}较高',
                        (shldr_mid_x, shldr_mid_y + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # 设置状态 - 现在需要传递具体的不良姿势类型
        bad_posture_types = []
        if has_forward_head:
            bad_posture_types.append('forward_head')
        if has_head_tilt:
            bad_posture_types.append('head_tilt')
        if has_spinal_curvature:
            bad_posture_types.append('spinal_curvature')

        if has_forward_head or has_head_tilt or has_spinal_curvature:
            state_tracker.set_state('bad_posture', bad_posture_types)

            # 显示不良坐姿警告
            frame_instance.draw_text(
                text='处于不良坐姿',
                pos=(40, frame_height - 140),
                text_color=(255, 255, 230),
                font_scale=0.7,
                bg_color=(221, 0, 0),  # 红色背景表示警告
            )

            # 显示具体问题
            problem_text = ""
            if has_forward_head and has_head_tilt and has_spinal_curvature:
                problem_text = "头部前倾 + 歪头 + 脊柱侧弯"
            elif has_forward_head and has_head_tilt:
                problem_text = "头部前倾 + 歪头"
            elif has_forward_head and has_spinal_curvature:
                problem_text = "头部前倾 + 脊柱侧弯"
            elif has_head_tilt and has_spinal_curvature:
                problem_text = "歪头 + 脊柱侧弯"
            elif has_forward_head:
                problem_text = "头部前倾"
            elif has_head_tilt:
                problem_text = "头部歪斜"
            elif has_spinal_curvature:
                problem_text = "脊柱侧弯"

            frame_instance.draw_text(
                text=problem_text,
                pos=(40, frame_height - 90),
                text_color=(255, 255, 230),
                font_scale=0.65,
                bg_color=(221, 0, 0),
            )

            # 显示具体角度
            detail_text = f"前倾: {head_forward_angle}° | 歪斜: {tilt_deviation:.1f}° | 肩膀差: {shoulder_level_diff:.0f}px"

            frame_instance.draw_text(
                text=detail_text,
                pos=(40, frame_height - 40),
                text_color=(255, 255, 230),
                font_scale=0.6,
                bg_color=(221, 0, 0),
            )

            # 检查是否需要播放提示音（仅针对头部前倾）
            if has_forward_head and state_tracker.should_play_alert() and not is_playing:
                # 播放提示音
                is_playing = True
                print("开始播放提示音")
                sound_thread = threading.Thread(target=play_sound, args=("incorrect",))
                sound_thread.start()
                state_tracker.mark_alert_played()

        else:
            # 姿态良好
            state_tracker.set_state('good_posture')

            # 显示良好姿态提示
            frame_instance.draw_text(
                text='姿态良好',
                pos=(40, frame_height - 90),
                text_color=(0, 255, 230),
                font_scale=0.7,
                bg_color=(18, 185, 0),  # 绿色背景表示良好
            )

            detail_text = f'前倾角度: {head_forward_angle}° | 歪斜角度: {tilt_deviation:.1f}° | 肩膀差: {shoulder_level_diff:.0f}px'

            frame_instance.draw_text(
                text=detail_text,
                pos=(40, frame_height - 40),
                text_color=(255, 255, 230),
                font_scale=0.6,
                bg_color=(18, 185, 0),
            )