![image](logo.png)
<div style="text-align: center;">A broker server for sending SMS.</div>

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
# setup settings.json in /opt/kds-sms-server
kds-sms-server init-db
echo """[Unit]
Description=SMS Broker - Listener - Responsible for receiving SMS as well as for the general API and UI.
After=multi-user.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/opt/kds-sms-server
ExecStart=/opt/kds-sms-server/bin/kds-sms-server listener

[Install]
WantedBy=multi-user.target""" > /etc/systemd/system/kds-sms-server-listener.service
echo """[Unit]
Description=SMS Broker - Worker - Responsible for processing SMS and database cleanup processes.
After=multi-user.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/opt/kds-sms-server
ExecStart=/opt/kds-sms-server/bin/kds-sms-server worker

[Install]
WantedBy=multi-user.target""" > /etc/systemd/system/kds-sms-server-worker.service
systemctl daemon-reload
systemctl enable kds-sms-server-listener.service
systemctl enable kds-sms-server-worker.service
systemctl start kds-sms-server-listener.service
systemctl start kds-sms-server-worker.service
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
systemctl stop kds-sms-server-listener.service
systemctl stop kds-sms-server-worker.service
kds-sms-server listener # Or kds-sms-server worker 
systemctl start kds-sms-server-listener.service
systemctl start kds-sms-server-worker.service
```

---
