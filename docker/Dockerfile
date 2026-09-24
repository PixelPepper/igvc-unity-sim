FROM ros:jazzy-ros-base-noble@sha256:386d06ec6d4188f731bae5678e07b4cb64a4e4d4152090c0bd1f881dcf7706f5
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git python3-colcon-common-extensions python3-rosdep \
    python3-numpy python3-opencv ros-jazzy-nav2-bringup ros-jazzy-rviz2 \
    ros-jazzy-xacro ros-jazzy-robot-state-publisher ros-jazzy-joint-state-publisher \
    ros-jazzy-teleop-twist-keyboard ros-jazzy-rmw-fastrtps-cpp \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/igvc
COPY docker/patch_nav2_cost_critic.py /opt/nav2-patched/patch_nav2_cost_critic.py
# Jazzy CostCritic otherwise skips footprint collisions at zero-cost centers
# when the requested 0.30 m inflation radius is below the robot's size.
RUN test "$(dpkg-query -W -f='${Version}' ros-jazzy-nav2-mppi-controller | cut -d- -f1)" = 1.3.12 \
    && git clone --depth 1 --branch 1.3.12 https://github.com/ros-navigation/navigation2.git /opt/nav2-patched/upstream \
    && test "$(git -C /opt/nav2-patched/upstream rev-parse HEAD)" = 6be3614013ec586051b86c97b919b293281490fe \
    && python3 /opt/nav2-patched/patch_nav2_cost_critic.py /opt/nav2-patched/upstream \
    && apt-get update && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths /opt/nav2-patched/upstream/nav2_mppi_controller --ignore-src --rosdistro jazzy -y \
    && source /opt/ros/jazzy/setup.bash && cd /opt/nav2-patched \
    && MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 colcon build --executor sequential --base-paths upstream/nav2_mppi_controller --packages-select nav2_mppi_controller \
       --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    && colcon test --packages-select nav2_mppi_controller --ctest-args -R '^critics_tests$' --output-on-failure \
    && colcon test-result --verbose \
    && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git /opt/endpoint \
    && git -C /opt/endpoint checkout 54c1a64b6d5ef6ffa0a0431570bb74329b79b15b
COPY ros2/src /opt/igvc/ros2/src
COPY ros2/config /opt/igvc/ros2/config
# ament_python is a colcon build type, supplied by colcon above, not a rosdep key.
RUN apt-get update && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths ros2/src /opt/endpoint --ignore-src --rosdistro jazzy --skip-keys ament_python -y \
    && source /opt/ros/jazzy/setup.bash \
    && source /opt/nav2-patched/install/setup.bash \
    && xacro ros2/src/igvc_description/urdf/r3_a.urdf.xacro -o ros2/src/igvc_description/urdf/r3_a.urdf \
    && colcon build --executor sequential --base-paths ros2/src /opt/endpoint \
       --cmake-args -DCMAKE_BUILD_TYPE=Release \
    && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends python3-pil python3-matplotlib && rm -rf /var/lib/apt/lists/*
COPY tools/*.py /opt/igvc/tools/
COPY docker /opt/igvc/docker
RUN sed -i 's/\r$//' /opt/igvc/docker/*.sh && chmod +x /opt/igvc/docker/*.sh
ENV ROS_DOMAIN_ID=42 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
    RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
    FASTRTPS_DEFAULT_PROFILES_FILE=/opt/igvc/ros2/config/fastdds.xml
ENTRYPOINT ["/opt/igvc/docker/entrypoint.sh"]
CMD ["ros2", "launch", "/opt/igvc/docker/simulation.launch.py"]
