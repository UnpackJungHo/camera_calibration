import cv2
import numpy as np
import yaml
import os
import threading

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

# 캘리브레이션 결과 로드
yaml_path = os.path.expanduser("~/box_vision/calib_result/ost.yaml")
with open(yaml_path) as f:
    data = yaml.safe_load(f)

K = np.array(data['camera_matrix']['data']).reshape(3, 3)
D = np.array(data['distortion_coefficients']['data'])

BOARD_SIZE = (8, 6)
SQUARE_SIZE = 0.025

objp = np.zeros((BOARD_SIZE[0] * BOARD_SIZE[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:BOARD_SIZE[0], 0:BOARD_SIZE[1]].T.reshape(-1, 2)
objp *= SQUARE_SIZE

criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)


class FrameGrabber(Node):
    def __init__(self):
        super().__init__('test2_frame_grabber')
        self.bridge = CvBridge()
        self.latest_frame = None
        self.lock = threading.Lock()
        self.sub = self.create_subscription(
            Image, '/image/raw', self._cb, 1)

    def _cb(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        with self.lock:
            self.latest_frame = frame

    def get_frame(self):
        with self.lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None


def main():
    rclpy.init()
    node = FrameGrabber()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    print("usb_cam 노드에서 프레임 수신 대기 중...")
    while node.get_frame() is None:
        cv2.waitKey(100)
    print("체커보드를 카메라 앞에 들고 SPACE로 캡쳐, Q로 종료하세요.")

    errors = []
    while len(errors) < 5:
        img = node.get_frame()
        if img is None:
            continue

        cv2.imshow("Press SPACE to capture, Q to quit", img)
        key = cv2.waitKey(30) & 0xFF

        if key == ord('q'):
            break
        if key != ord(' '):
            continue

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(gray, BOARD_SIZE, None)

        if not found:
            print("  체커보드 미검출. 다시 시도...")
            continue

        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)

        ok, rvec, tvec = cv2.solvePnP(objp, corners_refined, K, D)
        if not ok:
            continue

        projected, _ = cv2.projectPoints(objp, rvec, tvec, K, D)
        error = np.mean(np.linalg.norm(
            projected.reshape(-1, 2) - corners_refined.reshape(-1, 2), axis=1))
        errors.append(error)

        img_vis = img.copy()
        cv2.drawChessboardCorners(img_vis, BOARD_SIZE, corners_refined, True)
        for orig, proj in zip(corners_refined.reshape(-1, 2), projected.reshape(-1, 2)):
            cv2.line(img_vis, tuple(orig.astype(int)), tuple(proj.astype(int)), (0, 0, 255), 1)
        cv2.putText(img_vis, f"Reprojection Error: {error:.4f} px",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.imshow("Verification Result", img_vis)
        print(f"  이미지 {len(errors)}: error = {error:.4f} pixel")
        cv2.waitKey(2000)

    node.destroy_node()
    rclpy.shutdown()
    cv2.destroyAllWindows()

    if errors:
        mean_err = np.mean(errors)
        print(f"\n{'='*40}")
        print(f"평균 Reprojection Error: {mean_err:.4f} pixel")
        if mean_err < 0.3:
            print("판정: 우수 — 그대로 사용하세요")
        elif mean_err < 0.5:
            print("판정: 양호 — 사용 가능합니다")
        elif mean_err < 1.0:
            print("판정: 보통 — 가능하면 재캘리브레이션 권장")
        else:
            print("판정: 불량 — 재캘리브레이션 필요")
        print(f"{'='*40}")


if __name__ == '__main__':
    main()
