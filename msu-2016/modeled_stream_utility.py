# the main evaluation class

import sys
import os
import gc
import argparse
import numpy as np
import bisect 
from collections import defaultdict
import array

from update import Update
from nugget import Nugget

from population_model import LognormalPopulationModel
from user_model import UserModel
from user_interface_model import ReverseChronologicalInterfaceMixin
import utils

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
    
    def initialize_structures_for_topic(self, topic_updates):
        """
        initialize/presort updates before computing MSU
        """
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

            logger.info('presorting/initializing updates')
            self.initialize_structures_for_topic(topic_updates)

            
            #self.presort_updates(topic_updates)
            
            # time stamps of updates are stored separately for efficient searching
            # bisect on objects works [NO] 
            # TODO: try with numpy.searchsorted on an array of  timestamps in
            # an array; also TODO: how to clear and delete numpy vars
            # extracting update times for faster search
            
                            
            # for users in population
            usercount = 0
            while usercount < self.num_users:
                logger.info('user ' + str(usercount))
                
                # simulate user
                user_sim = self.sampled_users[usercount]
                
                # compute MSU for this user_sim for this topic qid
                user_msu = self._compute_user_MSU(user_sim, topic_updates)
                logger.debug(str(usercount) + str(user_sim) + str(user_msu))
                
                # store for each user and topic
                msu_user_topic[usercount][tpc_idx[qid]] = user_msu
                #logger.debug('{0} {1}'.format(user_sim, user_msu))                
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
        for u in xrange(self.num_users):
            user_msu_per_topic[u] = np.mean(msu_user_topic[u], dtype=float)
        ##user_msu_per_topic = np.mean(msu_user_topic, dtype=float, axis=1)
        logger.info('user msu/topic')
        logger.info( str(user_msu_per_topic) )


        topic_msu_per_user = np.mean(msu_user_topic, dtype=float, axis=0)
        # logger.info('topic msu/user')
        # logger.info( str(topic_msu_per_user) )
        # logger.info('topic {0} (idx {1}) msu = {2}'.format(qid, tpc_idx[qid], topic_msu))
        

        # mean MSU across all users
        msu_per_user = np.mean(user_msu_per_topic, dtype=float)
        
        run_msu = {}
        for qid in sorted(run.keys()):
            run_msu[qid] = topic_msu_per_user[tpc_idx[qid]]
        run_msu["AVG"] = msu_per_user
        
        #return msu_per_user
        return run_msu


class MSUReverseChronoOrder(ModeledStreamUtility, \
    ReverseChronologicalInterfaceMixin):
    """
    Simulates users reading updates in reverse chronological order at every session
    """

    def __init__(self, num_users, pop_session_durn_mean, pop_session_durn_stddev,
        pop_time_away_mean, pop_time_away_stddev, pop_lateness_decay):
        # TODO: population models can be mixins for future versions of MSU.
        # i.e. we may have population distribution specific
        # ModeledStreamUtility evaluation classes

        super(MSUReverseChronoOrder, self).__init__(num_users)

        self.population_model = LognormalPopulationModel(self.seed,
            pop_time_away_mean, pop_time_away_stddev, pop_session_durn_mean,
            pop_session_durn_stddev, pop_lateness_decay)
        
        #self.num_users = num_users
        logger.warning("num users %d" % (self.num_users,))

        self.sampled_users = []        
        self.update_emit_times = []

    def initialize_structures_for_topic(self, topic_updates):
        self.presort_updates(topic_updates)

    def sample_users_from_population(self, query_duration):
        if self.sampled_users:
            self.sampled_users = []
        
        # reset the seed so that the same users are
        # generated every time this function is called
        self.population_model.reset_random_seed()
            
        # sampling user params for one user at a time
        for ui in xrange(self.num_users):
            A, D, V, L = self.population_model.generate_user_params()
            self.sampled_users.append(UserModel(A,D,V,L))         
            # with open('debugging/py.all.users', 'w') as utf:
            #     for A,D,V,L in self.sampled_users:
            #         print >> utf, '\t'.join(map(str,[D,A,V]))
        
        # sampling all user params all together for all users
        # --> - results in 0.1 increase in score on average.
        #     - note that this is due to differences in random sampling order
        #       given the initial seed
        # for user_params in self.population_model.generate_user_params(self.num_users):
        #     self.sampled_users.append(UserModel(*user_params))
        #     # with open('debugging/py.all.together.users', 'w') as utf:
        #     #    for user in self.sampled_users:
        #     #        print >> utf, '\t'.join(map(str,[user.D, user.A, user.V]))
        
        # for each user generate session and away times
        useri = 0
        for user in self.sampled_users:
            #user = UserModel(*user_params)
            
            #user.generate_session_away_lengths(240*3600, True)
            user.generate_session_away_lengths(query_duration, True)
            
            # #logger.debug(str(len(user.session_away_durations)))
            # with open('debugging/py.ssn.away.times.user-{}'.format(useri+1), 'w') as utf:
            #     for ssn, away in user.session_away_durations:
            #         print >> utf, '\t'.join(map(str,[ssn, away]))
            useri += 1
            # if useri == 2:
            #     break

    def _compute_user_MSU(self, user_instance, updates):
        """
        returns MSU for user, when user reads updates in a reverse
        chronological order
        """
       
        #logger.debug(str(user_instance))
        #logger.debug('user session and away times:')

        user_topic_msu = 0.0
        current_time = 0.0
        oldest_available_update_idx = 0

        updates_read = defaultdict(bool)
        #updates_read = set()
        already_seen_ngts = {}
        ssn_starts = [0.0]
        num_updates = len(updates)
        
        # for writing individual session away times to file
        #ssn_durns = []
        #away_durns = []

        for session_duration, time_away in \
            user_instance.session_away_durations:
            #user_instance.generate_session_away_lengths(864000):
            
            #logger.debug('NEW SSN: current: %f session.length: %f time.away: %f' % (current_time, session_duration, time_away))
            #ssn_durns.append(session_duration)
            #away_durns.append(time_away)
            
            #logger.debug('session {}: ctime {}, ssndurn {}, awaytime {}'.format(len(ssn_starts)-1, current_time, session_duration, time_away))
                        
            # find latest update at current_time (session starts)
            latest_update_idx = bisect.bisect(self.update_emit_times,
                current_time)
            latest_update_idx -= 1 # to get the correct index
             
            if oldest_available_update_idx == num_updates:
                # no more updates to read
                # no need to eval further sessions
                #logger.debug('looked at all updates')
                break

            #logger.debug('oldest_available_update_idx = {0}'.format(oldest_available_update_idx))
            #logger.debug('latest_update_idx = {0}'.format(latest_update_idx))
            
            # read updates until session ends; note gain
            time_remaining = session_duration
            for upd_idx in \
                self.update_presentation_order(oldest_available_update_idx,
                    latest_update_idx, updates): 

                update = updates[upd_idx]
                #logger.debug('upd_idx = {0}, {1}'.format(upd_idx, str(update)))
                #logger.debug('upd_idx {}, upd_id {}'.format(upd_idx, update.updid))

                if upd_idx in updates_read:
                    # TODO: make this search through dict as efficient as
                    # possible
                    # read updates in reverse order upto the first update
                    # read in a previous session.
                    # --> no more updates to read as per MSU's user model.
                    #logger.debug('update already read')
                    break 

                upd_time_to_read = ( float(update.wlen) / user_instance.V)
                #logger.debug('upd_time_to_read = {0}, time_remaining = {1}'.format(upd_time_to_read, time_remaining))
                if upd_time_to_read > time_remaining:
                    # user could not completely read update
                    #OR if upd_idx == latest_update_idx:
                        # user could not complete reading even the first
                        # (single) update in the session.
                        # NOTE: MSU requires that an update be completely read
                        # for the user to get any gain. i.e. MSU considers
                        # partially read updates as unread 
                        # --> essentially no updates were read in this session
                    #logger.debug('update read partially')
                    #logger.debug('PARTIAL')
                    break #from this for loop

                updates_read[upd_idx] = True
                #updates_read.add(upd_idx)
                #logger.debug('COMPLETE')

                #logger.debug('update completely read')

                time_remaining -= upd_time_to_read
                if upd_idx >= oldest_available_update_idx:
                    oldest_available_update_idx = upd_idx + 1

                update_msu = 0.0
                
                # check for gain
                for ngt in update.nuggets:
                    if ngt.ngtid in already_seen_ngts: 
                        continue
                    ngt_after = bisect.bisect(ssn_starts, ngt.time)
                    alpha = (len(ssn_starts)-1) - ngt_after
                    #logger.debug('alpha {} = {} - {}'.format(alpha, (len(ssn_starts)-1), ngt_after)) 
                    already_seen_ngts[ngt.ngtid] = alpha                        
                    alpha = 0 if alpha < 0 else alpha                    
                    ngt_msu = (self.population_model.L ** alpha)
                    # TODO: ^^ non binary gain flag 
                    #logger.debug(' '.join(map(str, ['ngt gain = ', len(ssn_starts), ngt_after, alpha, ngt_msu, ngt])))
                    update_msu += ngt_msu
                    
                user_topic_msu += update_msu
                #logger.debug('msu = {}'.format(user_topic_msu))
                #logger.debug(' '.join(map(str, ['MSU++:', update_msu, user_topic_msu])))

            current_time += session_duration
            current_time += time_away
            ssn_starts.append(current_time)
         
        return user_topic_msu #, ssn_durns, away_durns


if __name__ == "__main__":
    
    ap = argparse.ArgumentParser(description="computes Modeled Stream Utility for input system")
    ap.add_argument("track", choices=["ts13", "ts14"])
    ap.add_argument("matches")
    ap.add_argument("nuggets")
    ap.add_argument("pool") #add duplicates from pool to the update --> nugget map
    #ap.add_argument("topic_query_durns") # to set time to begin at 0 seconds
    ap.add_argument("track_topics_xml") # to set time to begin at 0 seconds   
    ap.add_argument("update_lengths_folder", help="should contain \"<qid>*.len\" files containing (qid, updid, charlen, wordlen) columns per line") # update lengths are required for each update
    #ap.add_argument("--useAverageLengths", action="store_true", help="user average topic lengths for updates for which lengths are unavailable")
    #NOTE: this^^ flag is removed since there is no significant change (only 4 changes in scores and all of which were after the 3rd decimal point)
    ap.add_argument("num_users", type=int)
    ap.add_argument("population_session_duration_mean", type=float)
    ap.add_argument("population_session_duration_stddev", type=float)
    ap.add_argument("population_time_away_mean", type=float)
    ap.add_argument("population_time_away_stddev", type=float)
    ap.add_argument("lateness_decay", type=float)
    ap.add_argument("runfiles", nargs="+", help="all the run with gain attached files")
  
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
    
    MSU = MSUReverseChronoOrder(args.num_users,
            args.population_session_duration_mean,
            args.population_session_duration_stddev,
            args.population_time_away_mean, args.population_time_away_stddev,
            args.lateness_decay)

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




    
        
