# user interfaces at each session:
# Essentially, updates can be presented to the user in chronological, reverse
# chronological, ranked, or some other order.
# The behaviour over a user interface may affect the average gain per user

from update import Update
from operator import attrgetter, itemgetter
import heapq
from collections import defaultdict
import numpy as np
import sys

from user_model import LognormalAwayRBPPersistenceUserModel
#from cython_computations import _generate_push_model_user_trail

class UserInterfaceMixin(object):
    """
    Models the user interface presented to a user at each session.
    This class like an API that determines the order presentation of
    updates, which in turn is required to simulate user behavior for
    evaluation.
    """


    def presort_updates(self, updates):
        """
        presort updates 
        """
        updates.sort(key=lambda t: t.updid)
        updates.sort(key=lambda t: t.conf)
        updates.sort(key=lambda t: t.time)

    def update_presentation_order(self, u, v, updates):
        """
        orders/ranks updates[u:v] as required by the user interface model
        NOTE: the order of updates is expected to be in chronological
        (sequential) order.
        NOTE: updates[u] and updates[v] may be included/excluded depending on
        the interface model (see derived classes for details)
        :param u: start index of range of updates 
        :param v: end index of range of updates 
        :return: yields sorted (u <= indices <= v) for updates[u:v]
        """
        raise NotImplementedError


class ChronologicalInterfaceMixin(UserInterfaceMixin):
    """
    Models an interface where the user reads updates in chronological order at
    every session
    """

    def update_presentation_order(self, oldest_available_update_index, most_recent_update_index,
        updates):
        """
        sorts updates in chronological order; updates with same timestamps are sorted by decreasing
        confidence
        """
        u = oldest_available_update_index
        v = most_recent_update_index

        upds = sorted(updates[u:v+1], key=attrgetter('updid'))
        upds.sort(key=attrgetter('conf'), reverse = True)
        upds.sort(key=attrgetter('time'))

        ## for x in sorted(updates[u:v+1], key=attrgetter('time', 'conf', 'updid')):
        for x in upds:
            yield x

    
class ReverseChronologicalInterfaceMixin(UserInterfaceMixin):
    """
    Models an interface where the user reads updates in reverse chronological
    order at every session
    """

    def update_presentation_order(self, oldest_available_update_index, most_recent_update_index,
        updates):
        """
        sorts updates in reverse chronological order; updates with same timestamps are
        sorted by increasing confidence
        """
        u = oldest_available_update_index
        v = most_recent_update_index

        if v < u : 
            # typically happens when there is no update available to
            # read for the first session
            return 
        
        ##upds = sorted(updates[u:v+1], key=attrgetter('updid'))
        ##upds.sort(key=attrgetter('conf'), reverse = True)
        ##upds.sort(key=attrgetter('time'), reverse = True)

        #upds = sorted(enumerate(updates[u:v+1], u))
        #upds.sort(key=lambda t: t[1].updid)
        #upds.sort(key=lambda t: t[1].conf, reverse = True)
        #upds.sort(key=lambda t: t[1].time, reverse = True)
        #for x in upds:
        #    yield x[0]

        while v >= u:
            yield v
            v -= 1


class RankedInterfaceMixin(UserInterfaceMixin):
    """
    Models an interface where the user reads updates in ranked order by
    update.confidence
    """

    # there can be 3 kinds of ranked interface
    # 1. rank only the updates that were generated between two sessions by the
    # user
    # 2. rank all unread updates - including those from previous sessions.
    # This requires a map to be stored for all updates that have already been
    # read.
    # 3. rank unread updates from a prior window preceding the session
    # NOTE: currently we have implemented option 3 with partial support for option 2

    def __init__(self):
        super(RankedInterfaceMixin, self).__init__()
        self.conf_heap = []
        self.added_to_heap = defaultdict(bool)

    def reset_interface(self):
        self.conf_heap = []
        self.added_to_heap.clear()

    def add_updates_to_conf_heap(self, oldest_available_update_index, most_recent_update_index,
        updates):

        u = oldest_available_update_index
        v = most_recent_update_index
        
        for i in xrange(u, v+1):
            update = updates[i]
            if update.updid not in self.added_to_heap:
                heapq.heappush(self.conf_heap, (-update.conf, update.time, update.updid, i))
                self.added_to_heap[update.updid] = True

    def remove_update_from_conf_heap(self, updid):
        assert(updid == self.conf_heap[0][2])
        return heapq.heappop(self.conf_heap)

    def update_presentation_order(self, oldest_available_update_index, most_recent_update_index,
        updates):
        """
        sorts updates in by confidence; updates with same confidence are
        sorted in reverse chronological order
        """
        u = oldest_available_update_index
        v = most_recent_update_index
       
        while len(self.conf_heap):
            max_conf_update = self.conf_heap[0]
            yield max_conf_update[3]

    def heap_top_is_smaller(self, heap, update, upd_idx):
        """
        top: (confidence, time, updid, index)
        update: update object
        """
        if not heap:
            return True
        confidence, time, updid, index = heap[0]
        if confidence < update.conf:
            return True
        if confidence == update.conf:
            if time < update.time:
                return True
            if time == update.time:
                if updid < update.updid:
                    return True
                if updid == update.updid:
                    # print >>sys.stderr, 'possible duplicate update submitted'
                    # print >>sys.stderr, 'old index {}, new index {}'.format(index, upd_idx)
                    assert(index < upd_idx)
                    return True
        return False

    def add_to_heap(self, topkqueue, topkcount, update, upd_idx):
        if len(topkqueue) < topkcount:
            heapq.heappush( topkqueue, (update.conf, update.time, update.updid, upd_idx) )    
        elif self.heap_top_is_smaller(topkqueue, update, upd_idx) and len(topkqueue) == topkcount:                            
            heapq.heappushpop( topkqueue, (update.conf, update.time, update.updid, upd_idx) )
        assert(len(topkqueue) <= topkcount)

    
class PushRankedInterfaceMixin(RankedInterfaceMixin):
    """
    Models an interface where push notifications are sent by the system
    and the user may then read updates presented in a ranked order
    """
    def __init__(self):
        super(PushRankedInterfaceMixin, self).__init__()
        self.conf_heap = []

    def update_presentation_order(self, oldest_available_update_index, most_recent_update_index, updates):
        # TODO: this is a legacy function. code needs refactoring
        pass

    def generate_user_trail(self, user_instance, update_confs, update_times, query_duration, push_threshold, interaction_mode):
        """
        generates a trail of user behaviour given system actions (e.g. push notifications)
        push_threshold == 0.0 explicitly pushes each update
        """
                
        sessions = []       
        current_time = 0.0
        ui = 0
        
        if interaction_mode == 'only.pull' or interaction_mode == 'push.pull' :
            # regular sessions
            while current_time < query_duration:
                # read one update
                num_read = 1

                while np.random.random() < user_instance.P:
                    num_read += 1

                sessions.append( (current_time, num_read, 0) )
                time_away = user_instance.get_next_time_away_duration(current_time, query_duration)
                current_time += time_away 

        if interaction_mode == 'only.push' or interaction_mode =='push.pull':
            # push notification sessions
            for ui in xrange(len(update_confs)):
                if update_confs[ui] >= push_threshold:
                    num_read = 0
                    while np.random.random() < user_instance.P:  
                        num_read += 1
                    sessions.append((update_times[ui], num_read, 1))
        
        sessions.sort(key=lambda x: x[0])
        return sessions


if __name__ == "__main__":

    # sample command: 
    # python user_interface_model.py \
    # ../data/gain-attached-runs/input.UWMDSqlec2t25-gain-attached-norm | less 


    from modeled_stream_utility import ModeledStreamUtility as MSU
    import sys

    #MSU = ModeledStreamUtility()
    run = {}
    MSU.load_gain_attached_run(sys.argv[1], run)

    reverse = ReverseChronologicalInterfaceMixin()
    serial = ChronologicalInterfaceMixin()
    ranked = RankedInterfaceMixin()

    print 'testing interface code'
    print 'every 10 updates are in specified order'

    for qid in sorted(run.keys()):
        updates = run[qid]
        #for s in sorted(updates, key=attrgetter('time', 'conf', 'updid')):
        #    print s

        for ui in xrange(0, len(updates), 10):

            # reverse order
            for si in reverse.update_presentation_order(ui, ui+9, updates):
            # serial order
            ## for si in serial.update_presentation_order(ui, ui+9, updates):
            # ranked order
            ## for si in ranked.update_presentation_order(ui, ui+9, updates):
                print si
            print '---'
            
        break

