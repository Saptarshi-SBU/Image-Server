'''
    python module for image hosting
'''
import os
import cv2
import json
import gc
import objgraph
import uuid
import time
import datetime
import urllib
from functools import wraps, update_wrapper
from DB import InitPhotosDb
from imgApp import InsertPhoto, LookupPhotos, FilterPhotos, FilterPhotoAlbums, DeletePhoto, MarkPhotoFav, \
    UpdatePhotoTag, AutoCompleteAlbum, GetPath, GetAlbumPhotos, GetImageDir
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, make_response, send_from_directory
import traceback

def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
        
    return update_wrapper(no_cache, view)

def ProcessImage(filepath, scale_percent=25):
        img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
        width  = int(img_data.shape[1] * scale_percent / 100)
        height = int(img_data.shape[0] * scale_percent / 100)
        dim = (width, height)
        img_scal = cv2.resize(img_data, dim, interpolation=cv2.INTER_LINEAR)
        _, img_encoded = cv2.imencode('.jpg', img_scal) # encode converts to bytes
        return img_encoded.tostring()

class Home(Resource):

    def get(self):
        return send_file('{}'.format('main.html'))
        #return {"message": "Welcome to Sen Family's Image Server"}

class WelcomeBanner(Resource):

    def get(self):
        response = make_response(ProcessImage('api/welcome_2.0.jpg'))
        response.headers.set('Content-Type', 'image/jpg')
        return response

class GetPhotoRaw(Resource):

    #@nocache
    def get(self):
        img_uuid = request.args.get('img')
        if img_uuid is None:
            return abort(400)
        else:
            #objgraph.show_most_common_types()
            return send_file(GetPath(img_uuid), mimetype='image/jpg')

class GetPhotoScaled(Resource):

    def get(self):
        img_uuid = request.args.get('img')
        if img_uuid is None:
            return abort(400)
        else:
            response = make_response(ProcessImage(GetPath(img_uuid)))
            response.headers.set('Content-Type', 'image/jpg')
            return response

class ListPhotos(Resource):

    def get(self):
            img_list_string = json.dumps(LookupPhotos())
            #print 'json {}'.format(img_list_string)
            response = make_response(img_list_string)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.set('Content-Type', 'application/json')
            return response

class ListLikePhotos(Resource):

    def get(self):
            img_list_string = json.dumps(LookupPhotos(like=True))
            #print 'json {}'.format(img_list_string)
            response = make_response(img_list_string)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.set('Content-Type', 'application/json')
            return response

class ViewPhotos(Resource):

    def get(self):
            return send_file("view_tile.html")
            #return send_file("show_albums.html")

class EditPhotos(Resource):

    def get(self):
            img_album = urllib.unquote(request.args.get('img'))
            with open('api/edit_photo.html', 'r') as fp:
                data = fp.read()
                data = data.replace("ca509b27-cd33-45ab-9d71-6e1e2df48b09", str(img_album))
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

class ViewPhotosAuto(Resource):

    def get(self):
            html = "slide_view.html"
            return send_file('{}'.format(html))

class ViewLikedPhotos(Resource):

    def get(self):
            html = "view_like.html"
            return send_file('{}'.format(html))

class UploadPhotos(Resource):

    def get(self):
            html = "upload_album.html"
            return send_file('{}'.format(html))

    def post(self):
            #print type(request.files['file'])
            InsertPhoto(request.files['file'].filename, \
                        request.files['file'].read(), \
                        request.form["tag"])
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            #traceback.print_stack()
            return response

class SearchPhotos(Resource):

    def get(self):
            html = "search_photos.html"
            return send_file('{}'.format(html))

    def post(self):
            print request.form['from_year']
            print request.form['to_year']
            print request.form['album']
            result = FilterPhotos(request.form['from_year'], request.form['to_year'], request.form['album'])
            result = json.dumps(result)
            response = make_response(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class GetMyAlbums(Resource):

    def post(self):
            result = FilterPhotoAlbums()
            result = json.dumps(result)
            response = make_response(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class GetMyAlbum(Resource):

    def get(self):
            img_album = urllib.unquote(request.args.get('img'))
            with open('api/show_album.html', 'r') as fp:
                data = fp.read()
                data = data.replace("album_value", str(img_album))
                response = make_response(data)
                #print data
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

    def post(self):
            img_album = request.data
            result = GetAlbumPhotos(img_album)
            result = json.dumps(result)
            response = make_response(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class AutoCompleteAlbumSearch(Resource):

    def post(self):
            result = AutoCompleteAlbum(request.data)
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
            print request.data
            DeletePhoto(request.data)
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
            
class UpdatePhoto(Resource):

    def post(self):
            print request.data
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

app = Flask(__name__)
#app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)
api.add_resource(Home, '/')
api.add_resource(ViewPhotos, '/view')
api.add_resource(ViewPhotosAuto, '/auto')
api.add_resource(ViewLikedPhotos, '/viewlike')
api.add_resource(EditPhotos, '/edit')
api.add_resource(UploadPhotos, '/upload')
api.add_resource(RemovePhoto, '/deletephoto')
api.add_resource(WelcomeBanner, '/welcome')
api.add_resource(GetPhotoRaw, '/rawphoto')
api.add_resource(GetPhotoScaled, '/scaledphoto')
api.add_resource(ListPhotos, '/listphotos')
api.add_resource(ListLikePhotos, '/listlikephotos')
api.add_resource(SearchPhotos, '/search')
api.add_resource(GetMyAlbums, '/myalbums')
api.add_resource(GetMyAlbum, '/myalbum')
api.add_resource(AutoCompleteAlbumSearch, '/autocomplete')
api.add_resource(LikePhoto, '/likephoto')
api.add_resource(UnlikePhoto, '/unlikephoto')
api.add_resource(UpdatePhoto, '/updatephoto')
api.add_resource(DownloadPhoto, '/downloadphoto')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.config.from_object('config')
InitPhotosDb()
