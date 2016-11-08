# This script generates data to plot sum(gain) vs sum(pain) for the runs of 
# the Temporal Summarization 2013 and 2014 tracks.
# [Gain and Pain; Tan et al, SIGIR 16]

# NOTE: this script is a modifed version of msu-2016/modeled_stream_utility_ranked_order.py and msu-2016/modeled_stream_utility.py

# NOTES:
# 1. one user is simulated only
# 2. interface: ranked; 1 day window based on user session start time
# 3. user model: persistence 0.5; 3 +/- 1.5 hours away 

import sys
import os
import gc
import argparse
import numpy as np
import bisect
from collections import defaultdict

sys.path.append('../msu-2016/')

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


class ModeledStreamUtility(object):
    """
    Modeled Stream Utility evaluates systems that produce streams of updates.
    """

    # random number seed for experiments 
    seed = 1234

    def __init__(self, num_users):
        super(ModeledStreamUtility, self).__init__()
        self.num_users = num_users
    
    @staticmethod
    def load_run_and_attach_gain(runfile, updlens, nuggets, matches, useAverageLengths, track, query_durns):
        """
        This function attaches gain (nuggets) to sentences of a run, on the fly
        """
        run = {}        
        with open(runfile) as rf:
            for line in rf:
                if len(line.strip()) == 0: continue
                qid, teamid, runid, docid, sentid, updtime, confidence = line.strip().split() 
                if track == 'ts14':
                    qid = 'TS14.'+qid
                updid = docid + '-' + sentid
                updtime = float(updtime) - query_durns[qid][0] # timestamps to start from 0               
                confidence = float(confidence)
                updlen = 30 if not useAverageLengths else updlens[qid]["topic.avg.update.length"]     #default updlen is 30
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
                matching_nuggets = []
                if updid in matches[qid]:  #update is relevant                
                    ngts_in_upd = matches[qid][updid]                
                    for ngtid in ngts_in_upd:
                        if ngtid not in nuggets[qid]: # there are 2 nuggets not in nuggets.tsv
                            continue
                        num_ngts += 1
                        ngt_gain, ngt_time = nuggets[qid][ngtid]      
                        # ngtstr += ','.join([ str(s) for s in [ngtid, ngt_gain, ngt_time] ])
                        # ngtstr += ' '
                        matching_nuggets.append(Nugget(ngtid, ngt_gain, ngt_time))              
                
                #run[qid].append( [updtime, confidence, updid, updlen, num_ngts, ngtstr] )
                updobj = Update(qid, updid, updtime, confidence, updlen, num_ngts, ngtstr)
                updobj.nuggets = matching_nuggets
                if qid not in run:
                    run[qid] = []
                run[qid].append(updobj)                
        return run

    @staticmethod
    def load_gain_attached_run(run_gain_file, run):
        """
        loads an annotated output of a system, where each submitted update has
        number of nuggets and the individual nuggets listed along with each
        update.
        - ** expected INPUT **
          - each line is tab-separated and has the following fields:
            - qid, 0-normalized-update-timestamp, update-confidence, update-id,
            update-length-in-words, number-of-nuggets, {nuggets-in-update}
            - {nuggets-in-update} is a space-separated string of:
              - {nugget-1-data} {nugget-2-data} {nugget-3-data} ...
            - {nugget-x-data} is a comma-separated string containing:
              - nugget-id, nugget-importance, nugget-timestamp
        - ** example input **: topic 2 from input.CosineEgrep run [TST 2013]
        ```
        2       3600.0  2.0     1347368668-e91e25cdce508351fbe294623a5c95c9-47  9      0       
        2       3600.0  3.0     1347371604-0ee2fe22eac34ca3ffb67338573c6fbf-4   112    2       VMTS13.02.067,3,165005.0 VMTS13.02.057,3,164256.0 
        2       147600.0        1.0     1347509804-69ff1ba01b750de4553f1613367d265b-3 807     0       
        ```
        - [see also] trec_tst_2013_preprocessing.py
        :param run_gain_file: file path to the gain-attached-run
        :param run: [out] dictionary that is populated with the data from the file
        """
        logger.warning( 'loading gain attached run ' + run_gain_file)
        
        with open(run_gain_file) as rf:
            for line in rf:            
                fields = line.strip().split('\t')                        
                upd = None
                if len(fields) == 6:
                    fields += [""]        
                qid, updtime, updconf, updid, updlen, numngts, ngtstr = fields
                # NOTE: updid comes after confidence in gain attached runs
                upd = Update(qid, updid, updtime, updconf, updlen, numngts, ngtstr)
                if upd.qid not in run:
                    run[upd.qid] = []
                run[upd.qid].append(upd)

    #def update_presentation_order(self, oldest_available_update_index, most_recent_update_index,
    #    updates):
    #    """
    #    The order in which available updates are presented to the users for
    #    reading.
    #    """
    #    # NOTE: this function needs to be implemented based on the user
    #    # interface model [see class ReverseChronologicalInterfaceMixin, and,
    #    # class MSUReverseChronoOrder]
    #    raise NotImplementedError
    
    def sample_users_from_population(self, query_duration):
        """
        The compute_population_MSU() method calls this method to re-sample population for every query.
        This is sometimes useful when we are modifying user sims data during MSU computation.
        """
        raise NotImplementedError    

    def _compute_user_MSU(self, user_instance, updates):
        """
        simulate user behavior of the given user_instance over the given set
        of updates. [called for each topic's updates]
        :return: MSU for given updates for given user_instance
        """
        # NOTE: this function needs to be implemented based on the user
        # interface model [see class MSUReverseChronoOrder]
        raise NotImplementedError 

    def compute_population_MSU(self, run, query_durns):
        """
        computes MSU for each user in specified population and returns the
        average MSU of the population for a given system (for all topics)
        :param: run: system that produces streams of updates
        :return: mean MSU for a system
        """


        # if not self.sampled_users:
        #     self.sample_users_from_population()

        gc.collect()
        
        # intermediate MSUs for users and topics
        msu_user_topic = np.zeros( (self.num_users, len(run.keys())),
            dtype=float)
        pain_user_topic = np.zeros( (self.num_users, len(run.keys())), dtype=float)

        tpc_idx = dict( [ (t, i) for i, t in enumerate(sorted(run.keys())) ] )

        # for each topic
        for qid in sorted(run.keys()):

            logger.debug('topic ' + str(qid) + '----------')
            
            # reset the seed so that the same users are
            # generated every time sample_users_from_population() function is called
            self.population_model.reset_random_seed()
            self.sample_users_from_population(query_durns[qid][1] - query_durns[qid][0])
            
            topic_updates = []
            gc.collect()
            
            topic_updates = run[qid]

            logger.info('presorting updates')
            self.presort_updates(topic_updates)
            
            # time stamps of updates are stored separately for efficient searching
            # bisect on objects works [NO] 
            # TODO: try with numpy.searchsorted on an array of  timestamps in
            # an array; also TODO: how to clear and delete numpy vars
            # extracting update times for faster search
            self.update_emit_times = [ upd.time for upd in topic_updates ] 
                            
            # for users in population
            usercount = 0
            while usercount < self.num_users:
                logger.info('user ' + str(usercount))
                
                # simulate user
                user_sim = self.sampled_users[usercount]
                
                # compute MSU for this user_sim for this topic qid
                user_msu, user_pain = self._compute_user_MSU(user_sim, topic_updates)
                logger.debug(str(usercount) + str(user_sim) + str(user_msu) + ' ' + str(user_pain))
                
                # store for each user and topic
                msu_user_topic[usercount][tpc_idx[qid]] = user_msu
                pain_user_topic[usercount][tpc_idx[qid]] = user_pain
                #logger.debug('{0} {1} {2}'.format(user_sim, user_msu, user_pain))                
                #logger.debug('USERMSU:\t{}\t{}\t{}'.format(usercount+1, qid, user_msu))
                
                usercount += 1
                
            self.update_emit_times == []
            
            # #logger.debug('Breaking here just to check on generated user ssn and away times')
            # if qid > 1:
            #     break

        logger.info('user topic msu')
        logger.info('\n' + '\n'.join([str(m) for m in msu_user_topic]))

        
        # compute average MSU per topic for each user
        user_msu_per_topic = np.zeros(self.num_users, dtype=float)
        user_pain_per_topic = np.zeros(self.num_users, dtype=float)
        for u in xrange(self.num_users):
            user_msu_per_topic[u] = np.mean(msu_user_topic[u], dtype=float)
            user_pain_per_topic[u] = np.mean(pain_user_topic[u], dtype=float)
        ##user_msu_per_topic = np.mean(msu_user_topic, dtype=float, axis=1)
        logger.info('user msu/topic')
        logger.info( str(user_msu_per_topic) )
        logger.info( str(user_pain_per_topic) )


        topic_msu_per_user = np.mean(msu_user_topic, dtype=float, axis=0)
        topic_pain_per_user = np.mean(pain_user_topic, dtype=float, axis=0)
        # logger.info('topic msu/user')
        # logger.info( str(topic_msu_per_user) )
        # logger.info('topic {0} (idx {1}) msu = {2}'.format(qid, tpc_idx[qid], topic_msu))
        

        # mean MSU across all users
        msu_per_user = np.mean(user_msu_per_topic, dtype=float)
        pain_per_user = np.mean(user_pain_per_topic, dtype=float)
        
        run_msu = {}
        run_pain = {}
        for qid in sorted(run.keys()):
            run_msu[qid] = topic_msu_per_user[tpc_idx[qid]]
            run_pain[qid] = topic_pain_per_user[tpc_idx[qid]]
        run_msu["AVG"] = msu_per_user
        run_pain["AVG"] = pain_per_user
        
        #return msu_per_user
        return run_msu, run_pain


class MSURankedOrder(ModeledStreamUtility, RankedInterfaceMixin):
    """
    Simulates users reading updates in ranked order at every session.
    Users persist in reading updates at every session based on the RBP user model [Moffat, TOIS 2008]
    """

    def __init__(self, num_users, RBP_persistence_params, \
        population_time_away_mean, population_time_away_stddev, \
        pop_lateness_decay, window_size, fix_persistence, fix_time_away_param):

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
        self.fix_time_away_param = fix_time_away_param
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
            if self.fix_time_away_param:
                A = self.population_model.M_A
            self.sampled_users.append(LognormalAwayRBPPersistenceUserModel(A, P, V, L))

    def _compute_user_MSU(self, user_instance, updates):
        
        self.user_counter += 1
        if self.user_counter % 1000 == 0:
            logger.warning('{0} users simulated'.format(self.user_counter))

        user_topic_msu = 0.0
        user_topic_pain = 0.0
        current_time = 0.0
        oldest_available_update_idx = 0

        updates_read = defaultdict(bool)
        already_seen_ngts = {}
        ssn_starts = [0.0]
        num_updates = len(updates)
        
        self.reset_interface()
        
        #logger.warning('user {0}'.format(str(user_instance)))
        logger.debug('num_updates {0}'.format(num_updates))

        current_time = 0
        while current_time < self.query_duration:
            
            logger.debug('current_time {0}, window start {1}'.format(current_time, current_time - (current_time if self.window_size == -1 else self.window_size)))
            
            # find available sentences to read at this user session

            # find latest update at current_time (session starts)
            latest_update_idx = bisect.bisect(self.update_emit_times, current_time)
            latest_update_idx -= 1
                                 
            window_lower_limit = 0
            if self.window_size != -1: 
                window_lower_limit = current_time - self.window_size

                # consider updates from within past window_size seconds only
                oldest_available_update_idx = bisect.bisect(self.update_emit_times, 
                                                window_lower_limit) 
                if oldest_available_update_idx == num_updates:
                    # no more updates to read
                    # no need to eval further sessions
                    logger.debug('looked at all updates')
                    break
                #oldest_available_update_idx = 0 if oldest_available_update_idx == 0 else oldest_available_update_idx - 1
            else:
                # consider all update from start of query_duration
                oldest_available_update_idx = 0

            logger.debug('oldest_available_update_idx {0}, latest_update_idx {1}'.format(oldest_available_update_idx,latest_update_idx))
            logger.debug('available {0}'.format(str(updates[oldest_available_update_idx:latest_update_idx+1])))

            self.add_updates_to_conf_heap(oldest_available_update_idx, latest_update_idx, updates)
            logger.debug('conf_heap {0}'.format(self.conf_heap))

            # read sentences until user persists
            is_first_update = True
            for upd_idx in self.update_presentation_order(oldest_available_update_idx,
                latest_update_idx, updates):

                update =  updates[upd_idx]
                logger.debug('update {0}'.format(str(update)))
                
                if update.time < window_lower_limit:
                    # this update is not to be considered for display to the user anymore
                    logger.debug("update is OUT OF WINDOW LIMIT")
                    self.remove_update_from_conf_heap(update.updid)
                    continue
                
                #logger.debug('upddate {0}'.format(str(update)))
                
                # will the user persist in reading this udpate
                if not is_first_update and np.random.random_sample() > user_instance.P:
                    # the user will not read this update
                    logger.debug('USER DID NOT PERSIST')
                    break

                # note time elapsed for reading each update; increment current_time
                upd_time_to_read = (float(update.wlen) / user_instance.V)
                current_time += upd_time_to_read

                is_first_update = False

                updates_read[update.updid] = True
                # the user PERSISTED to read this update
                logger.debug('READ UPDATE')
                self.remove_update_from_conf_heap(update.updid)

                update_msu = 0.0
                # check for nuggets and update user msu
                for ngt in update.nuggets:
                    if ngt.ngtid in already_seen_ngts:
                        continue
                    ngt_after = bisect.bisect(ssn_starts, ngt.time)
                    alpha = (len(ssn_starts) -1) - ngt_after
                    already_seen_ngts[ngt.ngtid] = alpha
                    alpha = 0 if alpha < 0 else alpha
                    ngt_msu = (self.population_model.L ** alpha)
                    update_msu += ngt_msu
                
                user_topic_msu += update_msu
                
                if not update.nuggets:
                    user_topic_pain += 1

            # increment current_time with time spent away
            time_away = user_instance.get_next_time_away_duration(current_time, self.query_duration)
            current_time += time_away
            ssn_starts.append(current_time)
        
        #logger.warning( str(user_instance) )
        #logger.warning( 'gain {}, pain {}'.format(user_topic_msu, user_topic_pain))
                
        return (user_topic_msu, user_topic_pain)



        

if __name__ == '__main__':

    ap = argparse.ArgumentParser(description="prints Gain vs pain for each system while presenting a ranked order of updates at each user session")
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
    ap.add_argument("--fix_time_away_param", action="store_true", help="the time_away durations will be sampled from an exponential distribution parameterized by the population_time_away_mean only [USE with single user simulation]")

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
            args.fix_persistence,
            args.fix_time_away_param)
    
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
            print '%s\t%s\t%s\t%s' % (os.path.basename(runfile), str(topic), str(msu), str(pain))
