## Rogue pypi server
Need to put server.crt and server.key in same directory as pypigeon.py
or, just use a valid cert
```
usage: pypigeon.py [-h] -p PORT [-ua] [-f FPAYLOAD] [-c CPAYLOAD] [-l LPAC]

[PyPigeon: Rogue pypi server]

options:
  -h, --help   show this help message and exit
  -p PORT      Port to listen on
  -ua          Displays informative User-Agent from request
  -f FPAYLOAD  Set payload from file to append to setup.py
  -c CPAYLOAD  Set payload from commandline [ex: -c print('Haxed')] to appent to setup.py
  -l LPAC      Serve local package

```
Currently only handles pip modules that include a setup file, no whl support yet.
