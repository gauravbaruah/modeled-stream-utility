
## msu-2016

#### Software dependencies
1. [python-numpy](http://www.numpy.org/)

This code has been developed using a virtualenv with a numpy install.

1. Create a python [virtualenv](https://virtualenv.pypa.io/en/latest/)
2. ```source [your-virtual-env]/bin/activate```
3. ```pip install numpy```
4. run commands

### Data Requirements

1. Temporal Summarization 2013 qrels (present in ```data/ts-2013/qrels```)
2. Temporal Summarization 2013 submitted runs (download from [TREC](trec.nist.gov) into ```data/ts-2013/submitted-runs```).
3. Lengths of all sentences submitted to TS 2013 (download from [here](https://cs.uwaterloo.ca/~gbaruah/ts-2013-update-lengths.html) into ```data/ts-2013/update-lengths```).
2. Temporal Summarization 2014 submitted runs (download from [TREC](trec.nist.gov) into ```data/ts-2014/submitted-runs```).
3. Lengths of all sentences submitted to TS 2014 (download from [here](https://cs.uwaterloo.ca/~gbaruah/ts-2014-update-lengths.html) into ```data/ts-2014/update-lengths```).

### Code Layout

```msu-2016```
```├── Readme.md```: This Readme.md
```├── modeled_stream_utility.py``` : **main script**
```├── nugget.py```: nugget class for Temporal Summarization tracks
```├── update.py```: update class for sentences submitted to Temporal Summarization tracks
```├── get_query_durations.py```: extracts start and end timestamps for query durations from the tracks' topics.xml file
```├── probability_distributions.py```: base classes for probability distributions
```├── population_model.py```: user population model
```├── user_model.py```: user behavior model
```├── user_interface_model.py```: user interface models
```└── utils.py```: Utility functions 

Files for comparing msu-2016 and sigir-2015 codebases (see [codebase-comparison](codebase-comparison/Readme.md))
```├── modeled_stream_utility_with_time_trails.py```: script to evaluate using time trails made by R (see [sigir-2015/Readme.md](sigir-2015/Readme.md)```├── gen-pythonic-time-trails.py```


### Running the Evaluation
