#!/usr/bin/env python
"""
A script that takes a gpx file and copies it, writing a new track
around every segment, changing the track name of each track to the
date time of the first trackpoint, and deleting tracks with 3
trackpoints or less (see minpoints option). With the --crop option, it
can also drop each first and last point from every trackseg (this
improves cleaning as these points are often spurious)

Takes one argument, the path to the file to process
Options:
--suffix <string>: change the file suffix
--destination <string>: specify a destination folder for the processed file
--crop: turn on cropping of first and last trackpoints
--minpoints <integer>: set the maximum number of points a track must have
See --help for details

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


def renametracks(filename, minpoints, crop):
    """
    etree parsing functions. Returns a tree with new track
    names. Ignores the track structure and makes a new track, named
    with the date of the first trackpoint, every time a new segment is
    found.
    """
    tree = etree.parse(filename)
    root = tree.getroot()

    outtree = etree.Element('gpx',
                            attrib={"creator": "preprocessGPXtracks.py",
                                    "version": "1.0",
                                    "xmlns": "http://www.topografix.com/GPX/1/0"})

    xmlns = root.nsmap[None]
    trkseg = '{%s}trkseg' % (xmlns)

    skippedtracksegs = 0
    for trackseg in root.iter(trkseg):
        try:
            trktime = trackseg.find(('{%s}trkpt/{%s}time' % (xmlns, xmlns))).text
        except AttributeError:
            continue

        # drop tracks less than or equal to the point threshold
        # (adjust if we're cropping the first and last trackpoints
        # from each segment)
        seglen = len(trackseg)
        if not crop and seglen <= minpoints \
               or crop and seglen <= (minpoints + 2):
            print 'Found track seg with %d trackpoints or less - skipping' % minpoints
            skippedtracksegs += 1
            continue

        trk = etree.SubElement(outtree, 'trk')
        name = etree.SubElement(trk, 'name')
        name.text = trktime.strip()  # remove carriage returns with strip
        newtrkseg = etree.SubElement(trk, 'trkseg')

        for idx, trkpoint in enumerate(trackseg):
            # if the crop option is on, drop first and last trackpoint
            # from each segment
            if crop and idx == 0 or crop and idx == seglen - 1:
                continue
            newtrkpoint = etree.SubElement(newtrkseg, 'trkpt')
            newtrkpoint.set('lat', trkpoint.get('lat'))
            newtrkpoint.set('lon', trkpoint.get('lon'))
            ele = etree.SubElement(newtrkpoint, 'ele')
            time = etree.SubElement(newtrkpoint, 'time')
            ele.text = trkpoint.find(('{%s}ele' % xmlns)).text.strip()
            time.text = trkpoint.find(('{%s}time' % xmlns)).text.strip()

    if skippedtracksegs > 0:
        print "Skipped %d track segs with %d trackpoints or less" % \
          (skippedtracksegs, minpoints)
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
    """
    """
    usage = "usage: %prog [option -d] /path/to/gpx/file.gpx"
    parser = OptionParser(usage, version="%prog 0.1")
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
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("\nPlease define input GPX file")
    filename = args[0]
    checkfile(filename)
    return filename, options.destination, options.minpoints, \
           options.crop, options.suffix


def filewrite(newfilename, outtree):
    """
    """
    with open(newfilename, 'w') as writefile:
        writefile.write(etree.tostring(outtree,
                                       encoding="utf-8",
                                       pretty_print=True,
                                       xml_declaration=True))
    return


def main():
    '''
    parse the arguments and get everything to run
    '''
    filename, destination, minpoints, crop, suffix = parseargs()

    print "\nGenerating new gpx structure..."
    outtree = renametracks(filename, minpoints, crop)

    newfilename = makenewfilename(filename, destination, suffix)

    print "Writing file to  %s" % newfilename
    filewrite(newfilename, outtree)

    print "Done - script ends\n"


if __name__ == '__main__':
    sys.exit(main())
