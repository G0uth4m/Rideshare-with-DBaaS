from flask import Flask
import subprocess

app = Flask(__name__)


@app.route('/', methods=["GET"])
def test():
    global c
    c+=1
    if c == 1:
        subprocess.Popen("python test.py", shell=True)
    return str(c)


if __name__ == "__main__":
    c = 0
    app.run(debug=True)