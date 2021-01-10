'''
    python module for image hosting
'''
import os
import json
import time
import gc
import objgraph
import uuid
import time
import datetime
import urllib
import traceback
import flask
from functools import wraps, update_wrapper
from flask_restful import Resource, Api, reqparse
from flask import Flask, Blueprint, send_file, request, make_response, send_from_directory, render_template, url_for
from db.DB import InitPhotosDb
from db.query import InsertPhoto, LookupPhotos, FilterPhotos, FilterPhotoAlbums, DeletePhoto, MarkPhotoFav, \
    UpdatePhotoTag, LookupUser, AddUser, AutoCompleteAlbum, GetPath, GetAlbumPhotos, GetImageDir, GetHostIP, GetScaledImage
from image_processing.filtering import ProcessImage
#import flask_monitoringdashboard as dashboard
from flask_sqlalchemy import SQLAlchemy
from flask_statistics import Statistics
from flask_mail import Mail, Message

#configured via api.cfg
HOST_ADDRESS = GetHostIP()

#mail object
app_mail = None
app_mail_sender = "saptarshi.mrg@gmail.com"
app_main_receiver = "saptarshi.mrg@gmail.com"

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
        #time.sleep(1)
	with open('api/templates/main.html', 'r') as fp:
                data = fp.read()
		data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response
        #return send_file('{}'.format('main.html'))
        #return {"message": "Welcome to Sen Family's Image Server"}

class WelcomeBanner(Resource):

    def get(self):
        response = make_response(ProcessImage('api/images/welcome_2.0.jpg', scale_percent=20))
        response.headers.set('Content-Type', 'image/jpg')
        return response

class Favicon(Resource):

    def get(self):
        return send_file('{}'.format('images/favicon.ico'))

class FaviconApple(Resource):

    def get(self):
        return send_file('{}'.format('images/apple-touch-icon-152x152.png'))

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
            scale_pc = request.args.get('scale')
            if False and scale_pc is None:
                response = make_response(ProcessImage(GetPath(img_uuid)))
            else:
		frame = GetScaledImage(img_uuid)
		if frame:
		    response = make_response(frame)
		else:
                    response = make_response(ProcessImage(GetPath(img_uuid), int(scale_pc)))
            response.headers.set('Content-Type', 'image/jpg')
            #response.headers.set('Content-Type', 'image/png')
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

class ListGPhotos(Resource):

    def get(self):
	    result = FilterPhotos(0, 3000, "Google")
            img_list_string = json.dumps(result)
            response = make_response(img_list_string)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.set('Content-Type', 'application/json')
            return response

class ViewPhotos(Resource):

    def get(self):
	    with open('api/templates/view_tile.html', 'r') as fp:
                data = fp.read()
		data= data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

class EditPhotos(Resource):

    def get(self):
            img_album = urllib.unquote(request.args.get('img'))
            with open('api/templates/edit_photo.html', 'r') as fp:
                data = fp.read()
                data = data.replace("ca509b27-cd33-45ab-9d71-6e1e2df48b09", str(img_album))
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
	    with open('api/templates/gphotos_slide_view.html', 'r') as fp:
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

class UploadPhotos(Resource):

    def get(self):
	    with open('api/templates/upload_album.html', 'r') as fp:
                data = fp.read()
		data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

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
	    with open('api/templates/search_photos.html', 'r') as fp:
                data = fp.read()
		data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                response = make_response(data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response

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
            #print result
            response = make_response(result)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

class GetMyAlbum(Resource):

    def get(self):
            img_album = urllib.unquote(request.args.get('img'))
            with open('api/templates/show_album.html', 'r') as fp:
                data = fp.read()
                data = data.replace("album_value", str(img_album))
		data = data.replace("$SERVER_HOST_IP", HOST_ADDRESS)
                response = make_response(data)
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

class Login(Resource):

    def get(self):
            return make_response(render_template('login.html'))

    def post(self):
	    if LookupUser(request.form.get('email'), request.form.get('password')):
	    	return make_response(flask.redirect(url_for('api.home')))
	    else:
	    	return make_response(flask.redirect(url_for('api.signup')))

class Signup(Resource):

    def get(self):
            return make_response(render_template('signup.html'))

    def post(self):
	    AddUser(request.form.get('email'), request.form.get('password'))
	    return make_response(flask.redirect(url_for('api.login')))

class ImportPhotos(Resource):

    def get(self):
            # This should publish an event. The photo-syncer
            # will trigger download based on the event and
            # send an email to the user based on profile-settings.
            # User can then upload the downloaded photos in the usual way
	    msg = Message('SaptarshiApp', sender = app_mail_sender, recipients = [ app_main_receiver ])
	    msg.body = "An import task has been launched"
	    app_mail.send(msg)
    	    return make_response()

def page_not_found(e):
  return flask.redirect('http://192.168.160.199:4040/api/v1/favicon.apple')

app = Flask(__name__,template_folder='templates')
#app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = app_mail_sender
app.config['MAIL_PASSWORD'] = 'Nitj@4031'
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
api.add_resource(EditPhotos, '/edit')
api.add_resource(UploadPhotos, '/upload')
api.add_resource(RemovePhoto, '/deletephoto')
api.add_resource(WelcomeBanner, '/welcome')
api.add_resource(GetPhotoRaw, '/rawphoto')
api.add_resource(GetPhotoScaled, '/scaledphoto')
api.add_resource(ListPhotos, '/listphotos')
api.add_resource(ListLikePhotos, '/listlikephotos')
api.add_resource(ListGPhotos, '/listgphotos')
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
api.add_resource(ImportPhotos, '/import')
app.register_blueprint(api_blueprint, url_prefix="/api/v1")
app.register_error_handler(404, page_not_found)
app.config.from_object('config')
#dashboard.bind(app)
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
