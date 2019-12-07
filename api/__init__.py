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
from functools import wraps, update_wrapper
from DB import InitPhotosDb
from imgApp import InsertPhoto, LookupPhotos, FilterPhotos, FilterPhotoAlbums, DeletePhoto, MarkPhotoFav, UpdatePhotoTag, GetPath
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, make_response

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

class Home(Resource):

    def get(self):
        return send_file('{}'.format('main.html'))
        #return {"message": "Welcome to Sen Family's Image Server"}

class WelcomeBanner(Resource):

    def get(self):
        return send_file('{}'.format('welcome.jpg'), mimetype='image/jpg', cache_timeout=1)

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
            img_data = cv2.imread(GetPath(img_uuid), cv2.IMREAD_COLOR)
            img_scal = cv2.resize(img_data, dsize=(600, 600), interpolation=cv2.INTER_CUBIC)
            _, img_encoded = cv2.imencode('.jpg', img_scal) # encode converts to bytes
            response = make_response(img_encoded.tostring())
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
            html = "view.html"
            return send_file('{}'.format(html))

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
            html = "upload_form.html"
            return send_file('{}'.format(html))

    def post(self):
            #print type(request.files['file'])
            InsertPhoto(request.files['file'].filename, \
                        request.files['file'].read(), \
                        request.form["tag"])
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class SearchPhotos(Resource):

    def get(self):
            html = "filter-form.html"
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

class SearchAlbums(Resource):

    def post(self):
            result = FilterPhotoAlbums()
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

app = Flask(__name__)
api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)
api.add_resource(Home, '/')
api.add_resource(ViewPhotos, '/view')
api.add_resource(ViewPhotosAuto, '/auto')
api.add_resource(ViewLikedPhotos, '/viewlike')
api.add_resource(UploadPhotos, '/upload')
api.add_resource(RemovePhoto, '/deletephoto')
api.add_resource(WelcomeBanner, '/welcome')
api.add_resource(GetPhotoRaw, '/rawphoto')
api.add_resource(GetPhotoScaled, '/scaledphoto')
api.add_resource(ListPhotos, '/listphotos')
api.add_resource(ListLikePhotos, '/listlikephotos')
api.add_resource(SearchPhotos, '/search')
api.add_resource(SearchAlbums, '/searchalbums')
api.add_resource(LikePhoto, '/likephoto')
api.add_resource(UnlikePhoto, '/unlikephoto')
api.add_resource(UpdatePhoto, '/updatephoto')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.config.from_object('config')
InitPhotosDb()
