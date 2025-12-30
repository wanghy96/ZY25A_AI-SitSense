import cv2
import numpy as np

from utils import find_angle, get_landmark_features, draw_text, draw_dotted_line, calculate_angle_between_two_points

COLORS = {
    'black': (0, 0, 0),
    'blue': (0, 127, 255),
    'red': (255, 50, 50),
    'green': (0, 255, 127),
    'light_green': (100, 233, 127),
    'yellow': (255, 255, 0),
    'light_yellow': (255, 255, 230),
    'magenta': (255, 0, 255),
    'white': (255, 255, 255),
    'cyan': (0, 255, 255),
    'light_blue': (102, 204, 255),
    'orange': (255, 165, 0),
    'pink': (255, 192, 203),
    'purple': (128, 0, 128),
    'lime': (0, 255, 0)
}

LINE_TYPE = cv2.LINE_AA
FONT = cv2.FONT_HERSHEY_SIMPLEX
OFFSET_THRESH = 35.0


class FrameInstance:
    def __init__(self, frame: np.array, pose, face_mesh=None):
        self.frame = frame
        self.pose = pose
        self.face_mesh = face_mesh
        self.frame_height, self.frame_width, _ = frame.shape

        self.keypoints = pose.process(frame)
        self.face_keypoints = face_mesh.process(frame) if face_mesh else None

        self.coord = {
            # 头部关键点
            'nose': None,
            'left_eye_inner': None,    # 左眼内眼角
            'left_eye': None,          # 左眼中心
            'left_eye_outer': None,    # 左眼外眼角
            'right_eye_inner': None,   # 右眼内眼角
            'right_eye': None,         # 右眼中心
            'right_eye_outer': None,   # 右眼外眼角
            'left_ear': None,
            'right_ear': None,
            'left_mouth': None,
            'right_mouth': None,
            'left_iris': None,         # 左眼虹膜中心
            'right_iris': None,        # 右眼虹膜中心
            'neck': None,

            # 上半身左侧关键点
            'left_shldr': None,
            'left_elbow': None,
            'left_wrist': None,
            'left_hip': None,

            # 上半身右侧关键点
            'right_shldr': None,
            'right_elbow': None,
            'right_wrist': None,
            'right_hip': None,

            # 下半身关键点（保留原有）
            'left_knee': None,
            'left_ankle': None,
            'left_foot': None,
            'right_knee': None,
            'right_ankle': None,
            'right_foot': None,

            # 通用关键点（根据朝向选择左右侧）
            'shldr': None,
            'elbow': None,
            'wrist': None,
            'hip': None,
            'knee': None,
            'ankle': None,
            'foot': None,

            # 新增通用头部关键点
            'eye': None,
            'ear': None,
            'mouth': None,
            'eye_inner': None,
            'eye_outer': None,
            'iris': None
        }
        self.angle = {}
        self.orientation = None

        if self.validate():
            ps_lm = self.keypoints.pose_landmarks

            # 获取头部关键点
            self.coord['nose'] = get_landmark_features(ps_lm.landmark, 'nose', self.frame_width, self.frame_height)
            self.coord['left_eye_inner'] = get_landmark_features(ps_lm.landmark, 'left_eye_inner', self.frame_width, self.frame_height)
            self.coord['left_eye'] = get_landmark_features(ps_lm.landmark, 'left_eye', self.frame_width, self.frame_height)
            self.coord['left_eye_outer'] = get_landmark_features(ps_lm.landmark, 'left_eye_outer', self.frame_width, self.frame_height)
            self.coord['right_eye_inner'] = get_landmark_features(ps_lm.landmark, 'right_eye_inner', self.frame_width, self.frame_height)
            self.coord['right_eye'] = get_landmark_features(ps_lm.landmark, 'right_eye', self.frame_width, self.frame_height)
            self.coord['right_eye_outer'] = get_landmark_features(ps_lm.landmark, 'right_eye_outer', self.frame_width, self.frame_height)
            self.coord['left_ear'] = get_landmark_features(ps_lm.landmark, 'left_ear', self.frame_width, self.frame_height)
            self.coord['right_ear'] = get_landmark_features(ps_lm.landmark, 'right_ear', self.frame_width, self.frame_height)
            self.coord['left_mouth'] = get_landmark_features(ps_lm.landmark, 'left_mouth', self.frame_width, self.frame_height)
            self.coord['right_mouth'] = get_landmark_features(ps_lm.landmark, 'right_mouth', self.frame_width, self.frame_height)

            # 获取虹膜关键点（如果Face Mesh可用）
            if self.face_keypoints and self.face_keypoints.multi_face_landmarks:
                face_lm = self.face_keypoints.multi_face_landmarks[0]
                self.coord['left_iris'] = get_landmark_features(face_lm.landmark, 'left_iris', self.frame_width, self.frame_height)
                self.coord['right_iris'] = get_landmark_features(face_lm.landmark, 'right_iris', self.frame_width, self.frame_height)

            # 计算颈部位置（肩膀中点）
            left_shldr, left_elbow, left_wrist, left_hip, left_knee, left_ankle, left_foot = get_landmark_features(
                ps_lm.landmark, 'left', self.frame_width, self.frame_height)
            right_shldr, right_elbow, right_wrist, right_hip, right_knee, right_ankle, right_foot = get_landmark_features(
                ps_lm.landmark, 'right', self.frame_width, self.frame_height)

            self.coord['left_shldr'] = left_shldr
            self.coord['left_elbow'] = left_elbow
            self.coord['left_wrist'] = left_wrist
            self.coord['left_hip'] = left_hip
            self.coord['left_knee'] = left_knee
            self.coord['left_ankle'] = left_ankle
            self.coord['left_foot'] = left_foot

            self.coord['right_shldr'] = right_shldr
            self.coord['right_elbow'] = right_elbow
            self.coord['right_wrist'] = right_wrist
            self.coord['right_hip'] = right_hip
            self.coord['right_knee'] = right_knee
            self.coord['right_ankle'] = right_ankle
            self.coord['right_foot'] = right_foot

            # 计算颈部位置
            self.coord['neck'] = ((left_shldr[0] + right_shldr[0]) // 2,
                                  (left_shldr[1] + right_shldr[1]) // 2)

            offset_angle = self.get_angle('left_shldr', 'nose', 'right_shldr')

            if offset_angle > OFFSET_THRESH:
                self.orientation = 'front'
                # 正面朝向时，选择中间或平均值
                self.coord['eye'] = ((self.coord['left_eye'][0] + self.coord['right_eye'][0]) // 2,
                                     (self.coord['left_eye'][1] + self.coord['right_eye'][1]) // 2)
                self.coord['ear'] = ((self.coord['left_ear'][0] + self.coord['right_ear'][0]) // 2,
                                     (self.coord['left_ear'][1] + self.coord['right_ear'][1]) // 2)
                self.coord['mouth'] = ((self.coord['left_mouth'][0] + self.coord['right_mouth'][0]) // 2,
                                       (self.coord['left_mouth'][1] + self.coord['right_mouth'][1]) // 2)
                self.coord['eye_inner'] = ((self.coord['left_eye_inner'][0] + self.coord['right_eye_inner'][0]) // 2,
                                           (self.coord['left_eye_inner'][1] + self.coord['right_eye_inner'][1]) // 2)
                self.coord['eye_outer'] = ((self.coord['left_eye_outer'][0] + self.coord['right_eye_outer'][0]) // 2,
                                           (self.coord['left_eye_outer'][1] + self.coord['right_eye_outer'][1]) // 2)
                if self.coord['left_iris'] is not None and self.coord['right_iris'] is not None:
                    self.coord['iris'] = ((self.coord['left_iris'][0] + self.coord['right_iris'][0]) // 2,
                                          (self.coord['left_iris'][1] + self.coord['right_iris'][1]) // 2)
            else:
                dist_l_sh_hip = abs(self.coord['left_foot'][1] - self.coord['left_shldr'][1])
                dist_r_sh_hip = abs(self.coord['right_foot'][1] - self.coord['right_shldr'][1])

                if dist_l_sh_hip > dist_r_sh_hip:
                    self.orientation = 'left'
                    self.coord['shldr'] = self.coord['left_shldr']
                    self.coord['elbow'] = self.coord['left_elbow']
                    self.coord['wrist'] = self.coord['left_wrist']
                    self.coord['hip'] = self.coord['left_hip']
                    self.coord['knee'] = self.coord['left_knee']
                    self.coord['ankle'] = self.coord['left_ankle']
                    self.coord['foot'] = self.coord['left_foot']
                    self.coord['eye'] = self.coord['left_eye']
                    self.coord['ear'] = self.coord['left_ear']
                    self.coord['mouth'] = self.coord['left_mouth']
                    self.coord['eye_inner'] = self.coord['left_eye_inner']
                    self.coord['eye_outer'] = self.coord['left_eye_outer']
                    self.coord['iris'] = self.coord['left_iris']
                else:
                    self.orientation = 'right'
                    self.coord['shldr'] = self.coord['right_shldr']
                    self.coord['elbow'] = self.coord['right_elbow']
                    self.coord['wrist'] = self.coord['right_wrist']
                    self.coord['hip'] = self.coord['right_hip']
                    self.coord['knee'] = self.coord['right_knee']
                    self.coord['ankle'] = self.coord['right_ankle']
                    self.coord['foot'] = self.coord['right_foot']
                    self.coord['eye'] = self.coord['right_eye']
                    self.coord['ear'] = self.coord['right_ear']
                    self.coord['mouth'] = self.coord['right_mouth']
                    self.coord['eye_inner'] = self.coord['right_eye_inner']
                    self.coord['eye_outer'] = self.coord['right_eye_outer']
                    self.coord['iris'] = self.coord['right_iris']

    def validate(self):
        if self.keypoints.pose_landmarks:
            return True
        else:
            return False

    def get_frame(self):
        return self.frame

    def get_frame_width(self):
        return self.frame_width

    def get_frame_height(self):
        return self.frame_height

    def get_coord(self, feature):
        if self.validate() and feature in self.coord:
            return self.coord[feature]
        else:
            return np.array([0, 0])

    def get_orientation(self):
        return self.orientation

    def get_angle(self, point1, point2, point3):
        angle, coord1, coord2, coord3 = self.__get_angle__(point1, point2, point3)
        return int(angle)

    def get_angle_and_draw(self, point1, point2, point3, text_color='light_green', line_color='light_blue',
                           point_color='yellow', ellipse_color='white', dotted_line_color='blue'):
        angle, coord1, coord2, coord3 = self.__get_angle__(point1, point2, point3)

        # 以point2为原点，转换坐标系
        converted_cood1 = self.__convert_coord__(coord1, coord2)
        converted_cood2 = self.__convert_coord__(coord2, coord2)
        converted_cood3 = self.__convert_coord__(coord3, coord2)
        # cv2的角度是按顺时针方向计算，因此，常规角度要变号
        start_angle = 0 - calculate_angle_between_two_points(converted_cood2, converted_cood3)
        end_angle = 0 - calculate_angle_between_two_points(converted_cood2, converted_cood1)
        if abs(end_angle - start_angle) > 180:
            if end_angle > 0:
                end_angle = end_angle - 360
            else:
                end_angle = 360 + end_angle
        cv2.ellipse(self.frame, coord2, (20, 20),
                    angle=0, startAngle=start_angle, endAngle=end_angle,
                    color=self.__get_color__(ellipse_color), thickness=3, lineType=LINE_TYPE)

        # draw lines between points
        self.line(point1, point2, line_color, 4)
        if point3 == 'vertical' or point3 == 'horizontal' or point3 == 'nvertical' or point3 == 'nhorizontal':
            # draw vertical or horizontal line
            draw_dotted_line(self.frame, coord2, start=coord2[1] - 50, end=coord2[1] + 20,
                             line_color=self.__get_color__(dotted_line_color))
        else:
            self.line(point2, point3, line_color, 4)

        # draw point cicle
        self.circle(point1, radius=7, color=point_color)
        self.circle(point2, radius=7, color=point_color)
        if point3 in self.coord:
            self.circle(point3, radius=7, color=point_color)

        # show angle value
        cv2.putText(self.frame, str(int(angle)), (coord2[0] + 15, coord2[1]), FONT, 0.6,
                    self.__get_color__(text_color), 2, lineType=LINE_TYPE)

        return int(angle)

    def circle(self, *args, radius=7, color='yellow'):
        for arg in args:
            if arg in self.coord and self.coord[arg] is not None:
                cv2.circle(self.frame, self.coord[arg], radius, self.__get_color__(color), -1)

    def line(self, pt1, pt2, color='light_blue', thickness=4):
        if pt1 in self.coord and pt2 in self.coord and self.coord[pt1] is not None and self.coord[pt2] is not None:
            cv2.line(self.frame, self.coord[pt1], self.coord[pt2], self.__get_color__(color), thickness, LINE_TYPE)

    def draw_text(self, text, width=8, font=FONT, pos=(0, 0), font_scale=1.0, font_thickness=2, text_color=(0, 255, 0)
                  , bg_color=(0, 0, 0)):
        self.frame = draw_text(self.frame, text, width, font, pos, font_scale, font_thickness, text_color, bg_color)

    def put_text(self, text, pos, font_scale, color, thickness, line_type=LINE_TYPE):
        cv2.putText(self.frame, text=text, org=pos, fontFace=FONT, fontScale=font_scale,
                    color=self.__get_color__(color), thickness=thickness, lineType=line_type)

    def show_feedback(self, text, y, text_color, bg_color):
        self.draw_text(
            text,
            pos=(30, y),
            text_color=self.__get_color__(text_color),
            font_scale=0.6,
            bg_color=self.__get_color__(bg_color)
        )

        return self.frame

    def __get_angle__(self, point1, point2, point3):
        key = point1 + '#' + point2 + '#' + point3
        if key not in self.angle:
            coord1 = self.get_coord(point1)
            coord2 = self.get_coord(point2)
            coord3 = None
            if point3 in self.coord:
                coord3 = self.get_coord(point3)
            else:
                if point3 == 'vertical':
                    coord3 = self.__get_vertical_coord__(point2)
                if point3 == 'horizontal':
                    coord3 = self.__get_horizontal_coord__(point2)
                if point3 == 'nvertical':
                    coord3 = self.__get_nvertical_coord__(point2)
                if point3 == 'nhorizontal':
                    coord3 = self.__get_nhorizontal_coord__(point2)

            if coord3 is None:
                return 0, np.array([0, 0]), np.array([0, 0]), np.array([0, 0])

            angle = find_angle(coord1, coord3, coord2)
            self.angle[key] = {
                'angle': angle,
                'coord1': coord1,
                'coord2': coord2,
                'coord3': coord3,
            }

        return self.angle[key]['angle'], self.angle[key]['coord1'], self.angle[key]['coord2'], self.angle[key]['coord3']

    def __get_color__(self, color):
        if isinstance(color, str):
            return COLORS[color]
        else:
            return color

    def __get_vertical_coord__(self, feature):
        return np.array([self.get_coord(feature)[0], 0])

    def __get_horizontal_coord__(self, feature):
        return np.array([0, self.get_coord(feature)[1]])

    def __get_nvertical_coord__(self, feature):
        return np.array([self.get_coord(feature)[0], self.frame_height])

    def __get_nhorizontal_coord__(self, feature):
        return np.array([self.frame_width, self.get_coord(feature)[1]])

    def __convert_coord__(self, coord, origin_coord):
        return np.array([coord[0] - origin_coord[0], 0 - (coord[1] - origin_coord[1])])