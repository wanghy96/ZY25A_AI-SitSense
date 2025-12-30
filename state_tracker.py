import time


class StateTracker:
    def __init__(self, complete_state_sequence, inactive_thresh):
        self.complete_state_sequence = complete_state_sequence
        self.inactive_thresh = inactive_thresh

        self.state_seq = []
        self.curr_state = None
        self.prev_state = None

        self.start_inactive_time = time.perf_counter()
        self.inactive_long = 0.0  # INACTIVE_TIME

        # 头部前倾计时相关变量
        self.forward_head_start_time = None  # 头部前倾开始时间
        self.forward_head_duration = 0  # 当前头部前倾持续时间（秒）
        self.alert_played = False  # 是否已经播放过提示音

        # 新增：头部前倾统计变量
        self.forward_head_count = 0  # 头部前倾总次数
        self.forward_head_durations = []  # 每次头部前倾的持续时间列表
        self.current_forward_head_recorded = False  # 当前头部前倾是否已记录
        self.forward_head_popup_shown = False  # 头部前倾弹窗是否已显示

        # 新增：歪头统计变量
        self.head_tilt_start_time = None  # 歪头开始时间
        self.head_tilt_duration = 0  # 当前歪头持续时间（秒）
        self.head_tilt_count = 0  # 歪头总次数
        self.head_tilt_durations = []  # 每次歪头的持续时间列表
        self.current_head_tilt_recorded = False  # 当前歪头是否已记录
        self.head_tilt_popup_shown = False  # 歪头弹窗是否已显示

        # 新增：脊柱侧弯统计变量
        self.spinal_curvature_start_time = None  # 脊柱侧弯开始时间
        self.spinal_curvature_duration = 0  # 当前脊柱侧弯持续时间（秒）
        self.spinal_curvature_count = 0  # 脊柱侧弯总次数
        self.spinal_curvature_durations = []  # 每次脊柱侧弯的持续时间列表
        self.current_spinal_curvature_recorded = False  # 当前脊柱侧弯是否已记录
        self.spinal_curvature_popup_shown = False  # 脊柱侧弯弹窗是否已显示

        # 记录上次显示弹窗的姿势类型
        self.last_shown_posture = None
        
        # 新增：用于防止同一帧内多次触发警报的标志
        self.alert_triggered_this_frame = False

    def set_state(self, state, bad_posture_types=None):
        # 保存之前的状态
        old_state = self.curr_state
        self.curr_state = state

        # 如果没有指定不良姿势类型，默认为空
        if bad_posture_types is None:
            bad_posture_types = []
            
        # 重置当前帧警报触发状态
        self.alert_triggered_this_frame = False

        current_time = time.perf_counter()
        
        # 处理从不良状态回到正常状态的情况
        if old_state == 'bad_posture' and state != 'bad_posture':
            # 从不良状态切换到正常状态，重置所有弹窗状态
            self.forward_head_popup_shown = False
            self.head_tilt_popup_shown = False
            self.spinal_curvature_popup_shown = False
            self.last_shown_posture = None
        
        # 检测状态变化，用于各种不良姿势计时
        if state == 'bad_posture':
            # 处理不良姿势状态
            if old_state != 'bad_posture':
                # 从良好状态切换到不良状态
                self.alert_played = False  # 重置提示音状态
                # 重置所有弹窗状态
                self.forward_head_popup_shown = False
                self.head_tilt_popup_shown = False
                self.spinal_curvature_popup_shown = False
                self.last_shown_posture = None
            else:
                # 如果不良姿势类型发生变化，重置对应的弹窗状态
                active_postures = set(bad_posture_types)
                if 'forward_head' not in active_postures and self.forward_head_popup_shown:
                    self.forward_head_popup_shown = False
                if 'head_tilt' not in active_postures and self.head_tilt_popup_shown:
                    self.head_tilt_popup_shown = False
                if 'spinal_curvature' not in active_postures and self.spinal_curvature_popup_shown:
                    self.spinal_curvature_popup_shown = False
            
            # 对于每种不良姿势类型，单独处理计时开始和重置
            # 开始头部前倾计时或重置不需要的计时
            if 'forward_head' in bad_posture_types and self.forward_head_start_time is None:
                self.forward_head_start_time = current_time
                self.current_forward_head_recorded = False
                self.forward_head_popup_shown = False  # 新开始计时时重置弹窗状态
                print(f"开始头部前倾计时: {self.forward_head_start_time}")
            elif 'forward_head' not in bad_posture_types and self.forward_head_start_time is not None:
                # 如果不再是头部前倾，停止计时
                forward_head_duration = current_time - self.forward_head_start_time
                print(f"结束头部前倾状态，持续了: {forward_head_duration:.1f}秒")
                if self.current_forward_head_recorded:
                    self.forward_head_durations.append(forward_head_duration)
                    print(f"记录头部前倾持续时间: {forward_head_duration:.1f}秒")
                self.forward_head_start_time = None
                self.forward_head_popup_shown = False  # 停止计时时重置弹窗状态

            # 开始歪头计时或重置不需要的计时
            if 'head_tilt' in bad_posture_types and self.head_tilt_start_time is None:
                self.head_tilt_start_time = current_time
                self.current_head_tilt_recorded = False
                self.head_tilt_popup_shown = False  # 新开始计时时重置弹窗状态
                print(f"开始歪头计时: {self.head_tilt_start_time}")
            elif 'head_tilt' not in bad_posture_types and self.head_tilt_start_time is not None:
                # 如果不再是歪头，停止计时
                head_tilt_duration = current_time - self.head_tilt_start_time
                print(f"结束歪头状态，持续了: {head_tilt_duration:.1f}秒")
                if self.current_head_tilt_recorded:
                    self.head_tilt_durations.append(head_tilt_duration)
                    print(f"记录歪头持续时间: {head_tilt_duration:.1f}秒")
                self.head_tilt_start_time = None
                self.head_tilt_popup_shown = False  # 停止计时时重置弹窗状态

            # 开始脊柱侧弯计时或重置不需要的计时
            if 'spinal_curvature' in bad_posture_types and self.spinal_curvature_start_time is None:
                self.spinal_curvature_start_time = current_time
                self.current_spinal_curvature_recorded = False
                self.spinal_curvature_popup_shown = False  # 新开始计时时重置弹窗状态
                print(f"开始脊柱侧弯计时: {self.spinal_curvature_start_time}")
            elif 'spinal_curvature' not in bad_posture_types and self.spinal_curvature_start_time is not None:
                # 如果不再是脊柱侧弯，停止计时
                spinal_curvature_duration = current_time - self.spinal_curvature_start_time
                print(f"结束脊柱侧弯状态，持续了: {spinal_curvature_duration:.1f}秒")
                if self.current_spinal_curvature_recorded:
                    self.spinal_curvature_durations.append(spinal_curvature_duration)
                    print(f"记录脊柱侧弯持续时间: {spinal_curvature_duration:.1f}秒")
                self.spinal_curvature_start_time = None
                self.spinal_curvature_popup_shown = False  # 停止计时时重置弹窗状态

        elif state != 'bad_posture' and old_state == 'bad_posture':
            # 结束不良姿势状态，回到良好状态
            # 结束头部前倾计时
            if self.forward_head_start_time is not None:
                forward_head_duration = current_time - self.forward_head_start_time
                print(f"结束头部前倾状态，持续了: {forward_head_duration:.1f}秒")
                if self.current_forward_head_recorded:
                    self.forward_head_durations.append(forward_head_duration)
                    print(f"记录头部前倾持续时间: {forward_head_duration:.1f}秒")
                self.forward_head_start_time = None
                self.forward_head_popup_shown = False  # 重置弹窗状态

            # 结束歪头计时
            if self.head_tilt_start_time is not None:
                head_tilt_duration = current_time - self.head_tilt_start_time
                print(f"结束歪头状态，持续了: {head_tilt_duration:.1f}秒")
                if self.current_head_tilt_recorded:
                    self.head_tilt_durations.append(head_tilt_duration)
                    print(f"记录歪头持续时间: {head_tilt_duration:.1f}秒")
                self.head_tilt_start_time = None
                self.head_tilt_popup_shown = False  # 重置弹窗状态

            # 结束脊柱侧弯计时
            if self.spinal_curvature_start_time is not None:
                spinal_curvature_duration = current_time - self.spinal_curvature_start_time
                print(f"结束脊柱侧弯状态，持续了: {spinal_curvature_duration:.1f}秒")
                if self.current_spinal_curvature_recorded:
                    self.spinal_curvature_durations.append(spinal_curvature_duration)
                    print(f"记录脊柱侧弯持续时间: {spinal_curvature_duration:.1f}秒")
                self.spinal_curvature_start_time = None
                self.spinal_curvature_popup_shown = False  # 重置弹窗状态

            # 重置计时和提醒状态
            self.alert_played = False
            self.last_shown_posture = None  # 重置上次显示弹窗的姿势类型

    def get_state(self):
        return self.curr_state

    def get_forward_head_duration(self):
        """获取当前头部前倾持续时间"""
        if self.forward_head_start_time is not None:
            current_time = time.perf_counter()
            self.forward_head_duration = current_time - self.forward_head_start_time
        return self.forward_head_duration

    def get_head_tilt_duration(self):
        """获取当前歪头持续时间"""
        if self.head_tilt_start_time is not None:
            current_time = time.perf_counter()
            self.head_tilt_duration = current_time - self.head_tilt_start_time
        return self.head_tilt_duration

    def get_spinal_curvature_duration(self):
        """获取当前脊柱侧弯持续时间"""
        if self.spinal_curvature_start_time is not None:
            current_time = time.perf_counter()
            self.spinal_curvature_duration = current_time - self.spinal_curvature_start_time
        return self.spinal_curvature_duration

    def get_bad_posture_durations(self):
        """返回各类不良姿势的当前持续时间"""
        return {
            'forward_head': self.get_forward_head_duration(),
            'head_tilt': self.get_head_tilt_duration(),
            'spinal_curvature': self.get_spinal_curvature_duration(),
        }

    def should_trigger_alert(self, threshold_seconds=10.0):
        """
        检查是否有任意不良姿势超过阈值，且对应弹窗未显示
        返回 (是否触发, 姿势类型, 持续时间)
        """
        # 如果当前帧已经触发过警报，不再重复触发
        if self.alert_triggered_this_frame:
            return False, None, 0.0
            
        if self.curr_state != 'bad_posture':
            return False, None, 0.0

        durations = self.get_bad_posture_durations()
        
        # 检查是否有不良姿势持续时间超过阈值且弹窗未显示
        if durations['forward_head'] >= threshold_seconds and not self.forward_head_popup_shown:
            # 标记该类型弹窗已显示
            self.forward_head_popup_shown = True
            self.alert_triggered_this_frame = True
            self.last_shown_posture = 'forward_head'
            return True, 'forward_head', durations['forward_head']
        elif durations['head_tilt'] >= threshold_seconds and not self.head_tilt_popup_shown:
            # 标记该类型弹窗已显示
            self.head_tilt_popup_shown = True
            self.alert_triggered_this_frame = True
            self.last_shown_posture = 'head_tilt'
            return True, 'head_tilt', durations['head_tilt']
        elif durations['spinal_curvature'] >= threshold_seconds and not self.spinal_curvature_popup_shown:
            # 标记该类型弹窗已显示
            self.spinal_curvature_popup_shown = True
            self.alert_triggered_this_frame = True
            self.last_shown_posture = 'spinal_curvature'
            return True, 'spinal_curvature', durations['spinal_curvature']
        
        return False, None, 0.0
    
    def mark_popup_shown(self, posture_type):
        """
        标记特定类型的不良姿势弹窗已显示
        """
        if posture_type == 'forward_head':
            self.forward_head_popup_shown = True
        elif posture_type == 'head_tilt':
            self.head_tilt_popup_shown = True
        elif posture_type == 'spinal_curvature':
            self.spinal_curvature_popup_shown = True
        self.last_shown_posture = posture_type

    def check_and_record_bad_postures(self):
        """检查并记录各种不良姿势次数"""
        # 检查头部前倾
        forward_head_duration = self.get_forward_head_duration()
        if (forward_head_duration > 15.0 and
                not self.current_forward_head_recorded and
                self.forward_head_start_time is not None):
            self.forward_head_count += 1
            self.current_forward_head_recorded = True
            print(f"头部前倾次数加1，当前次数: {self.forward_head_count}")

        # 检查歪头
        head_tilt_duration = self.get_head_tilt_duration()
        if (head_tilt_duration > 15.0 and
                not self.current_head_tilt_recorded and
                self.head_tilt_start_time is not None):
            self.head_tilt_count += 1
            self.current_head_tilt_recorded = True
            print(f"歪头次数加1，当前次数: {self.head_tilt_count}")

        # 检查脊柱侧弯
        spinal_curvature_duration = self.get_spinal_curvature_duration()
        if (spinal_curvature_duration > 15.0 and
                not self.current_spinal_curvature_recorded and
                self.spinal_curvature_start_time is not None):
            self.spinal_curvature_count += 1
            self.current_spinal_curvature_recorded = True
            print(f"脊柱侧弯次数加1，当前次数: {self.spinal_curvature_count}")

    def get_all_stats(self):
        """获取所有不良姿势统计信息"""
        # 计算头部前倾平均持续时间
        forward_head_avg = 0.0
        if self.forward_head_count > 0 and len(self.forward_head_durations) > 0:
            forward_head_avg = sum(self.forward_head_durations) / len(self.forward_head_durations)

        # 计算歪头平均持续时间
        head_tilt_avg = 0.0
        if self.head_tilt_count > 0 and len(self.head_tilt_durations) > 0:
            head_tilt_avg = sum(self.head_tilt_durations) / len(self.head_tilt_durations)

        # 计算脊柱侧弯平均持续时间
        spinal_curvature_avg = 0.0
        if self.spinal_curvature_count > 0 and len(self.spinal_curvature_durations) > 0:
            spinal_curvature_avg = sum(self.spinal_curvature_durations) / len(self.spinal_curvature_durations)

        return {
            'forward_head': {
                'count': self.forward_head_count,
                'avg_duration': forward_head_avg,
                'durations': self.forward_head_durations.copy()
            },
            'head_tilt': {
                'count': self.head_tilt_count,
                'avg_duration': head_tilt_avg,
                'durations': self.head_tilt_durations.copy()
            },
            'spinal_curvature': {
                'count': self.spinal_curvature_count,
                'avg_duration': spinal_curvature_avg,
                'durations': self.spinal_curvature_durations.copy()
            }
        }

    def reset_state(self):
        self.state_seq = []
        self.curr_state = None
        self.prev_state = None
        # 重置计时
        self.forward_head_start_time = None
        self.forward_head_duration = 0
        self.alert_played = False
        self.current_forward_head_recorded = False
        self.forward_head_popup_shown = False

        self.head_tilt_start_time = None
        self.head_tilt_duration = 0
        self.current_head_tilt_recorded = False
        self.head_tilt_popup_shown = False

        self.spinal_curvature_start_time = None
        self.spinal_curvature_duration = 0
        self.current_spinal_curvature_recorded = False
        self.spinal_curvature_popup_shown = False
        
        self.last_shown_posture = None

    def before_process(self):
        # 保存之前的状态用于比较
        self.prev_state = self.curr_state

    def after_process(self, frame_instance):
        display_inactivity = False

        # 检查无活动状态
        if self.curr_state is None or self.curr_state == self.prev_state:
            current_time = time.perf_counter()
            self.inactive_long += current_time - self.start_inactive_time
            self.start_inactive_time = current_time
            if self.inactive_long >= self.inactive_thresh:
                # 重置所有状态
                self.reset()
                frame_instance.put_text(
                    text='由于长时间无活动，已重置状态!!!',
                    pos=(10, frame_instance.get_frame_height() - 25),
                    font_scale=0.7,
                    color='blue',
                    thickness=2)
                display_inactivity = True
        else:
            # 有活动，重置无活动计时器
            self.__reset_inactive_tracker__()

        # 更新各种不良姿势持续时间并检查是否需要记录
        self.check_and_record_bad_postures()

        # 获取当前各种不良姿势的持续时间
        forward_head_duration = self.get_forward_head_duration()
        head_tilt_duration = self.get_head_tilt_duration()
        spinal_curvature_duration = self.get_spinal_curvature_duration()

        # 显示状态和持续时间
        if self.curr_state == 'bad_posture':
            # 构建状态文本
            status_parts = []
            if self.forward_head_start_time is not None:
                status_parts.append(f"前倾: {forward_head_duration:.1f}秒")
            if self.head_tilt_start_time is not None:
                status_parts.append(f"歪头: {head_tilt_duration:.1f}秒")
            if self.spinal_curvature_start_time is not None:
                status_parts.append(f"侧弯: {spinal_curvature_duration:.1f}秒")

            duration_text = "不良坐姿 - " + " | ".join(status_parts)
            color = (221, 0, 0)  # 红色表示警告

            # 检查是否需要播放提示音（仅针对头部前倾）
            if forward_head_duration > 15.0 and not self.alert_played:
                self.alert_played = True
                # 设置标志，在trainer_process中播放音频
                print(f"需要播放提示音，头部前倾持续时间: {forward_head_duration:.1f}秒")
        else:
            duration_text = "姿态良好"
            color = (18, 185, 0)  # 绿色表示良好

        frame_instance.draw_text(
            text=duration_text,
            pos=(int(frame_instance.get_frame_width() * 0.75), 30),
            text_color=(255, 255, 230),
            font_scale=0.7,
            bg_color=color
        )

        if display_inactivity:
            self.__reset_inactive_tracker__()

    def reset(self):
        self.state_seq = []
        self.curr_state = None
        self.prev_state = None

        self.start_inactive_time = time.perf_counter()
        self.inactive_long = 0.0  # INACTIVE_TIME

        # 重置计时和统计
        self.forward_head_start_time = None
        self.forward_head_duration = 0
        self.alert_played = False
        self.current_forward_head_recorded = False
        self.forward_head_popup_shown = False

        self.head_tilt_start_time = None
        self.head_tilt_duration = 0
        self.current_head_tilt_recorded = False
        self.head_tilt_popup_shown = False

        self.spinal_curvature_start_time = None
        self.spinal_curvature_duration = 0
        self.current_spinal_curvature_recorded = False
        self.spinal_curvature_popup_shown = False
        
        self.last_shown_posture = None
        # 注意：这里不重置计数和持续时间列表，因为用户可能想要保留整个检测会话的统计

    def reset_stats(self):
        """重置统计信息（用于开始新的检测会话）"""
        self.forward_head_count = 0
        self.forward_head_durations = []
        self.current_forward_head_recorded = False

        self.head_tilt_count = 0
        self.head_tilt_durations = []
        self.current_head_tilt_recorded = False

        self.spinal_curvature_count = 0
        self.spinal_curvature_durations = []
        self.current_spinal_curvature_recorded = False

    def __reset_inactive_tracker__(self):
        self.start_inactive_time = time.perf_counter()
        self.inactive_long = 0.0

    def should_play_alert(self):
        """检查是否需要播放提示音"""
        return (self.curr_state == 'bad_posture' and
                self.get_forward_head_duration() > 15.0 and
                not self.alert_played)

    def mark_alert_played(self):
        """标记提示音已播放"""
        self.alert_played = True

    def should_show_popup(self, threshold_seconds=10.0):
        """
        检查是否需要弹出提醒（基于任意不良姿势持续时间且弹窗未显示过）
        返回 (是否需要显示, 姿势类型, 持续时间)
        """
        return self.should_trigger_alert(threshold_seconds)