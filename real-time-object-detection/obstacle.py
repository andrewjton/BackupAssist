class obstacle:
	def __init__(self, typ, size, x, y, dist):
		self.typ = typ
		self.size = size
		self.location = [x,y]
		self.distance = dist

	def getThreatLevel(self):
		return self.size / (self.distance + 1)