'''
    python module for image hosting
'''
import os
import cv2
import json
import uuid
import time
from DB import InitPhotosDb
from imgApp import InsertPhoto, LookupPhotos
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, make_response

class Home(Resource):

    def get(self):
        return {"message": "Welcome to Sen Family's Image Server"}

class WelcomeBanner(Resource):

    def get(self):
        return send_file('{}'.format('welcome.jpg'), mimetype='image/jpg')

class GetPhotoRaw(Resource):

    def get(self):
        img = request.args.get('img')
        if img is None:
            return abort(400)
        else:
            return send_file('{}'.format(img), mimetype='image/jpg')

class GetPhotoScaled(Resource):

    def get(self):
        img = request.args.get('img')
        if img is None:
            return abort(400)
        else:
            img_data = cv2.imread('{}'.format(img), cv2.IMREAD_COLOR)
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

class ViewPhotos(Resource):

    def get(self):
            html = "view.html"
            return send_file('{}'.format(html))

class UploadPhotos(Resource):

    def get(self):
            html = "form.html"
            return send_file('{}'.format(html))

    def post(self):
            #print type(request.files['file'])
            InsertPhoto(request.files['file'].filename, \
                        request.files['file'].read(), \
                        request.form["tag"])
            response = make_response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

app = Flask(__name__)
api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)
api.add_resource(Home, '/')
api.add_resource(ViewPhotos, '/view')
api.add_resource(UploadPhotos, '/upload')
api.add_resource(WelcomeBanner, '/welcome')
api.add_resource(GetPhotoRaw, '/rawphoto')
api.add_resource(GetPhotoScaled, '/scaledphoto')
api.add_resource(ListPhotos, '/listphotos')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.config.from_object('config')
InitPhotosDb()
