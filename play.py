#!/usr/bin/python2
from copy import copy
from Queue import Queue, Empty
from math import ceil, log
from mfind import get_tags, fwalk
from threading import RLock, Semaphore, Condition, Event
from sys import argv, stdin, stderr, stdout, exit
from collections import namedtuple, defaultdict, OrderedDict
from codecs import getwriter, getreader
from codecs import open as codecs_open
from contextlib import closing
argv = [x.decode('utf8') for x in argv]
stdin = getreader('utf8')(stdin)
stdout, stderr = [getwriter('utf8')(x) for x in stdout, stderr]


class Playlist(object):
	methods = OrderedDict()
	@classmethod
	def generate(cls, maxcount, *dirs):
		raise NotImplementedError
	@classmethod
	def add_method(cls, name, typ):
		cls.methods[name] = typ

# Method 1
class bPlaylist(Playlist):
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
	
	#####
	Track = namedtuple('Track', ['fname', 'tags'])
	@classmethod
	def get_track_tags(cls, files):
		for t in files:
			try:
				tags = tuple([(key, tuple(value)) for key, value in get_tags(t)])
			except ValueError:
				continue
			yield cls.Track(t, tags)
	@staticmethod
	def build_track_table(intracks):
		tracks = defaultdict(list)

		ntracks = len(intracks)
		for t in intracks:
			tracks[hash(t.tags) % ntracks].append(t.fname)
		return tracks
	@classmethod
	def generate(cls, maxcount, *dirs):
		intracks = list(cls.get_track_tags(fwalk(*dirs)))
		tracks = cls.build_track_table(intracks)
		
		ntracks = len(tracks)
		track0 = choice(intracks).fname
		del intracks
		pls = cls(track0, ntracks)
		seen = set([track0])


		print >>stderr, 'Iteration started.'
		while len(pls) < maxcount:
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
		return iter(pls.tracks)
Playlist.add_method('original', bPlaylist)




# Method 2
class Tree(object):
	class Node(object):
		__slots__ = '__parent', '__left', '__right', '__key', '__value'
		def __init__(self, key, value, parent = None):
			self.__parent = parent
			self.__left, self.__right = None, None
			self.__key, self.__value = key, value
		@property
		def parent(self):
			return self.__parent
		@parent.setter
		def parent(self, value):
			self.__parent = value
		@property
		def left(self):
			return self.__left
		@left.setter
		def left(self, value):
			self.__left = value
		@property
		def right(self):
			return self.__right
		@right.setter
		def right(self, value):
			self.__right = value
		@property
		def key(self):
			return self.__key
		@property
		def value(self):
			return self.__value
		
		def __iter__(self):
			if self.__left is not None:
				for x in self.__left:
					yield x
			yield self
			if self.__right is not None:
				for x in self.__right:
					yield x
		def __repr__(self):
			return '<Node %s=%s>' % (repr(self.__key), repr(self.__value))


	EMPTY_TREE, NODE_APPROXIMATE, NODE_EXACT = xrange(3)
	__slots__ = '__root',
	def __init__(self):
		self.__root = None
	def __repr__(self):
		if self.__root is None:
			return '<Tree 0>'
		else:
			return '<Tree %s>' % repr(self.__root)
	def __get_node(self, key):
		if self.__root is None:
			return self.EMPTY_TREE, None
		node = self.__root
		while True:
			if node.key == key:
				return self.NODE_EXACT, node
			elif key < node.key:
				if node.left is None:
					return self.NODE_APPROXIMATE, node
				node = node.left
			else:
				if node.right is None:
					return self.NODE_APPROXIMATE, node
				node = node.right
		raise RuntimeError
	def __setitem__(self, key, value):
		match, parent = self.__get_node(key)
		if match is self.EMPTY_TREE:
			self.__root = self.Node(key, value, None)
		elif match is self.NODE_EXACT:
			raise KeyError('Key already exists: %s' % key)
		else:
			node = self.Node(key, value, parent)
			if node.key < parent.key:
				if parent.left is not None:
					raise RuntimeError
				parent.left = node
			else:
				if parent.right is not None:
					raise RuntimeError
				parent.right = node
	def __iter__(self):
		if self.__root is not None:
			for node in self.__root:
				yield node.key, node.value

	def get(self, key, approximate = False):
		match, node = self.__get_node(key)
		if match is self.NODE_EXACT:
			return node.value
		elif match is self.NODE_APPROXIMATE and approximate:
			return node.value
		else:
			raise KeyError('No such key: %s' % key)
class trPlaylist(Playlist):
	@classmethod
	def generate(cls, maxcount, *dirs):
		playlist = []
		tree = Tree()

		for f in fwalk(*dirs):
			try:
				tags = tuple([(key, tuple(value)) for key, value in get_tags(f)])
			except ValueError:
				continue
			h = hash(tags)
			while True:
				try:
					tree[h] = f
					break
				except KeyError:
					h = h + 1 if h > 0 else h - 1
			if not len(playlist):
				playlist.append(f)
		
		for i in xrange(maxcount - 1):
			with open(playlist[-1], 'rb') as f:
				while True:
					key = hash(f.read(2048))
					g = tree.get(key, True)
					if g not in playlist:
						playlist.append(g)
						break
		return iter(playlist)
Playlist.add_method('tree', trPlaylist)





if __name__ == '__main__':
	from argparse import ArgumentParser
	from random import choice
	parser = ArgumentParser(description = 'Generate a playlist')
	parser.add_argument('playlist', help = 'Playlist to generate (- for stdout)', action = 'store')
	parser.add_argument('directories', metavar = 'dir', help = 'Directories to search', action = 'store', nargs = '+')
	parser.add_argument('-n', '--count', dest = 'count', type = int, help = 'Maximum number of tracks in generated playlist.', default = 0)
	parser.add_argument('-m', '--method', dest = 'method', help = 'Playlist generation method', choices = Playlist.methods.keys(), default = Playlist.methods.keys()[0])
	args = parser.parse_args(argv[1:])

	tracks = list(Playlist.methods[args.method].generate(args.count, *args.directories))
	print >>stderr, 'Writing playlist file.'
	if args.playlist == '-':
		for t in tracks:
			print >>stdout, t
	else:
		with closing(codecs_open(args.playlist, 'w', 'utf8')) as f:
			for t in tracks:
				print >>f, t
