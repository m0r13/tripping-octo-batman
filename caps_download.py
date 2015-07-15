#!/usr/bin/env python3

import os
import sys
import urllib.request
from bs4 import BeautifulSoup

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} url directory".format(sys.argv[0]))
        sys.exit(1)
    url, directory = sys.argv[1:3]

    data = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(data, "html.parser")

    i = 0
    for image in soup.find_all("img"):
        if not image.find_parent("td", align="right"):
            continue
        src = image["src"]
        full_src = "http://crowncapcollection.com/" + src
        basename = os.path.basename(src)
        path = os.path.join(directory, basename)

        if os.path.exists(path):
            i += 1
            continue
        
        print(i, full_src)
        f = open(path, "wb")
        f.write(urllib.request.urlopen(full_src).read())
        f.close()
        i += 1

