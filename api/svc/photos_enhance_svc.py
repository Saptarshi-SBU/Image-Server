#
# create sharpened images
# python -m api.svc.photos_enhanced_svc

#
from api import GetImgUUIDList
import os
import json
import time
from tqdm import tqdm
import threading
from ..db.DB import DBManager, PhotoModel
from ..db.query import GetImageDir, GetEnhancedImageDir, DBGetNewTopics, DBUpdateTopic, GetAlbumPhotos
from ..db.dbconf import *
from ..image_processing.filtering import ProcessImageEnhanced

#progressbar
pg = {}

def ConvertPhotosEnhancedMultiThreaded(uuid_list, partn, step_size):
	pg[partn] = 0
	begin = partn * step_size
	end = min((partn + 1) * step_size, len(uuid_list))
	if begin >= len(uuid_list):
		return
	#print (begin, end, GetEnhancedImageDir())
	for uuid in uuid_list[begin : end]:
		imgPath = '{}/{}.JPG'.format(GetImageDir(), uuid)
		imgPath2 = '{}/{}_e.JPG'.format(GetEnhancedImageDir(), uuid)
		#check exists
		#try:
		#	fd = os.open(imgPath2, os.O_RDONLY)
		#	os.close(fd)
		#	continue
		#except:
		#	pass
		try:
			fd = os.open(imgPath2, os.O_CREAT | os.O_RDWR)
			if fd > 0:
				data = ProcessImageEnhanced(imgPath)
				num_bytes = os.write(fd, data)
				if len(data) > num_bytes:
					print ('processed file write does not match expected bytes')
		except:
			print ("error processing image file :{}".format(imgPath2))

		if fd > 0 :
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

	new_path = GetEnhancedImageDir()
	if not os.path.exists(new_path):
		os.mkdir(new_path)
	
	while True:
		result = DBGetNewTopics()
		for r in result:
			if r.Topic == "Enhance":
				json_input = json.loads(r.JSONInput)
				result = GetAlbumPhotos(json_input["user_name"], json_input["img_album"])
				uuid_list = GetImgUUIDList(result)
				print ('processing Album:{} NumImages:{} Concurrency:{}'.format\
					(json_input["img_album"], len(uuid_list), num_threads))

				step_size = int(len(uuid_list) / num_threads)
				for i in range(num_threads + 1):
					t = threading.Thread(target=ConvertPhotosEnhancedMultiThreaded,
						args=(uuid_list, i, step_size))
					threads.append(t)
					t.start()
				time.sleep(2)
				json_output = ''' { "result" : "Progress" } '''
				DBUpdateTopic(r.UUID, json_output, 1) 
				threading.Thread(target=ScannerProgressBar, args=[len(uuid_list)]).start()
				for t in threads:
					t.join()
				json_output = ''' { "result" : "Done" } '''
				DBUpdateTopic(r.UUID, json_output, 2) 
		time.sleep(60)


ScannerDriver(8)
