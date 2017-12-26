# population model generates a population of users.
# 1. Users may have different availabilities of time 
# 2. Users may have different levels of interest 
# 3. Users may have different levels of tolerance for delays in getting late
# information
# --> These factors impact a user's session durations and times spent away
# from the system.
# The PopulationModel encapsulates how a population of users might behave
# while using a system.
# e.g. 
#   A single user might have A=3 hours, D=30 seconds
#   Another user might have A=3.5 hours, D=3 minutes
# However, this user may be sampled from a population of users that has
#   mean_A = 6 hours, mean_D = 2 minutes
#   This user populations could be a moderately interested one
# Another population of users might have
#   mean_A = 21 hours, mean_D = 15 minutes
#   This user population could be similar to users who read the daily
#   newspaper
# Another population of users might have
#   mean_A = 30 minutes, mean_D=1 minute
#   This user populations seems highly interested and intent on getting quick
#   short updates as soon as possible.
#


import sys
import numpy

from exceptions import NotImplementedError
from probability_distributions import Lognormal
from probability_distributions import Beta

class PopulationModel(object):
    """
    Population model simulations a set of users having similar/related stream
    browsing behavior.
    This is a base class that MUST be derived, for each differrent kind of
    population model. This is because populations could have lognormal,
    normal, power law, other distributions
    """

    def __init__(self, random_seed):
        """
        A population model must set the seed for random number generation.
        This ensures repeatability of user population when evaluating multiple
        systems
        """
        self.random_seed = random_seed
        self.reset_random_seed()
        
    def reset_random_seed(self):
        numpy.random.seed(self.random_seed)

    def generate_user_params(self):
        """
        Returns user parameters by sampling various distributions that model a
        populate.
        This function MUST be overriden in base classes, depending on kind of population
        model
        """
        raise NotImplementedError    

class LognormalAwayPersistenceSessionsPopulationModel(PopulationModel):
    """
    This population has Lognormal Away times + RBP persistence sessions
    """

    def __init__(self, random_seed, \
        time_away_duration_mean_M_A, \
        time_away_duration_stddev_S_A, \
        RBP_persistence_parameters, \
        lateness_decay_L ):

        super(LognormalAwayPersistenceSessionsPopulationModel, self).__init__(random_seed)

        self.M_A = time_away_duration_mean_M_A
        self.S_A = time_away_duration_stddev_S_A
        self.RBP_population_alpha, self.RBP_population_beta = RBP_persistence_parameters
        self.L = lateness_decay_L
        
        self.lnorm_away = Lognormal(self.M_A, self.S_A)
        self.beta_persistence = Beta(self.RBP_population_alpha, self.RBP_population_beta)

        # NOTE: reading speed parameters sourced from [Clarke and Smucker,
        # "Time Well Spent", IIiX, 2014]
        self.lnorm_reading = Lognormal(1,1)
        self.lnorm_reading.mean_mu = 1.29
        self.lnorm_reading.stddev_sigma = 0.558

    def generate_user_params(self, num_users=0):
        if num_users == 0:
            A = self.lnorm_away.get_random_sample()
            P = self.beta_persistence.get_random_sample()
            V = self.lnorm_reading.get_random_sample()
            L = self.L
            return A, P, V, L
        else:
            As = self.lnorm_away.get_random_samples(num_users)
            Ps = self.beta_persistence.get_random_samples(num_users)
            Vs = self.lnorm_reading.get_random_samples(num_users)
            Ls = [self.L]*num_users
            return zip(As, Ps, Vs, Ls)


class LognormalPopulationModel(PopulationModel):
    """
    Lognormal Population Model: the user population has lognormal
    distributions for time away and session durations
    """
    
    def __init__(self, random_seed, \
        time_away_duration_mean_M_A, \
        time_away_duration_stddev_S_A, \
        session_duration_mean_M_D, \
        session_duration_stddev_S_D, \
        lateness_decay_L):

        super(LognormalPopulationModel, self).__init__(random_seed)
        
        self.M_A = time_away_duration_mean_M_A
        self.S_A = time_away_duration_stddev_S_A
        self.M_D = session_duration_mean_M_D
        self.S_D = session_duration_stddev_S_D
        self.L = lateness_decay_L
        
        self.lnorm_away = Lognormal(self.M_A, self.S_A)
        self.lnorm_session = Lognormal(self.M_D, self.S_D)

        # NOTE: reading speed parameters sourced from [Clarke and Smucker,
        # "Time Well Spent", IIiX, 2014]
        self.lnorm_reading = Lognormal(1,1)
        self.lnorm_reading.mean_mu = 1.29
        self.lnorm_reading.stddev_sigma = 0.558

    def generate_user_params(self, num_users = 0):
        if num_users == 0:
            A = self.lnorm_away.get_random_sample()
            D = self.lnorm_session.get_random_sample()
            V = self.lnorm_reading.get_random_sample()
            L = self.L
            return A, D, V, L
        else:
            As = self.lnorm_away.get_random_samples(num_users)
            Ds = self.lnorm_session.get_random_samples(num_users)
            Vs = self.lnorm_reading.get_random_samples(num_users)
            Ls = [self.L] * num_users
            return zip(As, Ds, Vs, Ls)


if __name__ == "__main__":
    
    M_A, S_A, a, b, L = [ float(a) for a in sys.argv[1:] ]

    population = LognormalAwayPersistenceSessionsPopulationModel(1234, M_A, S_A, [a,b], L)

    for i in xrange(10):
        print (population.generate_user_params())


    # M_A, S_A, M_D, S_D, L = [ float(a) for a in sys.argv[1:] ]

    # population = LognormalPopulationModel(1234, M_A, S_A, M_D, S_D, L)

    # print population.lnorm_away.mean_mu
    # print population.lnorm_away.stddev_sigma

    # for i in xrange(50):
    #     print population.generate_user_params()

    
    # M_A, S_A, M_D, S_D, L = [ a*2 for a in [M_A, S_A, M_D, S_D, L]]

    # population = LognormalPopulationModel(1234, M_A, S_A, M_D, S_D, L)

    # for i in xrange(50):
    #     print population.generate_user_params()

        
