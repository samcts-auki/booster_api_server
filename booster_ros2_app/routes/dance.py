###########################################################
# RestAPI
###########################################################
dance_map = {
    "NewYear": 0,
    "Nezha": 1,
    "TowardsFuture": 2,
    "DabbingGesture": 3,
    "UltramanGesture": 4,
    "RespectGesture": 5,
    "CheeringGesture": 6,
    "LuckyCatGesture": 7,
    "Stop": 1000,
}

whole_body_dance_map = {
    "ArbicDance": 0,
    "MichaelDance1": 1,
    "MichaelDance2": 2,
    "MichaelDance3": 3,
    "MoonWalk": 4,
    "BoxingStyleKick": 5,
    "RoundhouseKick": 6,
}

from flask import Blueprint, jsonify, current_app, request

dance_bp = Blueprint("dance", __name__)

@dance_bp.route("/simple/list", methods=["GET"])
def dance_list():
    body = {"action_list": dance_map.keys()}
    return jsonify(body)

@dance_bp.route("/simple/action", methods=["POST"])
def dance_action():
    ros_node_instance = current_app.config["ros2_node"]

    action = request.json.get("action")
    action_num = dance_map.get(action)
    msg = ros_node_instance.create_msg(2016, {"dance_id": action_num})
    ret = ros_node_instance.send_booster_rpc_service(msg)

    return jsonify({"message": ret})

@dance_bp.route("/wholebody/list", methods=["GET"])
def wholebody_dance_list():
    body = {"action_list": dance_map.keys()}
    return jsonify(body)

@dance_bp.route("/wholebody/action", methods=["POST"])
def wholebody_dance_action():
    ros_node_instance = current_app.config["ros2_node"]

    action = request.json.get("action")
    action_num = whole_body_dance_map.get(action)
    msg = ros_node_instance.create_msg(2029, {"dance_id": action_num})
    ret = ros_node_instance.send_booster_rpc_service(msg)

    return jsonify({"message": ret})