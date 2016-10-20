# Modeled Stream Utility

Modeled Stream Utility (MSU) is a user-focused evaluation framework for
systems that retrieve information from a time ordered stream.

MSU simulates the behavior of a user accessing information from a stream about
a topic.  For instance, a user may return to a search engine multiple times,
spending some time browsing results, in order to keep abreast of an evolving
news event, such as hurricanes, sporting events, protests and other events,
where new facts of information come to light as the situation evolves.

MSU essentially models a user as alternating between time intervals spent reading updates and time intervals spent away from the stream.
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
│   └── ts-2013
│       ├── qrels
│       ├── submitted-runs
│       └── update-lengths
├── msu-2016
└── sigir-2015
```

The directory ```data``` contains (or should contain) track specific data (qrels and runs) as well as data required for MSU evaluation (sentence lengths).


The directory [sigir-2015](#sigir-2015) contains code for the paper [Evaluating Streams of Evolving News Events, SIGIR 2015] (https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf). This code only supports evaluation of the Temporal Summarization 2013 track. It was developed using a mix of ```R``` and ```Python``` scripts.

The directory [msu-2016](#msu-2016) contains a revamped, all Python-ic version of the MSU code. This version also supports MSU evaluation of both, the Temporal Summarization 2013 and 2014 tracks. 

**Note**: The sigir-2015 version and the msu-2106 version of the code produce minute differences in respective results. This is mainly due to the differences in sampling of random deviates from distributions by ```R``` and ```Python-numpy```.


## sigir-2015

#### Software dependencies
1. [R](https://www.r-project.org/) 

### Requirements

1. Temporal Summarization 2013 qrels (present in ```data/ts-2013/qrels```)
2. Temporal Summarization 2013 submitted runs (download from [TREC](trec.nist.gov) into ```data/ts-2013/submitted-runs```).
3. Lengths of all submitted sentences (download from [here](https://cs.uwaterloo.ca/~gbaruah/ts-2013-update-lengths.html) into ```data/ts-2013/update-lengths```).

### Running the Evaluation

#### Annotate submitted updates with contained nuggets
MSU requires that for the evaluation of a system, the system output be annotated by contained nuggets (see ```sigir-2015/attach-gain-to-run.py```).

```sigir-2015/attach-gain-to-run.py``` annotates systems' output for the TS 2013's participating systems. (MSU input format is also described in this script).

To annotate submitted updates with contained nuggets for given runs:
```
mkdir data/ts-2013/gain-attached-runs;

cd sigir-2015;

for run in `ls ../data/ts-2013/submitted-runs/input*`; do rbase=`basename $run`; python attach-gain-to-run.py ../data/ts-2013/qrels/matches.tsv ../data/ts-2013/qrels/nuggets.tsv ../data/ts-2013/qrels/pooled_updates.tsv ../data/ts-2013/topic_query_durations ../data/ts-2013/update-lengths $run ../data/ts-2013/gain-attached-runs/$rbase.with.gain; done
```

#### Generate trails of user behavior

We generate time-trails of users alternating between times spent reading and times spent away from the system.

```
mkdir data/ts-2013/simulation-data;

cd sigir-2015;

Rscript generate.time.trails.R 10800 5400 120 60 ../data/ts-2013/simulation-data 0 1000
```  

With the above arguments ```generate.time.trails.R``` simulates a user population that 

- on average spends 3 hours (with std.dev. 1.5 hours) away from the system,
- on average spends 2 minutes (with std.dev. 1 minute) reading updates,
- assigns the population an id of ```0```,
- simulates 1000 users from the population.

Note that this parameters are for the so called "_reasonable users_" (section 4.2 in the
[MSU paper](https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf)).


#### Evaluate systems using MSU

To compute Modeled Stream Utility all for gain-attached-runs: 
```
time python modeled_stream_utility.py 1000 120 60 10800 5400 0.5 ../data/gain-attached-runs/input.run* > runs.msu
```
Parameters (for "_reasonable users_" [section 4.2 in the
[paper](https://cs.uwaterloo.ca/~gbaruah/baruah-et-al-sigir-2015.pdf)] in the
above command are:

-  1000 users
-  120 seconds population mean session duration
-  60 seconds population session duration standard deviation
-  3 hours (10800 seconds) population mean time away
-  1.5 hours (5400 seconds) population time away standard deviation
-  0.5 latency decay for population 


## msu-2016

#### Software dependencies
1. [python-numpy](http://www.numpy.org/)

This code has been developed using a virtualenv with a numpy install.

1. Create a python [virtualenv](https://virtualenv.pypa.io/en/latest/)
2. ```source [your-virtual-env]/bin/activate```
3. ```pip install numpy```
4. run commands

## Change log
2016-10-20  |  starting new github repo for MSU  