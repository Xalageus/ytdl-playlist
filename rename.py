#!/usr/bin/python3
import sys, os, json, io, datetime, subprocess

#Begin Global vars--

files = os.listdir(path=sys.argv[2])
playlist = json.load(open(sys.argv[1]))

VIDEO_TYPES = [".mkv", ".mp4", ".webm"]
SUB_TYPES = [".vtt"]
ANNOTATION_TYPES = [".annotations.xml"]
DESCRIPTION_TYPES = [".description"]
INFO_TYPES = [".info.json"]
THUMB_TYPES = [".jpg"]
STD_ID_LEN = 11

#End Global vars--

#Begin Classes--

class Video(object):
    def __init__(self, id, video, subs, annotations, description, info, thumbnail, length):
        self.id = id
        self.video = video
        self.subs = subs
        self.annotations = annotations
        self.description = description
        self.info = info
        self.thumbnail = thumbnail
        self.fail = False
        self.length = length

    def __init__(self, id):
        self.id = id
        self.fail = False

#End Classes--

#Begin Functions--

def removeZeros(arr):
    """Remove 0s in a array"""

    count = 0

    for item in arr:
        if item != 0:
            count += 1

    newArr = [0] * count
    i = 0

    while i < count:
        newArr[i] = arr[i]
        i += 1

    return newArr

def printIds(playlist):
    """Print list of ids from a playlist json"""

    i = 0

    while i < len(playlist['entries']):
        print(str(i + 1) + ": " + playlist['entries'][i]['id'])
        i += 1

def getIds(playlist):
    """Get array of ids from a playlist json"""

    ids = [0] * len(playlist['entries'])
    i = 0

    while i < len(playlist['entries']):
        ids[i] = playlist['entries'][i]['id']
        i += 1

    return ids

def getRelevantFiles(files, TYPE):
    """Get array of files of a certain filetype(s)"""

    relevantFiles = [0] * len(files)
    i = 0

    for f in files:
        if any(f.endswith(ext) for ext in TYPE):
            relevantFiles[i] = f
            i += 1

    return relevantFiles

def stdCompareId(id, file, type):
    """Compare filename with given id assuming standard youtube-dl naming"""

    typeC = False
    i = 0

    while typeC is False:
        tFile = file[-len(type[i]):]
        if tFile == type[i]:
            typeC = True
        else:
            i += 1

    tFile = file[:-len(type[i])]
    idFromFile = tFile[-STD_ID_LEN:]

    if id == idFromFile:
        return True
    else:
        return False

def getFiles(id, files):
    """Search through files and associate an id"""

    found = False
    fail = False
    i = 0
    rFiles = removeZeros(getRelevantFiles(files, VIDEO_TYPES))

    video = Video(id)

    while not found and not fail:
        if i >= len(rFiles):
            fail = True
            video.fail = True
        else:
            if stdCompareId(id, rFiles[i], VIDEO_TYPES):
                video.video = rFiles[i]
                found = True
            else:
                i += 1

    return video

def exportParse(videos, startTime, endTime):
    """Export videos object data to .txt"""

    export = io.open("export.txt", "w", encoding="utf-8")
    i = 1

    export.write("Took " + str((endTime - startTime).total_seconds()) + " seconds\n\n")

    for v in videos:
        export.write("Video #: " + str(i) + "\n")
        export.write("Video fail status: " + str(v.fail) + "\n")
        export.write("Video id: " + str(v.id) + "\n")
        export.write("Video filename: " + v.video + "\n\n")

        i += 1

    export.close()

def getVideoLength(video):
    """Calls a ffprobe subprocess to get length of a video file"""
    
    print("Getting length for " + video + " ...", end=' ')

    length = subprocess.run(["ffprobe",
                            "-loglevel",
                            "quiet",
                            "-show_entries",
                            "format=duration",
                            "-print_format",
                            "default=nokey=1:noprint_wrappers=1",
                            "-i",
                            sys.argv[2] + "\\" + video],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

    print(str((float(length.stdout))) + " seconds")
    return float(length.stdout)

def calcTotalLength(playlistData):
    """Adds up lengths to get total length in float"""

    totalLength = 0.0

    for di in playlistData:
        totalLength += di['length']

    return totalLength

def reverseSlash(string):
    """Converts '\\\\' in a string to '/'"""

    newString = ""

    for c in string:
        if c == "\\":
            c = "/"

        newString += c

    return newString

def URIEncode(string):
    """Converts a space in a string to '%20'"""

    newString = ""

    for c in string:
        if c == " ":
            newString += "%20"
        else:
            newString += c

    return newString

def generatem3u8(playlistData, vlc):
    """Create header and data for m3u8 playlist with differences between a 
    vlc compatible version or not"""

    header = ""
    data = ""

    if vlc:
        header = "#EXTM3U\n"
        
        filePrefix = "file:///" + URIEncode(reverseSlash(sys.argv[2])) + "/"

        for di in playlistData:
            data += "#EXTINF:"
            data += str(int(di['length'])) + "," + di['file'] + "\n"
            data += filePrefix + URIEncode(di['file']) + "\n"
    else:
        header = "#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:0\n#EXT-X-TARGETDURATION:" + str(calcTotalLength(playlistData)) + "\n#EXT-X-ENDLIST\n"

        filePrefix = sys.argv[2] + "\\"

        for di in playlistData:
            data += "#EXTINF:"
            data += str(di['length']) + "," + di['file'] + "\n"
            data += filePrefix + di['file'] + "\n"

    return header + data

def createm3u8(videos, vlc, filename):
    """Write a playlist m3u8 to file"""

    ple = []

    for video in videos:
        video.length = getVideoLength(video.video)
        ple.append({'file' : video.video, 'length' : video.length,})

    if vlc:
        file = io.open(filename, "w", encoding="utf-8")
        file.write(generatem3u8(ple, True))
        file.close
    else:
        file = io.open(filename, "w", encoding="utf-8")
        file.write(generatem3u8(ple, False))
        file.close

    

    return videos

def reverseVideos(videos):
    """Reverses an object of videos with the last video becoming 
    the first"""

    return videos[::-1]

#End Functions--

#Begin Main--

startTime = datetime.datetime.now()

ids = getIds(playlist)

videos = [0] * len(ids)
pos = 0

for id in ids:
    videos[pos] = getFiles(id, files)
    pos += 1

endTime = datetime.datetime.now()

print("Took " + str((endTime - startTime).total_seconds()) + " seconds")
print("Writing parse to file...")
exportParse(videos, startTime, endTime)
createm3u8(videos, False, "playlist.m3u8")
createm3u8(videos, True, "playlist-vlc.m3u8")
createm3u8(reverseVideos(videos), False, "playlist-reversed.m3u8")
createm3u8(reverseVideos(videos), True, "playlist-reversed-vlc.m3u8")

#End Main--