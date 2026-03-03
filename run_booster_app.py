from booster_ros2_app import create_booster_app

from flask_cors import CORS
import rclpy
import threading

rclpy.init(args=None)
app = create_booster_app()
CORS(app)


@app.route("/health", methods=["GET"])
def health_check():
    return {"status": "ok"}

def run_flask():
    app.run(debug=False, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True # Allow Flask thread to exit when main thread exits
    flask_thread.start()

    try:
        rclpy.spin(app.config["ros2_node"]) # Spin the ROS 2 node
    except KeyboardInterrupt:
        pass
    finally:
        app.config["ros2_node"].destroy_node()
        rclpy.shutdown()