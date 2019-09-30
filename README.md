# 4Chan Media Downloader

This Python script allows you to download, and keeps up to date all files availables in a thread.

Actually, script support webm, and gif format.

**Only tested on macOS.**

## Pre-requisites

* Python installed
* Install required libraries

```terminal
pip install -R requirements.txt
```

## How to use it

* Find a thread URL seach as, for example, <http://boards.4chan.org/gif/thread/8728832783787>
* Launch script

```terminal
python3 startup.py -u http://boards.4chan.org/gif/thread/8728832783787 -e webm
```

This commande will download all **WEBM** files in the current thread

* To keep all your files downloaded up to date

```terminal
python3 startup.py -c yes
```

## Arguments

Script needs at least 2 arguments :

* **-u <thread_url>** : The thread url
* **-e <extensions_needed>** : Extensions can be chained (multiple -e calls)

## Next features

* Ask for a default download directory
* Check update and download a new thread in the same flow
* Implement more formats, such as jpg, etc...
* ?
