# gpxprocessing #

Process GPX files

## preprocessGPXtracks ##

A script that takes a gpx file, saving a new one with a standard
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
7. Trackpoints with a missing 'ele' (elevation) tag get added with
   a value of 0.
8. The --crop option drops the first and last point from every
   trackseg (this improves cleaning as these points are often
   spurious).

There is one argument: the path to the gpx file to process

Options:
* --suffix <string>: change the file suffix
* --destination <string>: specify a destination folder for the
    processed file
* --crop: turn on cropping of first and last trackpoints
* --minpoints <integer>: set the maximum number of points a track
    must have
* --quiet: don't print any information to STDOUT

See --help for details

I call it preprocesssing because I have several processes to go
through before the file is accepted into our spatialite reference
database. So this is a preliminary step before running
[gpx2spatialite] (https://github.com/ptrv/gpx2spatialite)
