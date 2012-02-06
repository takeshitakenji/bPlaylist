#!/usr/bin/env python2
from mfind import get_tags, fwalk
from codecs import open as codecs_open
from contextlib import closing
from sys import argv, stdin, stderr, stdout, exit
from codecs import getwriter, getreader
argv = [x.decode('utf8') for x in argv]
stdin = getreader('utf8')(stdin)
stdout, stderr = [getwriter('utf8')(x) for x in stdout, stderr]



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

if __name__ == '__main__':
	root = u'/home/music'

	playlist = []
	tree = Tree()

	for f in fwalk(root):
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
	
	for i in xrange(50):
		with open(playlist[-1], 'rb') as f:
			while True:
				key = hash(f.read(2048))
				g = tree.get(key, True)
				if g not in playlist:
					playlist.append(g)
					break
	for i in playlist:
		print >>stdout, i
