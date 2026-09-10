#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>
#include <vector>
#include "nav2_costmap_2d/layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav2_costmap_2d/cost_values.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "sensor_msgs/point_cloud2_iterator.hpp"

namespace igvc_lane_layer {
class LaneLayer : public nav2_costmap_2d::Layer {
  struct Point {double x,y;};
  using Steady=std::chrono::steady_clock;
  std::mutex mutex_;
  std::vector<Point> pending_, active_;
  Steady::time_point received_{};
  double old_min_x_=0,old_min_y_=0,old_max_x_=0,old_max_y_=0;
  bool have_old_=false;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr subscription_;
public:
  void onInitialize() override {
    auto node=node_.lock();
    if(!node)throw std::runtime_error("Lane layer node unavailable");
    enabled_=true;current_=false;
    declareParameter("topic", rclcpp::ParameterValue(std::string("/perception/lanes/points")));
    std::string topic;node->get_parameter(name_+".topic",topic);
    subscription_=node->create_subscription<sensor_msgs::msg::PointCloud2>(topic,rclcpp::SensorDataQoS().keep_last(1),
      [this](sensor_msgs::msg::PointCloud2::ConstSharedPtr msg){
        std::vector<Point> next;
        if(msg->header.frame_id!=layered_costmap_->getGlobalFrameID())return;
        try {
          sensor_msgs::PointCloud2ConstIterator<float> x(*msg,"x"),y(*msg,"y");
          for(;x!=x.end() && next.size()<8000;++x,++y)if(std::isfinite(*x)&&std::isfinite(*y))next.push_back({*x,*y});
        }catch(const std::runtime_error&){return;}
        std::lock_guard<std::mutex> lock(mutex_);pending_=std::move(next);received_=Steady::now();
      });
  }
  void updateBounds(double,double,double,double* min_x,double* min_y,double* max_x,double* max_y) override {
    std::lock_guard<std::mutex> lock(mutex_);
    current_=std::chrono::duration<double>(Steady::now()-received_).count()<.75;
    active_=current_?pending_:std::vector<Point>{};
    // Revisit prior bounds too: master resets this region, so expired marks disappear.
    if(have_old_){*min_x=std::min(*min_x,old_min_x_);*min_y=std::min(*min_y,old_min_y_);
      *max_x=std::max(*max_x,old_max_x_);*max_y=std::max(*max_y,old_max_y_);}
    have_old_=!active_.empty();
    if(!have_old_)return;
    old_min_x_=old_max_x_=active_[0].x;old_min_y_=old_max_y_=active_[0].y;
    for(auto p:active_){old_min_x_=std::min(old_min_x_,p.x);old_min_y_=std::min(old_min_y_,p.y);
      old_max_x_=std::max(old_max_x_,p.x);old_max_y_=std::max(old_max_y_,p.y);}
    const double pad=layered_costmap_->getCostmap()->getResolution();
    old_min_x_-=pad;old_min_y_-=pad;old_max_x_+=pad;old_max_y_+=pad;
    *min_x=std::min(*min_x,old_min_x_);*min_y=std::min(*min_y,old_min_y_);
    *max_x=std::max(*max_x,old_max_x_);*max_y=std::max(*max_y,old_max_y_);
  }
  void updateCosts(nav2_costmap_2d::Costmap2D& master,int min_i,int min_j,int max_i,int max_j) override {
    for(auto p:active_){unsigned int x,y;if(master.worldToMap(p.x,p.y,x,y) && int(x)>=min_i && int(x)<max_i && int(y)>=min_j && int(y)<max_j)
      master.setCost(x,y,nav2_costmap_2d::LETHAL_OBSTACLE);}
  }
  void reset() override {std::lock_guard<std::mutex> lock(mutex_);pending_.clear();received_={};current_=false;}
  bool isClearable() override {return true;}
};
}
PLUGINLIB_EXPORT_CLASS(igvc_lane_layer::LaneLayer,nav2_costmap_2d::Layer)
