import rclpy
from rclpy.node import Node
from booster_interface.srv import RpcService
from booster_interface.msg import BoosterApiReqMsg
import json
import time

def create_msg(api_id, param_dict=None):
    msg = BoosterApiReqMsg()
    msg.api_id = api_id
    if param_dict is not None:
        msg.body = json.dumps(param_dict)
    else:
        msg.body = ""
    return msg

def main():
    rclpy.init()
    node = Node('rpc_client_node')
    client = node.create_client(RpcService, 'booster_rpc_service')

    while not client.wait_for_service(timeout_sec=1.0):
        node.get_logger().info('service not available, waiting again...')
        if not rclpy.ok():
            node.get_logger().error('Interrupted while waiting for the service. Exiting.')
            return

    # 构造消息
    # 切换到手末端控制模式
    # 2012 is the API ID for kSwitchHandEndEffectorControlMode,refer to the b1_loco_api.hpp
    # req_msg = create_msg(2016, {"dance_id": 0})  # kSwitchHandEndEffectorControlMode
    req_msg = create_msg(2029, {"dance_id": 0})  # kSwitchHandEndEffectorControlMode

    while rclpy.ok():
        # 切换到手末端控制模式
        request = RpcService.Request()
        request.msg = req_msg
        future = client.call_async(request)
        rclpy.spin_until_future_complete(node, future)
        if future.result() is not None:
            node.get_logger().info('Result: %s' % future.result().msg.body)
        else:
            node.get_logger().error('Failed to call rpc service')
        time.sleep(2)
        break


    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()