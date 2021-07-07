'''
	python module for image hosting
'''
import os
import json
import jsonpickle
import time
import gc
#import objgraph
import random
import uuid
import time
import datetime
import urllib
import collections
import traceback
import flask
import functools
import threading
from tqdm import tqdm
from functools import wraps, update_wrapper
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, Response, make_response, send_from_directory, render_template, url_for, session, flash, jsonify
from .db.DB import DBGetPhoto, InitPhotosDb
from .db.query import InsertPhoto, LookupPhotos, LookupPhotosByDate, FilterPhotos, FilterPhotosPotraitStyle, FilterPhotoAlbums, DeletePhoto, MarkPhotoFav, \
    UpdatePhotoTag, LookupUser, AddUser, AutoCompleteAlbum, GetPath, GetAlbumPhotos, GetAlbumViewItems, DBGetPhotoLabel, DBAddPhotoLabel, \
    DBGetUnLabeledPhotos, FilterLabeledPhotos, FilterLabeledPhotosPotraitStyle, GetImageDir, GetHostIP, GetScaledImage, GetThumbnailImage, DBGetUserImage, DBSetUserImage
from .image_processing.filtering import ProcessImage, ProcessImageThumbnail, ProcessImageGrayScale, ProcessImageSharpenFilter, ProcessImageSepiaFilter
from .image_processing import imgcache
from .svc.gphotos_syncer_svc import gclient_get_response_code, GetPhotoOAuthURL, SyncPhotos, SyncPhotosStatus
#import flask_monitoringdashboard as dashboard
from flask_sqlalchemy import SQLAlchemy
from flask_statistics import Statistics
from flask_mail import Mail, Message
import pymysql
pymysql.install_as_MySQLdb()

# task entries
tasklist = []

#user tracking
u_session = collections.defaultdict(collections.defaultdict)

#serialize prefetch
prefetchMutex = threading.Lock()

# configured via api.cfg
HOST_ADDRESS = GetHostIP()

# mail object
app_mail = None
app_mail_sender = os.environ.get("MAIL_ID")
app_main_receiver = os.environ.get("MAIL_ID")


def checklogin(method):
    @functools.wraps(method)
    def check_login(*args, **kwargs):
        user_id = session.get("user_id")
        if not user_id:
            flash("please log in")
            return make_response(render_template('login.html'))
        else:
            return method(args, **kwargs)
    return check_login


def nocacheresponse(method):
    @functools.wraps(method)
    def nocache_response(*args, **kwargs):
        response = make_response(method(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response

    return update_wrapper(nocache_response, method)


def cacheresponse(method):
    @functools.wraps(method)
    def cache_response(*args, **kwargs):
        response = make_response(method(*args, **kwargs))
        response.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        return response

    return update_wrapper(cache_response, method)


class Home(Resource):

    @checklogin
    def get(self):
        # time.sleep(1)
        with open('api/templates/main.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            # return send_file('{}'.format('main.html'))
            # return {"message": "Welcome to Sen Family's Image Server"}


class WelcomeBanner(Resource):

    @cacheresponse
    def get(self):
        user_id = session.get("user_id")
        if user_id:
            img_uuid = DBGetUserImage(session["user_id"])
            if img_uuid:
                response = make_response(
                    ProcessImage(GetPath(img_uuid), int(20)))
                response.headers.set('Content-Type', 'image/jpg')
                return response
        response = make_response(ProcessImage(
            'api/images/welcome_2.0.jpg', scale_percent=20))
        response.headers.set('Content-Type', 'image/jpg')
        return response


class Favicon(Resource):

    def get(self):
        return send_file('{}'.format('images/favicon.ico'))


class FaviconApple(Resource):

    def get(self):
        return send_file('{}'.format('images/apple-touch-icon-152x152.png'))


class GetPhotoRaw(Resource):

    #@nocacheresponse
    def get(self):
        img_uuid = request.args.get('img')
        if img_uuid is None:
            return make_response("Invalid image request", 400)
        else:
            # objgraph.show_most_common_types()
            return send_file(GetPath(img_uuid), mimetype='image/jpg')


class GetPhotoScaled(Resource):

    @cacheresponse
    def get(self):
        img_data = None
        img_uuid = request.args.get('img')
        if img_uuid is None:
            return make_response("Invalid image request", 400)
        scale_pc = request.args.get('scale')
        if scale_pc is None:
            scale_pc = 15
        # checked if image with medium size is processed
        img_data = GetScaledImage(img_uuid)
        if not img_data:
            img_data = ProcessImage(GetPath(img_uuid), int(scale_pc))

        if img_data:
            response = make_response(img_data)
            response.headers.set('Content-Type', 'image/jpg')
            return response
        else:
            return make_response("image not found {}".format(img_uuid), 404)

class GetPhotoThumbnail(Resource):

    @cacheresponse
    def get(self):
        img_data = None
        user_name = session["user_id"]
        img_uuid = request.args.get('img')
        if img_uuid is None:
            return make_response("Invalid image request", 400)
        img_data = imgCache[0].lookup(user_name, img_uuid)
        if not img_data:
            print('image uuid {} not present in cache'.format(img_uuid))
            #checked if image with thumbail size is processed
            img_data = GetThumbnailImage(img_uuid)
            if not img_data:
                img_data = ProcessImageThumbnail(GetPath(img_uuid))
            if img_data:
                imgCache[0].insert(user_name, img_uuid, img_data)
                if user_name in u_session:
                    prefetch_ctx = u_session[user_name].get("current_album")
                    if prefetch_ctx:
                        threading.Thread(target=AutoLoadAlbum, args=(
                            imgCache, user_name, prefetch_ctx, 10), daemon=True).start()
        else:
            print('image uuid {} present in cache'.format(img_uuid))

        if img_data:
            response = make_response(img_data)
            response.headers.set('Content-Type', 'image/jpg')
            imgCache[0].stats()
            return response
        else:
            return make_response("image not found {}".format(img_uuid), 404)

class ListPhotos(Resource):

    def get(self):
        img_list_string = json.dumps(LookupPhotos(session.get("user_id")))
        # print 'json {}'.format(img_list_string)
        response = make_response(img_list_string)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.set('Content-Type', 'application/json')
        return response


class ListLikePhotos(Resource):

    def get(self):
        img_list_string = json.dumps(
            LookupPhotos(session.get("user_id"), like=True))
        # print 'json {}'.format(img_list_string)
        response = make_response(img_list_string)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.set('Content-Type', 'application/json')
        return response


class ListGPhotos(Resource):

    def get(self):
        l = []
        w_arr = request.args.getlist("width")
        h_arr = request.args.getlist("height")
        for w, h in zip(w_arr, h_arr):
            l.append((w, h))
        # print "cookie", request.cookies.get('user_id')
        #standard_sizes = set([ ("3024", "4032")])
        result = FilterPhotosPotraitStyle(
            session.get("user_id"), 0, 3000, set(l), "Google")
        img_list_string = json.dumps(result)
        response = make_response(img_list_string)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.set('Content-Type', 'application/json')
        return response


class ListObjectPhotos(Resource):

    def get(self):
        l = []
        w_arr = request.args.getlist("width")
        h_arr = request.args.getlist("height")
        for w, h in zip(w_arr, h_arr):
            l.append((w, h))
        result = FilterLabeledPhotosPotraitStyle(
            session.get("user_id"), "person", set(l), skip=True)
        img_list_string = json.dumps(result)
        response = make_response(img_list_string)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.set('Content-Type', 'application/json')
        return response


class ViewPhotos(Resource):

    def get(self):
        with open('api/templates/view_tile.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class EditPhotos(Resource):

    def get(self):
        img_album = urllib.parse.unquote(request.args.get('img'))
        with open('api/templates/edit_photo.html', 'r') as fp:
            data = fp.read()
            data = data.replace(
                "ca509b27-cd33-45ab-9d71-6e1e2df48b09", str(img_album))
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class ViewPhotosAuto(Resource):

    def get(self):
        with open('api/templates/slide_view.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class ViewGPhotosAuto(Resource):

    def get(self):
        # with open('api/templates/gphotos_slide_view_grid2.html', 'r') as fp:
        with open('api/templates/gphotos_slide_view_grid.html', 'r') as fp:
            # with open('api/templates/gphotos_slide_view.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class ViewLikedPhotos(Resource):

    def get(self):
        with open('api/templates/view_like.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class ViewLabeledPhotosAuto(Resource):

    def get(self):
        with open('api/templates/objects_slide_view.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class UploadPhotos(Resource):

    def get(self):
        with open('api/templates/upload_album.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

    def post(self):
        # print type(request.files['file'])
        InsertPhoto(session.get("user_id"),
                    request.files['file'].filename,
                    request.files['file'].read(),
                    request.form["tag"])
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        # traceback.print_stack()
        return response


class SearchPhotos(Resource):

    def get(self):
        with open('api/templates/search_photos.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

    def post(self):
        print(request.form['from_year'])
        print(request.form['to_year'])
        print(request.form['album'])
        result = FilterPhotos(session.get("user_id"),
                              request.form['from_year'], request.form['to_year'], request.form['album'])
        result = json.dumps(result)
        #print (result)
        response = make_response(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class GetMyAlbums(Resource):

    @checklogin
    def post(self):
        result = GetAlbumViewItems(session.get("user_id"))
        result = json.dumps(result)
        # print result
        response = make_response(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


def GetImgUUIDList(album_photos):
    result = list()
    for entry in album_photos:
        result.append(entry['value']['uuid'])
    return result


class AlbumPrefetchContext(object):

    def __init__(self, name, itemList):
        self.index = 0
        self.album = name
        self.list = itemList
        self.progress = False

    def next(self):
        pos = self.index
        self.index = (self.index + 1) % len(self.list)
        return pos

    def size(self):
        return len(self.list)

    def name(self):
        return self.album

    def at(self, index):
        return self.list[index]

    def progress(self):
        return self.progress

def AutoLoadAlbum(imgCache, user_name, prefetch_ctx, prefetch_count=10):
    with prefetchMutex:
        print('Autoloading Album...')
        if not user_name:
            print ('session user name not set')
            return
        if not prefetch_ctx:
            print("album prefetch context not set in session cookie")
            return
        prefetch_ctx = jsonpickle.decode(prefetch_ctx)
        if prefetch_ctx is True:
            print("album prefetch already in progress")
            return
        prefetch_ctx.progress = True
        u_session[user_name]["current_album"] = jsonpickle.encode(prefetch_ctx)
        # in case album url remains cached client side
        if prefetch_ctx.size() == 0:
            prefetch_ctx.index = 0
            result = GetAlbumPhotos(user_name, prefetch_ctx.name())
            prefetch_ctx.list = GetImgUUIDList(result)

        print('prefetching album images :{}'.format(prefetch_ctx.size()))
        for i in range(prefetch_count):
            index = prefetch_ctx.next()
            img_uuid = prefetch_ctx.at(index)
            img_data = imgCache[0].lookup(user_name, img_uuid)
            if not img_data:
                print('prefetching image :{} index :{}'.format(img_uuid, index))
                img_data = ProcessImageThumbnail(GetPath(img_uuid), http=False)
                if img_data:
                    imgCache[0].insert(user_name, img_uuid, img_data)
            else:
                print('image already prefetched :{}'.format(img_uuid))
        prefetch_ctx.progress = False
        u_session[user_name]["current_album"] = jsonpickle.encode(prefetch_ctx)
        print('prefetching album completed')

class GetMyAlbum(Resource):

    def get(self):
        img_album = urllib.parse.unquote(request.args.get('img'))
        prefetch_ctx = AlbumPrefetchContext(img_album, list())
        user_name = session.get("user_id")
        u_session[user_name]["current_album"] = jsonpickle.encode(prefetch_ctx)
        with open('api/templates/show_albums_tile.html', 'r') as fp:
            data = fp.read()
            data = data.replace("album_value", str(img_album))
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

    def post(self):
        user_name = session.get("user_id")
        img_album = request.data
        result = GetAlbumPhotos(user_name, img_album)
        prefetch_ctx = AlbumPrefetchContext(img_album, GetImgUUIDList(result))
        u_session[user_name]["current_album"] = jsonpickle.encode(prefetch_ctx)
        prefetch_ctx = u_session[user_name].get("current_album")
        threading.Thread(target=AutoLoadAlbum, args=(
            imgCache, user_name, prefetch_ctx, 30), daemon=True).start()
        result_str = json.dumps(result)
        # print img_album, result
        response = make_response(result_str)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class AutoCompleteAlbumSearch(Resource):

    def post(self):
        user_name = session.get("user_id")
        if request.data is None:
             return make_response("Invalid Search Request", 400)
        text = request.data.decode("utf-8")
        result = AutoCompleteAlbum(user_name, text)
        result = json.dumps(result)
        response = make_response(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class LikePhoto(Resource):

    def post(self):
        MarkPhotoFav(request.data)
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class UnlikePhoto(Resource):

    def post(self):
        MarkPhotoFav(request.data, False)
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class RemovePhoto(Resource):

    def post(self):
        print(request.data)
        DeletePhoto(request.data)
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class UpdatePhoto(Resource):

    def post(self):
        print(request.data)
        data = json.loads(request.data)
        UpdatePhotoTag(data['value']['uuid'], data['value']['tags'])
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class DownloadPhoto(Resource):

    def get(self):
        img_uuid = request.args.get("img")
        img_file = '{}.JPG'.format(img_uuid)
        return send_from_directory(GetImageDir(), img_file, as_attachment=True)


class Login(Resource):

    def get(self):
        return make_response(render_template('login.html'))

    def post(self):
        if LookupUser(request.form.get('email'), request.form.get('password')):
            session["user_id"] = request.form.get('email')
            u_session[session["user_id"]] = dict()
            res = make_response(flask.redirect(url_for('api.home')))
            #res.set_cookie('user_id', str(uuid.uuid4()), max_age=60*60*24*365*2)
            #print (session["user_id"])
            return res
        else:
            return make_response(flask.redirect(url_for('api.signup')))


class LogOut(Resource):

    def get(self):
        user_name = session.get("user_id")
        if user_name in u_session:
            del u_session[user_name]
        session.pop(user_name, None)
        return make_response(render_template('login.html'))

class SetWallPhoto(Resource):

    def post(self):
        if DBSetUserImage(session["user_id"], request.data):
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        else:
            return make_response(jsonify({"message": "invalid user id", "data": ""}), 403)


class Signup(Resource):

    def get(self):
        return make_response(render_template('signup.html'))

    def post(self):
        AddUser(request.form.get('email'), request.form.get('password'))
        return make_response(flask.redirect(url_for('api.login')))


class AuthorizeImportPhotos(Resource):

    def get(self):
        with open('api/templates/gphotos_import.html', 'r') as fp:
            data = fp.read()
            data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
            response = make_response(data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response


class ImportPhotos(Resource):

    def get(self):
        # This should publish an event. The photo-syncer
        # will trigger download based on the event and
        # send an email to the user based on profile-settings.
        # User can then upload the downloaded photos in the usual way

        #msg = Message('SaptarshiApp', sender = app_mail_sender, recipients = [ app_main_receiver ])
        #msg.body = "An import task has been launched"
        # app_mail.send(msg)
        return flask.redirect(GetPhotoOAuthURL(session.get("user_id")))

    def post(self):
        refresh_token = request.data  # request.form.get("token")
        print('request.data :' + refresh_token.decode("utf-8"))
        threading.Thread(target=SyncPhotos, args=(
            session.get("user_id"), refresh_token.decode("utf-8")), daemon=True).start()
        #SyncPhotos(session.get("user_id"), refresh_token.decode("utf-8"))
        return make_response()


class ImportPhotosStatus(Resource):

    def get(self):
        # This should publish an event. The photo-syncer
        # will trigger download based on the event and
        # send an email to the user based on profile-settings.
        # User can then upload the downloaded photos in the usual way

        #msg = Message('SaptarshiApp', sender = app_mail_sender, recipients = [ app_main_receiver ])
        #msg.body = "An import task has been launched"
        # app_mail.send(msg)
        def generate(user_id):
            curr = 0
            prev = 0
            pbar = tqdm(total=100)
            while curr <= 100:
                yield "data:" + str(curr) + "\n\n"
                curr = SyncPhotosStatus(user_id)
                pbar.update(curr - prev)
                prev = curr
                time.sleep(1)
        return Response(generate(session.get("user_id")), mimetype='text/event-stream')


class PhotoLabel(Resource):

    def get(self):
        img_uuid = request.args.get('img')
        result = DBGetPhotoLabel(img_uuid)
        result = json.dumps(result)
        response = make_response(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    def post(self):
        print(request.values.get('img'), request.values.get('labels'))
        DBAddPhotoLabel(request.values.get('img'),
                        request.values.get('labels'))
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response


class PhotoNotLabel(Resource):

    def get(self):
        result = DBGetUnLabeledPhotos()
        result = json.dumps(result)
        response = make_response(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

# 405 (METHOD NOT ALLOWED)

class PhotoGrayScale(Resource):

    def get(self):
        return Response()

    def post(self):
        print(request.data)
        img_uuid = request.data.decode("utf-8")
        print(img_uuid)
        data = ProcessImageGrayScale(GetPath(img_uuid))
        response = make_response(data)
        response.headers.set('Content-Type', 'image/jpg')
        return response

class PhotoSharpenFilter(Resource):

    def get(self):
        return Response()

    def post(self):
        print(request.data)
        img_uuid = request.data.decode("utf-8")
        print(img_uuid)
        data = ProcessImageSharpenFilter(GetPath(img_uuid))
        response = make_response(data)
        response.headers.set('Content-Type', 'image/jpg')
        return response

class PhotoSepiaFilter(Resource):

    def get(self):
        return Response()

    def post(self):
        print(request.data)
        img_uuid = request.data.decode("utf-8")
        print(img_uuid)
        data = ProcessImageSepiaFilter(GetPath(img_uuid))
        response = make_response(data)
        response.headers.set('Content-Type', 'image/jpg')
        return response

class PhotoMemory(Resource):

    def get(self):
        found = False
        user_name = session.get("user_id")
        dt = datetime.datetime.today().timetuple()
        result = LookupPhotosByDate(user_name, dt.tm_year-1, dt.tm_mon, dt.tm_mday)
        if len(result) > 0:
            found = True
        else:
            result = LookupPhotosByDate(user_name, dt.tm_year-1, dt.tm_mon)

        if len(result) > 0:
            with open('api/templates/memory.html', 'r') as fp:
                random.seed(datetime.datetime.now())
                p = random.randint(0, len(result) - 1)
                data = fp.read()
                data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                data = data.replace("ca509b27-cd33-45ab-9d71-6e1e2df48b09", result[p]['value']['uuid'])
                data = data.replace("album_value", result[p]['value']['tags'])
                if found:
                    data = data.replace("Day", "Day ({})".format(result[p]['value']['date']))
                else:
                    data = data.replace("Day", "Month ({})".format(result[p]['value']['date']))
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response
        else:
            return make_response() #render_template('nomemory.html'))

def page_not_found(e):
    return flask.redirect('http://192.168.160.199:4040/api/v1/favicon.apple')


app = Flask(__name__, template_folder='templates')
#app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = app_mail_sender
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)
api.add_resource(Home, '/')
api.add_resource(Favicon, '/favicon.ico')
api.add_resource(FaviconApple, '/favicon.apple')
api.add_resource(ViewPhotos, '/view')
api.add_resource(ViewPhotosAuto, '/auto')
api.add_resource(ViewGPhotosAuto, '/gauto')
api.add_resource(ViewLikedPhotos, '/viewlike')
api.add_resource(ViewLabeledPhotosAuto, '/viewobjects')
api.add_resource(EditPhotos, '/edit')
api.add_resource(UploadPhotos, '/upload')
api.add_resource(RemovePhoto, '/deletephoto')
api.add_resource(WelcomeBanner, '/welcome')
api.add_resource(GetPhotoRaw, '/rawphoto')
api.add_resource(GetPhotoScaled, '/scaledphoto')
api.add_resource(GetPhotoThumbnail, '/thumbnailphoto')
api.add_resource(ListPhotos, '/listphotos')
api.add_resource(ListLikePhotos, '/listlikephotos')
api.add_resource(ListGPhotos, '/listgphotos')
api.add_resource(ListObjectPhotos, '/listlabeledphotos')
api.add_resource(SearchPhotos, '/search')
api.add_resource(GetMyAlbums, '/myalbums')
api.add_resource(GetMyAlbum, '/myalbum')
api.add_resource(AutoCompleteAlbumSearch, '/autocomplete')
api.add_resource(LikePhoto, '/likephoto')
api.add_resource(UnlikePhoto, '/unlikephoto')
api.add_resource(UpdatePhoto, '/updatephoto')
api.add_resource(DownloadPhoto, '/downloadphoto')
api.add_resource(Login, '/login')
api.add_resource(Signup, '/signup')
api.add_resource(LogOut, '/logout')
api.add_resource(AuthorizeImportPhotos, '/authorizeimport')
api.add_resource(ImportPhotos, '/import')
api.add_resource(ImportPhotosStatus, '/importstatus')
api.add_resource(PhotoLabel, '/label')
api.add_resource(PhotoNotLabel, '/nolabel')
api.add_resource(SetWallPhoto, '/wallphoto')
api.add_resource(PhotoGrayScale, '/grayscale')
api.add_resource(PhotoSharpenFilter, '/sharpenfilter')
api.add_resource(PhotoSepiaFilter, '/sepiafilter')
api.add_resource(PhotoMemory, '/memory')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.register_error_handler(404, page_not_found)
app.config.from_object('config')
app.secret_key = "MY SECRET KEY"
# dashboard.bind(app)
app_mail = Mail(app)

db = SQLAlchemy(app)


class Request(db.Model):
    __tablename__ = "request"
    index = db.Column(db.Integer, primary_key=True, autoincrement=True)
    response_time = db.Column(db.Float)
    date = db.Column(db.DateTime)
    method = db.Column(db.String)
    size = db.Column(db.Integer)
    status_code = db.Column(db.Integer)
    path = db.Column(db.String)
    user_agent = db.Column(db.String)
    remote_address = db.Column(db.String)
    exception = db.Column(db.String)
    referrer = db.Column(db.String)
    browser = db.Column(db.String)
    platform = db.Column(db.String)
    mimetype = db.Column(db.String)


db.create_all()
db.session.commit()
statistics = Statistics(app, db, Request)
InitPhotosDb()
# initialize local image cache
imgCache = dict()
imgCache[0] = imgcache.GlobalLRUCacheImg(100)
