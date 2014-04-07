#!/usr/bin/env python
"""
A script that takes a gpx file and copies it, writing a new track
around every segment, changing the track name of each track to the
date time of the first trackpoint, and deleting tracks with 3
trackpoints or less (see minpoints option). It also ignores empty
track segments in the original file, removes duplicate segments
(based on the first timestamp occuring more than once), and sorts
the track segments by time.

With the --crop option, it can also drop each first and last point
from every trackseg (this improves cleaning as these points are
often spurious).

Takes one argument, the path to the file to process

Options:
* --suffix <string>: change the file suffix
* --destination <string>: specify a destination folder for the processed file
* --crop: turn on cropping of first and last trackpoints
* --minpoints <integer>: set the maximum number of points a track must have
* --quiet: don't print information to STDOUT
* See --help for details

I call it preprocesssing because I have several processes to go
through before the file is accepted into our spatialite reference
database. So this is a preliminary step before running
[gpx2spatialite] (https://github.com/ptrv/gpx2spatialite)

Personal note: an adaptation of renameGPXtracksEtree.py

Copyright 2011 Daniel Belasco Rogers <http://planbperformance.net/dan>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at
your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

try:
    from lxml import etree
except ImportError:
    print """
*************************************************
You do not have a module that this script needs
Please install python-lxml from the repositories
*************************************************
"""
    exit(2)
import sys
from os import path
from optparse import OptionParser
from datetime import datetime


def makeouttree(tracklist, xmlns, crop, minpoints, quiet):
    """
    This is where the new xml structure is made. Iterate through
    the tracklist, dropping tracks less or equal to minpoints,
    cropping first and last points if option is set. Produce
    outtree which will be written to the file eventually
    """
    skippedtracksegs = 0

    outtree = etree.Element('gpx',
                            attrib={"creator": "preprocessGPXtracks.py",
                                    "version": "1.0",
                                    "xmlns":
                                    "http://www.topografix.com/GPX/1/0"})

    filetime = etree.SubElement(outtree, 'time')
    filetime.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    for track in tracklist:
        # drop tracks less than or equal to minpoints
        # (adjust if we're cropping the first and last trackpoints
        # from each segment)
        tracklen = len(track)
        if not crop and tracklen <= minpoints \
           or crop and tracklen <= (minpoints + 2):
            skippedtracksegs += 1
            continue

        trk = etree.SubElement(outtree, 'trk')
        name = etree.SubElement(trk, 'name')
        newtrkseg = etree.SubElement(trk, 'trkseg')

        pointlist = track.findall('{%s}trkpt' % (xmlns))
        if crop:
            # make sure track name isn't from a point that is no
            # longer in outgoing list
            track.remove(pointlist[0])
            pointlist = pointlist[1:-1]

        for trkpoint in pointlist:
            newtrkpoint = etree.SubElement(newtrkseg, 'trkpt')
            newtrkpoint.set('lat', trkpoint.get('lat'))
            newtrkpoint.set('lon', trkpoint.get('lon'))
            ele = etree.SubElement(newtrkpoint, 'ele')
            time = etree.SubElement(newtrkpoint, 'time')
            ele.text = trkpoint.find(('{%s}ele' % xmlns)).text.strip()
            time.text = trkpoint.find(('{%s}time' % xmlns)).text.strip()

        name.text = track.find(('{%s}trkpt/{%s}time'
                                % (xmlns, xmlns))).text.strip()

    if not quiet:
        print 'Skipped %d track segs with %d \
trackpoints or less' % (skippedtracksegs, minpoints)

    return outtree


def makenewfilename(filename, destination, suffix):
    """
    derive a new filename from current one. If a destination path is
    specified, use this in constructing newfilename
    """
    head, tail = path.split(filename)
    filename, extension = path.splitext(tail)
    newfilename = '%s%s%s' % (filename, suffix, extension)

    if destination:
        newfilepath = path.join(destination, newfilename)
    else:
        newfilepath = path.join(head, newfilename)

    return newfilepath


def checkfile(filename):
    if not(path.isfile(filename)):
        print '*' * 48
        print "input file %s not found" % filename
        print '*' * 48
        sys.exit(2)
    if path.splitext(filename)[1] != '.gpx':
        print '*' * 48
        print "Please choose a gpx file as input"
        print '*' * 48
        sys.exit(2)
    return


def parseargs():
    usage = "usage: %prog [option -d] /path/to/gpx/file.gpx"
    parser = OptionParser(usage, version="%prog 0.2")
    parser.add_option("-d",
                      "--destination",
                      dest="destination",
                      default=None,
                      help="""
Specify a folder to save the tracknamed file in""")
    parser.add_option("-m",
                      "--minpoints",
                      dest="minpoints",
                      default=3,
                      help="""
Define a minimum number of points for a track to be processed. Tracks
with less than this number will be dropped
Default = 3""")
    parser.add_option("-c",
                      "--crop",
                      dest="crop",
                      default=False,
                      action="store_true",
                      help="""
Crop the first and last trackpoints from all segments.
Note: Still reject tracks that are equal to or below
the minpoints threshold after this.
Off by default""")
    parser.add_option("-s",
                      "--suffix",
                      dest="suffix",
                      default="_pp",
                      help="""
Change the suffix of the output gpx file.
Default '_pp'""")
    parser.add_option("-q",
                      "--quiet",
                      dest="quiet",
                      default=False,
                      action="store_true",
                      help="""
Quiet mode - silence the information.""")

    options, args = parser.parse_args()

    if len(args) != 1:
        parser.error("\nPlease define input GPX file")
    filename = args[0]

    checkfile(filename)

    return filename, options.destination, options.minpoints, \
        options.crop, options.suffix, options.quiet


def filewrite(newfilename, outtree, quiet):
    with open(newfilename, 'w') as writefile:
        writefile.write(etree.tostring(outtree,
                                       encoding="utf-8",
                                       pretty_print=True,
                                       xml_declaration=True))

    if not quiet:
        print "File written to %s" % newfilename
        print

    return


def gettracks(filename, quiet):
    """
    Returns a list of track segments and the namespace
    """
    tree = etree.parse(filename)
    oldroot = tree.getroot()
    xmlns = oldroot.nsmap[None]
    trkseg = '{%s}trk/{%s}trkseg' % (xmlns, xmlns)
    tracklist = oldroot.findall(trkseg)

    if not quiet:
        print "Found %d track segments" % len(tracklist)

    return tracklist, xmlns


def prepare(tracklist, xmlns, quiet):
    """
    for these purposes, a track is a track segment. Tracklist is a
    list of track segs, track is the individual segment DO NOT USE
    remove or pop, as this messes up the list iteration and misses
    empty tracks if there are two in a row. Also returns the list
    sorted by the first trackpoint time
    """
    newtracklist = []
    firstptlist = []
    numempty = 0
    numdupes = 0
    firstptfind = ('{%s}trkpt/{%s}time' % (xmlns, xmlns))

    for track in tracklist:
        if track.find('{%s}trkpt' % xmlns) is None:
            numempty += 1
        else:
            firstpt = track.find(firstptfind).text
            if firstpt in firstptlist:
                numdupes += 1
            else:
                newtracklist.append(track)
                firstptlist.append(firstpt)

    newtracklist = sorted(newtracklist, key=lambda x: x.find(firstptfind).text)

    if numempty > 0 and not quiet:
        print "Found %d empty tracks" % numempty
    if numdupes > 0 and not quiet:
        print "Found %d duplicate tracks" % numdupes

    return newtracklist, numempty, numdupes


def main():

    filename, destination, minpoints, crop, suffix, quiet = parseargs()

    tracklist, xmlns = gettracks(filename, quiet)

    tracklist, numempty, numdupes = prepare(tracklist, xmlns, quiet)

    outtree = makeouttree(tracklist, xmlns, crop, minpoints, quiet)

    newfilename = makenewfilename(filename, destination, suffix)

    filewrite(newfilename, outtree, quiet)


if __name__ == '__main__':
    sys.exit(main())
