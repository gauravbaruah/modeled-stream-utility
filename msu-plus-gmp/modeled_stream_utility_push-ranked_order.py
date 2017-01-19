# MSU evaluation with a ranked order of presentation

import sys
import os
import gc
import argparse
import bisect
from collections import defaultdict
import operator
import heapq
import array

from cython_computations import _compute_push_ranked_user_MSU

from update import Update
from nugget import Nugget
from population_model import LognormalAwayPersistenceSessionsPopulationModel
from user_model import LognormalAwayRBPPersistenceUserModel
from user_interface_model import PushRankedInterfaceMixin

from modeled_stream_utility import ModeledStreamUtility

import utils

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


class MSUPushRankedOrder(ModeledStreamUtility, PushRankedInterfaceMixin):
    """
    Simulates users reading updates in ranked order at every session.
    Users persist in reading updates at every session based on the RBP user model [Moffat, TOIS 2008]
    """

    def __init__(self, num_users, RBP_persistence_params, \
        population_time_away_mean, population_time_away_stddev, \
        lateness_decay, 
        window_size,
        fix_persistence, 
        fix_away_mean, 
        fix_reading_mean, 
        push_threshold, 
        interaction_mode):

        super(MSUPushRankedOrder, self).__init__(num_users)

        self.population_model = LognormalAwayPersistenceSessionsPopulationModel(self.seed,
                                population_time_away_mean, \
                                population_time_away_stddev, \
                                RBP_persistence_params, \
                                lateness_decay, )

        self.sampled_users = []
        self.update_emit_times = []
        self.update_confidences = []
        self.update_lengths = []                                                                                                    
        self.window_size = window_size
        self.fix_persistence = fix_persistence        
        self.fix_reading_mean = fix_reading_mean
        self.fix_away_mean = fix_away_mean        
        self.push_threshold = push_threshold
        self.interaction_mode = interaction_mode 
        self.user_counter = 0

    def normalize_confidences(self):
        #logger.warning(self.update_confidences)
        maxconf = max(self.update_confidences)
        minconf = min(self.update_confidences)
        if maxconf == minconf:
            maxconf = 1.0
            minconf = 0.0
        self.update_confidences = array.array('d', map(lambda x: (x - minconf)/(maxconf - minconf), self.update_confidences))
        #logger.warning(self.update_confidences)

    def initialize_structures_for_topic(self, topic_updates):
        self.presort_updates(topic_updates)
        self.update_emit_times = array.array('d', [ upd.time for upd in topic_updates ])
        self.update_confidences = array.array('d', [ upd.conf for upd in topic_updates ] )
        self.normalize_confidences()
        self.update_lengths = array.array('d', [upd.wlen for upd in topic_updates])

    def sample_users_from_population(self, query_duration):
        if self.sampled_users:
            self.sampled_users = []

        self.query_duration = query_duration

        # reset the seed so that the same users are
        # generated every time this function is called
        self.population_model.reset_random_seed()

        for ui in xrange(self.num_users):
            A, P, V, L = self.population_model.generate_user_params()
            if self.fix_persistence:
                P = self.fix_persistence            
            if self.fix_away_mean:
                A = self.fix_away_mean
            if self.fix_reading_mean:
                V = self.fix_reading_mean
            self.sampled_users.append(LognormalAwayRBPPersistenceUserModel(A, P, V, L))

    
    def _compute_user_MSU(self, user_instance, updates):
        
        # self.user_counter += 1
        # if self.user_counter % 1000 == 0:
        #     logger.warning('{0} users simulated'.format(self.user_counter))

        user_topic_msu = 0.0
        user_topic_pain = 0.0

        # generate user trail
        # - if in case a user reads till the start of the next session.
        #   - new ranked updates are shown when the new session starts
        #     - simulates that the user though persisting now wants new information (reload page because I am scraping the bottom here)
        
        #if self.user_counter == 23:
            #logger.setLevel(logging.DEBUG)
        #logger.warning('user {}'.format(user_instance))

        user_trail = self.generate_user_trail(user_instance, self.update_confidences, self.update_emit_times, self.query_duration, self.push_threshold, self.interaction_mode)
        # logger.debug('user_trail {}'.format(user_trail))        
        window_starts = array.array('d', map(lambda x: x[0] - self.window_size if x[0] - self.window_size >= 0.0 else 0.0, user_trail))
        if self.window_size == -1:
            window_starts = array.array('d', [0.0]*len(user_trail)) 
        # logger.debug('window_starts {}'.format(str(window_starts)))
        ssn_starts = array.array('d', [s for s,r,t in user_trail])
        # logger.debug('ssn_starts {}'.format(str(ssn_starts)))
        num_sessions = len(user_trail)

        
        # logger.debug('----------- user {} {}-------------------'.format(self.user_counter, user_instance))
        
        user_topic_msu, user_topic_pain = _compute_push_ranked_user_MSU(user_trail, window_starts, ssn_starts, 
            self.update_emit_times, self.update_confidences, self.update_lengths, updates,
            user_instance.V, user_instance.L, self.query_duration)
        # logger.debug(' user {} done'.format(self.user_counter))
        
        return user_topic_msu, user_topic_pain

       

if __name__ == '__main__':

    ap = argparse.ArgumentParser(description="computes MSU for systems while presenting a ranked order of updates at each user session")
    ap.add_argument("track", choices=["ts13", "ts14", "mb15"])
    ap.add_argument("-m", "--matchesFile", help="the qrel file (for tweets) or the matches file (for updates)")
    ap.add_argument("-n", "--nuggetsFile", help="the clusters file (for tweets) or the nuggets file (for updates)")
    ap.add_argument("--poolFile", help="needed for the TS tracks for tracking duplicates and if --restrict_runs_to_pool is active ") 
    ap.add_argument("-t", "--track_topics_file") # to set time to begin at 0 seconds   
    ap.add_argument("-l", "--update_lengths_folder", help="should contain \"<qid>*.len\" files containing (qid, updid, charlen, wordlen) columns per line") # update lengths are required for each update    
    ap.add_argument("--tweetEpochFile", help="tweet2dayepoch file needed for emit times of tweet ")
    ap.add_argument("-u", "--num_users", type=int, default=1)    
    ap.add_argument("-Apop", "--time_away_population_params", nargs=2, type=float, help="population time away mean and stddev", default=[10800.0, 5400.0])
    ap.add_argument("-Ppop", "--persistence_population_params", nargs=2, type=float, help="population RBP persistence mean and stddev", default=[0.2, 0.2])
    ap.add_argument("-w", "--window_size", type=int, default=86400, help="updates older than window_size from current session will not be shown to user (window_size = -1 --> all updates since start of query duration will be shown)")
    ap.add_argument("interaction_mode", choices=['only.push', 'only.pull', 'push.pull'], default='push.pull')
    ap.add_argument("runfiles", nargs="+")
    ap.add_argument("--user_persistence", type=float)
    ap.add_argument("--user_latency", type=float, default=1.0)
    ap.add_argument("--user_time_away_mean", type=float)
    ap.add_argument("--user_reading_mean", type=float)    
    ap.add_argument("--push_threshold", type=float, default=0.0, help="updates over this threshold are sent as push notifications")
    
    ap.add_argument("--restrict_runs_to_pool", action="store_true", help="the runs are restricted to their pool contributions")

    # NOTE: population reading speed parameters drawn from [Time Well Spent,
    # Clarke and Smucker, 2014]

    args = ap.parse_args()
    print >> sys.stderr, args
        
    if args.track in ['ts13', 'ts14']:
        if None in [args.nuggetsFile, args.matchesFile, args.poolFile, args.update_lengths_folder, args.track_topics_file]:
            logger.error('arguments -n -m --poolFile -t -l  are needed with track {}'.format(args.track))
            sys.exit()

        # load query durations.
        # this helps to start every duration with 0                
        logger.warning('getting topic query durations')
        query_durns = utils.get_topic_query_durations(args.track_topics_file, args.track)    
        for topic, durn in query_durns.iteritems():
            print >> sys.stderr, topic, float(durn[1] - durn[0])
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
        
        logger.warning('load nuggets and their timestamp and importance')
        nuggets = utils.read_in_nuggets(args.nuggetsFile, query_durns)    
        
        logger.warning('reading in update lengths')
        updlens = utils.read_in_update_lengths(args.update_lengths_folder, args.track)    
    
    if 'mb' in args.track:
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
        nuggets = utils.microblog_read_in_clusters(args.nuggetsFile, query_durns, matches, tweet_emit_times)    
        
        logger.warning('reading in update lengths --> Not Applicable for this track')
        # updlens = utils.read_in_update_lengths(args.update_lengths_folder, args.track)    
        
        args.push_threshold = 0.0

    Apop_mean, Apop_stdev = args.time_away_population_params
    
    MSU = MSUPushRankedOrder(args.num_users,
            args.persistence_population_params,
            Apop_mean, Apop_stdev,
            args.user_latency,
                args.window_size,
            args.user_persistence,            
            args.user_time_away_mean,
            args.user_reading_mean, 
            args.push_threshold,
            args.interaction_mode)

    MSU.track = args.track
    
    run = {}
    for runfile in args.runfiles:
        run.clear()
        run = {}
        gc.collect()        
        logger.warning('loading runfile ' + runfile )
        try:            
            run = None
            if args.track in ['ts13', 'ts14']:
                run = MSU.load_run_and_attach_gain(runfile, updlens, nuggets, matches, True, args.track, query_durns, pool, args.restrict_runs_to_pool) 
            elif 'mb' in args.track:
                run = MSU.microblog_load_run_and_attach_gain(runfile, nuggets, matches, args.track, query_durns)
            
            logger.warning('run total updates {}'.format(sum([len(v) for v in run.values()])))
            ignored_qid = "7" if args.track == "ts13" else ""
            if ignored_qid in run:
                run.pop(ignored_qid)
        except Exception, e:
            logger.error('ERROR: could not load runfile ' + runfile)
            logger.error('EXCEPTION: ' + str(e))
            exit(0)
        
        logger.warning('computing MSU...')
        run_msu, run_pain = MSU.compute_population_MSU(run, query_durns)
        # TODO: keep track of all the nuggets found
        
        printkeys = None
        if args.track in ["ts13", "mb15"]:
            keys = filter(lambda x: x.isdigit(), run_msu.keys())
            printkeys = map(str,sorted(map(int, keys))) + ["AVG"]
        elif args.track == 'ts14':
            keys = filter(lambda x: x != 'AVG', run_msu.keys())
            printkeys = sorted(keys) + ['AVG']
        
        
        for topic in printkeys:
            msu = run_msu[topic]
            pain = run_pain[topic]
            runname = os.path.basename(runfile)
            if args.track == 'ts13':
                runname = os.path.splitext(runname)[1]
            if args.track == 'mb15':
                runname = os.path.splitext(runname)[0]
                
            print '{}\t{}\t{:.3f}\t{:.3f}'.format(runname, topic, msu, pain)
