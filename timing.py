import timeit as tm
import time

def now():
	return tm.default_timer()

def timing(func):
	""" wrapper for writing time spend for a function call """
	def wrapper(*arg, **kw):
		"""source: http://www.daniweb.com/code/snippet368.html"""
		t1 = tm.default_timer()
		res = func(*arg, **kw)
		timer = tm.default_timer() - t1
		print(func.__name__, timer, 's')
		return res
	return wrapper

def dateToday():
	locTime = time.localtime()
	DAY = locTime.tm_mday
	MONTH = locTime.tm_mon
	YEAR = locTime.tm_year
	HOUR = locTime.tm_hour
	MINUTE = locTime.tm_min
	return '{0}-{1:02d}-{2:02d}-{3:02d}-{4:02d}'.format(YEAR, MONTH, DAY, HOUR, MINUTE)

def fileDate():
	locTime = time.localtime()
	DAY = locTime.tm_mday
	MONTH = locTime.tm_mon
	YEAR = locTime.tm_year

	return '{0}-{1:02d}-{2:02d}'.format(YEAR, MONTH, DAY)

def sleep(*args):
	return time.sleep(*args)
