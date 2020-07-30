# Introduction

This repo contains two main things:

1. the exploratory data analysis for Districtr to see if it was possible to calculate contiguity and cut edges;
2. an implementation of a server that calculates contiguity and cut edges in real time on the Districtr app.

## Exploratory data analysis for Districtr

This is what I did for the week 21--27 June: find a way to
convert Districtr JSON assingments to GerryChain
partitions.

## Server that calculates contiguity and cut edges in real time

This is a FLASK server that listens for POST requests from the Districtr app.
The POST request will contain a JSON object which is an assignment of geographic units to districts,
and the server will return the number of cut edges and whether or not the plan is contiguous.

I am working on some additional features 

### How to set up this server on PythonAnywhere

On the command line, first clone this repository:

`git clone https://github.com/lieuzhenghong/districtr-eda`

Then install Git LFS. It's a bit of a faff to get Git LFS setup on PythonAnywhere 
but [this guide](https://www.pythonanywhere.com/forums/topic/11703/) is very helpful:

`wget` the latest release from [https://github.com/git-lfs/git-lfs/releases](https://github.com/git-lfs/git-lfs/releases).

Then `tar -xvf` the latest release, and edit the `install.sh` file:
find the line that says `prefix=` and change it to
`prefix="~/.local/bin`.

Then `./install.sh`.

Then, go to the PythonAnywhere dashboard. In the "Web" tab, do the following:

1. Under the "Code" heading, point "Source code:" to `/home/mggg/districtr-eda`.

2. On the WSGI configuration file `mggg_pythonanywhere_com_wsgi.py`, set the following:

```python
import sys
#
## The "/home/lieu" below specifies your home
## directory -- the rest should be the directory you uploaded your Flask
## code to underneath the home directory.  So if you just ran
## "git clone git@github.com/myusername/myproject.git"
## ...or uploaded files to the directory "myproject", then you should
## specify "/home/lieu/myproject"
path = '/home/lieu/districtr-eda'
if path not in sys.path:
    sys.path.append(path)

from server import app as application  # noqa
```

Finally,

```bash
cd districtr-eda
pip3 install -r --user
export FLASK_APP=server.py
flask run
```

and you should observe

```
* Serving Flask app "server.py"
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```



