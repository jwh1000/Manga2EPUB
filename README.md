### Overview

Manga2EPUB uses a python server (set up with flask) and a tampermonkey script to scrape and download each page (as an image) from a manga site (currently only MangaTaro is supported) and organize them into chapters. A separate python script then packages these images into an EPUB file suitable for use in an eReader.

### Setup

Currently only works with Firefox (well, maybe it works with Chrome, but I haven't tested it). You will need the TamperMonkey plugin (to run the scraping script). Create a new script and paste the contents of manga_bridge.js inside. Make sure the script is enabled.

To use the tool, start the python server (run downloader_server.py) and navigate to a chapter (if you want the whole thing, chapter 1) on the manga site (again, only MangaTaro is supported as of 12/25/2025). On the bottom left of the Firefox window you should see a big blue button that says "Start Bridge". After clicking this button, the script will scroll through the chapter, sending each page as it loads to the server which will download it. At the end of the chapter it will automatically click next.

Once the chapters are downloaded, run pack_epub.py and enter the manga title. The .epub will be created, ready to be loaded into something like Calibre. 

