'''
    python module for image hosting
'''
import os
import cv2
import json
import uuid
import time
import ConfigParser
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, make_response

CONFIG_FILE="/etc/api.cfg"

def GetImageDir(cfg_file):
    config = ConfigParser.ConfigParser()
    config.read(cfg_file)
    return config.get("dir", "path")

class Home(Resource):

    def get(self):
        return {"message": "Welcome to Sen Family's Image Server"}

class ImageRaw(Resource):

    def get(self):
        img = request.args.get('img')
        if img is None:
            return abort(400)
        else:
            img_dir = GetImageDir(CONFIG_FILE)
            return send_file('{}/{}'.format(img_dir, img), mimetype='image/jpg')

class ImageScaled(Resource):

    def get(self):
        img = request.args.get('img')
        if img is None:
            return abort(400)
        else:
            img_dir = GetImageDir(CONFIG_FILE)
            img_data = cv2.imread('{}/{}'.format(img_dir, img), cv2.IMREAD_COLOR)
            img_scal = cv2.resize(img_data, dsize=(600, 600), interpolation=cv2.INTER_CUBIC)
            # encode converts to bytes
            _, img_encoded = cv2.imencode('.jpg', img_scal)
            response = make_response(img_encoded.tostring())
            response.headers.set('Content-Type', 'image/jpg')
            return response

class GetAllImages(Resource):

    def get(self):
            img_dir = GetImageDir(CONFIG_FILE)
            img_list = [f for f in os.listdir(img_dir)]
            img_list_string = json.dumps(img_list)
            #print 'json {}'.format(img_list_string)
            response = make_response(img_list_string)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.set('Content-Type', 'application/json')
            return response

class GetSourceHtml(Resource):

    def get(self):
            html = "sample.html"
            return send_file('{}'.format(html))

app = Flask(__name__)
api_blueprint = Blueprint('api', __name__)
api = Api(api_blueprint)
api.add_resource(Home, '/')
api.add_resource(GetSourceHtml, '/index')
api.add_resource(ImageRaw, '/rpics')
api.add_resource(ImageScaled, '/spics')
api.add_resource(GetAllImages, '/allpics')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.config.from_object('config')
