import os

from ament_index_python.packages import (get_package_prefix, get_package_share_directory)
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription)
from launch.conditions import IfCondition
from launch.substitutions import (Command, PathJoinSubstitution, LaunchConfiguration)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import SetParameter, Node

import xacro

def generate_launch_description():

    package_description = "barista_robot_description"
    xacro_file = "barista_robot_model.urdf.xacro"

    # Get Package Directories
    pkg_robot_description = get_package_share_directory(package_description)
    gz_sim_pkg = get_package_share_directory("ros_gz_sim")
    robot_desc_path = os.path.join(pkg_robot_description, "xacro", xacro_file)

    # Set the Path to Robot Mesh Models for Loading in Gazebo Sim
    install_dir_path_description = (get_package_prefix('barista_robot_description') + "/share")
    description_meshes_path = os.path.join(pkg_robot_description, "meshes")
    gazebo_resource_paths = [install_dir_path_description, description_meshes_path]
    
    if "GZ_SIM_RESOURCE_PATH" in os.environ:
        for resource_path in gazebo_resource_paths:
            if resource_path not in os.environ["GZ_SIM_RESOURCE_PATH"]:
                os.environ["GZ_SIM_RESOURCE_PATH"] += (':' + resource_path)
    else:
        os.environ["GZ_SIM_RESOURCE_PATH"] = (':'.join(gazebo_resource_paths))

    # -------------- Declare Launch Arguments --------------
    declare_include_laser = DeclareLaunchArgument(
        "include_laser",
        default_value="true",
        description="Optionally load the LiDAR scanner (true/false)",
    )

    # Spawn Arguments & Entity
    declare_spawn_model_name = DeclareLaunchArgument("model_name", default_value="barista_robot",
                                                     description="Model Spawn Name")
    declare_spawn_x = DeclareLaunchArgument("x", default_value="0.0",
                                            description="Model Spawn X Axis Value")
    declare_spawn_y = DeclareLaunchArgument("y", default_value="0.0",
                                            description="Model Spawn Y Axis Value")
    declare_spawn_z = DeclareLaunchArgument("z", default_value="0.2",
                                            description="Model Spawn Z Axis Value")
    declare_spawn_yaw = DeclareLaunchArgument("yaw", default_value="0.0",
                                            description="Model Spawn Yaw Value")

    # Robot State Publisher Node
    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher_node",
        emulate_tty=True,
        parameters=[
            {
                "robot_description": Command(
                    [
                        "xacro ",
                        robot_desc_path,
                        " robot_color:=blue"
                        " include_laser:=",
                        LaunchConfiguration("include_laser"),
                    ]
                )
            }
        ],
        output="screen",
    )

    # RVIZ Configuration Node
    rviz_config_dir = os.path.join(pkg_robot_description, 'rviz', 'barista_robot_rviz.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        name='rviz_node',
        parameters=[{'use_sim_time': True}],
        arguments=['-d', rviz_config_dir]
    )

    # Start Gazebo Sim World
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gz_sim_pkg, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": [
                "-r ",
                PathJoinSubstitution([pkg_robot_description, "worlds", "empty.world"]),
            ]
        }.items(),
    )

    gz_spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        name="barista_robot_spawn",
        arguments=[
            "-name", LaunchConfiguration("model_name"),
            "-allow_renaming", "true",
            "-topic", "robot_description",
            "-x", LaunchConfiguration("x"),
            "-y", LaunchConfiguration("y"),
            "-z", LaunchConfiguration("z"),
            "-Y", LaunchConfiguration("yaw"),
        ],
        output="screen",
    )

    # ROS-Gazebo Parameter Bridge
    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist",
            "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            # "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan"
        ],
        output="screen",
    )

    # Only publish /scan if include_laser=true
    gz_laser_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_laser_bridge",
        arguments=[
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        ],
        condition=IfCondition(LaunchConfiguration("include_laser")),
        output="screen",
    )

    return LaunchDescription(
        [
            SetParameter(name="use_sim_time", value=True),
            declare_include_laser,
            declare_spawn_model_name,
            declare_spawn_x,
            declare_spawn_y,
            declare_spawn_z,
            declare_spawn_yaw,
            robot_state_publisher_node,
            rviz_node,
            gz_sim,
            gz_spawn_entity,
            gz_bridge,
            gz_laser_bridge
        ]
    )