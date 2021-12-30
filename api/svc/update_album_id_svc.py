#
# setup album ids
# python -m api.svc.update_album_id_svc
#
import time
from tqdm import tqdm
import threading

from api.utils.checksum import comp_checksum
from ..db.DB import DBManager, PhotoModel
from ..db.query import GetPhotoAlbumID
from ..db.dbconf import *

#progressbar
pg = {}

def UpdateAlbumIDMultiThreaded(result, partn, r_start, r_end):
    pg[partn] = 0
    print(len(result), r_start, r_end)
    for r in result[r_start : min(r_end + 1, len(result))]:
        r.AlbumID = comp_checksum([r.Tags])
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
    with DBManager() as db:
        threads = []
        _dbSession = db.getSession()
        result = _dbSession.query(PhotoModel).all()
        result_list = [ r for r in result ] 
        count = int(len(result) / num_threads)
        for i in range(num_threads):
            t = threading.Thread(target = UpdateAlbumIDMultiThreaded, args=(result_list, i, i*count, (i + 1)*count))
            threads.append(t)
            t.start()
        threading.Thread(target=ScannerProgressBar, args=[len(result)]).start()
        for t in threads:
            t.join()    
        _dbSession.commit()

ScannerDriver(8)
