# sms-server
A broker server for sending SMS.

---
## Installation :pick:
```shell
apt install python3-venv -y
mkdir -p /opt/kds-sms-server
python3 -m venv /opt/kds-sms-server
source /opt/kds-sms-server/bin/activate
pip install kds-sms-server
ln /opt/kds-sms-server/bin/kds-sms-server /usr/bin/kds-sms-server
deactivate
echo """[Unit]
Description=A broker server for sending SMS.
After=multi-user.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/opt/kds-sms-server
ExecStart=/opt/kds-sms-server/bin/kds-sms-server

[Install]
WantedBy=multi-user.target""" > /etc/systemd/system/kds_sms_server.service
systemctl daemon-reload
systemctl enable kds_sms_server.service
systemctl start kds_sms_server.service
```

---
## Update :hourglass_flowing_sand:
```shell
source /opt/kds-sms-server/bin/activate
pip install -U kds-sms-server
deactivate
```

---
## Debug :gear:
```shell
systemctl stop kds_sms_server.service
kds-sms-server
systemctl start kds_sms_server.service
```

---
