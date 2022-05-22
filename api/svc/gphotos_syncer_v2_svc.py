#
# import photos from google.photos.com
#
# python -m api.scanner.google_photos_syncer_v2
#
#
from collections import defaultdict
import os
import sys
import json
import uuid
import configparser
from datetime import datetime, timedelta
from typing import Any
from requests_oauthlib import OAuth2Session
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from ..db import dbconf
from ..db.DB import InitPhotosDb
from ..db.query import DBGetUserGooglePhotosCredentials, DBGetNextSyncTopic, DBGetLastSyncTopic, DBAddNewTopic, DBUpdateTopic, DBDeleteSyncTopic, InsertPhoto, TestDuplicate
from ..utils.checksum import comp_checksum

#import pymysql
#pymysql.install_as_MySQLdb()

# client Map
google = dict()

redirect_url = 'urn:ietf:wg:oauth:2.0:oob'

# OAuth endpoints given in the Google API documentation
g_authorization_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
g_token_url = "https://www.googleapis.com/oauth2/v4/token"
g_scope = [
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.sharing"
]

def convert_to_datetime(string):
    i = string.find('T')
    s = string[0:i]
    t = string[i:]
    t = t.lstrip('T')
    t = t.rstrip('Z')
    date_string = '{} {}'.format(s, t)
    format_string = "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(date_string, format_string)

class DateDict:
    def __init__(self, y, m, d):
        self.year = y
        self.month = m
        self.day = d

    def to_dict(self):
        return {"year": self.year, "month": self.month, "day": self.day}

    def to_string(self):
        return json.dumps(self.to_dict())

    def to_datetime(self):
        return datetime(self.year, self.month, self.day)

GSyncDefaultEpochOrigin = DateDict(2022, 5, 20)

class GClientOAuth2(object):

    def __init__(self, client_id, client_secret, scope, authorization_base_url, redirect_uri, token_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.authorization_base_url = authorization_base_url
        self.redirect_uri = redirect_uri
        self.token_uri = token_uri
        extra = {"client_id": self.client_id,
                 "client_secret": self.client_secret}
        self.oauth_client2 = OAuth2Session(self.client_id, scope=self.scope,
                                           redirect_uri=self.redirect_uri,
                                           auto_refresh_url=self.token_uri,
                                           auto_refresh_kwargs=extra)

    def authorize(self, response_code=None):
        # Redirect user to Google for authorization
        # offline for refresh token
        # force to always make user click authorize
        authorization_url, state = self.oauth_client2.authorization_url(self.authorization_base_url,
                                                                        access_type="offline", prompt="select_account")
        # Get the authorization verifier code from the callback url
        #redirect_response = input('Paste the full redirect URL here:')
        if response_code is None:
            print('Please authorize the url from your browser:', authorization_url)
            response_code = input('Paste the response code here:')
        token_dict = self.oauth_client2.fetch_token(
            self.token_uri, client_secret=self.client_secret, code=response_code)
        if not token_dict:
            print("error fetching token")
        else:
            print("token_dict :{}".format(token_dict))

    def get_authorize_url(self):
        # Redirect user to Google for authorization
        # offline for refresh token
        # force to always make user click authorize
        authorization_url, state = self.oauth_client2.authorization_url(self.authorization_base_url,
                                                                        access_type="offline", prompt="select_account")
        return authorization_url

class GPhotosClient_V1(GClientOAuth2):

    def __init__(self, user_id, client_id, client_secret, scope, authorization_base_url,
                 token_url, need_redirect_url=None, response_code=None, db_engine=None):
        super(GPhotosClient_V1, self).__init__(client_id, client_secret, scope,
                                               authorization_base_url, redirect_url, token_url)
        if need_redirect_url:
            self.authorize_url = super(
                GPhotosClient_V1, self).get_authorize_url()
        else:
            self.authorize_url = None
            print(response_code)
            super(GPhotosClient_V1, self).authorize(
                response_code=response_code)
        self.db_engine = db_engine
        self.user_id = user_id
        self.total_items = 0
        self.items = 0

    def self_test(self):
        # Fetch a protected resource, i.e. user profile
        response = self.oauth_client2.get(
            'https://photoslibrary.googleapis.com/v1/albums')
        print("gClient selftest :" + str(response.content))

    def store_photo(self, file_name, raw_bytes):
        digest = comp_checksum(raw_bytes)
        if TestDuplicate(self.user_id, raw_bytes, digest, "My Google Photos"):
            print ("Detected duplicate entry:{}".format(file_name))
        else:
            InsertPhoto(self.user_id, file_name, raw_bytes, "My Google Photos")

    def get_sync_point(self):
        tuuid, topic, json_input = DBGetNextSyncTopic()
        if json_input:
            start = DateDict(json_input["Year"], json_input["Month"], json_input["Day"])
            return tuuid, topic, start, False

        tuuid, json_input = DBGetLastSyncTopic()
        if json_input:
            start = DateDict(json_input["Year"], json_input["Month"], json_input["Day"])
            return None, topic, start, True

        return None, topic, GSyncDefaultEpochOrigin, True

    def set_sync_point(self, yr, mon, day):
        json_input = dict()
        json_input["Year"] = yr
        json_input["Month"] = mon
        json_input["Day"] = day
        return DBAddNewTopic(uuid.uuid4(), "GPhotos", json.dumps(json_input))

    def update_sync_point(self, tuuid, topic, json_output):
        return DBUpdateTopic(tuuid, topic, json_output, 2)

    def remove_sync_point(self, tuuid):
        DBDeleteSyncTopic(tuuid)

    def get_next_sync_point(self, start):
        end =  start.to_datetime() + timedelta(days=30)
        if end > datetime.today():
            end = datetime.today()
        tp = end.timetuple()
        return DateDict(tp.tm_year, tp.tm_mon, tp.tm_mday)

    def download_photos_bydate(self):
        self.items = 0
        page_token = None
        splist = []
        start = None
        end = None
        tuuid = None
        while self.items < self.total_items:
            if page_token is None:
                tuuid, topic, start, need_update = self.get_sync_point()
                if need_update:
                    tuuid = self.set_sync_point(start.year, start.month, start.day)
                end = self.get_next_sync_point(start)

            body = {
                "pageToken": page_token,
                "filters": {
                    "dateFilter": {
                        "ranges": [
                            {"startDate": start.to_dict(), "endDate": end.to_dict()}
                        ]
                    },
                },
            }

            body = json.dumps(body)
            response = self.oauth_client2.request('POST', data=body,
                                                  url='https://photoslibrary.googleapis.com/v1/mediaItems:search')

            print ('last synced date :{} photos synced :{} total_items :{}'.
                format(start.to_string(), self.items, self.total_items))
            if response.status_code == 200:
                data_dict = json.loads(response.content)
                # print response.content, 'count:', len(data["mediaItems"])
                json_output = {
                    "result" : " ",
                    "synced" : 0,
                    "errors" : 0
                }
                if "mediaItems" in data_dict:
                    for ans in data_dict["mediaItems"]:
                        download_url = ans["baseUrl"] + "=d"
                        #creation_time = ans["mediaMetadata"]["creationTime"]
                        #file_name=ans["filename"]
                        try:
                            response = self.oauth_client2.request('GET', download_url)
                            print ("File {} {}".format(ans["filename"], ans["mimeType"]))
                            if ans["filename"].endswith('.jpg'):
                                self.store_photo(ans["filename"], response.content)
                            self.items += 1
                            json_output["synced"] += 1
                        except:
                            print("db insert error :{}".format(sys.exc_info()[0]))
                            json_output["errors"] += 1
                            raise
                else:
                    print("No mediaItems Key in data_dict")

                # print response.status_code, response.headers, len(response.content)
                if "nextPageToken" in data_dict:
                    page_token = data_dict["nextPageToken"]
                elif self.items > 0:
                    page_token = None
                    json_output["result"] = "Done"
                    self.update_sync_point(str(tuuid), topic, json.dumps(json_output))
                    self.set_sync_point(end.year, end.month, end.day)
                    start = end
                    splist.append(tuuid)
            else:
                print('error downloading photos, exit response status code :',
                      response.status_code)
                print(response.content)
                break

        for i in range(len(splist) - 1):
            self.remove_sync_point(str(splist[i]))

        self.items = self.total_items
        print('finished listing all media items')

    def count_photos_to_download(self):
        _, _, start, _ = self.get_sync_point()
        tp = datetime.today().timetuple()
        end = DateDict(tp.tm_year, tp.tm_mon, tp.tm_mday)
        page_token = None
        done = False
        self.total_items = 0
        print ('last synced date :{}, counting new photos...'.format(start.to_string()))
        while not done:
            body = {
                "pageToken": page_token,
                "filters": {
                    "dateFilter": {
                        "ranges": [
                            {"startDate": start.to_dict(), "endDate": end.to_dict()}
                        ]
                    },
                },
            }

            body = json.dumps(body)
            response = self.oauth_client2.request('POST', data=body,
                                                  url='https://photoslibrary.googleapis.com/v1/mediaItems:search')
            #print("response :" + str(response))
            if response.status_code == 200:
                data_dict = json.loads(response.content)
                print(response.content, 'data_dict:', data_dict)
                if data_dict and "mediaItems" in data_dict:
                    self.total_items += len(data_dict["mediaItems"])
                else:
                    print("key mediaItems not present in data_dict response")
                if "nextPageToken" in data_dict:
                    page_token = data_dict["nextPageToken"]
                else:
                    done = True
            else:
                print('error downloading photos, exit response status code :',
                      response.status_code)
                print(response.content)
                break
        print("total new photos to sync:{}".format(self.total_items))

    def get_status(self):
        if self.total_items > 0:
            print ('google photos sync progress:{}/{}'.format(self.items, self.total_items))
            return int((self.items * 100)/self.total_items)
        else:
            return 0

#
# Flask EndPoint Calls
#

def GetPhotoOAuthURL(user_id):
    '''
        fetches url for response code
    '''
    (g_client_id, g_client_secret) = DBGetUserGooglePhotosCredentials(user_id)
    google[user_id] = GPhotosClient_V1(user_id, g_client_id, g_client_secret, g_scope,
                                       g_authorization_base_url, g_token_url, need_redirect_url=True)
    google[user_id].self_test()
    return google[user_id].authorize_url

def SyncPhotos(user_id, response_code):
    '''
        kicks off a download session
    '''
    print("Sync Photos...")
    (g_client_id, g_client_secret) = DBGetUserGooglePhotosCredentials(user_id)
    google[user_id] = GPhotosClient_V1(user_id, g_client_id, g_client_secret, g_scope,
                                       g_authorization_base_url, g_token_url, need_redirect_url=False, response_code=response_code)
    google[user_id].self_test()
    google[user_id].count_photos_to_download()
    google[user_id].download_photos_bydate()

def SyncPhotosStatus(user_id):
    gc = google.get(user_id)
    if gc:
        return gc.get_status()
    else:
        return 0
