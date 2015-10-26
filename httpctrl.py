"""
Simple webserver to trigger built process from outside.
"""
import subprocess
import re
from flask import Flask, request
app = Flask(__name__)


@app.route("/")
def welcome():
    welcome = """
    <h1>UPB mw2pdf converter manual trigger</h1>

    <form action="build" method="get">
    Docname:<br>
    <input type="text" name="docname" = value="D2.1_wikitest">
    <input type="submit" value="Build!">
    </form>
    """
    return welcome


@app.route("/build", methods=['GET'])
def build():
    # get arguments
    docname = request.args.get("docname", None)
    # some minimal security
    if not re.match(r'[\w+\.]+$', docname):
        return "Malformed document name. Abort."
    # kick-off build process
    cmd = ["python",
           "build.py",
           "--ignore-fingerprint",
           "--uml",
           "--upload",
           "--download",
           "--latex",
           "--document",
           docname]
    subprocess.Popen(cmd)
    return "Started build process for <b>%s</b>. Updated document will be available (uploaded to the Wiki) in some minutes." % str(docname)

if __name__ == "__main__":
    app.debug = False
    app.run(host='0.0.0.0')
