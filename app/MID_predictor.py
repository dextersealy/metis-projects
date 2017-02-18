from __future__ import print_function, division
from collections import Counter
from collections import defaultdict
from collections import OrderedDict
from sklearn.externals import joblib
import flask
import getopt
import numpy as np
import pandas as pd
import pickle
import sys

#   Initialize Flask

app = flask.Flask(__name__)

#   Flask: local files

@app.route('/', defaults={'path': 'MID_predictor.html'})
@app.route('/<path:path>')
def send_js(path):
    return flask.send_from_directory('.', path)

    
#   Flask: predictor

@app.route("/predict", methods=["POST"])
def predict():
    """
    When A POST request with json data is made to this uri,
    Read the states from the json, predict probability and
    send it with a response
    """

    #	Retrieve data

    data = flask.request.json
    country = data['country']
    print(country)
    
    #	Calculate probablity

    scores = run_predict(country[0], country[1])

    #	Return result

    results = dict(zip(clf.classes_, scores))
    print('results =', [{ k : '{:.2f}'.format(v) for k, v in results.items()}])

    return flask.jsonify(results)


#   Flask: shutdown

@app.route('/shutdown', methods=['POST'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...\n'

    
def shutdown_server():
    func = flask.request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


#   Helper functions.

#   These helper functions construct the X observation vector required
#   by the classifier. See military_duplicates.ipynb for more
#   information.

dispute_actions = {
    0 : 'None', 1 : 'ThreatForce', 2 : 'ThreatBlockade', 3 : 'ThreatOccupy', 
    4 : 'ThreatDeclareWar', 5 : 'ThreatUseCBR', 6 : 'ThreatJoinWar', 7 : 'ShowForce',
    8 : 'Alert', 9 : 'NuclearAlert', 10 : 'Mobilize', 11 : 'FortifyBorder',
    12 : 'ViolateBorder', 13 : 'Blockade', 14 : 'Occupy' , 15 : 'Seizure',
    16 : 'Attack', 17 : 'Clash', 18 : 'DeclareWar', 19 : 'UseCBR', 
    20 : 'BeginWar', 21 : 'JoinWar'
    }

def get_X(df, state1, state2, year):
    """
    Construct X observation for predictor.
    """

    a_abb = get_abbrev(state1)
    b_abb = get_abbrev(state2)
    if not a_abb or not b_abb:
        return None

    #	Copy model template
    
    X = X_template.copy()

    #	Populate vector
    
    X.numab = 2
    
    priors = get_priors(df, a_abb, b_abb)
    for col in ['win', 'yield', 'fatal']:
        X['p_' + col] = priors['pa_' + col] + priors['pb_' + col]
    
    for f in ['milexp', 'milpers', 'totalpop', 'urbanpop']:
        ratio = get_ratio(a_abb, b_abb, year, f, nmc_dict)
        X['r_' + f] = ratio if ratio else np.median(df['r_' + f].dropna())

    contig = get_contiguity(a_abb, b_abb, year, contiguity_dict)
    if contig != 'Land':
        X['contig[T.{}]'.format(contig)] == 1.0

    pa_hiact_s = dispute_actions[priors['pa_hiact']]
    if pa_hiact_s != 'ThreatBlockade':
        X['pa_hiact_s[T.{}]'.format(pa_hiact_s)] = 1.0

    pb_hiact_s = dispute_actions[priors['pb_hiact']]
    if not pb_hiact_s in ['ThreatBlockade', 'Alert']:
        X['pb_hiact_s[T.{}]'.format(pb_hiact_s)] = 1.0
        
    X['maj'] = is_major(a_abb, year, majors_dict) + is_major(b_abb, year, majors_dict)

#    print(X)
    return X


def get_abbrev(country_name):
    entry = country_dict.get(country_name, None)
    return entry['StateAbb'] if entry else None


def get_priors(df, a_abb, b_abb):
    def priorsum(df, col):
        return df.groupby(['a_abb', 'b_abb'])[col].transform(pd.Series.cumsum) - df[col]

    def priormode(df, col):
        def _priormode(x):
            result = [0]
            c = Counter()
            for elem in x:
                c.update([elem])
                result.append(c.most_common()[0][0])
            return pd.Series(result)
        return df.groupby(['a_abb', 'b_abb'])[col].transform(_priormode)

    row = df.iloc[-1].copy()
    row.a_abb = a_abb if a_abb < b_abb else b_abb
    row.b_abb = b_abb if a_abb < b_abb else a_abb
    df = df.append(row)

    for col in ['a_win', 'b_win', 'a_yield', 'b_yield', 'a_fatal', 'b_fatal']:
        df['p' + col] = priorsum(df, col)
        
    for col in ['a_hiact', 'b_hiact']:
        df['p' + col] = priormode(df, col)

    return df.iloc[-1]


def get_ratio(a_abb, b_abb, year, item=None, dict_=None):
    """
    Given dictionary and item name, return the ratio of state B
    to state A.
    """
    def get_value(stabb, year, item, dict_):
        """
        Get NMC value from dictionary. If no value is present for the
        requested year, check N=4 years before or after and return the
        first value found.
        """
        result = dict_.get((stabb, year), None)
        if not result:
            for i in range(1, 5):
                result = dict_.get((stabb, year - i), None)
                if not result:
                    result = dict_.get((stabb, year + i), None)
                if result:
                    break
        return result[item] if result else None

    result = None
    a_val = get_value(a_abb, year, item, dict_)
    if a_val:
        b_val = get_value(b_abb, year, item, dict_)
        if b_val:
            result = b_val / a_val
    return result


def get_contiguity(a_abb, b_abb, year, dict_=None):
    """
    Given dataframe row and contiguity dictionary, return the 
    contiguity between the corresponding two states.
    """
    result = 'None'
    list_ = dict_.get((a_abb, b_abb), None)
    if list_:
        for start, end, conttype in list_:
            if start <= year and end >= year:
                result = conttype
    return result


def is_major(abb, year, dict_=None):
    result = 0
    if abb in dict_:
        span = dict_[abb]
        #   Make sure dispute is within state's span as major power
        if year >= span['styear'] and year <= span['endyear']:
            result = 1
    return result


#   Initialize model and data

global clf
global contiguity_dict
global country_dict
global df_model
global majors_dict
global nmc_dict
global X_template

def init():
    global clf
    global contiguity_dict
    global country_dict
    global df_model
    global majors_dict
    global nmc_dict
    global X_template

    clf = joblib.load('data/MID_predictor.pkl')

    df_model = pd.read_csv('data/MID_predictor_observations.csv')
    print('Observations: {}'.format(len(df_model)))

    X_template = pd.read_csv('data/MID_predictor_X.csv').iloc[-1]
    print('X: {}'.format(len(X_template)))

    cont = pd.read_csv('data/MID_predictor_contiguity.csv')
    contiguity_dict = defaultdict(list)
    for r in cont.itertuples():
        contiguity_dict[(r.statea, r.stateb)].append((r.start, r.end, r.conttype))
    print('Contiguity: {}'.format(len(contiguity_dict)))

    country_dict = pd.read_csv('data/MID_predictor_countries.csv').set_index('MAPName').to_dict(orient='index')
    print('Countries: {}'.format(len(country_dict)))

    majors_dict = pd.read_csv('data/MID_predictor_majors.csv').set_index('stabb').to_dict(orient='index')
    print('Major powers: {}'.format(len(majors_dict)))

    nmc_dict = pd.read_csv('data/MID_predictor_nmc.csv').set_index(['stabb', 'year']).to_dict(orient='index')
    print('NMC: {}'.format(len(nmc_dict)))

    
#   Decorator for caching results

result_cache = {}
def memoize(func):
    global result_cache
    def func_wrapper(*args, **kwargs):
        key = tuple(args)
        if key in result_cache:
            result = result_cache[key]
        else:
            result = func(*args, **kwargs)
            result_cache[key] = result
        return result

    return func_wrapper
    

#   Run model

@memoize
def run_predict(A, B, year=2010):
    X = get_X(df_model, A, B, 2010)
    return clf.predict_proba(X.reshape(1, -1))[0]


#   Test model

def test_predict(count):
    countries = country_dict.keys()
    for i in range(count):
        A, B = np.random.choice(countries, 2)
        scores = run_predict(A, B)
        scores = ['{:.2f}'.format(s) for s in scores]
        results = dict(zip(clf.classes_, scores))
        print('{} vs {} = {}'.format(A, B, results))
    

#   Main

def main(argv):
    try:
        opts, args = getopt.getopt(argv, 'c:dh:t', ['count=', 'debug', 'host=', 'test'])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    count = 20
    debug = False
    host = '0.0.0.0'
    test = False

    for opt, arg in opts:
        if opt in ['-c', '--count']:
            count = int(arg)
        elif opt in ['-d', '--debug']:
            debug = True
        elif opt in ['-h', '--host']:
            host = arg
        elif opt in ['-t', '--test']:
            test = True

    if test:
        init()
        test_predict(count)
    else:
        init()
        app.run(host=host, debug=debug)


if __name__ == '__main__':
    main(sys.argv[1:])
