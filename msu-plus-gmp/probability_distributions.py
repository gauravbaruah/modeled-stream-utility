# probability distributions required for the MSU evaluation model
 
import argparse
import sys

import numpy 

class Exponential(object):
    """
    Random samples from an Exponential probability distribution parameterized
    by scale_param_lambda. 
    ::note:: scale parameter is 1/rate parameter
    """

    def __init__(self, param_lambda):
        self.scale_param_lambda = float(param_lambda)

    def get_random_sample(self):
        """
        return: a single random sample from this exponential distribution
        """
        #return self.get_random_samples(1)[0]
        return numpy.random.exponential(size=None, scale=self.scale_param_lambda)

    def get_random_samples(self, num_samples):
        """
        return: a list of num_samples random samples from this exponential
        distribution
        """
        #return expon.rvs(size=num_samples, scale=self.scale_param_lambda)
        return numpy.random.exponential(size=num_samples, scale=self.scale_param_lambda)


class Beta(object):
    """
    Random samples from an Beta probability distribution parameterized
    by alpha and beta. 
    ::note:: scale parameter is 1/rate parameter
    """

    def __init__(self, alpha, beta):
        self.shape_param_alpha = float(alpha)
        self.shape_param_beta = float(beta)

    def get_random_sample(self):
        """
        return: a single random sample from this beta distribution
        """
        
        return numpy.random.beta(self.shape_param_alpha, self.shape_param_beta, size=None)

    def get_random_samples(self, num_samples):
        """
        return: a list of num_samples random samples from this beta
        distribution
        """
        
        return numpy.random.beta(self.shape_param_alpha, self.shape_param_beta, size=num_samples)


class Lognormal(object):
    """
    Random samples from a Lognormal probability distribution parameterized by
    data_mean and data_stddev. These parameters will be transformed to the
    lognormal's mean_mu and stddev_sigma
    """

    def __init__(self, data_mean, data_stddev):
        self.data_mean = float(data_mean)
        self.data_stddev = float(data_stddev)
        self.mean_mu, self.stddev_sigma = self.lognormal_param_transform()
        #self.mean_mu, self.stddev_sigma = data_mean, data_stddev

    def lognormal_param_transform(self):
        """
        transforms data_mean and data_stddev to parameters for this lognormal
        distribution
        """
        M = self.data_mean
        S = self.data_stddev
        variance = numpy.log( (S**2) / (M**2) + 1)
        sigma = numpy.sqrt(variance)
        mu = numpy.log(M) - (0.5 * (sigma**2))

        return mu, sigma


    def get_random_sample(self):
        """
        return: a single random sample from this lognormal distribution
        """
        return self.get_random_samples(1)[0]

    def get_random_samples(self, num_samples):
        """
        return: a list of num_samples random samples from this lognormal
        distribution
        """
        #return lognorm.rvs(size=num_samples, scale=self.mean_mu, s=self.stddev_sigma)
        return numpy.random.lognormal(mean=self.mean_mu, \
            sigma=self.stddev_sigma, size=num_samples)


if __name__ == "__main__":

    numpy.random.seed(1)

    #M, S = float(sys.argv[1]), float(sys.argv[2])
    #lognormal = Lognormal(M, S)

    #print 'mu', lognormal.mean_mu
    #print 'sigma', lognormal.stddev_sigma

    #randlognorm = lognormal.get_random_samples(100)
    #print randlognorm
    #print sum(randlognorm)/100

    # decay = float(sys.argv[1])

    # exponential = Exponential(2)

    # for x in xrange(10):
    #     print exponential.get_random_sample()

    # randexp = exponential.get_random_samples(10)
    # print randexp
    # print sum(randexp)/10
   
    
    a, b = float(sys.argv[1]), float(sys.argv[2])
    beta = Beta(a, b)

    for x in xrange(10):
        print beta.get_random_sample()

    randbeta = beta.get_random_samples(10)
    print randbeta