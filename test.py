import cv2
import numpy as np
import yaml
import glob
import os

# 1. 캘리브레이션 결과 로드
yaml_path = os.path.expanduser("~/box_vision/calib_result/ost.yaml")
with open(yaml_path) as f:
    data = yaml.safe_load(f)

K = np.array(data['camera_matrix']['data']).reshape(3,3)
D = np.array(data['distortion_coefficients']['data'])

print(f"K =\n{K}")
print(f"D = {D}")

# 2. 캘리브레이션 때 찍은 이미지로 검증
img_paths = sorted(glob.glob(os.path.expanduser(
    "~/box_vision/calib_result/left*.png")))

if not img_paths:
    print("이미지 없음. 카메라에서 직접 캡쳐합니다...")
    cap = cv2.VideoCapture("/dev/video48")
    ret, img = cap.read()
    cap.release()
    if not ret:
        print("카메라 캡쳐 실패")
        exit()
    img_paths_data = [img]
else:
    img_paths_data = [cv2.imread(p) for p in img_paths[:3]]
    print(f"검증 이미지 {len(img_paths)}장 발견, 처음 3장으로 확인")

# 3. 각 이미지에 대해 보정 전/후 비교
for i, img in enumerate(img_paths_data):
    if img is None:
        continue
    h, w = img.shape[:2]

    # 보정된 카메라 매트릭스 (alpha=1: 모든 픽셀 유지)
    newK, roi = cv2.getOptimalNewCameraMatrix(K, D, (w,h), alpha=1)

    # 왜곡 보정
    undistorted = cv2.undistort(img, K, D, None, newK)

    # 비교 이미지 생성
    comparison = np.hstack([img, undistorted])

    # 라벨 추가
    cv2.putText(comparison, "ORIGINAL (distorted)",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)
    cv2.putText(comparison, "UNDISTORTED (corrected)",
                (w+10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    # 중앙 수평선 그리기 (왜곡 확인용)
    cy = h // 2
    cv2.line(comparison, (0, cy), (w*2, cy), (255,0,0), 1)

    cv2.imshow(f"Calibration Verification [{i+1}]", comparison)
    print(f"이미지 {i+1}: 아무 키나 누르면 다음으로...")
    cv2.waitKey(0)

cv2.destroyAllWindows()
print("검증 완료!")