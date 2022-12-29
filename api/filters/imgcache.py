'''
    The image cache design is based on user memory quota and overall memory quota.
    Per user images are cached album-wise using LRU mechanism.
'''

import functools
from threading import Lock
import threading

cacheLock = threading.Lock()

def synchronized(func):
    @functools.wraps(func)
    def _synchronized(*args, **kwargs):
        with cacheLock:
            return func(*args, **kwargs)
    return _synchronized

class LRUCache(dict):

    def __init__(self, capacity):
        self.cap = capacity
        self.items = 0
    
    def get(self, k):
        if k not in self:
            return None
        val = self.pop(k)
        self[k] = val
        return val

    def put(self, k, v):
        self[k] = v
        if self.items > self.cap:
            k = self.pop(next(iter(self)))
            #print ('popped key {} from cache'.format(k))
            return True
        else:
            self.items += 1
            return False

    def purge(self):
        if self.items > 0:
            self.pop(next(iter(self)))
            self.items -= 1

class LRUCacheImg(object):

    def __init__(self, capacity):
        self.img_cache = LRUCache(capacity)

    def insert(self, img_uuid, img):
        ans = self.lookup(img_uuid)
        if not ans:
            return self.img_cache.put(img_uuid, img)
        return False

    def lookup(self, img_uuid):
        return self.img_cache.get(img_uuid)

    def evict(self):
        return self.img_cache.purge() 

    def size(self):
        return len(self.img_cache)  

class GlobalLRUCacheImg(object):

    def __init__(self, capacity):
        self.user_img_cache = dict()
        self.capacity = capacity
        self.count = 0
        self.hits = 0
        self.misses = 0
        self.evicted = 0

    @synchronized
    def insert(self, user_name, img_uuid, img):
        if user_name not in self.user_img_cache:
            self.user_img_cache[user_name] = LRUCacheImg(50)
        if self.user_img_cache[user_name].insert(img_uuid, img):
            self.count += 1
        else:
            self.evicted += 1
        if self.count >= self.capacity:
            self.purge()

    @synchronized
    def delete(self, user_name, img_uuid):
        if user_name not in self.user_img_cache:
            return None
        del self.user_img_cache[user_name]
    
    @synchronized
    def lookup(self, user_name, img_uuid):
        if user_name not in self.user_img_cache:
            return None
        else:
            val = self.user_img_cache[user_name].lookup(img_uuid)
            if val:
                self.hits += 1
            else:
                self.misses += 1
                print ('key {} not present in cache'.format(img_uuid))
            return val

    def purge(self):
        while self.count >= self.capacity:
            for user in self.user_img_cache:
                self.user_img_cache[user].evict()
                self.count -= 1
                self.evicted += 1

    def stats(self):
        size = 0
        for user in self.user_img_cache:
            size += self.user_img_cache[user].size()
        print ('ImgCache Stats : hits {} misses {} evicted {} numImages {}'.
            format(self.hits, self.misses, self.evicted, size))

if __name__ == "__main__":
    # initiate a cache with capacity of 100 images
    imgCache = GlobalLRUCacheImg(100)
    user1 = "joker1"
    for i in range(20):
        imgCache.insert(user1, i, i) 
        imgCache.lookup(user1, i)  
    user2 = "joker2"
    for i in range(20):
        imgCache.insert(user2, i, i)
        imgCache.lookup(user2, i)
    imgCache.stats()
