import os
import uuid
import random
import datetime
import exifread
import ConfigParser
from sqlalchemy import func
from sqlalchemy import and_
import sys
sys.path.append("..")
from ..utils.checksum import comp_checksum
from ..strings.auto_complete import AutoComplete
from DB import DBManager, DBAddPhoto, InitPhotosDb, DumpTables, PhotoModel

CONFIG_FILE="/etc/api.cfg"

def GetHostIP(cfg_file=CONFIG_FILE):
    config = ConfigParser.ConfigParser()
    config.read(cfg_file)
    return config.get("host", "ipv4")

def GetImageDir(cfg_file=CONFIG_FILE):
    config = ConfigParser.ConfigParser()
    config.read(cfg_file)
    return config.get("dir", "path")

def GetDateTime2(imagePath):
    fp = open(imagePath, 'rb')
    tags = exifread.process_file(fp)
    fp.close()
    dateinfo = str(tags['EXIF DateTimeOriginal'])
    dateinfo = dateinfo.split(' ')
    yymmdd = dateinfo[0].replace(':', ' ')
    return [int(s) for s in yymmdd.split(' ')]

def GetDateTime(imagePath):
    fp = open(imagePath, 'rb')
    tags = exifread.process_file(fp)
    fp.close()
    dateinfo = str(tags['EXIF DateTimeOriginal'])
    dateinfo = dateinfo.split(' ')
    yymmdd = dateinfo[0].replace(':', ' ')
    timeinfo = dateinfo[1].replace(':', ' ')
    timeinfo = [int(s) for s in timeinfo.split(' ')]
    secs = timeinfo[0] * 3600 + timeinfo[1] * 60 + timeinfo[2]
    return [ [int(s) for s in yymmdd.split(' ')], secs ]

def GetDateTimeLocal():
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    day = now.day
    return [year, month, day, 0]

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
            result = _dbSession.query(PhotoModel).filter((PhotoModel.Likes == "Like")).order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        ).order_by(
                        PhotoModel.DayTime
                        )
        else:               
            result = _dbSession.query(PhotoModel).order_by(
                        PhotoModel.Year.desc()
                        ).order_by(
                        PhotoModel.Month.desc()
                        ).order_by(
                        PhotoModel.Day.desc()
                        ).order_by(
                        PhotoModel.DayTime
                        )
        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}-{}'.format(photo.DayTime, photo.Day, photo.Month,
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
                        ).order_by(
                        PhotoModel.DayTime
                        )

        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}-{}'.format(photo.DayTime, photo.Day, photo.Month, \
                photo.Year), "name" : photo.Name, "tags" : photo.Tags , "like" : photo.Likes }})
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
                        ).order_by(
                        PhotoModel.DayTime
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
                        ).order_by(
                        PhotoModel.DayTime
                        )

        for photo in result:
            photoPaths.append({ "value" : { "uuid" : photo.UUID, "date" : '{}-{}-{}-{}'.format(photo.DayTime, photo.Day, photo.Month, \
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
                        ).order_by(
                        PhotoModel.DayTime
                        ).all()

    random.shuffle(result)

    #unique albums
    for photo in result:
        # show only high resolution photos
        if photo.Name.find("DSC") != -1:
            photoPaths[photo.Tags] = { \
                                        "value" : \
                                            { "uuid"  : photo.UUID, \
                                              "daytime" : photo.DayTime, \
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
        [[year, month, day], secs] = GetDateTime(imgPath)
    except:
        [year, month, day, secs] = GetDateTimeLocal()

    with DBManager() as db: 
        _dbSession = db.getSession()
        DBAddPhoto(_dbSession, img_uuid, filename, digest, \
            year, month, day, secs, img_dir, " ", description)
        _dbSession.commit()
    print ('{} saved to disk'.format(filename))

def MarkPhotoFav(img_uuid, like=True):    
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
        for i in result:
            if like:
                i.Likes = "Like"
            else:
                i.Likes = "Unlike"
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

def ScanPhotos():
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
    for i in result:
        print i

def GetScaledImage(img_uuid):
    img_data = None
    with DBManager() as db: 
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).filter((PhotoModel.UUID == img_uuid)).all()
	if len(result.NameSpace_Medium) > 1:
    		imgPath = '{}{}_m.JPG'.format(result.NameSpace_Medium, result.UUID)
		with open(imgPath, 'r') as f:
		    img_data = f.read()
    return img_data
