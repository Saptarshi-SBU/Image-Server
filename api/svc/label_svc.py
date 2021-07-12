#!/usr/bin/env python
# coding: utf-8
#
# image labeling service
#

import json
import requests
import configparser
from io import BytesIO
import dask.bag as dbag
from dask.diagnostics import ProgressBar
from image_processing.coco_resnet_50 import object_detection_api

LABELPHOTO_URL   = 'http://{}:4040/api/v1/label'
UNLABELPHOTO_URL = 'http://{}:4040/api/v1/nolabel'
LISTPHOTOS_URL   = 'http://{}:4040/api/v1/listphotos'
GETPHOTO_URL     = 'http://{}:4040/api/v1/scaledphoto'
NPARTITIONS = 2
CONFIG_FILE="/etc/api.cfg"

def GetHostIP(cfg_file=CONFIG_FILE):
	config = configparser.ConfigParser()
	config.read(cfg_file)
	return config.get("host", "ipv4")

def fetch_image_uuid_list():
    '''
        get a list of all image uuids
    '''
    uuid_list = []
    #response = requests.get(LISTPHOTOS_API)
    response = requests.get(UNLABELPHOTO_URL.format(GetHostIP()))
    data = response.content
    j_data = json.loads(data)
    #print (j_data)
    #for kv in j_data:
    #    uuid_list.append(kv['value']['uuid'])
    for img_uuid in j_data:
        uuid_list.append(img_uuid)
    return uuid_list

def label_image(img_uuid):
    '''
       detect & label objects per image using resnet50 model
    '''
    
    response = requests.get(GETPHOTO_URL.format(GetHostIP()),
        params={'img':img_uuid})
    if response.status_code != 200:
        print ('response error get photo :{}'.format(response.status_code))
    else:
        try:
            pred_cls = object_detection_api(BytesIO(response.content))
            labels = ' '.join(set(pred_cls))
            if len(labels) == 0:
                labels = ["unclassfied"]
            #print (labels)

            response = requests.post(LABELPHOTO_URL.format(GetHostIP()),
                data={'img':img_uuid, 'labels':labels})
            if response.status_code != 200:
                print ('response error post label photo :{}'.format(response.status_code))
                return

            response = requests.get(LABELPHOTO_URL.format(GetHostIP()),
                params={'img':img_uuid})
            if response.status_code != 200:
                print ('response error get label photo:{}'.format(response.status_code))
                return
            
            print ('labelling complete :{}::{}'.format(img_uuid, labels))
        except Exception as e:
            print ('img labeling error: {}'.format(img_uuid), e)

def label_all_images(img_uuid_list):        
    '''
      use dask worker pipleine to parallelize image labeling on the dataset 
    '''
    n = len(img_uuid_list)
    uuid_list = img_uuid_list[0 : min(n, n)]
    print ('total images :{} processing :{}'.format(n, len(uuid_list)))
    with ProgressBar():
        dbag.from_sequence(uuid_list, \
            npartitions=NPARTITIONS).map(label_image).compute(scheduler='threads')
            #npartitions=NPARTITIONS).map(label_image).compute(scheduler='threads', num_workers=2)

if __name__ == "__main__":
    img_uuid_list = fetch_image_uuid_list()
    label_all_images(img_uuid_list)
