# USAGE
# python real_time_object_detection.py --prototxt MobileNetSSD_deploy.prototxt.txt --model MobileNetSSD_deploy.caffemodel

# import the necessary packages
from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import imutils
import time
import cv2
import freenect
import sys
from obstacle import obstacle

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-p", "--prototxt", required=True,
	help="path to Caffe 'deploy' prototxt file")
ap.add_argument("-m", "--model", required=True,
	help="path to Caffe pre-trained model")
ap.add_argument("-c", "--confidence", type=float, default=0.2,
	help="minimum probability to filter weak detections")
ap.add_argument("-t", "--track", action="store_true", default=False,
	help="enable tracking/highlighting of objects")
args = vars(ap.parse_args())

# initialize the list of class labels MobileNet SSD was trained to
# detect, then generate a set of bounding box colors for each class
CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
	"bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
	"dog", "horse", "motorbike", "person", "pottedplant", "sheep",
	"sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

# load our serialized model from disk
print("[INFO] loading model...")
net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

# initialize the video stream, allow the cammera sensor to warmup,
# and initialize the FPS counter
print("[INFO] starting video stream...")
vs = VideoStream(src=0).start()
time.sleep(2.0)
fps = FPS().start()
# loop over the frames from the video stream

def getImage():	
	depth, timestamp = freenect.sync_get_video()
 
	np.clip(depth, 0, 2**20 - 1, depth)
	depth >>= 2
	depth = depth.astype(np.uint8)
	
	return depth

def getDepthMap():	
	depth, timestamp = freenect.sync_get_depth()
 
	np.clip(depth, 0, 2**10 - 1, depth)
	depth >>= 2
	depth = depth.astype(np.uint8)
	
	return depth

def getCenter(w1, h1, w2, h2):
	return ((w1+w2)/2.0, (h1+h2)/2.0)

def colorizeImage(frame, startX, startY, endX, endY):
	(h, w) = frame.shape[:2]
	startX = max(0, startX)
	startY = max(0, startY)
	endX = min(endX, w)
	endY = min(endY, h)
	frame[startY:endY,startX:endX,2] = 255*.3
	# for i in range(startY, endY):
	# 	for w in range(startX, endX):
	# 		try:

	# 			frame[i][w][2] = 255*.3
	# 		except:
	# 			print("[DEBUG] Tried to draw to invalid frame region!")
	# 			print("[DEBUG] Coordinates" + (i,w))

def brighten_image(frame):
	phi = 1
	theta = 1
	maxIntensity = 255.0 

	newImage1 = (maxIntensity/phi)*(frame/(maxIntensity/theta))**2
	return newImage1

if __name__ == "__main__":
	obj = obstacle("none", 0, 0, 0, -5)
	while True:
		# grab the frame from the threaded video stream and resize it
		# to have a maximum width of 400 pixels
		frame = getImage()#freenect.sync_get_video()#vs.read()
		frame = imutils.resize(frame, width=600)
		frame_d = getDepthMap()

		# grab the frame dimensions and convert it to a blob
		(h, w) = frame.shape[:2]
		blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)),
		  0.007843, (300, 300), 127.5)

		# pass the blob through the network and obtain the detections and
		# predictions
		net.setInput(blob)
		detections = net.forward()

		# loop over the detections
		for i in np.arange(0, detections.shape[2]):
		  # extract the confidence (i.e., probability) associated with
		  # the prediction
		  confidence = detections[0, 0, i, 2]

		  # filter out weak detections by ensuring the `confidence` is
		  # greater than the minimum confidence
		  if confidence > args["confidence"]:
			# extract the index of the class label from the
			# `detections`, then compute the (x, y)-coordinates of
			# the bounding box for the object
			idx = int(detections[0, 0, i, 1])
			box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
			(startX, startY, endX, endY) = box.astype("int")
			cx, cy = getCenter(detections[0, 0, i,3], detections[0, 0, i,4], detections[0, 0, i,5], detections[0, 0, i,6])
			cx = int(cx*w)
			cy = int(cy*h)

			if (args["track"] and (CLASSES[idx] == "car" or CLASSES[idx] == "person") ):
				colorizeImage(frame, startX, startY, endX, endY)
			#object specific calculations
			size = (endX-startX) * (endY-startY)
			dist = frame_d[cy, cx]
			threatLevel = size / (dist + 1)
			if (threatLevel > obj.getThreatLevel()):
				obj = obstacle(CLASSES[idx], size, cx, cy, dist)
				print("[EVENT] Switched tracking to a more dangerous obstacle")

			# frame = brighten_image(frame)
			# draw the prediction on the frame
			label = "{}: {:.2f}%".format(CLASSES[idx],
			  confidence * 100)
			cv2.rectangle(frame, (startX, startY), (endX, endY),
			  COLORS[idx], 2)
			y = startY - 15 if startY - 15 > 15 else startY + 15
			cv2.putText(frame, label, (startX, y),
			  cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)
			cv2.circle(frame, (cx,cy), 5, COLORS[idx], -1)

		# show the output frame
		cv2.imshow("Frame", frame)
		key = cv2.waitKey(1) & 0xFF

		# if the `q` key was pressed, break from the loop
		if key == ord("q"):
		  break

		# update the FPS counter
		fps.update()

	# stop the timer and display FPS information
	fps.stop()
	print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
	print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

	# do a bit of cleanup
	cv2.destroyAllWindows()
	vs.stop()



