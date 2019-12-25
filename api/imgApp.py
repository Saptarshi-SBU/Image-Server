import os
import uuid
import random
import datetime
import exifread
import ConfigParser
from sqlalchemy import func
from sqlalchemy import and_
from checksum import comp_checksum
from DB import DBManager, DBAddPhoto, InitPhotosDb, DumpTables, PhotoModel
from auto_complete import AutoComplete

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

def SortbyDate(jsonData):
    year  = int(jsonData["value"]["year"])
    month = int(jsonData["value"]["month"])
    day   = int(jsonData["value"]["day"])
    dt = datetime.date(year=year, month=month, day=day)
    return dt

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
            photo.Year), "name" : photo.Name, "tags" : photo.Tags }})
    return photoPaths

def GetAlbumPhotos(album):
    photoPaths = []
    result = []

    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter(PhotoModel.Tags == album) \
                        .order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        )

        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}'.format(photo.Day, photo.Month, \
                photo.Year), "name" : photo.Name, "tags" : photo.Tags }})
            #photoPaths.append(photo.UUID)
        return photoPaths

def FilterPhotos(start_year, to_year, album=None):
    photoPaths = []
    result = []

    #check unicode
    if not start_year.isnumeric():
        start_year = 0

    if not to_year.isnumeric():
        to_year = 2050

    with DBManager() as db: 
        _dbSession = db.getSession()
        if album:
            search = "%{}%".format(album)
            result = _dbSession.query(PhotoModel).filter(PhotoModel.Tags.ilike(search)) \
                        .order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        )
            result = [ photo for photo in result if photo.Year >= int(start_year) and \
                photo.Year <= int(to_year) ]
        else:
            result = _dbSession.query(PhotoModel).filter(and_(PhotoModel.Year >= int(start_year),
                         PhotoModel.Year <= int(to_year))) \
                        .order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        )

        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}'.format(photo.Day, photo.Month, \
                photo.Year), "name" : photo.Name, "tags" : photo.Tags }})
            #photoPaths.append(photo.UUID)

    return photoPaths

def FilterPhotoAlbums():
    photoPaths = {}
    photoList = []
    result = []
    with DBManager() as db:
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        ).all()

    random.shuffle(result)

    #unique albums
    for photo in result:
        photoPaths[photo.Tags] = { \
                                    "value" : \
                                        { "uuid"  : photo.UUID, \
                                          "day"   : photo.Day, \
                                          "month" : photo.Month, \
                                          "year"  : photo.Year, \
                                          "name"  : photo.Name, \
                                          "tags"  : photo.Tags, \
                                          "count" : int(0) \
                                        } \
                                 }

    with DBManager() as db:
        _dbSession = db.getSession()
        for key in photoPaths:
            photoPaths[key]["value"]["count"] = _dbSession.query(PhotoModel).filter(PhotoModel.Tags == key).count()
            photoList.append(photoPaths[key])

    photoList.sort(key=SortbyDate, reverse=True)
    return photoList


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

def MarkPhotoFav(img_uuid, like=True):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            if like:
                i.Reserved = "Like"
            else:
                i.Reserved = "Unlike"
            _dbSession.commit()
        print ("Marked Like photo :", img_uuid, like)

def DeletePhoto(img_uuid):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            _dbSession.delete(i)
        _dbSession.commit()

def UpdatePhotoTag(img_uuid, tag):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            i.Tags = tag
        _dbSession.commit()
        print ('Updated {} {}'.format(img_uuid, tag))   

def AutoCompleteAlbum(text):
    tl = []
    with DBManager() as db:
        _dbSession = db.getSession()
        for value in _dbSession.query(PhotoModel.Tags).distinct():
            tl.append(value[0].lower())
    return AutoComplete(tl, text)
