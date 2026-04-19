# box_vision

ROS2 Jazzy 기반 USB 카메라 드라이버 및 캘리브레이션 워크스페이스.  
`/image/raw` 토픽 발행, 카메라 파라미터 고정, 캘리브레이션 결과 검증까지 포함합니다.

---

## 환경

- OS: Ubuntu 24.04
- ROS2: Jazzy
- 카메라: Logitech C270 HD Webcam (`/dev/video48`)

---

## 1. 사전 패키지 설치

```bash
sudo apt install -y \
    ros-jazzy-camera-calibration \
    ros-jazzy-camera-calibration-parsers \
    ros-jazzy-cv-bridge \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-usb-cam \
    ros-jazzy-image-proc \
    ros-jazzy-rqt-image-view \
    v4l-utils \
    python3-semver
```

---

## 2. 카메라 장치 확인

```bash
v4l2-ctl --list-devices
```

USB 카메라가 잡히는 디바이스 번호를 확인합니다.  
필요 시 `src/usb_cam_launch/config/camera_params.yaml`과 `launch/usb_cam.launch.py`의 `DEVICE`, `video_device` 값을 수정하세요.

---

## 3. 워크스페이스 빌드

```bash
source /opt/ros/jazzy/setup.bash
cd ~/box_vision
colcon build
source install/setup.bash
```

---

## 4. 카메라 노드 실행

```bash
ros2 launch usb_cam_launch usb_cam.launch.py
```

정상 실행 시 아래 로그가 출력됩니다.

```
[INFO] camera calibration URL: file:///home/<user>/.ros/camera_info/camera.yaml
[INFO] Starting 'camera' (/dev/video48) at 640x480 via mmap (yuyv) at 30 FPS
[INFO] Setting 'brightness' to 128
[INFO] Setting 'contrast' to 32
...
```

### 카메라 파라미터 설정값

launch 실행 시 아래 v4l2 설정이 자동으로 적용됩니다.

| 항목 | 값 | 설명 |
|---|---|---|
| `auto_exposure` | 1 (Manual) | 자동 노출 끄기 |
| `exposure_time_absolute` | 200 | 노출 시간 고정 |
| `exposure_dynamic_framerate` | 0 | 노출에 따른 fps 변동 방지 |
| `white_balance_automatic` | 0 | 자동 화이트밸런스 끄기 |
| `white_balance_temperature` | 4500 | 색온도 고정 (형광등 기준) |
| `gain` | 8 | 센서 게인 |
| `brightness` | 128 | 밝기 |
| `contrast` | 32 | 대비 |
| `saturation` | 32 | 채도 |
| `sharpness` | 24 | 선명도 |

설정 적용 확인:

```bash
v4l2-ctl -d /dev/video48 --list-ctrls | grep -E "auto_exposure|exposure_time|white_balance|gain|brightness|contrast|saturation|sharpness"
```

정상 적용 예시:

```
white_balance_automatic     : value=0       ← 0으로 변경됨
white_balance_temperature   : value=4500    ← inactive 없어야 함
auto_exposure               : value=1       ← Manual Mode
exposure_time_absolute      : value=200     ← inactive 없어야 함
exposure_dynamic_framerate  : value=0
```

---

## 5. 토픽 확인

```bash
ros2 topic list
```

발행되는 주요 토픽:

```
/image/raw                          ← 메인 이미지 토픽
/camera/camera_info
/camera/image_raw/compressed
```

이미지 시각화:

```bash
ros2 run rqt_image_view rqt_image_view
```

`/image/raw` 토픽을 선택하면 카메라 영상을 확인할 수 있습니다.

---

## 6. 카메라 캘리브레이션

### 캘리브레이션 실행

카메라 노드가 실행 중인 상태에서 다른 터미널에서 실행합니다.  
체커보드: **8×6 내부 코너, 격자 크기 25mm**

```bash
source /opt/ros/jazzy/setup.bash
ros2 run camera_calibration cameracalibrator --size 8x6 --square 0.025 --no-service-check --ros-args --remap image:=/image/raw --remap camera_info:=/camera/camera_info
```

GUI에서 X, Y, Size, Skew 4개 바가 모두 초록색이 되면 **CALIBRATE** → **SAVE** 버튼을 클릭합니다.

### 캘리브레이션 결과 저장

SAVE 클릭 시 `/tmp/calibrationdata.tar.gz`로 저장됩니다.  
압축 해제 후 `ost.yaml`을 프로젝트로 복사합니다.

```bash
cd /tmp && tar xzf calibrationdata.tar.gz
cp /tmp/ost.yaml ~/box_vision/calib_result/ost.yaml
```

usb_cam 노드가 읽는 경로로 복사합니다.

```bash
mkdir -p ~/.ros/camera_info
cp ~/box_vision/calib_result/ost.yaml ~/.ros/camera_info/camera.yaml
```

`camera.yaml` 내 `camera_name` 항목이 `camera`인지 확인합니다.

```bash
grep camera_name ~/.ros/camera_info/camera.yaml
# → camera_name: camera
```

---

## 7. 캘리브레이션 검증

### test.py — 캘리브레이션 이미지로 왜곡 보정 확인

```bash
python3 test.py
```

캘리브레이션 때 수집한 이미지 중 3장에 대해 원본 vs 왜곡 보정 결과를 나란히 표시합니다.

### test2.py — 실시간 Reprojection Error 측정

카메라 노드가 실행 중인 상태에서 `/image/raw` 토픽을 구독하여 실시간으로 체커보드를 검출하고 reprojection error를 측정합니다.

```bash
source /opt/ros/jazzy/setup.bash
python3 test2.py
```

- `SPACE`: 현재 프레임 캡쳐 → 체커보드 검출 → error 계산
- `Q`: 종료
- 5장 캡쳐 후 평균 error 판정 출력

| Reprojection Error | 판정 |
|---|---|
| < 0.3 px | 우수 |
| 0.3 ~ 0.5 px | 양호 |
| 0.5 ~ 1.0 px | 보통 — 재캘리브레이션 권장 |
| > 1.0 px | 불량 — 재캘리브레이션 필요 |

---

## 프로젝트 구조

```
box_vision/
├── src/
│   └── usb_cam_launch/
│       ├── config/
│       │   └── camera_params.yaml   # 카메라 파라미터 (해상도, 포맷, 이미지 품질)
│       ├── launch/
│       │   └── usb_cam.launch.py    # v4l2 설정 → usb_cam 노드 순차 실행
│       ├── CMakeLists.txt
│       └── package.xml
├── calib_result/
│   └── ost.yaml                     # 캘리브레이션 결과 (K, D 행렬)
├── test.py                          # 왜곡 보정 시각화
└── test2.py                         # 실시간 reprojection error 측정
```
