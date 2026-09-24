#!/usr/bin/env python3
"""Patch pinned Nav2 1.3.12 and add a regression to its real critics_tests target.

Usage: python3 patch_nav2_cost_critic.py /path/to/navigation2
This only prepares source; it does not build, install, or modify running ROS.
All input files and HEAD must match the pinned upstream revision exactly.
Reapplication is rejected rather than silently accepting a partial patch.
"""

import argparse
import hashlib
from pathlib import Path
import subprocess


UPSTREAM_COMMIT = "6be3614013ec586051b86c97b919b293281490fe"
MARKER = "igvc-footprint-cost-critic-v1"
HASHES = {
    "src/critics/cost_critic.cpp":
        "854399e1bce650a5efb8e7cf6e0343f31c40ff798dd401ae1b3f78814579a962",
    "test/critics_tests.cpp":
        "7b7bbf7b47d822818c571f6bcbe9b17fd8988e8cf828fcd8fd0c7d74d4d2e449",
    "CMakeLists.txt":
        "c3d55c911334584731d224ce1dea5c529262ef050980e0be9b51fb40f8ae114d",
}
OLD = """        if (pose_cost < 1.0f) {
          continue;  // In free space
        }
"""
NEW = """        // A free center proves clearance only with a valid circumscribed
        // inflation threshold, or when footprint checking is not requested.
        if (pose_cost < 1.0f &&
          (!consider_footprint_ || possible_collision_cost_ >= 1.0f))
        {
          continue;
        }
"""

# Compiled by the existing upstream critics_tests target against mppi_critics.
# This exercises CostCritic::score, not a copied implementation of its condition.
REGRESSION = r'''

// IGVC regression: limited inflation must not turn a free center into a
// footprint-clearance claim. No simulator or course data is involved.
TEST(CriticTests, IgvcFreeCenterFootprintCollision)
{
  auto node = std::make_shared<rclcpp_lifecycle::LifecycleNode>("igvc_critic_test");
  rclcpp::NodeOptions options;
  options.parameter_overrides({
    rclcpp::Parameter("plugins", std::vector<std::string>{"inflation_layer"}),
    rclcpp::Parameter("inflation_layer.plugin", "nav2_costmap_2d::InflationLayer"),
    rclcpp::Parameter("inflation_layer.inflation_radius", 0.30),
    rclcpp::Parameter("inflation_layer.cost_scaling_factor", 5.0),
    rclcpp::Parameter("footprint", "[[0.6,0.5],[-1.1,0.5],[-1.1,-0.5],[0.6,-0.5]]"),
    rclcpp::Parameter("footprint_padding", 0.0),
    rclcpp::Parameter("track_unknown_space", false),
    rclcpp::Parameter("resolution", 0.05),
    rclcpp::Parameter("width", 10),
    rclcpp::Parameter("height", 10)});
  auto costmap_ros = std::make_shared<nav2_costmap_2d::Costmap2DROS>(options);
  rclcpp_lifecycle::State lstate;
  ASSERT_EQ(costmap_ros->on_configure(lstate), nav2_util::CallbackReturn::SUCCESS);
  ASSERT_FALSE(costmap_ros->getUseRadius());
  auto inflation = nav2_costmap_2d::InflationLayer::getInflationLayer(costmap_ros);
  ASSERT_NE(inflation, nullptr);
  ASSERT_DOUBLE_EQ(inflation->getInflationRadius(), 0.30);
  ASSERT_GT(costmap_ros->getLayeredCostmap()->getCircumscribedRadius(), 1.2);
  auto * map = costmap_ros->getCostmap();
  map->resizeMap(200, 200, 0.05, 0.0, 0.0);
  map->resetMap(0, 0, 200, 200);

  // Two small obstacles intersect the rear edge at yaw 0 and yaw pi/2.
  // The origin (5,5) remains free and >0.3 m from either obstacle.
  for (unsigned int a = 77; a <= 79; ++a) {
    for (unsigned int b = 99; b <= 101; ++b) {
      map->setCost(a, b, nav2_costmap_2d::LETHAL_OBSTACLE);
      map->setCost(b, a, nav2_costmap_2d::LETHAL_OBSTACLE);
    }
  }
  ASSERT_EQ(map->getCost(100, 100), nav2_costmap_2d::FREE_SPACE);

  ParametersHandler param_handler(node);
  auto getParam = param_handler.getParamGetter("critic");
  bool consider_footprint;
  int trajectory_point_step;
  getParam(consider_footprint, "consider_footprint", true);
  getParam(trajectory_point_step, "trajectory_point_step", 1);
  CostCritic critic;
  critic.on_configure(node, "mppi", "critic", costmap_ros, &param_handler);

  models::State state;
  models::Trajectories trajectories;
  trajectories.x = {{5.0f}, {5.0f}, {8.0f}};
  trajectories.y = {{5.0f}, {5.0f}, {8.0f}};
  trajectories.yaws = {{0.0f}, {1.57079632679f}, {0.0f}};
  models::Path path;
  geometry_msgs::msg::Pose goal;
  goal.position.x = 9.0;
  xt::xtensor<float, 1> costs = xt::zeros<float>({3});
  float model_dt = 0.1;
  CriticData data = {state, trajectories, path, goal, costs, model_dt,
    false, nullptr, nullptr, std::nullopt, std::nullopt};
  critic.score(data);
  EXPECT_GT(costs(0), 1000.0f);
  EXPECT_GT(costs(1), 1000.0f);
  EXPECT_FLOAT_EQ(costs(2), 0.0f);
  EXPECT_FALSE(data.fail_flag);

  // All candidates blocked must report optimizer failure, not zero cost.
  trajectories.x(2, 0) = 5.0f;
  trajectories.y(2, 0) = 5.0f;
  costs.fill(0.0f);
  critic.score(data);
  EXPECT_TRUE(data.fail_flag);
  EXPECT_GT(costs(2), 1000.0f);

  // Removing the obstacles restores a genuinely clear trajectory batch.
  map->resetMap(0, 0, 200, 200);
  costs.fill(0.0f);
  critic.score(data);
  EXPECT_FALSE(data.fail_flag);
  EXPECT_FLOAT_EQ(xt::sum(costs, immediate)(), 0.0f);
}
'''


def patch(root: Path) -> None:
    root = root.resolve(strict=True)
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != UPSTREAM_COMMIT:
        raise ValueError(f"Expected upstream {UPSTREAM_COMMIT}, got {revision}")
    package = root / "nav2_mppi_controller"
    originals = {}
    for relative, expected in HASHES.items():
        data = (package / relative).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Upstream content mismatch: {relative}; no files changed")
        originals[relative] = data.decode("utf-8")
    if (package / MARKER).exists():
        raise ValueError("Patch marker already exists; refusing partial/repeated patch")
    source = originals["src/critics/cost_critic.cpp"]
    if source.count(OLD) != 1:
        raise ValueError("Expected exactly one zero-center shortcut; no files changed")
    outputs = {
        "src/critics/cost_critic.cpp": source.replace(OLD, NEW),
        "test/critics_tests.cpp": originals["test/critics_tests.cpp"] + REGRESSION,
        "CMakeLists.txt": originals["CMakeLists.txt"] +
            f'\n# IGVC footprint collision fix provenance.\n'
            f'install(FILES "{MARKER}" DESTINATION share/${{PROJECT_NAME}})\n',
        MARKER: f"{MARKER}\nupstream_commit={UPSTREAM_COMMIT}\n",
    }
    for relative, content in outputs.items():
        (package / relative).write_bytes(content.encode("utf-8"))
    print(f"Applied {MARKER} to Nav2 {UPSTREAM_COMMIT}; C++ build/test still required")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    try:
        patch(args.source_root)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Patch refused: {error}\n")
