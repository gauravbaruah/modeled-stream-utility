# distutils: language=c++

cimport cython
import array
from collections import defaultdict
import bisect
import heapq
import operator
from libc.stdlib cimport malloc, free
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
from libcpp.vector cimport vector

import numpy


from sys import maxint

# import logging
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)
# #logger.setLevel(logging.DEBUG)


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
    # sourced from https://interactivepython.org/runestone/static/pythonds/Trees/BinaryHeapImplementation.html
    cdef vector[UpdateData] minheap
    cdef vector[UpdateData] maxheap
    cdef int heap_size
    cdef int max_heap_size    
    cdef int topkcount

    def __init__(self, int heap_size_limit):
        
        for i in xrange(2*heap_size_limit):
            self.minheap.push_back(UpdateData(float("inf"),float("inf"), 2**31-1,float("inf")))
            self.maxheap.push_back(UpdateData(float("-inf"), float("-inf"), -(2**31-1), float("-inf")))
        self.heap_size = 0
        self.topkcount = 0 
        self.max_heap_size = 0


    cdef int update_topkcount(self, int incr):
        self.topkcount += incr
        return self.topkcount

    cdef bint is_key_smaller(self, UpdateData A, UpdateData B):
        if A.conf < B.conf:
            return True
        if abs(A.conf - B.conf) < 1e-8:
            if A.time < B.time:
                return True
            if abs(A.time - B.time) < 1e-8:
                return A.index < B.index
        return False

    cdef percUp(self, int i):
        cdef UpdateData tmp
        while i // 2 > 0:
            if self.is_key_smaller(self.minheap[i], self.minheap[i//2]):
                tmp = self.minheap[i//2]
                self.minheap[i//2] = self.minheap[i]
                self.minheap[i] = tmp
            i = i//2
    
    cdef insert(self, UpdateData upd_data):
        # logger.debug('UpdateHeap: inserting {}'.format(upd_data))
        self.heap_size += 1
        self.minheap[self.heap_size] = upd_data
        self.percUp(self.heap_size)

    cdef int get_smaller_child(self, int i):
        if i*2 + 1 > self.heap_size:
            return i*2
        else:
            if self.is_key_smaller(self.minheap[i*2],self.minheap[i*2 +1]):
                return i*2
            else:
                return i*2+1

    cdef percDown(self, int i):
        cdef UpdateData tmp
        while (i*2) < self.heap_size:
            sc = self.get_smaller_child(i)
            if not self.is_key_smaller(self.minheap[i], self.minheap[sc]):
                tmp = self.minheap[i]
                self.minheap[i] = self.minheap[sc]
                self.minheap[sc] = tmp
            i = sc

    cdef push_into_topk(self, UpdateData upd_data):
        self.minheap[1] = upd_data
        self.percDown(1)        

    cdef re_minheapify(self, double time_filter):
        self.heap_size = 0        
        cdef num_filtered = 0
        for i in xrange(1, self.max_heap_size+1):
            if self.maxheap[i].time > time_filter:                
                self.insert(self.maxheap[i])
            else:
                num_filtered += 1
                
        self.max_heap_size = 0
        # logger.debug('UpdateHeap: re_minheapify: num_filtered {}'.format(num_filtered))

    # max heap functions --------------
    cdef bint is_key_greater(self, UpdateData A, UpdateData B):
        if A.conf > B.conf:
            return True
        if abs(A.conf - B.conf) < 1e-8:
            if A.time > B.time:
                return True
            if abs(A.time - B.time) < 1e-8:
                return A.index > B.index
        return False

    cdef _percUp_max(self, int i):
        cdef UpdateData tmp
        while i // 2 > 0:
            if self.is_key_greater(self.maxheap[i], self.maxheap[i//2]):
                tmp = self.maxheap[i//2]
                self.maxheap[i//2] = self.maxheap[i]
                self.maxheap[i] = tmp
            i = i//2
    
    cdef _insert_max(self, UpdateData upd_data):
        self.max_heap_size += 1
        self.maxheap[self.max_heap_size] = upd_data
        self._percUp_max(self.max_heap_size)

    cdef int _get_greater_child_max(self, int i):
        if i*2 + 1 > self.max_heap_size:
            return i*2
        else:
            if self.is_key_greater(self.maxheap[i*2], self.maxheap[i*2 +1]):
                return i*2
            else:
                return i*2+1

    cdef _percDown_max(self, int i):
        cdef UpdateData tmp
        while (i*2) < self.max_heap_size:
            sc = self._get_greater_child_max(i)
            if not self.is_key_greater(self.maxheap[i], self.maxheap[sc]):
                tmp = self.maxheap[i]
                self.maxheap[i] = self.maxheap[sc]
                self.maxheap[sc] = tmp
            i = sc

    cdef maxheapify(self):        
        for i in xrange(1, self.heap_size+1):
            self._insert_max(self.minheap[i])
        # assert(self.heap_size == self.max_heap_size)

    cdef UpdateData removemax(self):
        cdef UpdateData ret = self.maxheap[1]
        self.maxheap[1] = self.maxheap[self.max_heap_size]
        self.heap_size -= 1
        self.max_heap_size -= 1
        
        self._percDown_max(1) 
        
        return ret       
    
    cdef bint heap_top_is_smaller(self, double upd_time, double upd_conf, int upd_idx):        
        if not self.minheap.size():
            return True        
        if self.minheap[1].conf < upd_conf:
            return True
        if abs(self.minheap[1].conf - upd_conf) < 1e-8:
            if self.minheap[1].time < upd_time:
                return True
            if abs(self.minheap[1].time - upd_time) < 1e-8:
                return self.minheap[1].index < upd_idx
        return False

    cdef void add_to_heap(self, int upd_idx, double upd_time, double upd_conf, double upd_wlen):
        if self.heap_size < self.topkcount:            
            self.insert( UpdateData(upd_conf, upd_time, upd_idx, upd_wlen) )            
            # logger.debug('UpdateHeap: add_to_heap: default insert')
        elif self.topkcount >0 and self.heap_size == self.topkcount and self.heap_top_is_smaller(upd_time, upd_conf, upd_idx) :
            self.push_into_topk(UpdateData(upd_conf, upd_time, upd_idx, upd_wlen) )        
            # logger.debug('UpdateHeap: add_to_heap: topk insert')
    

#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef tuple process_session(updates_read, already_seen_ngts, updates, 
                double user_reading_speed, double user_latency_tolerance,
                double ssn_start, int ssn_reads, int uti,
                double next_ssn_start, double next_ssn_window_start,
                ssn_starts, # needed for alpha computation
                UpdateHeap topkqueue,
                ignore_verbosity = False):
    
    cdef double session_msu = 0.0
    cdef double session_pain = 0.0
    cdef double current_time = 0.0

    # logger.debug('session {}: start {}; reads {}'.format(uti, ssn_start, ssn_reads))

    topkqueue.update_topkcount(-ssn_reads)
    if topkqueue.heap_size == 0:
        # logger.debug('nothing in heap. return 0.0')
        return 0.0, 0.0

    topkqueue.maxheapify()              
            
    # logger.debug('topk count {}: maxqueue {} {}'.format(topkqueue.topkcount, topkqueue.max_heap_size, [ (e.conf, e.index) for e in topkqueue.maxheap][:topkqueue.max_heap_size+1]))

    cdef double read_update_wlen = 0.0
    cdef double upd_time_to_read = 0.0
    cdef double read_update_msu = 0.0

    cdef int alpha = 0
    cdef int ngt_after = 0
    cdef double ngt_msu = 0.0

    #for ai in xrange(len(available_updates)): # for num_reads
    while ssn_reads >0 and topkqueue.max_heap_size > 0:
        # logger.debug('starting to read {}; max_heap_size {}'.format(ssn_reads, topkqueue.max_heap_size))
        ssn_reads -= 1
        
        upddata = topkqueue.maxheap[1]
        # logger.debug(upddata)

        read_update_wlen = upddata.wlen
        
        upd_time_to_read = (float(read_update_wlen) / user_reading_speed)
        current_time += upd_time_to_read

        if current_time > next_ssn_start and not ignore_verbosity:
            # user persisted in reading upto the start of the next session
            # logger.debug('user persisted in reading upto the start of the next session')
            
            break
        
        updates_read[upddata.index] = True
        # logger.debug('before removemax')
        topkqueue.removemax()        
        # logger.debug('removed maxtop. maxqueue {} {}'.format(topkqueue.max_heap_size, [ (e.conf, e.index) for e in topkqueue.maxheap]))
        
        read_update = updates[upddata.index]
        # logger.debug('read update {}'.format(read_update))
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

        if not read_update.nuggets:
            session_pain += 1.0
    # logger.debug('processed session msu ={}'.format(session_msu))

    topkqueue.re_minheapify(next_ssn_window_start)
    # logger.debug('after re-minheap {} {}'.format(topkqueue.heap_size, [ (e.conf, e.index) for e in topkqueue.minheap][:topkqueue.heap_size+1]))
    return session_msu, session_pain


@cython.boundscheck(False)
@cython.wraparound(False)
cdef int find_max_heap_size(user_trail, window_starts, int num_sessions):    
    cdef int wi = 0
    cdef int ci = 0
    cdef int heap_size = 0
    cdef int max_heap_size = 0
    # # logger.debug('num_sessions {}'.format(num_sessions))
    for wi in xrange(num_sessions):
        # # logger.debug('{}, w {}, s {}, check {} {}'.format(wi, window_starts[wi], user_trail[wi], ci, user_trail[ci]))
        heap_size += user_trail[wi][1]
        if max_heap_size < heap_size:
            max_heap_size = heap_size
        
        while window_starts[wi] > user_trail[ci][0]:
            heap_size -= user_trail[ci][1]
            ci+=1
        # # logger.debug('heap_size {} {}'.format(heap_size, max_heap_size))
        
    return max_heap_size



#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
def _compute_ranked_user_MSU(user_trail, window_starts, ssn_starts, 
            update_times, update_confidences, update_lengths, updates,
            double user_reading_speed, double user_latency_tolerance,
            double query_duration):
    
    # if user_index == 23:
    #     logger.setLevel(logging.DEBUG)

    user_topic_msu = 0.0
    updates_read = {}
    already_seen_ngts = {}        
    
    cdef int num_updates = len(update_times)    
    cdef int num_sessions = len(user_trail)
            
    #topkqueue = []
    #cdef int topkcount = 0
    
    heap_size_limit = find_max_heap_size(user_trail, window_starts, num_sessions)
    # logger.debug('heap_size_limit {}'.format(heap_size_limit))    
    cdef UpdateHeap topkqueue = UpdateHeap(heap_size_limit);
    # logger.debug('made the queue')
        
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
        # logger.debug('update {}: {}'.format(upd_idx, updates[upd_idx]))


        # check for window starts
        while wsi < num_sessions and window_starts[wsi] < update_times[upd_idx]:
            #topkcount += user_trail[wsi][1]
            topkqueue.update_topkcount(user_trail[wsi][1])
            # logger.debug('window {} started; needs {} '.format(wsi, user_trail[wsi][1]))
            wsi += 1
        # logger.debug('topkcount {}'.format(topkqueue.topkcount))

        while uti < num_sessions and ssn_starts[uti] < update_times[upd_idx]:    
            # this is the first update beyond a session start
            # --> process this session
            ssn_start = user_trail[uti][0]
            ssn_reads = user_trail[uti][1]
            next_ssn_start = ssn_starts[uti+1] if uti +1 != num_sessions else query_duration            
            next_ssn_window_start = window_starts[uti+1] if uti +1 != num_sessions else query_duration
            
            
            session_msu, session_pain = process_session(updates_read, already_seen_ngts, updates,
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
        # logger.debug('checking/added update {} to queue {} {}'.format(upd_idx, topkqueue.heap_size, [(e.conf, e.index) for e in topkqueue.minheap][:topkqueue.heap_size+1]))
        
        upd_idx += 1            

    # handle sessions beyond the last update
    if upd_idx >= len(updates):
        # logger.debug('all updates processed.')        
        pass
    while uti < num_sessions:
        # logger.debug('processing leftover session')
        ssn_start = user_trail[uti][0]
        ssn_reads = user_trail[uti][1]
        next_ssn_start = ssn_starts[uti+1] if uti +1 != num_sessions else query_duration            
        next_ssn_window_start = window_starts[uti+1] if uti +1 != num_sessions else query_duration
        
        session_msu, session_pain = process_session(updates_read, already_seen_ngts, updates,
                                                user_reading_speed, user_latency_tolerance,
                                                ssn_start, ssn_reads, uti,
                                                next_ssn_start, next_ssn_window_start,
                                                ssn_starts,
                                                topkqueue)
        user_topic_msu += session_msu
        user_topic_pain += session_pain
        if len(updates_read) == num_updates:
            # logger.debug('read all updates')
            break
        if topkqueue.topkcount < 0:
            # logger.debug('no more updates left to satisfy user needs')
            break
        uti += 1
    
    # logger.debug('user_topic_msu {}'.format(user_topic_msu))

    return user_topic_msu, user_topic_pain


# cdef get_next_time_away_duration(self, current_time=None, query_duration=None):
#         """
#         returns a single time away duration
#         if current_time and query_duration are specified, the generated
#             time away length is truncated if it exceeds the query_duration
#         else
#             a single duration is returned
#         """
#         cdef duration = self.A_exp.get_random_sample()
#         if current_time and query_duration:
#             current_time = float(current_time)
#             query_duration = float(query_duration)
#             if current_time + duration > query_duration:
#                 duration = query_duration - current_time
#         return duration


# def _generate_push_model_user_trail(double user_A, double user_P, update_confs, update_times, double query_duration, double push_threshold, bint only_push):
#     sessions = []       
#     cdef double current_time = 0.0
#     cdef int ui = 0
    
#     if not only_push:
#         # regular sessions
#         while current_time < query_duration:
#             # read one update
#             num_read = 1

#             while numpy.random.random() < user_P:
#                 num_read += 1

#             sessions.append( (current_time, num_read, 0) )
#             time_away = get_next_time_away_duration(current_time, query_duration)
#             current_time += time_away 

#     # push notification sessions
#     for ui in xrange(len(update_confs)):
#         if update_confs[ui] >= push_threshold:
#             num_read = 1
#             while numpy.random.random() < user_P:  
#                 num_read += 1
#             sessions.append(update_times[ui], num_read, 1)
    
#     sessions.sort(key=lambda x: x[0])
#     return sessions

    
@cython.boundscheck(False)
@cython.wraparound(False)
def _compute_push_ranked_user_MSU(user_trail, window_starts, ssn_starts, 
            update_times, update_confidences, update_lengths, updates,
            double user_reading_speed, double user_latency_tolerance,
            double query_duration,
            bint ignore_verbosity):
    
    # if user_index == 23:
    #     logger.setLevel(logging.DEBUG)

    cdef double user_topic_msu = 0.0
    cdef double user_topic_pain = 0.0
    updates_read = {}
    already_seen_ngts = {}        
    
    cdef int num_updates = len(update_times)    
    cdef int num_sessions = len(user_trail)
            
    cdef int heap_size_limit = find_max_heap_size(user_trail, window_starts, num_sessions)
    # logger.debug('heap_size_limit {}'.format(heap_size_limit))    
    cdef UpdateHeap topkqueue = UpdateHeap(heap_size_limit);
    # logger.debug('made the queue')
        
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
        # logger.debug('update {}: {}'.format(upd_idx, updates[upd_idx]))

        topkqueue.add_to_heap(upd_idx,
            update_times[upd_idx], update_confidences[upd_idx], update_lengths[upd_idx])
        # logger.debug('checking/added update {} to queue {} {}'.format(upd_idx, topkqueue.heap_size, [(e.conf, e.index) for e in topkqueue.minheap][:topkqueue.heap_size+1]))


        # check for window starts
        while wsi < num_sessions and (abs(window_starts[wsi] - update_times[upd_idx]) < 1e-8 or window_starts[wsi] - update_times[upd_idx] < 1e-8):
            #topkcount += user_trail[wsi][1]
            topkqueue.update_topkcount(user_trail[wsi][1])
            # logger.debug('window {} started; needs {} '.format(wsi, user_trail[wsi][1]))
            wsi += 1
        # logger.debug('topkcount {}'.format(topkqueue.topkcount))

        while uti < num_sessions and (abs(ssn_starts[uti] - update_times[upd_idx]) < 1e-8 or ssn_starts[uti] - update_times[upd_idx] < 1e-8):    
            # this is the first update beyond a session start
            # --> process this session
            ssn_start = user_trail[uti][0]
            ssn_reads = user_trail[uti][1]
            next_ssn_start = ssn_starts[uti+1] if uti +1 != num_sessions else query_duration            
            next_ssn_window_start = window_starts[uti+1] if uti +1 != num_sessions else query_duration
            
            
            session_msu, session_pain = process_session(updates_read, already_seen_ngts, updates,
                                                    user_reading_speed, user_latency_tolerance,
                                                    ssn_start, ssn_reads, uti,
                                                    next_ssn_start, next_ssn_window_start,
                                                    ssn_starts,
                                                    topkqueue,
                                                    ignore_verbosity)
            user_topic_msu += session_msu
            user_topic_pain += session_pain
            uti += 1

        if uti == num_sessions:
            # logger.debug('all sessions processed')
            break

        upd_idx += 1            

    # handle sessions beyond the last update
    if upd_idx >= len(updates):
        # logger.debug('all updates processed.')        
        pass
    while uti < num_sessions:
        # logger.debug('processing leftover session')
        ssn_start = user_trail[uti][0]
        ssn_reads = user_trail[uti][1]
        next_ssn_start = ssn_starts[uti+1] if uti +1 != num_sessions else query_duration            
        next_ssn_window_start = window_starts[uti+1] if uti +1 != num_sessions else query_duration
        
        session_msu, session_pain = process_session(updates_read, already_seen_ngts, updates,
                                               user_reading_speed, user_latency_tolerance,
                                                ssn_start, ssn_reads, uti,
                                                next_ssn_start, next_ssn_window_start,
                                                ssn_starts,
                                                topkqueue,
                                                ignore_verbosity)
        user_topic_msu += session_msu
        user_topic_pain += session_pain
        if len(updates_read) == num_updates:
            # logger.debug('read all updates')
            break
        if topkqueue.topkcount < 0:
            # logger.debug('no more updates left to satisfy user needs')
            break
        uti += 1
    
    # logger.debug('user_topic_msu {}'.format(user_topic_msu))

    return user_topic_msu, user_topic_pain

