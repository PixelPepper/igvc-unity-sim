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
RUN git clone https://github.com/Unity-Technologies/ROS-TCP-Endpoint.git /opt/endpoint \
    && git -C /opt/endpoint checkout 54c1a64b6d5ef6ffa0a0431570bb74329b79b15b
COPY ros2/src /opt/igvc/ros2/src
COPY ros2/config /opt/igvc/ros2/config
# ament_python is a colcon build type, supplied by colcon above, not a rosdep key.
RUN apt-get update && rosdep update --rosdistro jazzy \
    && rosdep install --from-paths ros2/src /opt/endpoint --ignore-src --rosdistro jazzy --skip-keys ament_python -y \
    && source /opt/ros/jazzy/setup.bash \
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
