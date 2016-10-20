# Modeled Stream Utility

Modeled Stream Utility (MSU) easures the utility of a stream of information in terms of gain experienced by a user when browsing a stream.
MSU models the stream browsing behavior of users and computes gain (the amount of relevant information read) based on the content read by respective user. 
The MSU user model allows simulation of user having various characteristics of stream browsing behavior. This allows us to evaluate the utility  of information streams for various types of users.

The directory [sigir-2015](#sigir-2015) contains code for the paper [Evaluating Streams of Evolving News Events, SIGIR 2015] (https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf). This code only supports evaluation of the Temporal Summarization 2013 track.

The directory [msu-2016](#msu-2016) contains a revamped, all Python-ic version of the MSU code. This version also supports MSU evaluation of both, the Temporal Summarization 2013 and 2014 tracks. 

**Note**: The sigir-2015 version and the msu-2106 version of the code produce minute differences in the results. This is mainly due to the differences in the production of random deviates from distributions using R vs using Python-numpy.

## Change log
2016-10-20  |  starting new github repo for MSU  