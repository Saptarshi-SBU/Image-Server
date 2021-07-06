#
# create thumbnails (800x532) for images of any dimensions
# python -m api.svc.photos_thumbnail_svc
#
import os
import time
from tqdm import tqdm
import threading
from ..db.DB import DBManager, PhotoModel
from ..db.query import GetImageDir, GetThumbnailImageDir
from ..db.dbconf import *
from ..image_processing.filtering import ProcessImageThumbnail

#progressbar
pg = {}

def ConvertPhotosThumbnailSingleThreaded(uuid_list):
	with DBManager() as db: 
		pg[0] = 0
		print ('total records :{}'.format(len(uuid_list)))
		for uuid in uuid_list:
			imgPath = '{}/{}.JPG'.format(GetImageDir(), uuid)
			imgPath2 = '{}/{}_s.JPG'.format(GetThumbnailImageDir(), uuid)
			fd = os.open(imgPath2, os.O_CREAT | os.O_RDWR)
			if fd > 0:
				data = ProcessImageThumbnail(imgPath, http=False)
				num_bytes = os.write(fd, data)
				if len(data) == num_bytes:
					print (num_bytes, imgPath2)
				else:
					print ('processed file write does not match expected bytes')
				os.close(fd)
				pg[0] += 1
				if pg[0] % 100 == 0:
			   		print ('completed :{}%'.format((pg[0] * 100)/len(uuid_list)))

def ConvertPhotosThumbnailMultiThreaded(uuid_list, partn, step_size):
	pg[partn] = 0
	begin = partn * step_size
	end = min((partn + 1) * step_size, len(uuid_list))
	if begin >= len(uuid_list):
		return
	#print (begin, end, GetThumbnailImageDir())
	for uuid in uuid_list[begin : end]:
		imgPath = '{}/{}.JPG'.format(GetImageDir(), uuid)
		imgPath2 = '{}/{}_s.JPG'.format(GetThumbnailImageDir(), uuid)
		fd = os.open(imgPath2, os.O_CREAT | os.O_RDWR)
		if fd > 0:
			data = ProcessImageThumbnail(imgPath, http=False)
			os.write(fd, data)
			os.close(fd)
		pg[partn] += 1

def ScannerProgressBar(n):
	curr = 0
	prev = 0
	pbar = tqdm(total=n)
	while curr < n:
		curr = sum ([pg[c] for c in pg])
		time.sleep(0.1)
		pbar.update(curr-prev)
		prev = curr
	pbar.close()

def ScannerDriver(num_threads):
	threads = []
	uuid_list = []

	new_path = GetThumbnailImageDir()
	if not os.path.exists(new_path):
		os.mkdir(new_path)
	
	with DBManager() as db:
		_dbSession = db.getSession()
		result = _dbSession.query(PhotoModel).all()
		uuid_list = [ r.UUID for r in result ]

	print ('Processing records :{} Concurrency'.format\
			(len(uuid_list)), num_threads)

	if num_threads == 1:
		t = threading.Thread(target=ConvertPhotosThumbnailSingleThreaded,
			args=(uuid_list))
		threads.append(t)
		t.start()
	else:
		step_size = int(len(uuid_list) / num_threads)
		for i in range(num_threads + 1):
			t = threading.Thread(target=ConvertPhotosThumbnailMultiThreaded,
				args=(uuid_list, i, step_size))
			threads.append(t)
			t.start()
			time.sleep(2)

	threading.Thread(target=ScannerProgressBar, args=[len(uuid_list)]).start()
	for t in threads:
		t.join()    

ScannerDriver(8)
