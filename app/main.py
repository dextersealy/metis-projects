from __future__ import print_function, division
import flask
import getopt
import numpy as np
import pandas as pd
import sys
import json

#   Initialize globals

app = flask.Flask(__name__)
listings = pd.DataFrame()

#   Flask: data

@app.route('/', defaults={'path': 'home.html'})
@app.route('/<path:path>')
def send_js(path):
    print('sending {}'.format(path))
    return flask.send_from_directory('.', path)

#   Flask: actions

@app.route("/select", methods=["POST"])
def select():
    """
    When A POST request with json data is made to this uri,
    Read the selected cluster and return the associated
    listings.
    """
    global listings
    
    #	Retrieve data

    data = flask.request.json
    print(data)
    model = data['model']
    cluster = int(data['cluster'])

    #   Get results
    
    column_map = { 'NMF' : 'nmf_clusters', 'KMeans' : 'km_clusters',
        'Ward' : 'ward_clusters' }
    column = listings[column_map[model]]
    matched = listings[column==cluster].reset_index()
    results = matched.to_dict(orient='records')

    #	Return result
    
    print('{} results'.format(len(results)))
    return flask.jsonify(results)


#   Initialize application

def app_init():
    global listings
    listings = pd.read_json('nodes.json', orient='index')
    print(listings.info())

    
#   Main

def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'dh:', ['debug', 'host='])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    debug = False
    host = '0.0.0.0'

    for opt, arg in opts:
        if opt in ['-d', '--debug']:
            debug = True
        elif opt in ['-h', '--host']:
            host = arg

    app_init()
    app.run(host=host, debug=debug)


if __name__ == '__main__':
    main(sys.argv[1:])
