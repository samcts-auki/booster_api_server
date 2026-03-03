import numpy as np
import json
import threading

import rclpy
from rclpy.node import Node
from rclpy.duration import Duration
from rclpy.action import ActionClient
from tf2_ros import TransformBroadcaster, Buffer, TransformListener

from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav2_msgs.action import NavigateToPose # Import the specific action
from action_msgs.msg import GoalStatus

# Booster
from booster_interface.srv import RpcService
from booster_interface.msg import BoosterApiReqMsg

def transform_to_matrix(transform: TransformStamped) -> np.ndarray:
    """
    Convert a TransformStamped or Transform message to a 4x4 homogeneous matrix.
    
    Args:
        transform: geometry_msgs.msg.TransformStamped or Transform

    Returns:
        4x4 numpy array representing the transform
    """
    # Extract translation
    x = transform.transform.translation.x
    y = transform.transform.translation.y
    z = transform.transform.translation.z

    # Extract quaternion
    qx = transform.transform.rotation.x
    qy = transform.transform.rotation.y
    qz = transform.transform.rotation.z
    qw = transform.transform.rotation.w

    # Compute rotation matrix from quaternion
    R = np.array([
        [1 - 2*qy**2 - 2*qz**2,     2*qx*qy - 2*qz*qw,       2*qx*qz + 2*qy*qw],
        [2*qx*qy + 2*qz*qw,         1 - 2*qx**2 - 2*qz**2,   2*qy*qz - 2*qx*qw],
        [2*qx*qz - 2*qy*qw,         2*qy*qz + 2*qx*qw,       1 - 2*qx**2 - 2*qy**2]
    ])

    # Construct homogeneous matrix
    T = np.eye(4)
    T[0:3, 0:3] = R
    T[0:3, 3] = [x, y, z]

    return T


class ROS2Node(Node):
    def __init__(self):
        super().__init__('ros2_g1_control_server_node')
        self._status = "idle"

        # Action Client for NavigateToPose
        self._action_client = ActionClient(
            self,
            NavigateToPose,
            '/navigate_to_pose' # The action server name
        )

        # Transform Tools
        self._tf_broadcaster = TransformBroadcaster(self)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Booster RPC Client
        self._rpc_client = self.create_client(RpcService, 'booster_rpc_service')
        while not self._rpc_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
            if not rclpy.ok():
                self.get_logger().error('Interrupted while waiting for the service. Exiting.')
                return
            
        self._goal_handle = None
        self._send_goal_future = None
        self._get_result_future = None
        self.get_logger().info("ROS2Publisher node initialized")

    def create_msg(self, api_id, param_dict=None):
        msg = BoosterApiReqMsg()
        msg.api_id = api_id
        if param_dict is not None:
            msg.body = json.dumps(param_dict)
        else:
            msg.body = ""
        return msg

    def send_booster_rpc_service(self, req_msg):
        request = RpcService.Request()
        request.msg = req_msg
        future = self._rpc_client.call_async(request)
        # rclpy.spin_until_future_complete(self, future)
        event = threading.Event()
        future.add_done_callback(lambda _: event.set())
        
        if event.wait(timeout=5.0):  # 5 second timeout
            self.get_logger().info('Result: %s' % future.result().msg.body)
            return future.result().msg.body
        else:
            self.get_logger().error('Failed to call rpc service')
            return None

    def get_current_pose(self):
        T_Map_Pose: TransformStamped = self.tf_buffer.lookup_transform(
            'map',
            'pelvis_base',
            rclpy.time.Time(),
            timeout=Duration(seconds=0.1)
        )
        return transform_to_matrix(T_Map_Pose)

    def publish_transform(self, translation, rotation, child_frame="goal"):
        t = TransformStamped()

        t.header.stamp = self.get_clock().now().to_msg()
        t.header.frame_id = "map"
        t.child_frame_id = child_frame
        t.transform.translation.x = translation[0]
        t.transform.translation.y = translation[1]
        t.transform.translation.z = translation[2]
        t.transform.rotation.x = rotation[0]
        t.transform.rotation.y = rotation[1]
        t.transform.rotation.z = rotation[2]
        t.transform.rotation.w = rotation[3]

        self._tf_broadcaster.sendTransform(t)
        self.get_logger().info(f"Published Transform: {t}")
    
    def send_goal(self, translation, rotation):
        if self._goal_handle is not None:
            return False

        goal_msg = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = translation[0]
        pose.pose.position.y = translation[1]
        pose.pose.position.z = translation[2]
        pose.pose.orientation.x = rotation[0]
        pose.pose.orientation.y = rotation[1]
        pose.pose.orientation.z = rotation[2]
        pose.pose.orientation.w = rotation[3]

        goal_msg.pose = pose

        rec = self._action_client.wait_for_server(timeout_sec=10) # Ensure the action server is available
        if not rec:
            self.get_logger().warn('Action server not available!')
            return False

        self._send_goal_future = self._action_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        self._send_goal_future.add_done_callback(self.goal_response_callback)
        return True
    
    def goal_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected :(')
            self._status = "idle"
            return

        self.get_logger().info('Goal accepted :)')
        self._status = "navigating"
        self._get_result_future = goal_handle.get_result_async()
        self._get_result_future.add_done_callback(self.get_result_callback)
        self._goal_handle = goal_handle
        return

    def feedback_callback(self, feedback_msg):
        # Process and log navigation feedback (e.g., distance remaining)
        self.get_logger().info(f'Received feedback: {feedback_msg.feedback.distance_remaining:.2f}m remaining')

    def get_result_callback(self, future):
        result = future.result().result
        status = future.result().status
        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Goal succeeded!')
        else:
            self.get_logger().info(f'Goal failed with status: {status}')
        self._status = "idle"
        self._goal_handle = None
        self._get_result_future = None
        self._send_goal_future = None
        return

    def cancel_done(self, future):
        cancel_response = future.result()
        if len(cancel_response.goals_canceling) > 0:
            self.get_logger().info('Goal successfully canceled')
            self._status = "idle"
            self._goal_handle = None
            self._get_result_future = None
            self._send_goal_future = None
        else:
            self.get_logger().info('Goal failed to cancel')
        return

    def get_status(self):
        return self._status

    def clear_goal(self):
        if self._goal_handle is not None:
            future = self._goal_handle.cancel_goal_async()
            future.add_done_callback(self.cancel_done)
            self._status = "cancelling"
        return