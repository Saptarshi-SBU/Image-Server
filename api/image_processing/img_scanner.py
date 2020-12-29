import os
import time
import threading
import sys
sys.path.append("..")
import db.DB
from db.DB import DBManager, PhotoModel
from db.query import GetMediumScaledImageDir
from db.dbconf import *
from image_processing.filtering import ProcessImage, TestImageSizeRatio

def CheckConvertScalingSavings():
	with DBManager() as db: 
	    k = 0
	    win = []
	    curr_lat = 0
	    org_size = 0
	    cur_size = 0
	    n = len(result)
	    print ('total records :{}'.format(n))
	    _dbSession = db.getSession()
	    result = _dbSession.query(PhotoModel).all()
	    for r in result:
		k += 1
		imgPath = '{}{}.JPG'.format(r.NameSpace, r.UUID)
		start = time.time()
		org, red = TestImageSizeRatio(imgPath)
		end = time.time()
		win.append([org, red, end - start])
		curr_lat += win[-1][2]
		cur_size += win[-1][1]
		org_size += win[-1][0]
		if k % 100 == 0:
		    print ('completed :{}% avg_lat:{}secs reduction:{}%'.format((k * 100)/n, (curr_lat/len(win)), cur_size*100.0/org_size))
		if len(win) > 100:
		    curr_lat -= win[0][2]
		    cur_size -= win[0][1]
		    org_size -= win[0][0]
		    win.pop(0)
	    _dbSession.commit()

def ConvertPhotosMediumSingleThreaded(new_path):
	with DBManager() as db: 
	    k = 0
	    _dbSession = db.getSession()
	    result = _dbSession.query(PhotoModel).all()
	    n = len(result)
	    print ('total records :{}'.format(n))
	    for r in result:
		if len(r.NameSpace_Medium) > 1:
		    continue
		k += 1
		imgPath = '{}{}.JPG'.format(r.NameSpace, r.UUID)
		data = ProcessImage(imgPath)
		imgPath2 = '{}{}_m.JPG'.format(new_path, r.UUID)
		fd = os.open(imgPath2, os.O_CREAT | os.O_RDWR)
		if fd > 0:
		   num_bytes = os.write(fd, data)
		   if len(data) == num_bytes:
		      r.NameSpace_Medium = new_path
		   else:
		      print 'processed file write does not match expected bytes'
		os.close(fd)
		if k % 100 == 0:
		   print ('completed :{}%'.format((k * 100)/n))
	    _dbSession.commit()

def ConvertPhotosMediumMultiThreaded(result, r_start, r_end, new_path):
    k = 0
    n = r_end - r_start + 1
    print ('records :{}'.format(n))
    for r in result[r_start : min(r_end + 1, len(result))]:
	if len(r.NameSpace_Medium) > 1:
	    continue
	k += 1
	imgPath = '{}{}.JPG'.format(r.NameSpace, r.UUID)
	data = ProcessImage(imgPath)
	imgPath2 = '{}{}_m.JPG'.format(new_path, r.UUID)
	fd = os.open(imgPath2, os.O_CREAT | os.O_RDWR)
	if fd > 0:
	   num_bytes = os.write(fd, data)
	   if len(data) == num_bytes:
	      r.NameSpace_Medium = new_path
	   else:
	      print 'processed file write does not match expected bytes'
	os.close(fd)
	if k % 100 == 0:
	   print ('completed :{}% thread:{}'.format((k * 100)/n, threading.currentThread().getName()))

def ScannerDriver(num_threads):
	new_path = GetMediumScaledImageDir()
	if not os.path.exists(new_path):
	    os.mkdir(new_path)
	if num_threads == 1:
	    ConvertPhotosMediumSingleThreaded(new_path)
	else:
	    with DBManager() as db:
		threads = []
		_dbSession = db.getSession()
		result = _dbSession.query(PhotoModel).all()
		count = len(result) / num_threads
		for i in range(num_threads):
		    t = threading.Thread(target = ConvertPhotosMediumT, args=(result, i*count, (i + 1)*count, new_path,))
		    threads.append(t)
		    t.start()
		for t in threads:
		    t.join()    
		_dbSession.commit()

ScannerDriver(1)
