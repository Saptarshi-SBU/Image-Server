import os
import uuid
import datetime
import exifread
import ConfigParser
from sqlalchemy import and_
from DB import DBManager, DBAddPhoto, InitPhotosDb, DumpTables, PhotoModel

CONFIG_FILE="/etc/api.cfg"

def GetImageDir(cfg_file):
    config = ConfigParser.ConfigParser()
    config.read(cfg_file)
    return config.get("dir", "path")

def GetDateTime(imagePath):
    fp = open(imagePath, 'rb')
    tags = exifread.process_file(fp)
    fp.close()
    dateinfo = str(tags['EXIF DateTimeOriginal'])
    dateinfo = dateinfo.split(' ')
    yymmdd = dateinfo[0].replace(':', ' ')
    return [int(s) for s in yymmdd.split(' ')]

def GetPath(img_uuid):
    img_dir = GetImageDir(CONFIG_FILE)
    imgPath = '{}/{}.JPG'.format(img_dir, img_uuid)
    return imgPath

def LookupPhotos():
    photoPaths = []
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = DumpTables(_dbSession)
        for photo in result:
            photoPaths.append(photo.UUID)
    return photoPaths

def FilterPhotos(start_year, to_year, album):    
    photoPaths = []
    with DBManager() as db: 
        _dbSession = db.getSession()
        if album:
            result = _dbSession.query(PhotoModel).filter((PhotoModel.Description == album)).all()

        if len(result) == 0:
            result = _dbSession.query(PhotoModel).filter(and_(PhotoModel.Year >= int(start_year),
                         PhotoModel.Year <= int(to_year))).all()
        for photo in result:
            photoPaths.append(photo.UUID)
    return photoPaths

def InsertPhoto(filename, fileBlob, description):    
    img_dir = GetImageDir(CONFIG_FILE)
    img_uuid = uuid.uuid4()
    imgPath = '{}/{}.JPG'.format(img_dir, img_uuid)
    fd = os.open(imgPath, os.O_RDWR | os.O_CREAT, 0644)
    os.write(fd, fileBlob)
    [year, month, day] = GetDateTime(imgPath)
    with DBManager() as db: 
        _dbSession = db.getSession()
        DBAddPhoto(_dbSession, img_uuid, filename, \
            year, month, day, img_dir, " ", description)
        _dbSession.commit()
