# cython: profile=True
cimport cython
import array
from collections import defaultdict
import bisect
import heapq
import operator


# import logging
# logger = logging.getLogger(__name__)

#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef bint heap_top_is_smaller(heap, double upd_time, double upd_conf, int upd_idx):
    """
    top: (confidence, time, index)
    update: update object
    """
    if not heap:
        return True
    # top_conf, top_time, top_index, top_wlen = heap[0]
    if heap[0][0] < upd_conf:
        return True
    if abs(heap[0][0] - upd_conf) < 1e-8:
        if heap[0][1] < upd_time:
            return True
        if abs(heap[0][1] - upd_time) < 1e-8:
            return heap[0][2] < upd_idx
    return False

#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef void add_to_heap(topkqueue, int topkcount, int upd_idx, double upd_time, double upd_conf, double upd_wlen):
    if len(topkqueue) < topkcount:
        heapq.heappush( topkqueue, (upd_conf, upd_time, upd_idx, upd_wlen) )    
    elif topkcount >0 and len(topkqueue) == topkcount and heap_top_is_smaller(topkqueue, upd_time, upd_conf, upd_idx) :                            
        heapq.heappushpop( topkqueue, (upd_conf, upd_time, upd_idx, upd_wlen) )
    #assert(len(topkqueue) <= topkcount)

#@cython.profile(True)
@cython.boundscheck(False)
@cython.wraparound(False)
cdef process_session(updates_read, already_seen_ngts, updates, 
                double user_reading_speed, double user_latency_tolerance,
                double ssn_start, int ssn_reads, int uti,
                double next_ssn_start, double next_ssn_window_start,
                ssn_starts, # needed for alpha computation
                topkqueue, topkcount):
    
    cdef double session_msu = 0.0
    cdef double current_time = 0.0

    # logger.debug('session {}: start {}; reads {}'.format(uti, ssn_start, ssn_reads))

    available_updates = sorted(topkqueue, key=operator.itemgetter(0), reverse=True)                
    
    topkqueue = available_updates[ssn_reads:]
    heapq.heapify(topkqueue)
    topkcount -= ssn_reads
    #assert(topkcount >= 0)                

    available_updates = available_updates[:ssn_reads]
    # logger.debug('available_updates {}'.format(available_updates))
    # logger.debug('topk count {} queue {}'.format(topkcount, topkqueue))

    cdef double read_update_wlen = 0.0
    cdef double upd_time_to_read = 0.0
    cdef double read_update_msu = 0.0

    cdef int alpha = 0
    cdef int ngt_after = 0
    cdef double ngt_msu = 0.0

    for ai in xrange(len(available_updates)): # for num_reads
        
        read_update_wlen = available_updates[ai][3]
        
        upd_time_to_read = (float(read_update_wlen) / user_reading_speed)
        current_time += upd_time_to_read

        if current_time > next_ssn_start:
            # user persisted in reading upto the start of the next session
            # logger.info('user persisted in reading upto the start of the next session')
            
            for ti in xrange(ai, len(available_updates)):                            
                if available_updates[ti][1] > next_ssn_window_start:
                    add_to_heap(topkqueue, topkcount, 
                        available_updates[ti][2],
                        available_updates[ti][0], 
                        available_updates[ti][1],
                        available_updates[ti][3]
                        )
            break
        
        updates_read[available_updates[ai][2]] = True
        # logger.debug('read update {}'.format(read_update))
        
        read_update = updates[available_updates[ai][2]]
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
    return session_msu, topkqueue, topkcount

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
            
    topkqueue = []
    cdef int topkcount = 0

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
            topkcount += user_trail[wsi][1]
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
            
            
            session_msu, topkqueue, topkcount = process_session(updates_read, already_seen_ngts, updates,
                                                    user_reading_speed, user_latency_tolerance,
                                                    ssn_start, ssn_reads, uti,
                                                    next_ssn_start, next_ssn_window_start,
                                                    ssn_starts,
                                                    topkqueue, topkcount)
            user_topic_msu += session_msu
            uti += 1

        if uti == num_sessions:
            # logger.debug('all sessions processed')
            break

        add_to_heap(topkqueue, topkcount, upd_idx,
            update_times[upd_idx], update_confidences[upd_idx], update_lengths[upd_idx])
        # logger.debug('adding update {} to queue'.format(upd_idx))
        ## logger.debug('topkqueue {}'.format(topkqueue))
        upd_idx += 1            

    # handle sessions beyond the last update
    # if upd_idx >= len(updates):
        # logger.debug('all updates processed.')        
    while uti < num_sessions:
        # logger.debug('processing leftover session')
        session_msu, topkqueue, topkcount = process_session(updates_read, already_seen_ngts, updates,
                                                user_reading_speed, user_latency_tolerance,
                                                ssn_start, ssn_reads, uti,
                                                next_ssn_start, next_ssn_window_start,
                                                ssn_starts,
                                                topkqueue, topkcount)
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

    
    return user_topic_msu