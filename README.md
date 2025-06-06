<p align="center">
  <a href="#"><img src="https://github.com/JuliusKoenig/sms-server/blob/main/docs/logo.png" alt="SMS Broker"></a>
</p>
<p align="center">
    <em>A broker server for sending SMS.</em>
</p>

---
## Installation :pick:
```shell
apt install python3-venv -y
mkdir -p /opt/sms-broker
python3 -m venv /opt/sms-broker
source /opt/sms-broker/bin/activate
pip install sms-broker
ln /opt/sms-broker/bin/sms-broker /usr/bin/sms-broker
deactivate
# setup settings.json in /opt/sms-broker
sms-broker init-db
echo """[Unit]
Description=KDS SMS Server - Listener - Responsible for receiving SMS as well as for the general API and UI.
After=multi-user.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/opt/sms-broker
ExecStart=/opt/sms-broker/bin/sms-broker listener

[Install]
WantedBy=multi-user.target""" > /etc/systemd/system/sms-broker-listener.service
echo """[Unit]
Description=KDS SMS Server - Worker - Responsible for processing SMS and database cleanup processes.
After=multi-user.target

[Service]
Type=simple
Restart=always
WorkingDirectory=/opt/sms-broker
ExecStart=/opt/sms-broker/bin/sms-broker worker

[Install]
WantedBy=multi-user.target""" > /etc/systemd/system/sms-broker-worker.service
systemctl daemon-reload
systemctl enable sms-broker-listener.service
systemctl enable sms-broker-worker.service
systemctl start sms-broker-listener.service
systemctl start sms-broker-worker.service
```

---
## Update :hourglass_flowing_sand:
```shell
source /opt/sms-broker/bin/activate
pip install -U sms-broker
deactivate
```

---
## Debug :gear:
```shell
systemctl stop sms-broker-listener.service
systemctl stop sms-broker-worker.service
sms-broker listener # Or kds-sms-server worker 
systemctl start sms-broker-listener.service
systemctl start sms-broker-worker.service
```

---
