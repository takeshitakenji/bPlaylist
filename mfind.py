#!/usr/bin/env python2
from mutagen.id3 import ID3, ID3NoHeaderError
from mutagen.easymp4 import EasyMP4
from mutagen.easyid3 import EasyID3
from mutagen.oggvorbis import OggVorbis
from mutagen.flac import FLAC
from re import compile, IGNORECASE

from os import walk
from os.path import join, isfile
from sys import argv, stdin, stderr, stdout, exit
from collections import namedtuple
from codecs import getwriter, getreader
argv = [x.decode('utf8') for x in argv]
stdin = getreader('utf8')(stdin)
stdout, stderr = [getwriter('utf8')(x) for x in stdout, stderr]


Match = namedtuple('Match', ['filename', 'matches'])


fhandler = {
	'mp3' : EasyID3,
	'ogg' : OggVorbis,
	'flac' : FLAC,
	'm4a' : EasyMP4
}
extre = compile(r'\.(%s)$' % '|'.join(fhandler.iterkeys()), IGNORECASE)
def get_tags(fname):
	m = extre.search(fname)
	if m is None:
		raise ValueError('Unknown file type.')
	ext = m.group(1).lower()
	tags = {}
	try:
		info = fhandler[ext](fname)
		return list(info.iteritems())
	except ID3NoHeaderError:
		raise ValueError(u'No ID3 tags: %s' % fname)

def find(infiles, string):
	sre = compile(string, IGNORECASE)
	for f in infiles:
		try:
			tags = get_tags(f)
		except ValueError:
			continue
		fmatches = {}
		for key, values in tags:
			mvalues = []
			for value in values:
				value = unicode(value)
				if not sre.search(value) is None:
					mvalues.append(value)
			if mvalues:
				fmatches[key] = mvalues

		if fmatches:
			yield Match(f, fmatches)


def fwalk(*dirs):
	for d in dirs:
		if isfile(d):
			yield d
		else:
			for dirpath, dirnames, filenames in walk(d):
				for f in filenames:
					f = join(dirpath, f)
					if isfile(f):
						yield unicode(f)
if __name__ == '__main__':
	try:
		string, dirs = argv[1], argv[2:]
		if not dirs:
			raise ValueError
	except (ValueError, IndexError):
		print >>stderr, u'Usage: %s expr dir1 [ .. dirN ]' % argv[0]
		exit(1)
	for match in find(fwalk(*dirs), string):
		print >>stdout, match.filename
		for key, values in match.matches.iteritems():
			indent = ' ' * (len(key) + 2)
			print >>stdout, u'  %s: %s' % (key, values[0])
			for value in values[1:]:
				print >>stdout, indent, value
