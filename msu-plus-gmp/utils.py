import argparse
import os
from operator import itemgetter
import time
import math
import xml.etree.ElementTree as ET
import sys

from collections import defaultdict
import json

def read_in_pool_file(pool_file):
    pool = {}
    duplicates = {}
    with open(pool_file) as pf:
        line = pf.readline()    #header
        for line in pf:
            qid, updid, doc_id, sentence_id, update_len, duplicate_of_id, update_text = line.strip().split('\t')
            #qid = int(qid)
            if qid not in duplicates or qid not in pool:
                duplicates[qid] = {}
                pool[qid] = set()

            pool[qid].add(updid)
            
            if duplicate_of_id == "NULL": # not a duplicate                
                continue
            if duplicate_of_id not in duplicates[qid]:
                duplicates[qid][duplicate_of_id] = set()
            duplicates[qid][duplicate_of_id].add(updid)  #updid is duplicate_of upd with id
    return pool, duplicates
    
def read_in_matches_track_duplicates(matches_file, duplicates):
    matches = {}
    with open(matches_file) as mf:
        line = mf.readline()    #header
        for line in mf:
            qid, update_id, nugget_id, match_start, match_end, auto_p = line.strip().split()
            #qid=int(qid)
            if qid not in matches:
                matches[qid] = {}
            if update_id not in matches[qid]:
                matches[qid][update_id] = []
            matches[qid][update_id].append(nugget_id)
            if qid in duplicates and update_id in duplicates[qid]:
                for dup in duplicates[qid][update_id]:
                    if dup not in matches[qid]:
                        matches[qid][dup] = []
                    matches[qid][dup].append(nugget_id)
    return matches
    
def read_in_nuggets(nuggets_file, query_durns):
    nuggets = {}
    with open(nuggets_file) as ngf:
        line = ngf.readline()   #header
        for line in ngf:
            query_id, nugget_id, timestamp, importance, nugget_len, nugget_text = line.strip().split('\t')
            #if not query_id.isdigit(): continue
            #query_id = int(query_id)
            if query_id not in nuggets:
                nuggets[query_id] = {}
            if query_id in query_durns:
                nuggets[query_id][nugget_id] = (int(importance), float(timestamp) - query_durns[query_id][0])
    return nuggets
    
def read_in_update_lengths(update_lengths_folder, track="ts13"):
    updlens = {}
    
    for lenfile in os.listdir(update_lengths_folder):
        if not lenfile.endswith(".len"):
            continue                
        with open(os.path.join(update_lengths_folder, lenfile)) as lf:            
            for line in lf:
                tid, updid, clen, wlen = "", "", "", ""
                if track == 'ts13':
                    tid, updid, clen, wlen = line.strip().split()
                elif track == 'ts14':
                    #print >> sys.stderr, line                    
                    tid, updid, wlen = line.strip().split()
                    tid = 'TS14.'+tid
                #tid = int(tid)
                if tid not in updlens:
                    updlens[tid] = {}
                updlens[tid][updid] = int(wlen)
    
    # get average lengths per topic
    for qid, update_lengths in updlens.items():
        avg = math.fsum(update_lengths.values())
        avg /= len(update_lengths)
        updlens[qid]["topic.avg.update.length"] = avg
        print >> sys.stderr,  qid,  avg
    return updlens
    

def read_in_run_attach_gain(runfile, updlens, matches, useAverageLengths):
    run = {}
    with open(runfile) as rf:
        for line in rf:
            if len(line.strip()) == 0: continue
            qid, teamid, runid, docid, sentid, updtime, confidence = line.strip().split() 
            #qid = int(qid)
            updid = docid + '-' + sentid
            updtime = float(updtime) - query_durns[qid][0] # timestamps to start from 0
            confidence = float(confidence)
            updlen = 30 if not useAverageLengths else updlens[qid]["topic.avg.update.length"]     #default updlen is 0
            if updid in updlens[qid]:
                updlen = updlens[qid][updid]
            else:
                pass
                #print >> sys.stderr, 'no length for ', updid
            
            if qid not in run:
                run[qid] = []
                
            #gain for update
            ngtstr = ""
            num_ngts = 0
            if updid in matches[qid]:  #update is relevant                
                ngts_in_upd = matches[qid][updid]                
                for ngtid in ngts_in_upd:
                    if ngtid not in nuggets[qid]: # there are 2 nuggets not in nuggets.tsv
                        continue
                    num_ngts += 1
                    ngt_gain, ngt_time = nuggets[qid][ngtid]      
                    ngtstr += ','.join([ str(s) for s in [ngtid, ngt_gain, ngt_time] ])
                    ngtstr += ' '              
            
            run[qid].append( [updtime, confidence, updid, updlen, num_ngts, ngtstr] )
    return run
    
def get_topic_query_durations(topicfile, track):
    tree = ET.parse(topicfile)
    events = tree.getroot()
    tqd = dict()
    for event in events:
        id, start, end = None, None, None
        for child in event:
            if child.tag == 'id':
                #print child.text
                id = child.text
                if track == 'ts14':
                    id = 'TS14.' + id
            if child.tag == 'start':
                #print child.text
                start = child.text
            if child.tag == 'end':
                #print child.text
                end = child.text
        tqd[id] = (float(start), float(end))
    return tqd

def microblog_set_topic_query_durations(topics, track):
    start , end = 0, 0
    if track == 'mb15':
        #Evaluation start: Monday, July 20, 2015, 00:00:00 UTC
        #Evaluation end: Wednesday, July 29, 2015, 23:59:59 UTC
        start = 1437350400.0
        end = 1438214399.0
    tqd = dict()
    for qid in topics:
        tqd[qid] = (start, end)
    return tqd

def microblog_read_in_qrels(qrelFile):
    qrels = {}
    with open(qrelFile) as qf:
        for line in qf:
            qid, q0, updid, rel = line.strip().split()
            if qid not in qrels:
                qrels[qid] = {}
            rel = int(rel)
            if rel == 3: rel = 1
            if rel == 4: rel = 2
            if rel == -1: rel = 0
            qrels[qid][updid] = rel
    return qrels

def microblog_read_int_tweet_epochs(epochFile):
    
    tweet_emit_times = defaultdict(float)
    with open(epochFile) as ef:
        for line in ef:            
            tweet, day, epoch = line.strip().split()
            tweet_emit_times[tweet] = float(epoch)
    return tweet_emit_times

def microblog_read_in_clusters(nuggetsFile, query_durns, matches, tweet_emit_times):
    clusters = {}
    clid = 0
    with open(nuggetsFile) as nf:
        data = json.load(nf)
        topics = data["topics"]
        for qid in topics:
            qid = qid.replace("MB", "")
            if qid not in clusters:
                clusters[qid] = {}
            for cluster in topics["MB"+qid]["clusters"]:
                clid += 1
                for tweet in cluster:
                    tweet_rel = matches[qid][tweet]
                    tweet_time = tweet_emit_times[tweet] - query_durns[qid][0]
                    if clid not in clusters[qid]:
                        clusters[qid][clid] = [tweet_rel, tweet_time]
                    else:
                        clusters[qid][clid] = [tweet_rel if tweet_rel > clusters[qid][clid][0] else clusters[qid][clid][0], 
                                                tweet_time if tweet_time < clusters[qid][clid][1] else clusters[qid][clid][1] ]
                                        
                    matches[qid][tweet] = clid
    return clusters
                

    
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="attaches gain against every update in run")
    ap.add_argument("matches")
    ap.add_argument("nuggets")
    ap.add_argument("pool") #add duplicates from pool to the update --> nugget map
    ap.add_argument("topic_query_durns") # to set time to begin at 0 seconds   
    ap.add_argument("update_lengths_folder", help="should contain \"<qid>*.len\" files containing (qid, updid, charlen, wordlen) columns per line") # update lengths are required for each update
    ap.add_argument("--useAverageLengths", action="store_true", help="user average topic lengths for updates for which lengths are unavailable")
    ap.add_argument("run_file") 
    ap.add_argument("outfile")
    
    args = ap.parse_args()
    
    
    # load query durations.
    # this helps to start every duration with 0                
    query_durns = {}
    with open(args.topic_query_durns) as qdf:
        for line in qdf:
            qid, qstart, qend = line.strip().split()
            #qid=int(qid)
            query_durns[qid] = (float(qstart), float(qend))
    
        
    print 'identify duplicate updates from the pool'
    tstart = time.time()
    # all duplicates have the same relevance judgement.
    duplicates = read_in_pool_file(args.pool)
    print time.time() - tstart
                
    # ignored topics in the pool
    duplicates[7] = {} 
    duplicates[9911] = {}
    duplicates[11] = {} 
    
    # note relevant updates (and their duplicates)
    # keep track of nuggets present in each relevant update 
    print 'reading in matches, tracking duplicates'
    tstart = time.time()
    matches = read_in_matches_track_duplicates(args.matches, duplicates)
    print time.time() - tstart
    
    print 'load nuggets and their timestamp and importance'
    tstart = time.time()
    nuggets = read_in_nuggets(args.nuggets, query_durns)    
    print time.time() - tstart

   
    print 'reading in update lengths'
    tstart = time.time()
    updlens = read_in_update_lengths(args.update_lengths_folder)    
    print time.time() - tstart

   

    
    # attaching gain to the updates 
    print 'reading in the run' , args.run_file
    tstart = time.time()
    run = read_in_run_attach_gain(args.run_file, updlens, matches, args.useAverageLengths)
    print time.time() - tstart
    
    print 'sorting updates by conf and time and writing out file'
    tstart = time.time()
    with open(args.outfile, 'w') as of:
        for qid in sorted(run.keys()):
            upds = run[qid]
            
            # NOTE: sort by update id first for breaking ties in confidence
            # and time (rare - due to floating point confidence - but can
            # occur), see comments below             
            upds.sort(key=itemgetter(2))
            #print 'TODO: ENABLE THIS COMMENT' 
            # NOTE: ^this was not in part of the original MSU code
            
            # sort by increasing confidence             
            upds.sort(key=itemgetter(1))
            # NOTE: for updates emitted at the same time, we are breaking ties
            # by confidence
            # NOTE: we are sorting confidence in ascending order BECAUSE we
            # are reading the stream backwards.

            # sort by increasing time             
            upds.sort(key=itemgetter(0))
            # NOTE: since python sort is stable, the second sort by time works
            # to keep corrent confidence order  
            # https://docs.python.org/2/howto/sorting.html#sort-stability-and-complex-sorts
            
            ##upds.sort(key=itemgetter(0, 1, 2))
            # NOTE: using operator.itemgetter is slightly faster
            # NOTE: sorting individually is slightly faster than using a
            # composite key tuple. WHY? I _guess_ its because of the stable
            # sorting of python _AND_ because the update-ids are prefixed with
            # a unix-time-stamp. Thus subsequent sorts are faster after the
            # initial sorting by update-id.
            # - NOTE: this means that there would be slight change in results 
            #   because of the change in updates sort order

            # write out to file
            for u in upds:                
                print >> of, '\t'.join( [str(qid)] + [str(v) for v in u] )
    print time.time() - tstart
