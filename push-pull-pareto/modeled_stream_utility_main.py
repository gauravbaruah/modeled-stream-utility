# This script is the main.py that calls other MSU modules as per command line 
# arguments. We try to include all command line arguments here in order to 
# leave the other MSU class files cleaner.

import sys
import os
import gc
import argparse
import bisect
from collections import defaultdict
import operator
import heapq
import array
import re

import utils
from modeled_stream_utility_push_ranked_order import MSUPushRankedOrder

# logging setup
import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.WARNING)
logger.setLevel(logging.INFO)
#logger.setLevel(logging.DEBUG)



ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

def logargs(func):
    def inner(*args, **kwargs):
        logger.info('%s : %s %s' % (func.__name__, args, kwargs))
        return func(*args, **kwargs)
    return inner

def get_msu_evaluator_for_interface_and_interaction(args):
    MSU = None
    Apop_mean, Apop_stdev = args.time_away_population_params

    if args.interaction_mode == "only.push":        
        if args.interface_type == "ranked":
            MSU = MSUPushRankedOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "chrono":
            MSU = MSUPushChronoOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "reverse.chrono":
            MSU = MSUPushReverseOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
    elif args.interaction_mode == "only.pull":
        if args.interface_type == "ranked":
            MSU = MSUPullRankedOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "chrono":
            MSU = MSUPullChronoOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "reverse.chrono":
            MSU = MSUPullReverseOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
    elif args.interaction_mode == "push.pull":
        if args.interface_type == "ranked":
            MSU = MSUPushPullRankedOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "chrono":
            MSU = MSUPushPullChronoOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
        elif args.interface_type == "reverse.chrono":
            MSU = MSUPushPullReverseOrder(args.num_users, args.persistence_population_params, 
                    Apop_mean, Apop_stdev, args.user_latency, args.window_size, 
                    args.user_persistence, args.user_time_away_mean, args.user_reading_mean, 
                    args.push_threshold, args.interaction_mode)
    assert(MSU)
    return MSU


if __name__ == '__main__':

    ap = argparse.ArgumentParser(description="computes Modeled Stream Utility for systems.")
    
    # which type of MSU
    ap.add_argument("interaction_mode", choices=['only.push', 'only.pull', 'push.pull'])
    ap.add_argument("interface_type", choices=["ranked", "chrono", "reverse.chrono"])

    # which TREC track (dataset)
    ap.add_argument("track", choices=["ts13", "ts14", "mb15", "rts16"])
    ap.add_argument("-m", "--matchesFile", help="the qrel file (for tweets) or the matches file (for updates)")
    ap.add_argument("-n", "--nuggetsFile", help="the clusters file (for tweets) or the nuggets file (for updates)")
    ap.add_argument("--poolFile", help="needed for the TS tracks for tracking duplicates and if --restrict_runs_to_pool is active ") 
    ap.add_argument("-t", "--track_topics_file") # to set time to begin at 0 seconds   
    ap.add_argument("-l", "--update_lengths_folder", help="should contain \"<qid>*.len\" files containing (qid, updid, charlen, wordlen) columns per line") # update lengths are required for each update    
    ap.add_argument("--tweetEpochFile", help="tweet2dayepoch file needed for emit times of tweet ")
    
    # system settings
    ap.add_argument("-w", "--window_size", type=int, default=86400, help="updates older than window_size from current session will not be shown to user (window_size = -1 --> all updates since start of query duration will be shown)")
    ap.add_argument("--push_threshold", type=float, default=0.0, help="updates over this threshold are sent as push notifications")
    
    # user(s) settings
    ap.add_argument("-u", "--num_users", type=int, default=1)        
    ap.add_argument("--user_persistence", type=float)
    ap.add_argument("--user_latency", type=float, default=1.0)
    ap.add_argument("--user_time_away_mean", type=float)
    ap.add_argument("--user_reading_mean", type=float)    
    
    # legacy arguments (not in use)
    ap.add_argument("-Apop", "--time_away_population_params", nargs=2, type=float, help="population time away mean and stddev", default=[10800.0, 5400.0])
    ap.add_argument("-Ppop", "--persistence_population_params", nargs=2, type=float, help="population RBP persistence mean and stddev", default=[0.2, 0.2])
    
    # MSU evaluation settings
    ap.add_argument("--restrict_runs_to_pool", action="store_true", help="the runs are restricted to their pool contributions")
    ap.add_argument("--ignore_verbosity", action="store_true", help="ignore verbosity computations i.e. user reading speed does not affect reading of updates", default=False)

    # systems to be evaluated
    ap.add_argument("runfiles", nargs="+")
   
    args = ap.parse_args()
    print (args, file=sys.stderr)

    # reading in track data -------------------------------------------------    
    if args.track in ['ts13', 'ts14']:
        if None in [args.nuggetsFile, args.matchesFile, args.poolFile, args.update_lengths_folder, args.track_topics_file]:
            logger.error('arguments -n -m --poolFile -t -l  are needed with track {}'.format(args.track))
            sys.exit()

        # load query durations.
        # this helps to start every duration with 0                
        logger.warning('getting topic query durations')
        query_durns = utils.get_topic_query_durations(args.track_topics_file, args.track)    
        for topic, durn in query_durns.items():
            print (topic, float(durn[1] - durn[0]), file=sys.stderr)
        #sys.exit()
            
        logger.warning('identify duplicate updates from the pool')
        # all duplicates have the same relevance judgement.
        pool, duplicates = utils.read_in_pool_file(args.poolFile)
                    
        # ignored topics in the pool
        if args.track == "ts13":
            duplicates['7'] = {} 
            duplicates['9911'] = {} 
                        
        # note relevant updates (and their duplicates)
        # keep track of nuggets present in each relevant update 
        logger.warning('reading in matches, tracking duplicates')
        matches = utils.read_in_matches_track_duplicates(args.matchesFile, duplicates)

        if args.track == 'ts13':
            matches.pop('11', None)
            matches.pop('9911', None)
            matches.pop('7', None)
        
        logger.warning('load nuggets and their timestamp and importance')
        nuggets = utils.read_in_nuggets(args.nuggetsFile, query_durns)    
        
        logger.warning('reading in update lengths')
        updlens = utils.read_in_update_lengths(args.update_lengths_folder, args.track)    
    
    if args.track in ['mb15', 'rts16']:
        if None in [args.nuggetsFile, args.matchesFile, args.tweetEpochFile]:
            logger.error('arguments -n -m --tweetEpochFile are needed with track {}'.format(args.track))
            sys.exit()

        # read in qrels
        logger.warning('reading in qrels')
        matches = utils.microblog_read_in_qrels(args.matchesFile)

        logger.warning('set topic query durations')
        query_durns = utils.microblog_set_topic_query_durations(matches.keys(), args.track)    

        logger.warning('reading in tweet emit times (epoch)')
        tweet_emit_times = utils.microblog_read_int_tweet_epochs(args.tweetEpochFile)
                    
        logger.warning('load clusters and get their earliest timestamp ')
        nuggets = utils.microblog_read_in_clusters(args.nuggetsFile, query_durns, matches, tweet_emit_times, args.track)    
        
        logger.warning('reading in update lengths --> Not Applicable for this track')
        # updlens = utils.read_in_update_lengths(args.update_lengths_folder, args.track)    
        
        args.push_threshold = 0.0

    logger.warning('track {}. number of keys {}'.format(args.track, len(matches.keys())))
    #logger.warning('track {}. number of nuggets for topics \n{}'.format(args.track, '\n'.join(['{}\t{}'.format(qid, len(nuggets)) for qid, nuggets in nuggets.items()])))
    

    # setting up MSU parameters -------------------------------------------
    MSU = get_msu_evaluator_for_interface_and_interaction(args)
    MSU.track = args.track
    MSU.ignore_verbosity = args.ignore_verbosity
    
    run = {}
    for runfile in args.runfiles:
        run.clear()
        run = {}
        gc.collect()   
        if args.track == 'rts16' and os.path.splitext(os.path.basename(runfile))[0] in ['iitbhu-15']:
            logger.warning('ignoring bad run {}. See TREC-RTS-Tracks/2016/scenarioA/eval-scripts/README.txt'.format(runfile))
            continue
        if args.track == 'mb15' and  os.path.splitext(os.path.basename(runfile))[0] in ['DALTRECAA1', 'DALTRECMA1', 'DALTRECMA2']:
            logger.warning('ignoring bad run {}. Run has too many tweets --> bad for analysis'.format(runfile))
            continue

        logger.warning('loading runfile ' + runfile )
        try:            
            run = None
            if args.track in ['ts13', 'ts14']:
                run = MSU.load_run_and_attach_gain(runfile, updlens, nuggets, matches, True, args.track, query_durns, pool, args.restrict_runs_to_pool) 
            elif args.track in ['mb15', 'rts16']:
                run = MSU.microblog_load_run_and_attach_gain(runfile, nuggets, matches, args.track, query_durns)
            
            logger.warning('run total updates {} in {} topics'.format(sum([len(v) for v in run.values()]), len(run)))
            ignored_qid = "7" if args.track == "ts13" else ""
            if ignored_qid in run:
                run.pop(ignored_qid)
        except Exception as e:
            logger.error('ERROR: could not load runfile ' + runfile)
            logger.error('EXCEPTION: ' + str(e))
            exit(0)

               
        logger.warning('computing MSU... for {} topics'.format(len(matches.keys())))
        run_msu, run_pain = MSU.compute_population_MSU(run, query_durns, len(matches.keys()))
        # TODO: keep track of all the nuggets found
        
        printkeys = None
        if args.track in ["ts13", "mb15"]:
            # print in sorted qid order when topic ids are numeric
            keys = filter(lambda x: x.isdigit(), run_msu.keys())
            printkeys = list(map(str,sorted(map(int, keys)))) + ["AVG"]
        elif args.track in ['ts14', 'rts16']:
            # print in sorted qid order when topic ids are strings
            keys = filter(lambda x: x != 'AVG' , run_msu.keys())
            printkeys = sorted(keys, key=lambda x: int(re.findall(r'\d+', x)[0]) ) + ['AVG']
        
        
        for topic in printkeys:
            msu = run_msu[topic]
            pain = run_pain[topic]
            runname = os.path.basename(runfile)
            if args.track == 'ts13':
                runname = runname.replace("input.", '')
            if args.track in ['mb15', 'rts16']:
                runname = os.path.splitext(runname)[0]
                
            print ('{}\t{}\t{:.3f}\t{:.3f}'.format(runname, topic, msu, pain))
