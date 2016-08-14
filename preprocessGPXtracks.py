#!/usr/bin/env python
"""A script that takes a gpx file, saving a new one with a standard
suffix '_pp' (that can be changed with the --suffix option) after
performing the following adjustments to it:
1. Each segment in the original file becomes a track in the new
   file i.e. tracks and tracksegments become de facto the same
   thing.
2. Each new track has the name of the timestamp of the first
   trackpoint.
3. Tracksegments/Tracks with less than the default number of 3
   trackpoints are deleted from the processed file. This can be
   changed with the --minpoints option.
4. Empty track segments in the original file are deleted
5. Duplicate segments (based on the first timestamp occuring more
   than once) are deleted.
6. Track segments are sorted by time.
7. Trackpoints in each segment are ordered by time (it happened in
   2016 that Dan's GPS started writing GPX tracks with some
   trackpoints out of place).
8. Trackpoints with a missing 'ele' (elevation) tag get added with
   a value of 0.
9. The --crop option drops the first and last point from every
   trackseg (this improves cleaning as these points are often
   spurious).

I call it preprocesssing because I have several processes to go
through before the file is accepted into our spatialite reference
database. So this is a preliminary step before running
[gpx2spatialite] (https://github.com/ptrv/gpx2spatialite)

Copyright 2011 Daniel Belasco Rogers dbr <danbelasco@yahoo.co.uk>

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
    print("""
*************************************************
You do not have a module that this script needs
Please install python-lxml from the repositories
*************************************************
""")
    exit(2)
import sys
import argparse
from os import path
from datetime import datetime

__version = "0.3"


def parseargs():
    desc = "A script that takes a gpx file, saving a new one with a "
    desc += "standard suffix '_pp' (that can be changed with the "
    desc += "--suffix option) after performing the following adjustments "
    desc += "to it: "
    desc += "1. Each segment in the original file becomes a track in the "
    desc += "new file i.e. tracks and tracksegments become the same "
    desc += "thing. "
    desc += "2. Each new track has the name of the timestamp of the "
    desc += "first trackpoint. "
    desc += "3. Tracksegments / Tracks with less than the default number "
    desc += "of 3 trackpoints are deleted from the processed file. This can "
    desc += "be changed with the --minpoints option. "
    desc += "4. Empty track segments in the original file are deleted. "
    desc += "5. Duplicate segments (based on the first timestamp occuring "
    desc += "more than once) are deleted. "
    desc += "6. Track segments are sorted by time. "
    desc += "7. Trackpoints in each segment are ordered by time "
    desc += "(it happened in 2016 that Dan's GPS started writing GPX tracks "
    desc += "with some trackpoints out of place). "
    desc += "8. Trackpoints with a missing 'ele' (elevation) tag get added "
    desc += "with a value of 0. "
    desc += "9. The --crop option drops the first and last point from "
    desc += "every trackseg (this improves cleaning as these points are "
    desc += "often spurious). "
    desc += "I call it preprocesssing because I have several processes to "
    desc += "go through before the file is accepted into our spatialite "
    desc += "reference database. So this is a preliminary step before "
    desc += "running [gpx2spatialite] (https://github.com/ptrv/gpx2spatialite) "
    desc += "Version={}".format(__version)

    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {version}'.format(version=__version))
    parser.add_argument("gpxfile", help="GPX file to process")
    parser.add_argument("-d",
                        "--destination",
                        default=None,
                        help="""Specify a different folder to save the output file in. Default
                        is the same folder as the original GPX file""")
    parser.add_argument("-m",
                        "--minpoints",
                        default=3,
                        help="""Define a minimum number of points
                        for a track to be processed. Tracks with
                        less than this number will be dropped
                        Default = 3""")
    parser.add_argument("-c",
                        "--crop",
                        default=False,
                        action="store_true",
                        help="""Crop the first and last trackpoints from all segments. Note:
                        Still reject tracks that are equal to or
                        below the minpoints threshold after this.
                        Off by default""")
    parser.add_argument("-s",
                        "--suffix",
                        default="_pp",
                        help="""Change the suffix of the output gpx file. 
                        Default '_pp'""")
    parser.add_argument("-q",
                        "--quiet",
                        default=False,
                        action="store_true",
                        help="Quiet mode - silence the information.")
    parser.add_argument("-o",
                        "--stdout",
                        default=False,
                        action="store_true",
                        help="""Print file to stdout. Useful for redirecting. Also sets Quiet
                        mode to True.""")
    return parser.parse_args()


def makepointdict(pointlist, xmlns, quiet):
    """Turn the pointlist from each track(seg) into a dictionary"""
    pointdict = {}

    for trkpoint in pointlist:
        lat = trkpoint.get('lat')
        lon = trkpoint.get('lon')
        try:
            ele = trkpoint.find(('{%s}ele' % xmlns)).text.strip()
        except AttributeError:
            if not quiet:
                print("No elevation tag found - assuming 0")
            ele = "0"
        time = trkpoint.find(('{%s}time' % xmlns)).text.strip()
        pointdict[time] = (lat, lon, ele)

    return pointdict


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

        # Turn the pointlist into a dictionary so we can sort by time
        pointdict = makepointdict(pointlist, xmlns, quiet)

        for time in sorted(pointdict.keys()):
            newtrkpoint = etree.SubElement(newtrkseg, 'trkpt')
            newtrkpoint.set('lat', pointdict[time][0])
            newtrkpoint.set('lon', pointdict[time][1])
            ele = etree.SubElement(newtrkpoint, 'ele')
            ele.text = pointdict[time][2]
            timetag = etree.SubElement(newtrkpoint, 'time')
            timetag.text = time

        name.text = track.find(('{%s}trkpt/{%s}time'
                                % (xmlns, xmlns))).text.strip()

    if not quiet:
        print('Skipped %d track segs with %d \
trackpoints or less' % (skippedtracksegs, minpoints))

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
        print('*' * 48)
        print("input file %s not found" % filename)
        print('*' * 48)
        sys.exit(2)
    if path.splitext(filename)[1] != '.gpx':
        print('*' * 48)
        print("Please choose a gpx file as input")
        print('*' * 48)
        sys.exit(2)
    return


def filewrite(newfilename, outtree, quiet, stdout):
    if stdout:
        print((etree.tostring(outtree,
                              encoding="utf-8",
                              pretty_print=True,
                              xml_declaration=True)))
    else:
        with open(newfilename, 'wb') as writefile:
            writefile.write(etree.tostring(outtree,
                                           encoding="utf-8",
                                           pretty_print=True,
                                           xml_declaration=True))

        if not quiet:
            print("File written to %s" % newfilename)
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
        print("Found %d track segments" % len(tracklist))

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
        print("Found %d empty tracks" % numempty)
    if numdupes > 0 and not quiet:
        print("Found %d duplicate tracks" % numdupes)

    return newtracklist, numempty, numdupes


def main():

    args = parseargs()

    filename = path.expanduser(args.gpxfile)
    checkfile(filename)

    tracklist, xmlns = gettracks(filename, args.quiet)

    tracklist, numempty, numdupes = prepare(tracklist, xmlns, args.quiet)

    outtree = makeouttree(tracklist, xmlns, args.crop,
                          args.minpoints, args.quiet)

    newfilename = makenewfilename(filename, args.destination, args.suffix)

    filewrite(newfilename, outtree, args.quiet, args.stdout)


if __name__ == '__main__':
    sys.exit(main())
