from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os

DEVICE = '/dev/video48'


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('usb_cam_launch'),
        'config',
        'camera_params.yaml'
    )

    set_exposure = ExecuteProcess(
        cmd=[
            'v4l2-ctl', '-d', DEVICE,
            '-c', 'auto_exposure=1',
            '-c', 'exposure_time_absolute=200',
            '-c', 'exposure_dynamic_framerate=0',
        ],
        output='screen',
    )

    set_white_balance = ExecuteProcess(
        cmd=[
            'v4l2-ctl', '-d', DEVICE,
            '-c', 'white_balance_automatic=0',
            '-c', 'white_balance_temperature=4500',
        ],
        output='screen',
    )

    camera_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='usb_cam',
        namespace='camera',
        parameters=[config],
        remappings=[
            ('image_raw', '/image/raw'),
        ],
        output='screen',
    )

    # white_balance 설정 후 카메라 노드 시작
    start_camera_after_v4l2 = RegisterEventHandler(
        OnProcessExit(
            target_action=set_white_balance,
            on_exit=[camera_node],
        )
    )

    # exposure 설정 완료 후 white_balance 설정 실행
    start_wb_after_exposure = RegisterEventHandler(
        OnProcessExit(
            target_action=set_exposure,
            on_exit=[set_white_balance],
        )
    )

    return LaunchDescription([
        set_exposure,
        start_wb_after_exposure,
        start_camera_after_v4l2,
    ])
