# cython: profile=True
cimport cython
import array
from collections import defaultdict
import bisect
import heapq
import operator
from libc.stdlib cimport malloc, free
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
from libcpp.vector cimport vector

from sys import maxint

# import logging
# logger = logging.getLogger(__name__)
# ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
# formatter = logging.Formatter('%(levelname)s - %(message)s')
# ch.setFormatter(formatter)
# logger.addHandler(ch)

cdef struct UpdateData:
    double conf
    double time
    int index
    double wlen

    

cdef class UpdateHeap:
    cdef vector[UpdateData] minheap
    cdef vector[UpdateData] maxheap
    cdef int heap_size
    cdef int max_heap_size
    cdef int topkcount

    def __init__(self, int max_heap_size):
        
        for i in xrange(max_heap_size):
            self.minheap.push_back(UpdateData(float("inf"),float("inf"),maxint,float("inf")))
            self.maxheap.push_back(UpdateData(float("-inf"), float("-inf"), -1, float("-inf")))
        self.heap_size = 0
        self.topkcount = 0        

    cdef int update_topkcount(self, incr):
        self.topkcount += incr
        return self.topkcount

    cdef minheappush(self, upd_data):
        pass

    cdef minheappushpop(self, upd_data):
        pass

    cdef re_minheapify(self, time_filter):
        for upddata in self.maxheap:                            
            if upddata.time > time_filter:
                self.minheappush(upddata)
        pass
    
    cdef maxheapify(self):
        pass

    cdef popmax(self):
        pass
    
    cdef bint heap_top_is_smaller(self, double upd_time, double upd_conf, int upd_idx):
        """
        top: (confidence, time, index)
        update: update object
        """
        if not self.minheap.size():
            return True
        # top_conf, top_time, top_index, top_wlen = heap[0]
        if self.minheap[0].conf < upd_conf:
            return True
        if abs(self.minheap[0].conf - upd_conf) < 1e-8:
            if self.minheap[0].time < upd_time:
                return True
            if abs(self.minheap[0].time - upd_time) < 1e-8:
                return self.minheap[0].index < upd_idx
        return False

    cdef void add_to_heap(self, int upd_idx, double upd_time, double upd_conf, double upd_wlen):
        if self.heap_size < self.topkcount:
            self.minheappush( UpdateData(upd_conf, upd_time, upd_idx, upd_wlen) )            
        elif self.topkcount >0 and self.heap_size == self.topkcount and self.heap_top_is_smaller(upd_time, upd_conf, upd_idx) :
            self.minheappushpop( UpdateData(upd_conf, upd_time, upd_idx, upd_wlen) )        
    

#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef process_session(updates_read, already_seen_ngts, updates, 
                double user_reading_speed, double user_latency_tolerance,
                double ssn_start, int ssn_reads, int uti,
                double next_ssn_start, double next_ssn_window_start,
                ssn_starts, # needed for alpha computation
                UpdateHeap topkqueue):
    
    cdef double session_msu = 0.0
    cdef double current_time = 0.0

    # logger.debug('session {}: start {}; reads {}'.format(uti, ssn_start, ssn_reads))

    #available_updates = sorted(topkqueue, key=operator.itemgetter(0), reverse=True)  
    topkqueue.maxheapify()              
        
    topkqueue.update_topkcount(-ssn_reads)
    
    # logger.debug('available_updates {}'.format(available_updates))
    # logger.debug('topk count {} queue {}'.format(topkcount, topkqueue))

    cdef double read_update_wlen = 0.0
    cdef double upd_time_to_read = 0.0
    cdef double read_update_msu = 0.0

    cdef int alpha = 0
    cdef int ngt_after = 0
    cdef double ngt_msu = 0.0

    #for ai in xrange(len(available_updates)): # for num_reads
    while ssn_reads >0:
        ssn_reads -= 1

        upddata = topkqueue.maxheap[0]

        read_update_wlen = upddata.wlen
        
        upd_time_to_read = (float(read_update_wlen) / user_reading_speed)
        current_time += upd_time_to_read

        if current_time > next_ssn_start:
            # user persisted in reading upto the start of the next session
            # logger.info('user persisted in reading upto the start of the next session')
            
            break
        
        updates_read[upddata.index] = True
        topkqueue.popmax()
        # logger.debug('read update {}'.format(read_update))
        
        read_update = updates[upddata.index]
        read_update_msu = 0.0
        # check for nuggets and update user msu
        for ngt in read_update.nuggets:
            if ngt.ngtid in already_seen_ngts:
                continue
            ngt_after = bisect.bisect(ssn_starts, ngt.time)                
            alpha = uti - ngt_after
            already_seen_ngts[ngt.ngtid] = alpha
            alpha = 0 if alpha < 0 else alpha
            ngt_msu = (user_latency_tolerance ** alpha)
            # logger.debug('ngt {} alpha {} msu {}'.format(ngt, alpha, ngt_msu))
            read_update_msu += ngt_msu
        
        session_msu += read_update_msu
    # logger.debug('processed session msu ={}'.format(session_msu))

    topkqueue.re_minheapify(next_ssn_window_start)
    return session_msu


@cython.boundscheck(False)
@cython.wraparound(False)
cdef int find_max_heap_size(user_trail, window_starts, int num_sessions):    
    cdef int wi = 0
    cdef int ci = 0
    cdef int heap_size = 0
    cdef int max_heap_size = 0
    # logger.debug('num_sessions {}'.format(num_sessions))
    for wi in xrange(num_sessions):
        # logger.debug('{}, w {}, s {}, check {} {}'.format(wi, window_starts[wi], user_trail[wi], ci, user_trail[ci]))
        heap_size += user_trail[wi][1]
        if max_heap_size < heap_size:
            max_heap_size = heap_size
        
        while window_starts[wi] > user_trail[ci][0]:
            heap_size -= user_trail[ci][1]
            ci+=1
        # logger.debug('heap_size {} {}'.format(heap_size, max_heap_size))
        
    return max_heap_size



#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def _compute_ranked_user_MSU(user_trail, window_starts, ssn_starts, 
            update_times, update_confidences, update_lengths, updates,
            double user_reading_speed, double user_latency_tolerance,
            double query_duration):
    
    user_topic_msu = 0.0
    updates_read = {}
    already_seen_ngts = {}        
    
    cdef int num_updates = len(update_times)    
    cdef int num_sessions = len(user_trail)
            
    #topkqueue = []
    cdef int topkcount = 0
    
    max_heap_size = find_max_heap_size(user_trail, window_starts, num_sessions)
    # logger.debug('max_heap_size {}'.format(max_heap_size))
    #cdef UpdateData *topkqueue = <UpdateData*>malloc(max_heap_size * sizeof(UpdateData))
    cdef UpdateHeap topkqueue = UpdateHeap(max_heap_size);
    

    cdef int uti = 0
    cdef int wsi = 0
    cdef int upd_idx = 0

    cdef:
        double ssn_start = 0.0
        double next_ssn_start = 0.0
        double next_ssn_window_start = 0.0
        double session_msu = 0.0
        int ssn_reads = 0

    while upd_idx < num_updates:
        # update = updates[upd_idx]
        
        # logger.debug('-------')
        # logger.debug('update {}: {}'.format(upd_idx, update))


        # check for window starts
        while wsi < num_sessions and window_starts[wsi] < update_times[upd_idx]:
            #topkcount += user_trail[wsi][1]
            topkqueue.update_topkcount(user_trail[wsi][1])
            # logger.debug('window {} started; needs {} '.format(wsi, user_trail[wsi][1]))
            wsi += 1
        # logger.debug('topkcount {}'.format(topkcount))

        while uti < num_sessions and ssn_starts[uti] < update_times[upd_idx]:    
            # this is the first update beyond a session start
            # --> process this session
            ssn_start = user_trail[uti][0]
            ssn_reads = user_trail[uti][1]
            next_ssn_start = ssn_starts[uti+1] if uti +1 != num_sessions else query_duration            
            next_ssn_window_start = window_starts[uti+1] if uti +1 != num_sessions else query_duration
            
            
            session_msu = process_session(updates_read, already_seen_ngts, updates,
                                                    user_reading_speed, user_latency_tolerance,
                                                    ssn_start, ssn_reads, uti,
                                                    next_ssn_start, next_ssn_window_start,
                                                    ssn_starts,
                                                    topkqueue)
            user_topic_msu += session_msu
            uti += 1

        if uti == num_sessions:
            # logger.debug('all sessions processed')
            break

        topkqueue.add_to_heap(upd_idx,
            update_times[upd_idx], update_confidences[upd_idx], update_lengths[upd_idx])
        # logger.debug('adding update {} to queue'.format(upd_idx))
        ## logger.debug('topkqueue {}'.format(topkqueue))
        upd_idx += 1            

    # handle sessions beyond the last update
    # if upd_idx >= len(updates):
        # logger.debug('all updates processed.')        
    while uti < num_sessions:
        # logger.debug('processing leftover session')
        session_msu = process_session(updates_read, already_seen_ngts, updates,
                                                user_reading_speed, user_latency_tolerance,
                                                ssn_start, ssn_reads, uti,
                                                next_ssn_start, next_ssn_window_start,
                                                ssn_starts,
                                                topkqueue)
        user_topic_msu += session_msu
        if len(updates_read) == num_updates:
            # logger.debug('read all updates')
            break
        if topkcount < 0:
            # logger.debug('no more updates left to satisfy user needs')
            break
        uti += 1

    # logger.debug( str(user_instance) )
    # logger.debug(user_topic_msu)

    #free(topkqueue)
    
    return user_topic_msu