import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node

def generate_launch_description():
    pkg_name = 'pkg_name'
    perception_node = Node(
        package=pkg_name,
        executable='perception_node',
        name='perception_node',
        output='screen',
        arguments=[/camera/image_raw:=/camera/image_raw],
    )

    # --- 4. RViz ---
    navigation_node = Node(
        package='rviz2',
        executable='navigation_node',
        name='navigation_node',
        arguments=[/scan:=/scan],
        output='screen'
    )

    return LaunchDescription([
        perception_node,
        navigation_node
    ])