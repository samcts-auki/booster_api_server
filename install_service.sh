#!/bin/bash

# --- Configuration ---
SERVICE_NAME="booster_api_server"
APP_DIR=$(pwd)
PYTHON_BIN="/usr/bin/python3"
SCRIPT_NAME="run_booster_app.py"

echo "🚀 Starting installation for $SERVICE_NAME..."

# 1. Create the systemd user directory if it doesn't exist
mkdir -p ~/.config/systemd/user/

# 2. Write the service file
cat <<EOF > ~/.config/systemd/user/$SERVICE_NAME.service
[Unit]
Description=Flask Server User Instance
After=network.target

[Service]
WorkingDirectory=$APP_DIR
ExecStart=/bin/bash -c "source /opt/ros/humble/setup.bash && source /home/booster/Workspace/ros2/booster_robotics_sdk_ros2/booster_ros2_interface/install/setup.bash && python3 $APP_DIR/$SCRIPT_NAME"
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

echo "✅ Service file created at ~/.config/systemd/user/$SERVICE_NAME.service"

# 3. Reload the user daemon to recognize the new file
systemctl --user daemon-reload

# 4. Enable and start the service
systemctl --user enable $SERVICE_NAME
systemctl --user restart $SERVICE_NAME

# 5. Enable lingering so it starts on machine boot (requires sudo)
echo "🔑 Enabling lingering for user $(whoami) (requires sudo password)..."
sudo loginctl enable-linger $(whoami)

echo "---"
echo "🎉 Installation complete!"
echo "📊 Check status: systemctl --user status $SERVICE_NAME"
echo "📝 View logs:    journalctl --user -u $SERVICE_NAME -f"