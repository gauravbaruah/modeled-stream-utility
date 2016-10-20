# module to pre-process the
# 1. qrels
# 2. runs
# of the Temporal Summarization track (TST) 2013 for evaluation using Modeled Stream
# Utility

# NOTE: Length of Updates
# 1. The length of each update submitted by every participating system was
# computed by searching for the update given the update-id in the KBA Stream
# corpus 2013. 
# 2. The length of each update was recorded as the number of tokens split by
# whitespace.
# 3. In all 6,224,892 updates were submitted accross all topics by all the
# participating runs.
# 4. The mapping from update-id to word-length and char-length is 330MB
# uncompressed.
# 5. Please email gbaruah [at] uwaterloo [dot] ca for related data and
# information.
# 6. Lengths for updates can also be downloaded from TBD TODO

# NOTE: Topic query durations
# 1. For TST 2013, the query duration spans 10 days for each topic. However
# the exact times at which each query is different
# 2. We normalize the query duration to span from 0 seconds to 864000 seconds
# as the query duration.
# 3. The update timestamps and the nugget timestamps are also normalized to
# fall within this range for each topic.
# 4. The data/qrels/topic_query_durns file contains the exact start and end times for
# each topic. Data from this file is used to normalize respective timestamps
# for the topics updates and nuggets.


# Preprocessing of the TST 2013 runs and qrels
# - attaches gain against every update in the run
# - prints out the run sorted by (time, conf)
# - ** expected output **
#   - each line is tab-separated and has the following fields:
#     - qid, 0-normalized-update-timestamp, update-confidence, update-id,
#       update-length-in-words, number-of-nuggets, {nuggets-in-update}
#     - {nuggets-in-update} is a space-separated string of:
#       - {nugget-1-data} {nugget-2-data} {nugget-3-data} ...
#     - {nugget-x-data} is a comma-separated string containing:
#       - nugget-id, nugget-importance, nugget-timestamp
# - ** example output **: topic 2 from input.CosineEgrep run [TST 2013]
#   ```
#   2       3600.0  2.0     1347368668-e91e25cdce508351fbe294623a5c95c9-47  9      0       
#   2       3600.0  3.0     1347371604-0ee2fe22eac34ca3ffb67338573c6fbf-4   112    2       VMTS13.02.067,3,165005.0 VMTS13.02.057,3,164256.0 
#   2       147600.0        1.0     1347509804-69ff1ba01b750de4553f1613367d265b-3 807     0       
#   ```
# This output format is required as input for modeled_stream_utility.py

import argparse
import os

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description="attaches gain against every update in run")
    ap.add_argument("matches")
    ap.add_argument("nuggets")
    ap.add_argument("pool") #add duplicates from pool to the update --> nugget map
    ap.add_argument("topic_query_durns") # to set time to begin at 0 seconds   
    ap.add_argument("update_lengths_folder") # update lengths are required for each update
    ap.add_argument("run_file") 
    ap.add_argument("outfile")
    
    args = ap.parse_args()
    
    
    print 'identify duplicate updates from the pool'
    duplicates = {}
    with open(args.pool) as pf:
        line = pf.readline()    #header
        for line in pf:
            qid, updid, doc_id, sentence_id, update_len, duplicate_of_id, update_text = line.strip().split('\t')
            qid = int(qid)
            if qid not in duplicates:
                duplicates[qid] = {}
            if duplicate_of_id == "NULL": continue
            if duplicate_of_id not in duplicates[qid]:
                duplicates[qid][duplicate_of_id] = set()
            duplicates[qid][duplicate_of_id].add(updid)  #updid is duplicate_of upd with id
            
    # ignored topics in the pool
    duplicates[7] = {} 
    duplicates[9911] = {} 
    
    # note relevant updates (and their duplicates)
    # keep track of nuggets present in each relevant update 
    print 'reading in matches, tracking duplicates'
    matches = {}
    with open(args.matches) as mf:
        line = mf.readline()    #header
        for line in mf:
            qid, update_id, nugget_id, match_start, match_end, auto_p = line.strip().split()
            qid=int(qid)
            if qid not in matches:
                matches[qid] = {}
            if update_id not in matches[qid]:
                matches[qid][update_id] = []
            matches[qid][update_id].append(nugget_id)
            if update_id in duplicates[qid]:
                for dup in duplicates[qid][update_id]:
                    if dup not in matches[qid]:
                        matches[qid][dup] = []
                    matches[qid][dup].append(nugget_id)
                    # --> add the duplicates of relevant updates to the matches as well.
    
    # load query durations.
    # this helps to start every duration with 0                
    query_durns = {}
    with open(args.topic_query_durns) as qdf:
        for line in qdf:
            qid, qstart, qend = line.strip().split()
            qid=int(qid)
            query_durns[qid] = (float(qstart), float(qend))

    print 'load nuggets and their timestamp and importance'
    nuggets = {}
    with open(args.nuggets) as ngf:
        line = ngf.readline()   #header
        for line in ngf:
            query_id, nugget_id, timestamp, importance, nugget_len, nugget_text = line.strip().split('\t')
            if not query_id.isdigit(): continue
            query_id = int(query_id)
            if query_id not in nuggets:
                nuggets[query_id] = {}
            nuggets[query_id][nugget_id] = (int(importance), float(timestamp) - query_durns[query_id][0])

    print 'reading in update lengths'
    updlens = {}
    for qid in xrange(1,11):
        with open(os.path.join(args.update_lengths_folder, str(qid) + ".updid-char-word.len")) as lf:
            for line in lf:
                tid, updid, clen, wlen = line.strip().split()
                tid = int(tid)
                if tid not in updlens:
                    updlens[tid] = {}
                updlens[tid][updid] = int(wlen)

    # attaching gain to the updates 
    print 'reading in the run' , args.run_file
    run = {}
    with open(args.run_file) as rf:
        for line in rf:
            if len(line.strip()) == 0: continue
            qid, teamid, runid, docid, sentid, updtime, confidence = line.strip().split() 
            qid = int(qid)
            updid = docid + '-' + sentid
            updtime = float(updtime) - query_durns[qid][0] # timestamps to start from 0
            confidence = float(confidence)
            updlen = 30      #default updlen is 0 ## this is in case we do not have the length for updid
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
    
    print 'sorting updates by conf and time and writing out file'
    with open(args.outfile, 'w') as of:
        for qid in sorted(run.keys()):
            upds = run[qid]
            upds.sort(key=lambda x: x[1]) 
            #NOTE: for updates emitted at the same time, we are breaking ties by confidence
            #NOTE: we are sorting confidence in ascending order BECAUSE we are reading the stream backwards.
            upds.sort(key=lambda x: x[0])  
            #NOTE: since python sort is stable, the second sort by time works to keep corrent confidence order  
            # https://docs.python.org/2/howto/sorting.html#sort-stability-and-complex-sorts
            for u in upds:                
                print >> of, '\t'.join( [str(qid)] + [str(v) for v in u] )
        
