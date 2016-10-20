# computes user performance on every topic for run, for every user

# DONE do this for Gb and GBd metrics first


import argparse
import os
import bisect
import sys
import numpy as np
import gc

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.WARNING)
#logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class Nugget:
    def __init__(self, ngtid, gain, time):
        self.ngtid = ngtid
        #self.gain = int(gain)
        self.time = float(time)
        self.alpha = 0
        
    def __str__(self):
        return str( (self.ngtid, self.gain, self.time, self.alpha) )

class Update:
    def __init__(self, qid, updid, updtime, updconf, updlen, numngts, ngtstr):
        self.qid = int(qid)
        self.updid = updid
        self.time = float(updtime)
        #self.conf = float(updconf)
        self.wlen = int(updlen)
        self.numngts = int(numngts)
        self.nuggets = []
        if ngtstr or self.numngts:
            for ngts in ngtstr.split():
                #ngtid, gs, ts = 
                self.nuggets.append(Nugget(*ngts.split(',')))
    
    def __str__(self):
        return str( (self.qid, self.updid, self.time, self.conf, self.wlen, self.numngts, [str(n) for n in self.nuggets]) )
        
class Session:
    def __init__(self, start, time_spent, time_away):
        self.time_spent = time_spent
        self.time_away = time_away
        self.start = start
        #self.end = start + time_spent
        
    def __str__(self):
        return str( ( self.start, self.end , self.time_spent, self.time_away) )

def load_user_sessions(outfnamepre, uid, sessions, ssn_starts):
    ttfile = outfnamepre + "time-trails/time-trail-user-" + str(uid)
    print ttfile
    current_time = 0.0
    #if len(sessions):
    #    del sessions[:]
    #    del ssn_starts[:]
    #gc.collect()
    sessions = []
    ssn_starts = []
    with open(ttfile) as tf:
        line = tf.readline() #skip header
        for line in tf:
            ssn_durn, time_away = [float (e) for e in line.strip().split('\t')]
            sessions.append(Session(current_time, ssn_durn, time_away))                
            current_time += (ssn_durn + time_away)                
    ssn_starts = [ssn.start for ssn in sessions]
    
def computeMetrics(run, user_sessions, user_ssn_starts, user_speed, runname, discounts, outuserperf, outmeanperf, outfnamepre):
    
    topic_upd_times = {}  #NOTE: this requires run_gain_file to be sorted appropriately
    for qid in run.keys():
        topic_upd_times[qid] = [ upd.time for upd in run[qid] ]
        #print len(topic_upd_times[qid])
        
    num_discounts = len(discounts)
    mean_avg_Gbd = np.zeros(num_discounts, dtype=float) 
    mean_avg_Gbd_per_updRead = np.zeros(num_discounts, dtype=float) 
    mean_avg_Gbd_per_updInRun = np.zeros(num_discounts, dtype=float)
    mean_avg_Gbd_per_sec = np.zeros(num_discounts, dtype=float) 

    for uid in user_speed:
        #load user time trail keeping arrival and duration
        #keep arrivals separately for alpha computation
        
        sessions = user_sessions[uid]
        ssn_starts = user_ssn_starts[uid] #[ ssn.start for ssn in sessions ]        
        #ttfile = outfnamepre + "time-trails/time-trail-user-" + str(uid)
        ##print ttfile
        #current_time = 0.0
        #sessions = []
        #ssn_starts = []
        #with open(ttfile) as tf:
        #    line = tf.readline() #skip header
        #    for line in tf:
        #        ssn_durn, time_away = [float (e) for e in line.strip().split('\t')]
        #        sessions.append(Session(current_time, ssn_durn, time_away))                
        #        current_time += (ssn_durn + time_away)                
        #ssn_starts = [ssn.start for ssn in sessions]
        
        #user performance metrics per query
        avg_Gbd = np.zeros(num_discounts, dtype=float) 
        avg_Gbd_per_updRead = np.zeros(num_discounts, dtype=float) 
        avg_Gbd_per_updInRun = np.zeros(num_discounts, dtype=float) 
        avg_Gbd_per_sec = np.zeros(num_discounts, dtype=float) 
        
        for qid in sorted(run.keys()):
            if qid == 7: continue
            
            #logger.debug('topic ' + str(qid) + '----------')
            
            updates = run[qid]
            update_times = topic_upd_times[qid]
            
            #for every ssn_start read updates backward and track:
            #  gain, alpha, tws, and all other metrics
            
            #add graded metrics later
            Gbd = np.zeros(num_discounts, dtype=float) 
            Gbd_per_updRead = np.zeros(num_discounts, dtype=float) 
            Gbd_per_updInRun = np.zeros(num_discounts, dtype=float) 
            Gbd_per_sec = np.zeros(num_discounts, dtype=float) 
            num_upd_read = 0 
            tspent = 0.0
            
            #write out already seen nuggets.
            # will be usefull for graded comparisons later. 
            already_seen_ngts = {}
            
            last_read_upd_idx = -1
            for sno in xrange(len(sessions)):
                ssn = sessions[sno]                
                
                #logger.debug('session {}: ctime {}, ssndurn {}, awaytime {}'.format(sno, ssn.start, ssn.time_spent, ssn.time_away ))
                #lo = last_read_upd_idx
                #if lo < 0: lo = 0
                latest_upd_idx = bisect.bisect(update_times, ssn.start) 
                latest_upd_idx -= 1
                #print qid, ssn.start, update_times[latest_upd_idx]
                i = latest_upd_idx
                partial_upd_idx = -1
                reading_time = 0
                while i >= 0 and i > last_read_upd_idx and reading_time < ssn.time_spent:
                    upd = updates[i]
                    
                    #logger.debug('upd_idx {}, upd_id {}'.format(i, upd.updid))
                    
                    #print upd.time, upd.wlen
                    upd_read_time = (upd.wlen / user_speed[uid])                    
                    
                    if reading_time + upd_read_time > ssn.time_spent: #partially read
                        partial_upd_idx = i
                        reading_time += (ssn.time_spent - reading_time)
                        #logger.debug('PARTIAL')
                        break
                    #logger.debug('COMPLETE')
                    num_upd_read += 1
                    reading_time += upd_read_time
                    #print (upd.wlen / user_speed[uid])
                    for ngt in upd.nuggets:
                        if ngt.ngtid in already_seen_ngts: continue
                        ngt_after = bisect.bisect(ssn_starts, ngt.time)
                        alpha = sno - ngt_after 
                        #logger.debug('alpha {} = {} - {}'.format(alpha, sno, ngt_after)) 
                        already_seen_ngts[ngt.ngtid] = alpha                        
                        alpha = 0 if alpha < 0 else alpha
                        #print qid, ngt, alpha
                        for d in xrange(num_discounts):
                            Gbd[d] += (discounts[d] ** alpha)              
                    #logger.debug('msu = {}'.format(Gbd[d]))      
                    i -= 1
                
                if partial_upd_idx == latest_upd_idx: #could not completely read the first update in this ssn
                    pass #do not set last_read_update to this upd
                else:
                    last_read_upd_idx = latest_upd_idx
                tspent += reading_time #for this session                
                
            avg_Gbd += Gbd  
                      
            Gbd_per_updRead = (Gbd/float(num_upd_read)) if num_upd_read > 0 else np.zeros(num_discounts, dtype=float)
            avg_Gbd_per_updRead += Gbd_per_updRead
            # TODO: it may also happen that the updates are too long to be read in one session.
            # This will always lead to zero updates being read
            #~ try:
                #~ avg_Gbd_per_updRead += (Gbd/float(num_upd_read))
            #~ except:
                #~ print Gbd, num_upd_read, tspent
                #~ print [ (ssn.start, ssn.time_spent) for ssn in sessions ]
                #~ print user_speed[uid]
                #~ print [ (upd.time, upd.wlen, upd.wlen/user_speed[uid]) for upd in updates ]
                #~ exit()
                
            num_upd_inRun = len(updates)
            Gbd_per_updInRun = (Gbd/float(num_upd_inRun))
            avg_Gbd_per_updInRun += Gbd_per_updInRun
	    
            Gbd_per_sec = (Gbd/tspent) if tspent > 0 else np.zeros(num_discounts, dtype=float)
            #~ try:
                #~ Gbd_per_sec = (Gbd/tspent)
            #~ except:
                #~ print Gbd, num_upd_read, tspent
                #~ print [ (ssn.start, ssn.time_spent, ssn.time_away) for ssn in sessions ]
                #~ print user_speed[uid]
                #~ print [ (upd.time, upd.wlen, upd.wlen/user_speed[uid]) for upd in updates ]
                #~ exit()		
            avg_Gbd_per_sec += Gbd_per_sec
            #print uid, qid, gain_bin, gain_bin_disc
            
            nuggets_seen = ' '.join([k+','+str(v) for k, v in already_seen_ngts.items()])
            
            for d in xrange(num_discounts):
                print >> outuserperf[d], '\t'.join([str(x) for x in [runname, uid, qid, Gbd[d], Gbd_per_updRead[d], Gbd_per_updInRun[d], Gbd_per_sec[d], num_upd_read, num_upd_inRun, tspent, nuggets_seen]])
        
        num_topics =  len(run.keys()) - 1 #9;  # some runs have only 9 topics so len(run.keys() -1 is wrong
        #logger.debug('run keys ' + str(run.keys()))
        avg_Gbd /= num_topics
        avg_Gbd_per_updRead /= num_topics
        avg_Gbd_per_updInRun /= num_topics
        avg_Gbd_per_sec /= num_topics
        #print uid, qid, avg_Gbd, avg_Gbd_per_updRead, avg_Gbd_per_updInRun, avg_Gbd_per_sec
        
        mean_avg_Gbd += avg_Gbd
        mean_avg_Gbd_per_updRead += avg_Gbd_per_updRead
        mean_avg_Gbd_per_updInRun+= avg_Gbd_per_updInRun
        mean_avg_Gbd_per_sec += avg_Gbd_per_sec        
        
        # logger.warning('breaking MSU after users. TODO: remove this')
        # if uid == 2:
        #     break
        
    
    mean_avg_Gbd /= 1000
    mean_avg_Gbd_per_updRead /= 1000
    mean_avg_Gbd_per_updInRun /= 1000
    mean_avg_Gbd_per_sec /= 1000
    
    for d in xrange(num_discounts):    
        print >> outmeanperf[d], '\t'.join([str(x) for x in [ runname, mean_avg_Gbd[d], mean_avg_Gbd_per_updRead[d], mean_avg_Gbd_per_updInRun[d], mean_avg_Gbd_per_sec[d]]])

def load_gain_attached_run(run_gain_file, run):
    
    print >> sys.stderr, 'loading gain attached run', run_gain_file
    #run = {}
    
    with open(run_gain_file) as rf:
        for line in rf:            
            fields = line.strip().split('\t')                        
            #print fields
            upd = None
            if len(fields) == 6:
                fields += [""]        
            
            qid, updtime, updconf, updid, updlen, numngts, ngtstr = fields
            #NOTE: updid comes after confidence in gain attached runs
            upd = Update(qid, updid, updtime, updconf, updlen, numngts, ngtstr)
            #print upd
            if upd.qid not in run:
                run[upd.qid] = []
                
            run[upd.qid].append(upd)
            
    assert(len(run.keys()) == 10)
    #return run
    #for k in sorted(run.keys()):
    #    print k, len(run[k])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="computes cumulative gain and other metrics for every user model, for every topic, in all runs. outputs params.mean.metrics params.user.performance files")
    ap.add_argument("user_params", help="file listing user parameters, one user on each line") # for reading speed input 
    ap.add_argument("time_trail_folder", help="paths prefix for output files")
    #ap.add_argument("discount", type=float, help="value of discount to be used for alpha (#ssn since ngt.time)")
    ap.add_argument("runfiles", nargs="+", help="all the run with gain attached files")
    #ap.add_argument("topic_query_durns", help="file containing list of topic query-durations")
    #ap.add_argument("update_lengths_folder", help="folder containing files containing update lengths")
    ap.add_argument("--discount", help="specific discount value. (produces multiple outputs based on discounts by default).", type=float)
    
    args = ap.parse_args()
    print >> sys.stderr, args
    
    discounts = [0.1, 0.25, 0.5, 0.75, 0.9, 0, 1 ]
    
    if args.discount:
        discounts = [args.discount]
    
    outfnamepre = args.user_params[:-len("user.params")]
    print >> sys.stderr, outfnamepre
    
    
    print >> sys.stderr, 'loading user reading speeds'    
    user_speed = {}
    userc = 1
    with open(args.user_params) as uf:
        line = uf.readline(); #skip header  
        for line in uf:     
            inter_arrival_time, avg_ssn_durn, reading_speed = [float(e) for e in line.strip().split('\t') ]
            #NOTE: ssn_durn is currently resampled at every arrival. We have the option to simulate the session duration about a mean.
            user_speed[userc] = reading_speed  #other variables work in the time-trail
            #users[userc] = (inter_arrival_time, avg_ssn_durn, reading_speed)
            userc += 1     

    print >> sys.stderr, 'preloading sessions'
    user_sessions = {}
    user_ssn_starts = {}
    for uid in user_speed:
        ttfile = outfnamepre + "time-trails/time-trail-user-" + str(uid)
        #print ttfile
        current_time = 0.0
        user_sessions[uid] = []
        with open(ttfile) as tf:
            line = tf.readline() #skip header
            for line in tf:
                ssn_durn, time_away = [float (e) for e in line.strip().split('\t')]
                user_sessions[uid].append(Session(current_time, ssn_durn, time_away))                
                current_time += (ssn_durn + time_away)                
        user_ssn_starts[uid] = [ssn.start for ssn in user_sessions[uid]]
    gc.collect()
    

    user_model_pre = outfnamepre
    print >> sys.stderr, 'writing out files prefixes' # for different lateness discounts
    paramid = int(os.path.basename(outfnamepre)[:-1])
    outdir = os.path.dirname(outfnamepre)
    outuserperf = []
    outmeanperf = []
    for d in xrange(len(discounts)):
        print >> sys.stderr, outfnamepre
        outuserperf.append(open(outfnamepre + "user.metrics", 'w'))
        outmeanperf.append(open(outfnamepre + "mean.metrics", 'w'))
        print >> outmeanperf[d], 'runname\tGbd\tGbd_per_updRead\tGbd_per_updInRun\tGbd_per_sec' 
        print >> outuserperf[d], 'runname\tuid\tqid\tGbd\tGbd_per_updRead\tGbd_per_updInRun\tGbd_per_sec\tnum_upd_read\tnum_upd_inRun\ttspent\tnuggets_alpha' 
        #paramid += 324
        paramid += 54  #for reasonable
        outfnamepre = os.path.join(outdir, str(paramid) + ".")
        # TODO: change this multiple default id issue for release
        
        
    run = {}
    for runfile in args.runfiles:
        #runname = runfile.split('.')[1]
        runname = os.path.basename(runfile).split('.')[1]
        run.clear()
        run = {}
        load_gain_attached_run(runfile,run)
        gc.collect()
        print >> sys.stderr, 'computing user performance for', runfile
        computeMetrics(run, user_sessions, user_ssn_starts, user_speed, runname, discounts, outuserperf, outmeanperf, user_model_pre) 
        
    for d in xrange(len(discounts)):
        outuserperf[d].close()
        outmeanperf[d].close()
    
    print >> sys.stderr, 'output files are:'
    print >> sys.stderr, '\n'.join([ f.name for f in outmeanperf])    
        
        
