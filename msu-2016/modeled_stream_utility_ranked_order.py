# MSU evaluation with a ranked order of presentation

import sys
import os
import gc
import argparse
import bisect
from collections import defaultdict
import operator
import heapq

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
        self.window_size = window_size
        self.fix_persistence = fix_persistence
        self.user_counter = 0

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


    def process_session(self, updates, user_trail, uti, topkqueue, topkcount, updates_read, ssn_starts, window_starts, user_instance, already_seen_ngts ):
        ssn_start, ssn_reads = user_trail[uti]
        next_ssn_start = user_trail[uti+1][0]
        current_time = ssn_start
        session_msu = 0.0

        logger.debug('session {}: start {}; reads {}'.format(uti, ssn_start, ssn_reads))

        available_updates = sorted(topkqueue, key=operator.itemgetter(0), reverse=True)                
        
        topkqueue = available_updates[ssn_reads:]
        heapq.heapify(topkqueue)
        topkcount -= ssn_reads
        #assert(topkcount >= 0)                

        available_updates = available_updates[:ssn_reads]
        logger.debug('available_updates {}'.format(available_updates))
        logger.debug('topk count {} queue {}'.format(topkcount, topkqueue))

        for ai in xrange(len(available_updates)): # for num_reads
    
            read_update = updates[available_updates[ai][3]]
            
            upd_time_to_read = (float(read_update.wlen) / user_instance.V)
            current_time += upd_time_to_read
            if current_time > next_ssn_start:
                # user persisted in reading upto the start of the next session
                logger.info('user persisted in reading upto the start of the next session')
                next_ssn_window_start = window_starts[uti+1]
                for ti in xrange(ai, len(available_updates)):                            
                    if available_updates[ti][1] > next_ssn_window_start:
                        self.add_to_heap(topkqueue, topkcount, updates[available_updates[ti][3]], available_updates[ti][3])
                break
            
            updates_read[read_update.updid] = True
            logger.debug('read update {}'.format(read_update))
            
            read_update_msu = 0.0
            # check for nuggets and update user msu
            for ngt in read_update.nuggets:
                if ngt.ngtid in already_seen_ngts:
                    continue
                ngt_after = bisect.bisect(ssn_starts, ngt.time)                
                alpha = uti - ngt_after
                already_seen_ngts[ngt.ngtid] = alpha
                alpha = 0 if alpha < 0 else alpha
                ngt_msu = (user_instance.L ** alpha)
                logger.debug('ngt {} alpha {} msu {}'.format(ngt, alpha, ngt_msu))
                read_update_msu += ngt_msu
            
            session_msu += read_update_msu
        logger.debug('processed session msu ={}'.format(session_msu))
        return session_msu, topkqueue, topkcount

    def _compute_user_MSU(self, user_instance, updates):
        
        self.user_counter += 1
        if self.user_counter % 1000 == 0:
            logger.warning('{0} users simulated'.format(self.user_counter))

        user_topic_msu = 0.0
        current_time = 0.0
        oldest_available_update_idx = 0

        updates_read = defaultdict(bool)
        already_seen_ngts = {}        
        num_updates = len(updates)

        logger.warning('user {0}'.format(str(user_instance)))
        logger.debug('num_updates {0}'.format(num_updates))

        # generate user trail
        # - if in case a user reads till the start of the next session.
        #   - new ranked updates are shown when the new session starts
        #     - simulates that the user though persisting now wants new information (reload page because I am scraping the bottom here)

        user_trail = user_instance.generate_user_trail(self.query_duration)
        logger.debug('user_trail {}'.format(user_trail))        
        window_starts = map(lambda x: (x[0], x[1][0] - self.window_size) if x[1][0] - self.window_size >= 0.0 else (x[0], 0.0), enumerate(user_trail))
        if self.window_size == -1:
            window_starts = map(lambda x: (x[0], 0.0), enumerate(user_trail))
        logger.debug('window_starts {}'.format(window_starts))
        ssn_starts = [s for s,r in user_trail]
        logger.debug('ssn_starts {}'.format(ssn_starts))
               
        topkqueue = []
        topkcount = 0

        uti = 0
        wsi = 0
        upd_idx = 0

        while upd_idx < len(updates):
            update = updates[upd_idx]
            logger.debug('-------')
            logger.debug('update {}: {}'.format(upd_idx, update))

            # check for window starts
            while window_starts[wsi][1] < update.time:
                topkcount += user_trail[wsi][1]
                logger.debug('window {} started; needs {} '.format(wsi, user_trail[wsi][1]))
                wsi += 1
            logger.debug('topkcount {}'.format(topkcount))

            while user_trail[uti][0] < update.time:    
                # this is the first update beyond a session start
                # --> process this session
                session_msu, topkqueue, topkcount = self.process_session(updates, user_trail, uti, topkqueue, topkcount, updates_read, ssn_starts, window_starts, user_instance, already_seen_ngts)
                user_topic_msu += session_msu
                uti += 1

            self.add_to_heap(topkqueue, topkcount, update, upd_idx)
            logger.debug('adding update {} to queue'.format(upd_idx))
            #logger.debug('topkqueue {}'.format(topkqueue))
            upd_idx += 1
            if uti == len(user_trail):
                logger.debug('all sessions processed')
                break

        # handle sessions beyond the last update
        if upd_idx >= len(updates):
            logger.debug('all updates processed.')        
        while uti < len(user_trail):
            logger.debug('processing leftover session')
            session_msu, topkqueue, topkcount = self.process_session(updates, user_trail, uti, topkqueue, topkcount, updates_read, ssn_starts, window_starts, user_instance, already_seen_ngts)
            user_topic_msu += session_msu
            if len(updates_read) == len(updates):
                logger.debug('read all updates')
                break
            if topkcount < 0:
                logger.debug('no more updates left to satisfy user needs')
                break
            uti += 1

        logger.warning( str(user_instance) )
        logger.warning(user_topic_msu)

        
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
        run_msu = MSU.compute_population_MSU(run, query_durns)
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
            print '%s\t%s\t%s' % (os.path.basename(runfile), str(topic), str(msu))
