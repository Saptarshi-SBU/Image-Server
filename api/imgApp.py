import os
import uuid
import datetime
import exifread
import ConfigParser
from sqlalchemy import and_
from checksum import comp_checksum
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

def GetDateTimeLocal():
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    day = now.day
    return [year, month, day]

def GetPath(img_uuid):
    img_dir = GetImageDir(CONFIG_FILE)
    imgPath = '{}/{}.JPG'.format(img_dir, img_uuid)
    return imgPath

def LookupPhotos(like=False):
    photoPaths = []
    with DBManager() as db: 
        _dbSession = db.getSession()
        if like:
            result = _dbSession.query(PhotoModel).filter((PhotoModel.Reserved == "Like")).order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        )
        else:               
            result = _dbSession.query(PhotoModel).order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        )
        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}'.format(photo.Day, photo.Month,
            photo.Year), "name" : photo.Name }})
    return photoPaths

def FilterPhotos(start_year, to_year, album):    
    photoPaths = []
    result = []
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

def TestDuplicate(sourceBlob, digest):
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.Digest == digest)).all()
        for photo in result:
            imgPath = '{}/{}.JPG'.format(photo.NameSpace, photo.UUID)
            with open(imgPath) as fp:
                fileBlob = fp.read()
                if bytearray(sourceBlob) == bytearray(fileBlob):
                    return True
    return False   

def InsertPhoto(filename, fileBlob, description):    
    img_dir = GetImageDir(CONFIG_FILE)
    img_uuid = uuid.uuid4()
    digest = comp_checksum(fileBlob)

    if TestDuplicate(fileBlob, digest):
        print ("Detected duplicate entry")
        return;

    imgPath = '{}/{}.JPG'.format(img_dir, img_uuid)
    fd = os.open(imgPath, os.O_RDWR | os.O_CREAT, 0644)
    os.write(fd, fileBlob)
    os.close(fd)    
    try:
        [year, month, day] = GetDateTime(imgPath)
    except:
        [year, month, day] = GetDateTimeLocal()

    with DBManager() as db: 
        _dbSession = db.getSession()
        DBAddPhoto(_dbSession, img_uuid, filename, digest, \
            year, month, day, img_dir, " ", description)
        _dbSession.commit()

def MarkPhotoFav(img_uuid):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            i.Reserved = "Like"
        _dbSession.commit()
        print ("Marked Like photo :", img_uuid)

def DeletePhoto(img_uuid):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            _dbSession.delete(i)
        _dbSession.commit()
