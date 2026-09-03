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

   # Define the robot model files to be used
    robot_name_1 = "rick"
    robot_name_2 = "morty"
    
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

    # Load Robot State Publisher 1
    rsp_robot1 = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher_node",
        namespace=robot_name_1,
        emulate_tty=True,
        parameters=[
            {
                'frame_prefix': robot_name_1 + '/',
                "robot_description": Command(
                    [
                        "xacro ",
                        robot_desc_path,
                        " robot_name:=",
                        robot_name_1,
                        " include_laser:=",
                        LaunchConfiguration("include_laser"),
                    ]
                )
            }
        ],
        output="screen",
    )

    # Static Transform Publishers to connect TF trees
    static_tf_robot1 = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="world_to_robot1_odom",
        arguments=[
            "--x", "0.0",
            "--y", "-0.5",
            "--z", "0.0",
            "--yaw", "3.14",
            "--pitch", "0.0",
            "--roll", "0.0",
            "--frame-id", "world",
            "--child-frame-id", robot_name_1 + "/odom",
        ],
        output="screen",
    )

    # Load Robot State Publisher 2
    rsp_robot2 = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher_node",
        namespace=robot_name_2,
        emulate_tty=True,
        parameters=[
            {
                'frame_prefix': robot_name_2 + '/',
                "robot_description": Command(
                    [
                        "xacro ",
                        robot_desc_path,
                        " robot_name:=",
                        robot_name_2,
                        " include_laser:=",
                        LaunchConfiguration("include_laser"),
                    ]
                )
            }
        ],
        output="screen",
    )

    static_tf_robot2 = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="world_to_robot2_odom",
        arguments=[
            "--x", "0.0",
            "--y", "0.5",
            "--z", "0.0",
            "--yaw", "3.14",
            "--pitch", "0.0",
            "--roll", "0.0",
            "--frame-id", "world",
            "--child-frame-id", robot_name_2 + "/odom",
        ],
        output="screen",
    )

    # RVIZ Configuration Node
    rviz_config_dir = os.path.join(pkg_robot_description, 'rviz', 'robot_chase_rviz_config.rviz')
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

    # Spawn Robot 1
    spawn_robot1 = Node(
        package="ros_gz_sim",
        executable="create",
        name="barista_robot1_spawn",
        arguments=[
            "-name", robot_name_1,
            "-allow_renaming", "true",
            "-topic", robot_name_1 + "/robot_description",
            "-x", "0.0",
            "-y", "-0.5",
            "-z", "0.2",
            "-Y", "3.14",
        ],
        output="screen",
    )

    # Spawn Robot 2
    spawn_robot2 = Node(
        package="ros_gz_sim",
        executable="create",
        name="barista_robot2_spawn",
        arguments=[
            "-name", robot_name_2,
            "-allow_renaming", "true",
            "-topic", robot_name_2 + "/robot_description",
            "-x", "0.0",
            "-y", "0.5",
            "-z", "0.2",
            "-Y", "3.14",
        ],
        output="screen",
    )

    # ROS-Gazebo Parameter Bridge
    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_bridge",
        arguments=[
            "/clock" + "@rosgraph_msgs/msg/Clock" + "[gz.msgs.Clock",
            "/tf" + "@tf2_msgs/msg/TFMessage" + "[gz.msgs.Pose_V",
            "/" + robot_name_1 + "/cmd_vel" + "@geometry_msgs/msg/Twist" + "@gz.msgs.Twist",
            "/" + robot_name_2 + "/cmd_vel" + "@geometry_msgs/msg/Twist" + "@gz.msgs.Twist",
            "/" + robot_name_1 + "/odom" + "@nav_msgs/msg/Odometry" + "[gz.msgs.Odometry",
            "/" + robot_name_2 + "/odom" + "@nav_msgs/msg/Odometry" + "[gz.msgs.Odometry",
            "/" + robot_name_1 + "/joint_states" + "@sensor_msgs/msg/JointState" + "[gz.msgs.Model",
            "/" + robot_name_2 + "/joint_states" + "@sensor_msgs/msg/JointState" + "[gz.msgs.Model",
        ],
        output="screen",
    )

    # Only publish /scan if include_laser=true
    gz_laser_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_laser_bridge",
        arguments=[
            "/" + robot_name_1 + "/scan" + "@sensor_msgs/msg/LaserScan" + "[gz.msgs.LaserScan",
            "/" + robot_name_2 + "/scan" + "@sensor_msgs/msg/LaserScan" + "[gz.msgs.LaserScan",
        ],
        condition=IfCondition(LaunchConfiguration("include_laser")),
        output="screen",
    )

    return LaunchDescription(
        [
            SetParameter(name="use_sim_time", value=True),
            declare_include_laser,
            rsp_robot1,
            static_tf_robot1,
            rsp_robot2,
            static_tf_robot2,
            rviz_node,
            gz_sim,
            spawn_robot1,
            spawn_robot2,
            gz_bridge,
            gz_laser_bridge
        ]
    )