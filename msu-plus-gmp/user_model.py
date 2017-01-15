# user-model to simulate the behavior of a user interacting with a stream of
# information

import sys
import numpy
from probability_distributions import Exponential

class UserModel(object):
    """
    For MSU, a user alternates between 
    - spending time with the system (sessions for reading updates) D
    - spending time away from the system A
    This classes generates lengths of sessions and times spent away.
    Additionally, each user has 
    - a specific reading speed V
    - a specific discount L for late reported information (For some users,
      relevance value of information may reduce with the passage of time. e.g.
      critical information is desired earlier rather than later.)
    Given A, D, V, L we can simulate a user browsing a stream of updates.
    We can also determine which updates are read depending on the user
    interface used (see UserInterface)
    """

    def __init__(self, mean_time_away_A, mean_session_duration_D, \
        reading_speed_V, lateness_decay_L):
        self.A = float(mean_time_away_A)
        self.D = float(mean_session_duration_D)
        self.V = float(reading_speed_V)
        self.L = float(lateness_decay_L)

        # scale = 1/rate 
        self.A_exp = Exponential(self.A)
        self.D_exp = Exponential(self.D)
        
        self.session_away_durations = []

    def __repr__(self):
        return str ({
                'A': self.A,
                'D': self.D,
                'V': self.V,
                'L': self.L,
            })


    def get_next_session_duration(self, current_time=None, query_duration=None):
        """
        returns a single session duration
        if current_time and query_duration are specified, the generated
            #session length is truncated if it exceeds the query_duration
            session length is NOT truncated if it exceeds the query_duration
            and None is returned
        else
            a single duration is returned
        """
        duration = self.D_exp.get_random_sample()
        if current_time and query_duration:
            current_time = float(current_time)
            query_duration = float(query_duration)
            if current_time + duration > query_duration:
                duration = query_duration - current_time
        return duration

    def get_next_time_away_duration(self, current_time=None, query_duration=None):
        """
        returns a single time away duration
        if current_time and query_duration are specified, the generated
            time away length is truncated if it exceeds the query_duration
        else
            a single duration is returned
        """
        duration = self.A_exp.get_random_sample()
        if current_time and query_duration:
            current_time = float(current_time)
            query_duration = float(query_duration)
            if current_time + duration > query_duration:
                duration = query_duration - current_time
        return duration

    def generate_session_away_lengths(self, query_duration, save=False):
        """
        returns (generates) list of (session, away) durations that fit into the given
        query duration.
        save, if true, saves the generated sessions in self.session_away_durations
        """
        sa = []
        current_time = 0.0
        query_duration = float(query_duration)
        
        #logger.error('in func')

        while current_time < query_duration:
            session = self.D_exp.get_random_sample()
            if session + current_time > query_duration:
                # there is no time for a full session.
                break 
                # NOTE: truncating the last session is a _different_ user
                # model than the original R code used for the MSU paper (the
                # break above)
                ## session = query_duration - current_time
            current_time += session

            away = self.A_exp.get_random_sample()
            if away + current_time >= query_duration: 
                away = query_duration - current_time
                assert(away >= 0) 
                # the user may get one last session in before the
                # query_duration ends
            #logger.error('something')
            #if not save:
            #    yield (session, away)
            #else:
            #    logger.error(str(session))
            self.session_away_durations.append((session, away))
            #sa.append( (session, away) )
            current_time += away

        return self.session_away_durations




    # TODO:[much later] def simulate-reading-of-presented-updates
    # user can read presented updates in order OR out-of-order depending on
    # behavior model. a la EGU???

class LognormalAwayRBPPersistenceUserModel(object):
    """
    A user that alternates between 
    - spending time with the system reading updates
    - spending time away from the system A
    The number of updates read by a user at each session is determined by 
    P the persistence of the user [Moffal, TOIS 2008].
    Additionally, each user has 
    - a specific reading speed V
    - a specific discount L for late reported information (For some users,
      relevance value of information may reduce with the passage of time. e.g.
      critical information is desired earlier rather than later.)
    Given A, P, V, L we can simulate a user browsing a stream of updates when updates are
    presented in a ranked order at every session.
    """

    def __init__ (self, mean_time_away_A, persistence_P, reading_speed_V, lateness_decay_L):
        self.A = float(mean_time_away_A)
        self.P = float(persistence_P)
        self.V = float(reading_speed_V)
        self.L = float(lateness_decay_L)

        self.A_exp = Exponential(self.A)

    def __repr__(self):
        return str ({
                'A': self.A,
                'P': self.P,
                'V': self.V,
                'L': self.L,
            })

    def get_next_time_away_duration(self, current_time=None, query_duration=None):
        """
        returns a single time away duration
        if current_time and query_duration are specified, the generated
            time away length is truncated if it exceeds the query_duration
        else
            a single duration is returned
        """
        duration = self.A_exp.get_random_sample()
        if current_time and query_duration:
            current_time = float(current_time)
            query_duration = float(query_duration)
            if current_time + duration > query_duration:
                duration = query_duration - current_time
        return duration

    # TODO: this function needs to be moved to the user interface module
    def generate_user_trail(self, query_duration):
        """
        return [(session_start, num_read),] tuples based on user model parameters
        """ 
        sessions = []       
        current_time = 0.0
        while current_time < query_duration:
            # read one update
            num_read = 1

            while numpy.random.random() < self.P:
                num_read += 1

            sessions.append( (current_time, num_read) )
            time_away = self.get_next_time_away_duration(current_time, query_duration)
            current_time += time_away
        
        return sessions


if __name__ == "__main__":

    numpy.random.seed(1)
    
    
    user = LognormalAwayRBPPersistenceUserModel(200, 0.5, 1.25, 0.5)

    current_time = 0
    qdurn = 60 * 60
    while current_time < qdurn:
        ssndurn = 60
        current_time += ssndurn
        if current_time > qdurn: break
        awaydurn = user.get_next_time_away_duration(current_time, qdurn)
        current_time += awaydurn
        print ssndurn, awaydurn, current_time

    # D, A, V, L = [float(arg) for arg in sys.argv[1:] ]

    # user = UserModel(A, D, V, L)
    # tups = user.generate_session_away_lengths(24*3600)
    # #tups = [ t for t in user.generate_session_away_lengths(24*3600) ]

    # print '\n'.join( [ str(t) for t in tups] )
    # print numpy.mean([ t[0] for t in tups] )
    # print numpy.mean([ t[1] for t in tups] )

    # print user
    # numpy.random.seed(1)

    # current_time = 0
    # qdurn = 24*3600
    # while current_time < qdurn:
    #     ssndurn = user.get_next_session_duration(current_time, qdurn)
    #     current_time += ssndurn
    #     if current_time >= qdurn:
    #         break
    #     awaydurn = user.get_next_time_away_duration(current_time, qdurn)
    #     current_time += awaydurn
    #     print ssndurn, awaydurn


