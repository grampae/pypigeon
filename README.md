![Alt Text](bird.png)

## Rogue pypi server
Pypigeon allows an attacker to inject Python code into the requested package as well as to host tooling that could prove useful during a Red team engagement.

 
[https://occamsec.com/pip-dreams-and-security-schemes-chaos-in-your-configuration-files/](https://occamsec.com/pip-dreams-and-security-schemes-chaos-in-your-configuration-files/)

You will need to provide a valid cert and point to it in the script.
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
