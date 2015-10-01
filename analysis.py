import json
ts_id='sin'
with open('./experiments/'+ts_id+'/config.json') as cf:
    xpnm=json.load(cf)['experiment-name']

# get data from db
    
from spearmint.utils.database.mongodb import MongoDB
mdb=MongoDB()





import pandas as pd
def get_runs():
    jobs=mdb.load(xpnm,'jobs',{'status':'complete'})
    try: jobs[0]
    except KeyError: jobs=[jobs]
    finally: params=jobs[0]['params'].keys()

    data=[]
    import numpy as np
    for ajb in jobs:
        arow=[]
        for ap in params:
            dd=ajb['params'][ap]['values'][0]
            dt=ajb['params'][ap]['type'][0]
            arow.append(np.array(dd,dtype=dt))
        arow.append(ajb['values']['main'])
        arow.append((ajb['id']))
        data.append(tuple(arow))

    columns=params[:]
    columns.append('o')
    columns.append('run_id')
    runs=pd.DataFrame(data=data,columns=columns)
    return runs


def get_best_params():
    #todo what if muliple nets with same 'params'?
    runs=get_runs()
    bp=dict(runs.ix[runs['o'].idxmin()])
    bp.pop('o')
    best_params={}
    for ap in (bp):
        try: #chk for number
            bp[ap]/1.0
            best_params[ap]=float(bp[ap])
        except:
            best_params[ap]=bp[ap]
    return best_params

import rnn
rnn.env(ts_id)
from rnn import tbl
import omain
def get_best_net():
    #assert(len(list(tbl.find(**best_params)))==1)
    params=get_best_params()
    params['iter']=omain.itermap(params['iter'])
    return rnn.get_net(params)


import matplotlib.pyplot as plt
import data
ts=data.get(ts_id) #,length=100) len should ~250
tl=int(.7*len(ts))
trn=(ts[:tl])
vld=(ts[tl:])

def diag(ts=trn,i=0):
    plt.plot(ts[i])
    plt.plot(get_best_net().predict(ts)[i])


import sklearn.metrics as metrics
def get_errs(ts,net=get_best_net()):
    p=net.predict(ts)
    errs=[]
    for i in xrange(ts.shape[0]):
        errs.append(metrics.mean_squared_error(ts[i,:,0],p[i])**1 )
    return errs
