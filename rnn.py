import theanets
import numpy as np

import climate
climate.enable_default_logging()

import os
import dataset

import data


def env(ts_id):
    
    global mydir
    global db
    global tbl

    global trn
    global vld
    global dim_out
    global dim_in
    global noise
    
    mydir=os.path.split(os.path.realpath(__file__))[0];
    os.chdir(mydir)

    dbfp=os.path.join('experiments',ts_id,'output','rnn.sqlite')
    #dbfp='test.sqlite'
    dbp='sqlite:///'+dbfp
    erase=False #for testing =True
    if erase==True:
        try: os.remove(dbfp)
        except: pass

    db=dataset.connect(dbp)
    tbl=db[ts_id]

    ts=data.get(ts_id) 
    tl=int(.75*len(ts))
    trn=data.list_call(ts[:tl])
    vld=data.list_call(ts[tl:])
    dim_out=dim_in=data.dim(ts_id)

    noise=np.std(data.get_series(ts_id))
    
        



def get_net(params,i=-1): # n -1 gets the last one interted
    """get str rep from db and put it into a file"""
    pc=params.copy()
    found=list(tbl.find(**pc))
    #if len(found)>1: raise Exception('more than one model matched params')
    if len(found)==0: return None
    found=found[i] # get's the last one inserted

    try:
        tfp=ntf(dir=mydir,suffix='.tmp',delete=False)
        with open(tfp.name,'wb') as f: f.write(found['net'])
        tfp.close()
        net=theanets.Network.load(tfp.name)
    finally: #cleanup
        os.remove(tfp.name)
    return net

from tempfile import NamedTemporaryFile as ntf
def save_net(params,net,run_id=None):
    
    pc=params.copy()

    try:
        tfp=ntf(dir=mydir,suffix='.tmp',delete=False)
        net.save(tfp.name)
        with open(tfp.name,'rb') as f: pc['net']=buffer(f.read())
        tfp.close()
    finally: #cleanup
        os.remove(tfp.name)

    if run_id != None: pc['run_id']=run_id
    return tbl.insert(pc)




def make_net(params):
    p=params
    layers=[dim_in]
    for alyr in xrange(params['nl']):
        layers.append( dict(form='lstm' #'rnn'
                            ,size=p['n']
                            ,activation='sigmoid' #ignored on lstm
                            ) )
    layers.append(dim_out)
    #net  = theanets.recurrent.Regressor(
    net = theanets.recurrent.Autoencoder(layers)
    return net



def function(params,run_id=None):

    # get network
    
    pc=params.copy()
    pc.pop('iter')
    netfind=list(tbl.find(**pc))
    # has a net with these params ever been created?
    if len(netfind)==0:
        net=make_net(pc)
        del netfind
        state                             ='new';                 stateit=0
    else:
        # is there a previous net to resume from?
        lastiters=[arow['iter'] for arow in tbl.distinct('iter',**pc) \
                   if arow['iter']<params['iter']]
        if len(lastiters)==0:        state='no previous iter';    stateit=1
        else:
            lastiter=sorted(lastiters)
            lastiter=lastiter[-1]
        
            # chk how many lastiter vs thisiter
            thisiters=list(tbl.find(**params))
            pcc=pc.copy()
            pcc['iter']=lastiter
            lastiters=list(tbl.find(**pcc))
            nthisiter=len(thisiters)
            nlastiter=len(lastiters)

        
            if nthisiter>=nlastiter: state='no previous iter';    stateit=2
            elif nthisiter<nlastiter:state='previous iter found'; stateit=3
            else: raise Exception('undefined state')

        if state=='previous iter found':
            pcc=pc.copy()
            pcc['iter']=lastiter
            net=get_net(pcc,i=nthisiter) #'careful! looks good
        elif state=='no previous iter':
            net=make_net(pc)
        else:
            raise Exception('undefined state handler')
    #not elegant but whatever
    print 'stateit',stateit

    xp=theanets.Experiment(net)
    
    xpit=xp.itertrain( trn , vld
                       ,algorithm='rmsprop'
                       ,input_noise=noise
                       #,input_dropout=.3 #idk how this would app here
                       ,nesterov=True
                       #,max_gradient_norm=1
                       ,learning_rate=0.0001 #default
                       #,batch_size=bs
                       #,momentum=0.9
                       ,min_improvement=.005
                       ,patience=5
                       ,validate_every=1
    )

    # assume iter index starts with 0
    if   stateit==0: it=params['iter']+1
    elif stateit==1: it=params['iter']+1
    elif stateit==2: it=params['iter']+1
    elif stateit==3: it=params['iter']-lastiter
    else: raise Exception('undefined state')
    print 'it',it
    import math
    for ait in xrange(it):
        # there is 'err' and 'loss'. mostly the same
        # index 1 is the validation error
        try:
            o= xpit.next()[1]['loss']
            if math.isnan(o):
                raise ValueError('got nan validation')
        except StopIteration: pass
            
    save_net(params,xp.network,run_id=run_id)
    return o #should return the o from the .next() w/o the stopiteration




def test():
    function({'n1':1,'iter':0})
    #function({'n1':1,'iter':0}) # should be a new model
    function({'n1':1,'iter':3}) # should pick up where left off
    #function({'n1':1,'iter':4} #shld pick up where left off
    function({'n1':1,'iter':5}) #shld pick up where left off
    function({'n1':1,'iter':5}) # shld be new
    
def testseq():
    function({'n1':1,'iter':0})
    function({'n1':1,'iter':1}) # should pick up where left off
    function({'n1':1,'iter':2}) #shld pick up where left off
    function({'n1':1,'iter':1}) # should be new

def testtwo():
    function({'n1':1,'iter':9})
    function({'n1':1,'iter':9}) # new

