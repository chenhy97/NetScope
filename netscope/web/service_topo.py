from flask import Flask, render_template
from pathlib import Path

app = Flask(__name__)
root_dir = Path(__file__).resolve().parent.parent


@app.route('/')
def topo_origin():
    with open(root_dir / 'web/static/topo_origin.html', "r") as f:
        return f.read()


@app.route('/rca')
def topo_culprit():
    with open(root_dir / 'web/static/topo_culprit.html', "r") as f:
        return f.read()


if __name__ == '__main__':
    app.run(debug=True)
