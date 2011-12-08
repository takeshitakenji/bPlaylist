#!/usr/bin/python2
from copy import copy
from Queue import Queue, Empty
from math import ceil, log
from mfind import get_tags, fwalk
from threading import RLock, Semaphore, Condition, Event
from sys import argv, stdin, stderr, stdout, exit
from collections import namedtuple, defaultdict
from codecs import getwriter, getreader
from codecs import open as codecs_open
from contextlib import closing
argv = [x.decode('utf8') for x in argv]
stdin = getreader('utf8')(stdin)
stdout, stderr = [getwriter('utf8')(x) for x in stdout, stderr]




class Playlist(object):
	beginskip = 2 ** 10
	midskip = 2 ** 15
	def __init__(self, track0, ntracks):
		self.__queue = Queue()
		self.__queue.put(track0)
		
		self.__tracks = [track0]
		self.__tlock = Semaphore()

		self.__handle = None
		self.__flock = Semaphore()

		self.__ntracks = ntracks
		bitstep = long(ceil(log(ntracks, 2)))

		self.__bitmask = 0
		for i in xrange(bitstep):
			self.__bitmask = (self.__bitmask << 1) | 1
		self.__bytestep = long(ceil(float(bitstep) / 8))
	def __del__(self):
		with self.__flock:
			if not self.__handle is None:
				self.__handle.close()
				self.__handle = None
	def __next_track(self):
		try:
			if not self.__handle is None:
				self.__handle.close()
			self.__handle = open(self.__queue.get(block = False))
			self.__handle.read(self.beginskip)
		except Empty:
			self.__handle = None
			raise StopIteration
	def next(self, step = None):
		bstep = self.__bytestep if step is None else step
		with self.__flock:
			if self.__handle is None:
				self.__next_track()
			s = self.__handle.read(bstep)
			while len(s) < bstep:
				self.__next_track()
				s = self.__handle.read(bstep)
			ret = reduce(lambda acc, x: (acc << 8) | x, [ord(c) for c in s], 0)
			if step is None:
				ret &= self.__bitmask
				ret %= self.__ntracks
			return ret
	def __len__(self):
		with self.__tlock:
			return len(self.__tracks)
	@property
	def tracks(self):
		with self.__tlock:
			return copy(self.__tracks)
	def append(self, track):
		with self.__tlock:
			self.__queue.put(track)
			self.__tracks.append(track)

Track = namedtuple('Track', ['fname', 'tags'])
def get_track_tags(files):
	for t in files:
		try:
			tags = tuple([(key, tuple(value)) for key, value in get_tags(t)])
		except ValueError:
			continue
		yield Track(t, tags)
def build_track_table(intracks):
	tracks = defaultdict(list)

	ntracks = len(intracks)
	for t in intracks:
		tracks[hash(t.tags) % ntracks].append(t.fname)
	return tracks

if __name__ == '__main__':
	from argparse import ArgumentParser
	from random import choice
	parser = ArgumentParser(description = 'Generate a playlist')
	parser.add_argument('playlist', help = 'Playlist to generate (- for stdout)', action = 'store')
	parser.add_argument('directories', metavar = 'dir', help = 'Directories to search', action = 'store', nargs = '+')
	parser.add_argument('-n', '--count', dest = 'count', type = int, help = 'Maximum number of tracks in generated playlist.', default = 0)
	args = parser.parse_args(argv[1:])

	intracks = list(get_track_tags(fwalk(*args.directories)))
	tracks = build_track_table(intracks)
	
	ntracks = len(tracks)
	track0 = choice(intracks).fname
	del intracks
	pls = Playlist(track0, ntracks)
	seen = set([track0])


	print >>stderr, 'Iteration started.'
	try:
		while len(pls) != args.count:
			i = pls.next()
			if not i in tracks:
				continue
			t = tracks[i]
			i = 0
			if len(t) > 1:
				i = pls.next(1) % len(t)
			if not t[i] in seen:
				seen.add(t[i])
				pls.append(t[i])
	except (KeyboardInterrupt, StopIteration):
		pass
	print >>stderr, 'Writing playlist file.'
	if args.playlist == '-':
		for t in pls.tracks:
			print >>stdout, t
	else:
		with closing(codecs_open(args.playlist, 'w', 'utf8')) as f:
			for t in pls.tracks:
				print >>f, t
