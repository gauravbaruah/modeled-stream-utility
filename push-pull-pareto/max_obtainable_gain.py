# essentially counts the total number of unique 
# relevant items that were returned across all runs

import argparse
import json
import sys

from utils import read_in_pool_file, read_in_matches_track_duplicates, microblog_read_in_clusters, read_in_nuggets


def get_findable_nuggets(matchesFile):
    findables = {}
    with open(matchesFile) as mf:
        mf.readline()
        for line in mf:
            query_id, update_id, nugget_id, match_start, match_end, auto_p = line.strip().split('\t')
            if query_id not in findables:
                findables[query_id] = set()
            findables[query_id].add(nugget_id)
    findables = dict(map(lambda x: (x[0], len(x[1])), findables.items()) )
    return findables

def get_findable_clusters(matchesFile):
    findables = {}
    with open(matchesFile) as mf:
        clusters = json.loads(mf.read())['topics']
        for qid in clusters:
            findables[qid] = len(clusters[qid]['clusters'])
    return findables

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='find all unique relevant items returned by runs')
    ap.add_argument('track', choices=["ts13", "ts14", "mb15", "rts16"])
    ap.add_argument("--matchesFile", help="the qrel file (for tweets) or the matches file (for updates)")
    #ap.add_argument("--nuggetsFile", help="the clusters file (for tweets) or the nuggets file (for updates)")
    ap.add_argument("--clustersFile", help="the clusters file (for tweets) or the nuggets file (for updates)")
    
    #ap.add_argument("--poolFile", help="needed for the TS tracks for tracking duplicates and if --restrict_runs_to_pool is active ") 
    #ap.add_argument("runfiles", nargs="+")
    args = ap.parse_args()

    

    # NOTE:
    # only the nuggets found in the pooled updates are listed in the matches file
    # --> these therefore, are all the nuggets found across all runs --> the normalization factor
    #
    # the clusters in the mb and rts tracks are in json format,
    # the total number of clusters is the unique relevant items found across all runs --> normalization factor

    findable_relevant_items = {}
    if args.track in ['ts13', 'ts14']:
        if not args.matchesFile:
            print ('ERROR: --matchesFile needed with track {}'.format(args.track))
            sys.exit()
        findable_relevant_items = get_findable_nuggets(args.matchesFile)
    elif args.track in ['mb15', 'rts16']:
        if not args.clustersFile:
            print ('ERROR: --clustersFile needed with track {}'.format(args.track))
            sys.exit()
        findable_relevant_items = get_findable_clusters(args.clustersFile)

    for qid, all_found in sorted(findable_relevant_items.items()):
        print ('{}\t{}'.format(qid, all_found))
    