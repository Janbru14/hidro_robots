import os

from ament_index_python.packages import get_package_prefix, get_package_share_directory

from launch import LaunchDescription, LaunchService
from launch.actions import (AppendEnvironmentVariable, DeclareLaunchArgument,
                             IncludeLaunchDescription)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (Command, FindExecutable, LaunchConfiguration,
                                   PathJoinSubstitution, PythonExpression)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    ld = LaunchDescription()

    # Expose the odri_ros2_gazebo plugin to Gazebo Harmonic
    ld.add_action(AppendEnvironmentVariable(
        'GZ_SIM_SYSTEM_PLUGIN_PATH',
        os.path.join(get_package_prefix('odri_ros2_gazebo'), 'lib')))

    # Expose hidro_robots meshes so model://hidro_robots/... URIs resolve
    ld.add_action(AppendEnvironmentVariable(
        'GZ_SIM_RESOURCE_PATH',
        os.path.dirname(get_package_share_directory('hidro_robots'))))

    ld.add_action(DeclareLaunchArgument(
        'robot_name',
        description='Robot model name (must match a folder under hidro_robots/robots/)',
        default_value=''))

    ld.add_action(DeclareLaunchArgument(
        'event_based_sim',
        description='Use faster physics step (1 kHz instead of 250 Hz)',
        default_value='False'))

    ld.add_action(DeclareLaunchArgument(
        'gui',
        description='Set to false to run Gazebo headless (server only)',
        default_value='true'))

    # ── World file ────────────────────────────────────────────────────────
    world_filename = PythonExpression([
        "'event_based.world' if ",
        LaunchConfiguration('event_based_sim'),
        " else 'basic_world.world'"])
    world_path = PathJoinSubstitution(
        [FindPackageShare('hidro_robots'), 'worlds', world_filename])

    # gz sim flags: -r = run immediately; -s = server only (no GUI)
    gz_server_flag = PythonExpression([
        "' -s' if ('",
        LaunchConfiguration('gui'),
        "' == 'false' or ",
        LaunchConfiguration('event_based_sim'),
        ") else ''"])

    # ── Gazebo Harmonic ───────────────────────────────────────────────────
    ld.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution(
                    [FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
            ]),
            launch_arguments={
                'gz_args': [world_path, ' -r', gz_server_flag],
            }.items()))

    # ── Robot description (xacro → URDF) ─────────────────────────────────
    robot_description_content = Command([
        PathJoinSubstitution([FindExecutable(name='xacro')]), ' ',
        PathJoinSubstitution([
            FindPackageShare('hidro_robots'), 'robots',
            LaunchConfiguration('robot_name'), 'xacro', 'description.urdf.xacro',
        ]),
        ' event_based_sim:=', LaunchConfiguration('event_based_sim'),
    ])
    robot_description = {
        'robot_description': ParameterValue(robot_description_content, value_type=str)}

    # ── Robot state publisher ─────────────────────────────────────────────
    ld.add_action(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            namespace='gazebo',
            output='screen',
            parameters=[robot_description]))

    # ── Spawn entity in Gazebo Harmonic ───────────────────────────────────
    ld.add_action(
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=[
                '-topic', 'gazebo/robot_description',
                '-name',  LaunchConfiguration('robot_name'),
                '-x', '0', '-y', '0', '-z', '0.3',
            ],
            output='screen'))

    return ld


if __name__ == '__main__':
    ls = LaunchService()
    ls.include_launch_description(generate_launch_description())
    import sys
    sys.exit(ls.run())
