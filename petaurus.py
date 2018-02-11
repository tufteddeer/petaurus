import os
import sys
import shutil
import time
import yaml

tmpDir = ".cdrip"
targetDirTemplate = "Audiobooks/$SERIES/$ALBUM/CD $CD"
fileNameTemplate = "$ALBUM $CD-$TRACKNUMBER.ogg"

def main():
    checkTool("cdparanoia")
    checkTool("opusenc")
    ejectDisc = checkTool("eject", True)
    
    audiobooksToRead = []
    #if a metadata file is specified via arg[1], read it. if not, use interactive mode.
    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]):
            audiobooksToRead = readMetaFile(sys.argv[1])
        else:
            print(sys.argv[1] + " does not exist.")
    else:
        readAnother = True
        while readAnother:
            meta = readAlbumMeta()
            audiobooksToRead.append(meta)
            readAnother = read("Add another Album", "y/N") == "y"

    for book in audiobooksToRead:
        for i in range(1, int(book["TOTAL_CDS"])+1):
            book["CD"] = prefixNumber(i)
            input("Insert disc " + str(i) + " from " + book["ALBUM"] + " and press enter.")
            ripDisc(book)
            if ejectDisc:
                    os.system("eject")

def ripDisc(meta):
    global tmpDir
    tmpDir += str(time.time())
    try:
        os.makedirs(tmpDir)
    except OSError:
        print("Temporary directory " + tmpDir + " exists. Exiting.")
        cleanupAndExit(1)

    #run cdparanoia to produce .wav files
    exc = os.system("cd " + tmpDir + " && cdparanoia -B")
    if exc != 0:
        print("Failed to read disc.")
        cleanupAndExit(1)
    
    counter = 1
    for filename in os.listdir(tmpDir):
        if filename.endswith(".cdda.wav"):
            #modify track specific metadata
            meta["TRACKNUMBER"] = prefixNumber(counter)
            meta["TITLE"] = meta["ALBUM"]+" "+str(meta["CD"])+"-"+str(meta["TRACKNUMBER"])
    
            wavToOpus(filename, meta)
        else:
            continue

        counter = counter+1

    targetDir = fillTemplate(targetDirTemplate, meta)
    os.makedirs(targetDir, exist_ok=True)
    for finalFile in os.listdir(tmpDir):
        if finalFile.endswith(".ogg"):
            shutil.move(tmpDir + "/" + finalFile, targetDir + "/" + finalFile)

    shutil.rmtree(tmpDir)

def wavToOpus(filename, meta):
    out = tmpDir + "/" + fillTemplate(fileNameTemplate, meta)
    out = out.replace(" ", "\\ ")
    comments = buildCommentArgs(meta)
    cmd = "opusenc " + tmpDir + "/" + filename + " " + out + " " + comments
    exc = os.system(cmd)
    if exc != 0:
        print("Failed to convert " + tmpDir + "/" + filename + " to " + out)
        cleanupAndExit(1)
    return out

def buildCommentArgs(meta):
    comments = ""
    for key, value in meta.items():
        if not value == "":
            comments += " --comment " + key + "=" + str(value).replace(" ", "\\ ")

    return comments

def fillTemplate(template, meta):
    for key, value in meta.items(): 
        template = template.replace("$" + key, str(value))
    return template

def cleanupAndExit(status):
    shutil.rmtree(tmpDir)
    sys.exit(status)


def checkTool(cmd, optional=False):
    ok = shutil.which(cmd)
    if not ok and not optional:
        print(cmd + " must be installed and in the PATH environment variable!")
        sys.exit(1)
    if not ok:
        print("Optional command " + cmd + " is not installed or not in PATH")
        return False
    return True

def read(prompt, default):
    userinput = input(prompt + " (" + default + "): ")
    if userinput == '':
        return default
    return userinput

def readAlbumMeta():
    meta = {}
    meta["ALBUM"] = read("Album Title", "Unknown Album")
    meta["ARTIST"] = read("Artist", "Unknown Artist")
    meta["SERIES"] = read("Series", "")
    meta["PERFORMER"] = read("Performer", "Unknown Performer")
    meta["TOTAL_CDS"] = int(read("Number of CDs? ", "1"))
    
    meta["TITLE"] = "",
    meta["TRACKNUMBER"] = "",
    meta["CD"] = "1"
    return meta

def readMetaFile(filename):
    books = []

    with open(filename) as f:
        dataMap = yaml.safe_load(f)
        for book in dataMap:
            meta = {}
            meta["ALBUM"] = "Unknown Album"
            meta["ARTIST"] =  "Unknown Artist"
            meta["SERIES"] = ""
            meta["PERFORMER"] = "Unknown Performer"
            meta["TOTAL_CDS"] = "1"
            meta["TITLE"] = "",
            meta["TRACKNUMBER"] = "",
            meta["CD"] = "1"
            meta["ALBUM"] = book
            #overwrite defaults with custom values
            for attr in dataMap[book]:
                meta[attr] = dataMap[book][attr]
            books.append(meta)
    return books

def prefixNumber(number):
    if number < 10:
        return "0" + str(number)
    else:
        return str(number)

if __name__ == "__main__":
    main()
