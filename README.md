## Introduction

 A web based image hosting service for private setups built using Flask as the backend.
 The service can host both medium and high resolution pictures. There are backend services
 for downsampling and resizing images so that images are served with minimal use of network
 bandwidth. Custom image visualizations like grid views, slideshows are exposed via REST API
 endpoints.

 New extensions allow it to connect to cloud storage for fetching personal images from
 the cloud. This is useful when users tend to exceed alloted free space in the cloud.

 Now you can deploy, browse and mantain all your personal images with least concern about
 security, in a home environment.
 
## Features

  +) Provides capabilities for creating personal albums, browsing and searching albums.
  
  +) Provides a list of REST based APIs to interact with the service.

  +) Cloud Connector for importing pictures from your Google Drive.
  
  +) Run analytics such as image labelling service in the background.

## Installation & Deployment Steps

 +)  mount /dev/<disk> /mnt/target

 +)  edit /etc/api.cfg

 +)  systemctl start mysqld

 +)  python run.py

## MySQL database migration Steps
 On Host A
 +) mysqldump -u photoserver -p Photos > photos.sql

 On Host B
 +) sudo mysql
  ++) create user 'photoserver'@'localhost' password xxx
  ++) select * from user;
 +) mysql -u photoserver -p
  ++) create database Photos;
  ++) GRANT ALL PRIVILEGES ON *.* TO 'photoserver'@'localhost';
 +)sudo mysql -u photoserver -p Photos < photos.sql
 
## Screenshots

### Browse Albums:

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Albums.png" width="800">

### Search Albums:

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Search.png" width="800">

### Image Labelling Service

##### $python -m api.svc.label_svc

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/LabelledPhoto03.png" width="800">

### Import GoogleCloud Photos :

##### $python -m api.svc.gphotos_syncer_svc (provide access token)
##### $python -m api.svc.photos_resizing_svc
##### $python -m api.svc.photos_dimensions_svc

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/GooglePhoto05.png" width="800">

### API Statistics :

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Statistics.png" width="800">
