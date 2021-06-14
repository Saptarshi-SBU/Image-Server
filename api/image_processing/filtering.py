import cv2
import base64

def GetImageDimensions(filepath):
	img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
	if img_data is None:
	    print ("invalid image file:", filepath)
	    return None, None
	height = int(img_data.shape[0])
	width  = int(img_data.shape[1])
	return width, height

def ProcessImageDeprecated(filepath, scale_percent=15):
	img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
	if img_data is None:
	    print (filepath)
	height = int(img_data.shape[0] * scale_percent / 100)
	width  = int(img_data.shape[1] * scale_percent / 100)
	dim = (width, height)
	img_scal = cv2.resize(img_data, dim, interpolation=cv2.INTER_LINEAR)
	_, img_encoded = cv2.imencode('.jpg', img_scal) # encode converts to bytes
	return img_encoded.tostring()

def ProcessImage(filepath, scale_percent=15):
	img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
	if img_data is None:
	    print ("invalid image file:", filepath)
	    return None
	height = int(img_data.shape[0])
	width  = int(img_data.shape[1])
	#print (filepath, height, width)
	img_frame = cv2.pyrDown(img_data, dstsize=(width // 2, height // 2))
	img_frame = cv2.pyrDown(img_frame)
	#encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
	encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
	_, img_encoded = cv2.imencode('.jpg', img_frame, encode_param) # encode converts to bytes
	return img_encoded.tostring()

def ProcessImageGrayScale(filepath):
	img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
	#encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
	#_, img_encoded = cv2.imencode('.jpg', img_data, encode_param)
	#return img_encoded.tostring()
	if img_data is None:
	    print ("invalid image file:", filepath)
	    return None
	gray = cv2.cvtColor(img_data, cv2.COLOR_BGR2GRAY)
	_, img_encoded = cv2.imencode('.jpg', gray) # encode converts to bytes
	#base64 for being displayed inlined as a blob by js
	return base64.b64encode(img_encoded).decode('utf-8')

def TestImageSizeRatio(filepath):
	img_data = cv2.imread(filepath, cv2.IMREAD_COLOR)
	if img_data is None:
	    print ("invalid image file:", filepath)
	    return None
	height = int(img_data.shape[0])
	width  = int(img_data.shape[1])
	img_frame = cv2.pyrDown(img_data, dstsize=(width // 2, height // 2))
	#encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
	encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
	_, img_encoded = cv2.imencode('.jpg', img_frame, encode_param) # encode converts to bytes
	return img_data.size, img_encoded.size
