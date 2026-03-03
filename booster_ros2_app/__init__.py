from flask import Flask
import yaml
import time

def create_booster_app():
    app = Flask(__name__)

    # Create Objects
    from booster_ros2_app.core.ros2_node import ROS2Node

    # ROS2 Node
    ros2_node = ROS2Node()
    
    app.config["ros2_node"] = ros2_node

    from booster_ros2_app.routes.dance import dance_bp

    app.register_blueprint(dance_bp, url_prefix="/dance")

    return app