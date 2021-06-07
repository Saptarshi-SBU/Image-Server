#
# import photos from google.photos.com
#
# python -m api.scanner.google_photos_syncer
#
#
import os
import sys
import json
import configparser
from datetime import datetime
from typing import Any
from requests_oauthlib import OAuth2Session
import sqlalchemy as sa
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import pymysql
pymysql.install_as_MySQLdb()

# Credentials you get from registering a new application
# Obtained from Google API Developer Console
g_client_id = '372962811824-fvhje3978smseeouchdbf4bk3p57gf5i.apps.googleusercontent.com'
g_client_secret = 'C4n2ygSbn69D6tJAF0oPz9Bk'

redirect_url = 'urn:ietf:wg:oauth:2.0:oob'

# OAuth endpoints given in the Google API documentation
g_authorization_base_url = "https://accounts.google.com/o/oauth2/v2/auth"
g_token_url = "https://www.googleapis.com/oauth2/v4/token"
g_scope = [
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.sharing"
]

DB_ENGINE = "sqlite:///{database}"
DBCONFIG_DICT = {'database': 'GPhotos.db'}

CONFIG_FILE = "/etc/api.cfg"


def gclient_get_response_code(cfg_file=CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(cfg_file)
    if 'gphotos' in config:
        return config.get("gphotos", "code")
    else:
        return None


def gclient_set_response_code(code, cfg_file=CONFIG_FILE):
    config = configparser.ConfigParser()
    config.read(cfg_file)
    config.set("gphotos", "code", str(code))
    with open(cfg_file, "w+") as config_file:
        config.write(config_file)


def convert_to_datetime(string):
    i = string.find('T')
    s = string[0:i]
    t = string[i:]
    t = t.lstrip('T')
    t = t.rstrip('Z')
    date_string = '{} {}'.format(s, t)
    format_string = "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(date_string, format_string)


Base = declarative_base()


class GPhoto(Base):
    __tablename__ = "gphoto"
    filename = Column(String, primary_key=True)
    date_time = Column(DateTime)
    user_name = Column(String)


class DBManager():

    def __init__(self):
        """
        loads db configuration for establishing connection
        """
        DB_URL_DEFAULT = (DB_ENGINE.format(**DBCONFIG_DICT))
        self._engine = sa.create_engine(DB_URL_DEFAULT)
        self._sessionMaker = sessionmaker(bind=self._engine)

    def __enter__(self):
        """
        opens connection to the specified database
        :returns Database Handle
        """
        self._session = self._sessionMaker()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close Connection to the specified database
        """
        self._session.close()

    def getSession(self):
        """
        returns the underlying session object of sql client
        """
        return self._session

    def createDb(self):
        """
        Create arep Database
        """
        conn = self._engine.connect()
        conn.execute("CREATE DATABASE IF NOT EXISTS %s" % 'Gphotos')
        conn.execute("COMMIT")

    def dropDb(self):
        """
        Create arep Database
        """
        assert self.create
        conn = self._engine.connect()
        conn.execute("DROP DATABASE IF EXISTS %s" % 'Gphotos')
        conn.execute("COMMIT")

    def createTables(self):
        """
        Create arep Tables
        """
        Base.metadata.create_all(self._engine)


def InitPhotosDb():
    """
      Initializes the arep db and tables
    """
    with DBManager() as db:
        # db.createDb()
        db.createTables()

# Model Queries


def DBGetPhotos(user_id):
    """
            fetches all records
    """
    with DBManager() as db:
        dbSession = db.getSession()
        return dbSession.query(GPhoto).filter(GPhoto.user_name==user_id).all()


def DBGetMaxDate(user_id):
    with DBManager() as db:
        dbSession = db.getSession()
        result = dbSession.query(GPhoto).filter(GPhoto.user_name==user_id).sa.func.max(GPhoto.date_time).first()
        print(result)
        for r in result:
            t = r.timetuple()
            print(r, r.timetuple())
            print(t.tm_year, t.tm_mon, t.tm_mday)
            return r


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
        print('Please authorize the url from your browser:', authorization_url)
        # Get the authorization verifier code from the callback url
        #redirect_response = raw_input('Paste the full redirect URL here:')
        if response_code is None:
            response_code = input('Paste the response code here:')
        self.oauth_client2.fetch_token(
            self.token_uri, client_secret=self.client_secret, code=response_code)

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
        super(GPhotosClient_V1, self).__init__(g_client_id, g_client_secret, g_scope,
                                               g_authorization_base_url, redirect_url, g_token_url)
        if need_redirect_url:
            self.authorize_url = super(
                GPhotosClient_V1, self).get_authorize_url()
        else:
            self.authorize_url = None
            super(GPhotosClient_V1, self).authorize(response_code=response_code)
        self.user_id = user_id
        self.db_engine = db_engine
        self.total_items = 0
        self.items = 0

    def self_test(self):
        # Fetch a protected resource, i.e. user profile
        response = self.oauth_client2.get(
            'https://photoslibrary.googleapis.com/v1/albums')
        print(response.content)

    def store_photo(self, data_dir, file_name, raw_bytes):
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        path = '{}/{}'.format(data_dir, file_name)
        print(path)
        fd = os.open(path, os.O_CREAT | os.O_RDWR)
        os.write(fd, raw_bytes)
        os.close(fd)

    def download_all_photos(self):
        params = {}
        done = False
        while not done:
            response = self.oauth_client2.request('GET',
                                                  url='https://photoslibrary.googleapis.com/v1/mediaItems', params=params)
            if response.status_code == 200:
                data_dict = json.loads(response.content)
                # print response.content, 'count:', len(data["mediaItems"])
                for ans in data_dict["mediaItems"]:
                    download_url = ans["baseUrl"] + "=d"
                    creation_time = ans["mediaMetadata"]["creationTime"]
                    response = self.oauth_client2.request('GET', download_url)
                    self.store_photo(
                        ans["mimeType"], ans["filename"], response.content)
                    with DBManager() as db:
                        _dbSession = db.getSession()
                        entry = GPhoto(filename=ans["filename"],
                                       date_time=convert_to_datetime(creation_time),
                                       user_id=self.user_id)
                        _dbSession.add(entry)
                        _dbSession.commit()
                        print(entry)
                    # print response.status_code, response.headers, len(response.content)
                if "nextPageToken" in data_dict:
                    params = {"pageToken": data_dict["nextPageToken"]}
                else:
                    done = True
                    print('finished listing all media items')
            else:
                print('error downloading photos, exit response status code :',
                      response.status_code)
                break

    def download_photos_bydate(self):
        page_token = None
        done = False

        class Y:
            def __init__(self, y, m, d):
                self.year = y
                self.month = m
                self.day = d

            def to_dict(self):
                return {"year": self.year, "month": self.month, "day": self.day}

        dt = DBGetMaxDate()
        #start = Y(dt.timetuple().tm_year, dt.timetuple().tm_mon, dt.timetuple().tm_mday + 1)
        start = Y(dt.timetuple().tm_year, dt.timetuple().tm_mon, 1)
        end = Y(3000, 12, 31)
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

            if response.status_code == 200:
                data_dict = json.loads(response.content)
                # print response.content, 'count:', len(data["mediaItems"])
                self.total_items += len(data_dict["mediaItems"])
                for ans in data_dict["mediaItems"]:
                    download_url = ans["baseUrl"] + "=d"
                    creation_time = ans["mediaMetadata"]["creationTime"]
                    response = self.oauth_client2.request('GET', download_url)
                    self.store_photo(
                        ans["mimeType"], ans["filename"], response.content)
                    with DBManager() as db:
                        dbSession = db.getSession()
                        entry = GPhoto(filename=ans["filename"],
                                       date_time=convert_to_datetime(creation_time),
                                       user_id=self.user_id)
                        try:
                            dbSession.add(entry)
                            dbSession.commit()
                            print(entry)
                            self.items += 1
                        except:
                            print("db insert error :{}".format(
                                sys.exc_info()[0]))
                # print response.status_code, response.headers, len(response.content)
                if "nextPageToken" in data_dict:
                    page_token = data_dict["nextPageToken"]
                else:
                    done = True
                    self.items = self.total_items
                    print('finished listing all media items')
            else:
                print('error downloading photos, exit response status code :',
                      response.status_code)
                print(response.content)
                break

    def get_status(self):
        return (self.items, self.total_items)

#client name
google = None

def GetPhotoOAuthURL(user_id):
    '''
            fetches url for response code
    '''
    google = GPhotosClient_V1(user_id, g_client_id, g_client_secret, g_scope,
                              g_authorization_base_url, g_token_url, need_redirect_url=True)
    google.self_test()
    return google.authorize_url


def SyncPhotos(user_id, response_code):
	'''
		kicks off a download session
	'''
	print("Sync Photos...")
	InitPhotosDb()
	google = GPhotosClient_V1(user_id, g_client_id, g_client_secret, g_scope,
							g_authorization_base_url, g_token_url, need_redirect_url=False, response_code=response_code)
	google.self_test()
	# google.download_all_photos()
	google.download_photos_bydate()

def SyncPhotosStatus(user_id):
    return google.get_status()

if __name__ == "__main__":
    InitPhotosDb()
    result = DBGetPhotos()
    print(result)
    for r in result:
        print(r.filename, r.date_time)
    user_id = "saptarshi.mrg@gmail.com"
    result = DBGetMaxDate(user_id)
    google = GPhotosClient_V1(user_id, g_client_id, g_client_secret, g_scope,
                              g_authorization_base_url, g_token_url)
    google.self_test()
    # google.download_all_photos()
    google.download_photos_bydate()
