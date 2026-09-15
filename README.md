# Grafana to Nextcloud TALK bridge
This little python app will enable your Grafana to send notifications to your desired Nextcloud talk room. You don´t need a nextcloud bot or another addon or plugin. Also, we will make use of webhook targets in stock Grafana. What I want to say is, all you need is Grafana, a nextcloud talk and an debian/ubuntu lxc/vm and you my friend are ready to rock!

## Requirements
* Grafana
* Nextcloud with Nextcloud Talk
* Debian or Ubuntu LXC/VM

## Setup
1. We will first prepare a service account with an app password on our nextcloud and add him to the targeted room
2. We will setup the python app and systemd service on the lxc/VM
3. We will configure the webhook target on Grafana
4. Optional: We will monitor the app via Uptime Kuma

### Nextcloud setup
1. Create a new user
2. If you don´t already have a nextcloud talk channel for your notifications, create one
3. Add the new user to the channel
4. Copy the channel id. To do so enter the channel. You just need to copy the last part of the url. For example if your url is *https://nextcloud.pizzaparty.lan/call/xvq3a88p* you need to copy the *xvq3a88p*
5. Logout and login as the new user
![NextcloudAPPtoken](https://github.com/wolkenlosIT/grafana-nextcloudTALK-bridge/blob/main/setupimages/nextcloudapptoken.jpg)
6. Click on your profile pic ---> Click on Settings ---> Click on Security --> Scroll down to *Devices & sessions* and enter an App Name --> Click on *Generate new app password*
7. The popup will present you the password. Copy it. We will need it in the next step
8. Optional: If you want to add an avatar to the service account: Now is a good time to do so!
9. With this the setup on your nextcloud is completed

### Python app setup
1. Log into your debian or ubuntu lxc/vm with root or a sudo user
2. Let´s create the app first. Our working dictionary will be:
```shell
sudo mkdir /opt/grafana-talk-bridge
```
3. Copy/past the app.py or download it to the directory. You don´t have to change anything here.
```shell
sudo nano /opt/grafana-talk-bridge/app.py
```

5. Let´s create the webhook secret:
```shell
openssl rand -hex 16
```
6. Copy the secret and let´s create our environments file. Fill it out, too! Don´t change the port if you don´t know what you are doing!
```shell
sudo nano /etc/grafana-talk-bridge.env
```
7. Let´s add a user, group and change the permission to our files, so that we can let the app run as a non root user:
```shell
sudo groupadd --system grafana-talk
sudo useradd --system --gid grafana-talk --home-dir /opt/grafana-talk-bridge --shell /usr/sbin/nologin grafana-talk
sudo chown -R grafana-talk:grafana-talk /opt/grafana-talk-bridge
sudo chown root:grafana-talk /etc/grafana-talk-bridge.env
sudo chmod 640 /etc/grafana-talk-bridge.env
```
8. The next step is the creation of a systemd service:
```shell
sudo nano /etc/systemd/system/grafana-talk-bridge.service
```
9. Reload the deamon and enable the service for an autostart:
```shell
sudo systemctl daemon-reload
sudo systemctl enable grafana-talk-bridge.service
```
10. You can now start the app via systemd and check the status:
```shell
sudo systemctl start grafana-talk-bridge.service
sudo systemctl status grafana-talk-bridge.service
```
11. You can check with the following if the webservice is reachable:
```shell
curl -i http://127.0.0.1:8790/health
```
12. With this. We can move to our grafana server!

### Grafana setup
1. Log into your Grafana. Then click on "Alerting" and "Manage contact points"
![grafanawebhooksetup1](https://github.com/wolkenlosIT/grafana-nextcloudTALK-bridge/blob/main/setupimages/grafanasetup1.jpg)
2. Click on "New contact point":
![grafanawebhooksetup2](https://github.com/wolkenlosIT/grafana-nextcloudTALK-bridge/blob/main/setupimages/grafanasetup2.jpg) 
3. You can enter whatever under "Name".  As "Integration" select "Webhook" and for "URL" add your lxc/vm url in the following format: http://SWAP_WITH_YOUR_LXC_IP_ADRESS:8790/grafana
![grafanawebhooksetup3](https://github.com/wolkenlosIT/grafana-nextcloudTALK-bridge/blob/main/setupimages/grafanasetup3.jpg)
4. The"HTTP Method" is "POST" . Add one "Extra Header" with the "Name": "X-Grafana-Webhook-Secret" and the value, which is the webhook secret you created in the last part.
5. Press Test. If everything is working you should have received a message in your Nextcloud Talk room
8. Safe

### Monitor the bridge with Uptime Kuma
1. Log into your Uptime Kuma
2. Add a new monitor
3. For "Monitortyp" select "HTTP(s)"
4. For the "URL" http://SWAP_WITH_YOUR_LXC_IP_ADRESS:8790/health
5. Safe

##
I hope you like this! 
You can ask me questions in German too!







