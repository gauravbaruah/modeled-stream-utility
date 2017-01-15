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

from cython_computations import _compute_ranked_user_MSU

from update import Update
from nugget import Nugget
from population_model import LognormalAwayPersistenceSessionsPopulationModel
from user_model import LognormalAwayRBPPersistenceUserModel
from user_interface_model import RankedInterfaceMixin

from modeled_stream_utility import ModeledStreamUtility

import utils

# logging setup
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
#logger.setLevel(logging.INFO)
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


class MSURankedOrder(ModeledStreamUtility, RankedInterfaceMixin):
    """
    Simulates users reading updates in ranked order at every session.
    Users persist in reading updates at every session based on the RBP user model [Moffat, TOIS 2008]
    """

    def __init__(self, num_users, RBP_persistence_params, \
        population_time_away_mean, population_time_away_stddev, \
        pop_lateness_decay, window_size, fix_persistence):

        super(MSURankedOrder, self).__init__(num_users)

        self.population_model = LognormalAwayPersistenceSessionsPopulationModel(self.seed,
                                population_time_away_mean, \
                                population_time_away_stddev, \
                                RBP_persistence_params, \
                                pop_lateness_decay, )

        self.sampled_users = []
        self.update_emit_times = []
        self.update_confidences = []
        self.update_lengths = []                                                                                                    
        self.window_size = window_size
        self.fix_persistence = fix_persistence
        self.user_counter = 0

    def normalize_confidences(self):
        #logger.warning(self.update_confidences)
        maxconf = max(self.update_confidences)
        minconf = min(self.update_confidences)
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
            self.sampled_users.append(LognormalAwayRBPPersistenceUserModel(A, P, V, L))

    
    def _compute_user_MSU(self, user_instance, updates):
        
        # self.user_counter += 1
        # if self.user_counter % 1000 == 0:
        #     logger.warning('{0} users simulated'.format(self.user_counter))

        user_topic_msu = 0.0

        # generate user trail
        # - if in case a user reads till the start of the next session.
        #   - new ranked updates are shown when the new session starts
        #     - simulates that the user though persisting now wants new information (reload page because I am scraping the bottom here)
        
        #if self.user_counter == 23:
            #logger.setLevel(logging.DEBUG)

        user_trail = user_instance.generate_user_trail(self.query_duration)
        # logger.debug('user_trail {}'.format(user_trail))        
        window_starts = array.array('d', map(lambda x: x[0] - self.window_size if x[0] - self.window_size >= 0.0 else 0.0, user_trail))
        if self.window_size == -1:
            window_starts = array.array('d', [0.0]*len(user_trail)) 
        # logger.debug('window_starts {}'.format(str(window_starts)))
        ssn_starts = array.array('d', [s for s,r in user_trail])
        # logger.debug('ssn_starts {}'.format(str(ssn_starts)))
        num_sessions = len(user_trail)

        
        # logger.debug('----------- user {} {}-------------------'.format(self.user_counter, user_instance))
        
        user_topic_msu = _compute_ranked_user_MSU(user_trail, window_starts, ssn_starts, 
            self.update_emit_times, self.update_confidences, self.update_lengths, updates,
            user_instance.V, user_instance.L, self.query_duration)
        # logger.debug(' user {} done'.format(self.user_counter))
        
        return user_topic_msu

       

if __name__ == '__main__':

    ap = argparse.ArgumentParser(description="computes MSU for systems while presenting a ranked order of updates at each user session")
    ap.add_argument("track", choices=["ts13", "ts14"])
    ap.add_argument("matches")
    ap.add_argument("nuggets")
    ap.add_argument("pool") 
    ap.add_argument("track_topics_xml") # to set time to begin at 0 seconds   
    ap.add_argument("update_lengths_folder", help="should contain \"<qid>*.len\" files containing (qid, updid, charlen, wordlen) columns per line") # update lengths are required for each update    
    ap.add_argument("num_users", type=int)
    ap.add_argument("population_time_away_mean", type=float)
    ap.add_argument("population_time_away_stddev", type=float)
    ap.add_argument("lateness_decay", type=float)
    ap.add_argument("--RBP_persistence", nargs=2, type=float, default=[2.0,2.0], \
        help="models the spread of \"reading persistence\" across the user population via a beta distribution")
    ap.add_argument("--window_size", type=int, default=86400, help="updates older than window_size from current session will not be shown to user (window_size = -1 --> all updates since start of query duration will be shown)")
    ap.add_argument("runfiles", nargs="+")
    ap.add_argument("--fix_persistence", type=float)

    # NOTE: population reading speed parameters drawn from [Time Well Spent,
    # Clarke and Smucker, 2014]

    args = ap.parse_args()
    print >> sys.stderr, args
    

    # load query durations.
    # this helps to start every duration with 0                
    logger.warning('getting topic query durations')
    query_durns = utils.get_topic_query_durations(args.track_topics_xml, args.track)
    for topic, durn in query_durns.iteritems():
        print >> sys.stderr, topic, float(durn[1] - durn[0])
    #sys.exit()
        
    logger.warning('identify duplicate updates from the pool')
    # all duplicates have the same relevance judgement.
    duplicates = utils.read_in_pool_file(args.pool)
    
    # ignored topics in the pool
    if args.track == "ts13":
        duplicates['7'] = {} 
        duplicates['9911'] = {} 
                    
    # note relevant updates (and their duplicates)
    # keep track of nuggets present in each relevant update 
    logger.warning('reading in matches, tracking duplicates')
    matches = utils.read_in_matches_track_duplicates(args.matches, duplicates)
    
    logger.warning('load nuggets and their timestamp and importance')
    nuggets = utils.read_in_nuggets(args.nuggets, query_durns)    
       
    logger.warning('reading in update lengths')
    updlens = utils.read_in_update_lengths(args.update_lengths_folder, args.track)    
    
    MSU = MSURankedOrder(args.num_users,
            args.RBP_persistence,
            args.population_time_away_mean, args.population_time_away_stddev,
            args.lateness_decay,
            args.window_size,
            args.fix_persistence)
    
    run = {}
    for runfile in args.runfiles:
        run.clear()
        run = {}
        gc.collect()        
        logger.warning('loading runfile ' + runfile )
        try: 
            run = MSU.load_run_and_attach_gain(runfile, updlens, nuggets, matches, True, args.track, query_durns) #args.useAverageLengths)
            ignored_qid = "7" if args.track == "ts13" else ""
            if ignored_qid in run:
                run.pop(ignored_qid)
        except Exception, e:
            logger.error('ERROR: could not load runfile' + runfile)
            logger.error('EXCEPTION: ' + str(e))
            exit(0)

        logger.warning('computing MSU...')
        run_msu, run_pain = MSU.compute_population_MSU(run, query_durns)
        # TODO: keep track of all the nuggets found
        
        printkeys = None
        if args.track == "ts13":
            keys = filter(lambda x: x.isdigit(), run_msu.keys())
            printkeys = map(str,sorted(map(int, keys))) + ["AVG"]
        elif args.track == 'ts14':
            keys = filter(lambda x: x != 'AVG', run_msu.keys())
            printkeys = sorted(keys) + ['AVG']
        
        for topic in printkeys:
            msu = run_msu[topic]
            pain = run_pain[topic]
            print '%s\t%s\t%s' % (os.path.basename(runfile), str(topic), str(msu), )
            print '{}\t{}\t{:.3f}\t{:.3f}'.format(os.path.basename(runfile), topic, msu, pain)
