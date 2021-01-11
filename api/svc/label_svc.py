#!/usr/bin/env python
# coding: utf-8
#
# image labeling service
#

import requests
import json
from io import BytesIO
from coco_resnet_50 import object_detection_api
import dask
import dask.bag as db

API_HOST = '10.2.59.13'
LABELPHOTO_API = 'http://{}:4040/api/v1/label'.format(API_HOST)
LISTPHOTOS_API = 'http://{}:4040/api/v1/listphotos'.format(API_HOST)
GETPHOTO_API   = 'http://{}:4040/api/v1/scaledphoto'.format(API_HOST)
NPARTITIONS = 4

def fetch_image_uuid_list():
    '''
        get a list of all image uuids
    '''
    uuid_list = []
    response = requests.get(LISTPHOTOS_API)
    data = response.content
    j_data = json.loads(data)
    for kv in j_data:
        uuid_list.append(kv['value']['uuid'])
    return uuid_list

def label_image(img_uuid):
    '''
       detect & label objects per image using resnet50 model
    '''
    try:
        response = requests.get(GETPHOTO_API, params={'img':img_uuid})
        pred_cls = object_detection_api(BytesIO(response.content))
        labels = ' '.join(set(pred_cls))
        print (labels)
        response = requests.post(LABELPHOTO_API, data={'img':img_uuid, 'labels':labels})
        response = requests.get(LABELPHOTO_API, params={'img':img_uuid})
        print (response.content)
    except:
        print ('img labeling error: {}'.format(img_uuid))

def label_all_images(img_uuid_list):        
    '''
      use dask worker pipleine to parallelize image labeling on the dataset 
    '''
    db.from_sequence(img_uuid_list, \
            npartitions=NPARTITIONS).map(label_image).compute()

if __name__ == "__main__":
    img_uuid_list = fetch_image_uuid_list()
    label_all_images(img_uuid_list)
