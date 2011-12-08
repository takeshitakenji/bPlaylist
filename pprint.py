#!/usr/bin/env python2
from mfind import get_tags
from codecs import getwriter, getreader
from os.path import isfile, join
from codecs import open as codecs_open
from sys import argv, stdin, stderr, stdout, exit
argv = [x.decode('utf8') for x in argv]
stdin = getreader('utf8')(stdin)
stdout, stderr = [getwriter('utf8')(x) for x in stdout, stderr]

if __name__ == '__main__':
	from argparse import ArgumentParser
	parser = ArgumentParser(description = 'Print tag information for tracks in playlists')
	parser.add_argument('playlists', metavar = 'playlist', help = 'Playlists to read', action = 'store', nargs = '+')
	parser.add_argument('--base-dir', dest = 'basedir', help = 'Base directory for each item in playlist', action = 'store')
	args = parser.parse_args(argv[1:])

	for playlist in args.playlists:
		with codecs_open(playlist, 'rU', 'utf8') as f:
			for line in f:
				if line[-1] == '\n':
					line = line[:-1]
				if args.basedir:
					line = join(args.basedir, line)
				try:
					tags = get_tags(line)
				except ValueError:
					print >>stderr, 'Failed to read tags from file:', line
					continue
				except IOError:
					print >>stderr, 'Unable to open file:', line
					continue
				print >>stdout, line
				for tag, values in tags:
					if not values:
						continue
					print >>stdout, '   %s: %s' % (tag, values[0])
					indent = ' ' * (len(tag) + 3)
					for value in values[1:]:
						print >>stdout, indent, value
