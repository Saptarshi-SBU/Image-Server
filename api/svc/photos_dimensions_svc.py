#
# python -m api.svc.photos_dimensions.py
#
import os
import time
import threading
from ..db.DB import DBManager, PhotoModel, PhotoSizeModel
from ..db.dbconf import *
from ..db.query import DBGetPhotoDimensions, DBAddPhotoDimensions, FilterPhotos
from ..image_processing.filtering import GetImageDimensions

def ScanAddPhotosDimension():
    count = 0
    photos = []
    result = FilterPhotos(0, 3000, None)
    for photo in result:
	count = count + 1
        w, h = DBGetPhotoDimensions(photo["value"]["uuid"])
        if w is None:
    	    with DBManager() as db:
        	_dbSession = db.getSession()
                result2 = _dbSession.query(PhotoModel).filter \
			(PhotoModel.UUID==photo["value"]["uuid"]).first()
	        imgPath = '{}/{}.JPG'.format(result2.NameSpace, result2.UUID)
	    w, h = GetImageDimensions(imgPath)
	    assert w, "invalid image dimensions:{}".format(imgPath)
            DBAddPhotoDimensions(result2.UUID, w, h)
	    print ('{} saving dimensions :{} weight :{} height :{}'.format(count, photo, w, h))

if __name__ == "__main__" :
    ScanAddPhotosDimension()
