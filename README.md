## Introduction

 A web based image hosting service for private setups built using Flask as the backend.

 You can deploy, browse and mantain all your personal images with least concern about
 security in a controlled environment.
 
 New extensions allow it to connect to cloud storage for fetching personal images from
 the cloud. This is useful when users tend to exceed alloted free space in the cloud.

## Features

  +) Provides capabilities for creating personal albums, searching albums.
  
  +) Provides a list of REST based APIs to interact with the service.

  +) Cloud Connector for importing pictures from your Google Drive.
  
  +) Run analytics such as image labelling service in the background.

## Installation & Deployment Steps

 +)  mount /dev/<disk> /mnt/target

 +)  edit /etc/api.cfg

 +)  systemctl start mysqld

 +)  python run.py
 
## Screenshots

### Browse Albums:

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Albums.png" width="800">

### Search Albums:

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Search.png" width="800">

### Image Labelling Service

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/LabelledPhoto03.png" width="800">

### Import GoogleCloud Photos :

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/GooglePhoto03.png" width="800">

### API Statistics :

 <img src="https://github.com/Saptarshi-SBU/APIserver/blob/master/api/docs/screenshots/Statistics.png" width="800">
