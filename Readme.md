# Modeled Stream Utility

Modeled Stream Utility (MSU) is a user-focused evaluation framework for
systems that retrieve information from a time ordered stream.

MSU simulates the behavior of a user accessing information from a stream about
a topic.  For instance, a user may return to a search engine multiple times,
spending some time browsing results, in order to keep abreast of an evolving
news event, such as hurricanes, sporting events, protests and other events,
where new facts of information come to light as the situation evolves.

MSU essentially models a user as alternating between time intervals spent reading updates (sessions) and time intervals spent away from the stream.
The duration of respective time intervals depends on the browsing characteristics of the user. For instance, a highly interested user may read updates with shorter intervals of time spent away from the system. A busy user may spend longer durations away from the system 
(see ["Evaluating Streams of Evolving News Events", Gaurav Baruah, Mark
Smucker, Charles Clarke, _SIGIR
2015_](https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf)).

Modeled Stream Utility (MSU) measures the utility of a stream of information in terms of gain experienced by a user when browsing a stream.
MSU models the stream browsing behavior of users and computes gain (the amount of relevant information read) based on the content read by respective user. 
The MSU user model allows simulation of user having various characteristics of stream browsing behavior. This allows us to evaluate the utility  of information streams for various types of users.

### Directory Layout
```
├── data
│   ├── ts-2013
│   │   ├── qrels
│   │   ├── submitted-runs
|   |   ├── update-lengths
│   │   └── ...
│   └── ts-2014
│       ├── qrels
│       ├── submitted-runs
│       └── update-lengths
├── msu-2016
└── sigir-2015
```

The directory ```data``` contains (or should contain) track specific data (qrels and runs) as well as data required for MSU evaluation (sentence lengths).


The directory [sigir-2015](sigir-2015/Readme.md) contains code for the paper [Evaluating Streams of Evolving News Events, SIGIR 2015] (https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf). This code only supports evaluation of the Temporal Summarization 2013 track. It was developed using a mix of ```R``` and ```Python``` scripts.

The directory [msu-2016](msu-2016/Readme.md) contains a revamped, all Python-ic version of the MSU code (**MAIN CODEBASE**). This version also supports MSU evaluation of both, the Temporal Summarization 2013 and 2014 tracks. 

**Note**: The sigir-2015 version and the msu-2106 version of the code produce minute differences in respective results. This is mainly due to the differences in sampling of random deviates from distributions by ```R``` and ```Python-numpy```.

## Change log
2016-10-20  |  starting new github repo for MSU  