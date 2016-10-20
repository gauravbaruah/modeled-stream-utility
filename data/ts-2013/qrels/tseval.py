#!/usr/bin/python
from __future__ import division
import argparse, sys, os
from math import exp, pi, atan
from pprint import pprint
import numpy as np
import itertools

# Expects >=4 files: Nuggets File, Updates File, Match File, Runs File(s)

# Nuggets File - Relevant text extracted from Wikipedia articles
# Query_ID Nugget_ID Nugget_Timestamp Nugget_Importance Nugget_Length (...)
# Where (...) can be extra information, including the nugget text

# Runs File - Runs file(s) provided by participant
# Query_ID Team_ID Run_ID Document_ID Sentence_ID Decision_Timestamp Confidence_Value

# Updates Sample File - Which updates were sampled:
# Query_ID Update_ID Document_ID Sentence_ID Update_Length (Update_Text)

# Matches File - What updates match what nuggets
# Query_ID Update_ID Nugget_ID Update_Start Update_End


# PARAMETERS

# Whether or not to use arc-tan for latency-penalized discount, ensures smooth
# decay with increased time
atan_discount = True

# Exponential base for latency-penalized discount
latency_base = 0.95

# Unit normalizer for latency-penalized discount (difference in seconds)
# 3600 * 6 = 6 hours, i.e. flat after about a day
latency_step = 3600 * 6

# Dictates range of latency, 2/pi is 0 to 2
latency_range = 2/pi

# Metric index on which to sort output
max_impt = 3
sorter = 2 # Expected latency-penalized gain
# measures = (nupd, expgain, explatgain, comphens, comphenslat, expverb,
# explat, expconfgain, expconflatgain, comphensconf, comphensconflat,
# expconfverb, expconflat)

# END PARAMETERS

# Global options
debug = False
binaryrel = False

# For coloring debug output
redstart = '\033[1;31m'
grstart = '\033[1;34m'
colorend = '\033[0;0m'

# Stored internally because I'm a bad person and I didn't want to have to read
# and require the xml file
starttimes = {
  "1": 1329910380,
  "2": 1347368400,
  "3": 1342766280,
  "4": 1344180300,
  "5": 1346170800,
  "6": 1351090800,
  "8": 1354286700,
  "9": 1352306147,
  "10": 1353492000
}

#Updates are stored internally as <document_id>-<sentence_id>
def make_updid(did, sid):
    return '%s-%s' % (did, sid)

# Performs all accumulation of metrics
def calc_metric(nuggets, allsamples, allruns, matches, nuggtots, nuggetsh):
    print "\t".join(("QueryID", "TeamID", "RunID", "# Updates", "Expected Gain", "Expected Latency Gain", "Comprehensiveness", "Latency Comprehensiveness", "Expected Verbosity", "Expected Latency", 
                    "Expected Confidence-Biased Gain", "Expected Confidence-Biased Latency Gain", "Confidence-Biased Comprehensiveness", "Confidence-Biased Latency Comprehensiveness", "Expected Confidence-Biased Verbosity", "Expected Confidence-Biased Latency"))

    results = {}
    totals = {}

    # For each query
    for qid, teams in sorted(allruns.items()):
        try:
            # Get the samples for the query
            samples = allsamples[qid]
        except KeyError:
            continue
        # For each team
        for tid, runs in sorted(teams.items()):
            # For each run
            for rid, docs in sorted(runs.items()):

                # Initialize all accumulators
                sumgain = 0
                sumlatgain = 0
                sumrecall = 0
                sumlatrecall = 0
                sumlat = 0
                sumverb = 0
                sumconfgain = 0
                sumconflatgain = 0
                sumconfrecall = 0
                sumconflatrecall = 0
                sumconfverb = 0
                sumconflat = 0
                sumconf = 0
                sumwords = 0
                nupd = 0
                nmatch = 0
                seen = {}
                gainarr = []

                # For each update
                for upd in sorted(docs, key=lambda x: x["time"]):
                    updid = make_updid(upd["did"], upd["sid"])
                    if (updid not in samples):
                        continue
                    supd = samples[updid]
                    # Handle exact duplicates
                    if supd["duplicate"] and supd["duplicate"] in samples:
                        updid = supd["duplicate"]
                        supd = samples[updid]

                    # Initialize update accumulators
                    gain = 0
                    matches_len = 0
                    latency_gain = 0
                    updlat = 0
                    unmatch = 0
                    otext = supd["text"]
                    updarr = [0] * len(otext)

                    # Handle duplicate updates and non-matching updates
                    if updid not in seen and updid in matches[qid]:

                        # For each match
                        for match in matches[qid][updid]:
                            try:
                                # Get associated nugget
                                nugg = nuggets[qid][match["nid"]]
                            except KeyError, err:
                                printd("Match contains invalid nugget QID:%s, NID:%s; %s" % (qid, match["nid"], err))
                                continue

                            # Convert character matches to word matches
                            updst = match["updstart"]
                            updnd = match["updend"]
                            updst = max(0, supd["text"].rfind(" ", 0, updst + 1))
                            updnd = supd["text"].find(" ", updnd, len(otext))
                            if updnd == -1:
                                updnd = len(otext)

                            # Handle novelty in nugget matches
                            if match["nid"] in seen:
                                printd("\tAlready Matched: I%d %s" % (nugg["impt"], nugg["text"]))
                                continue
                            seen[match["nid"]] = 1

                            # Mark all matched words in the update as matched
                            wordst = supd["text"].count(" ", 0, updst)
                            wordnd = supd["text"].count(" ", 0, updnd)
                            for ind in range(wordst, wordnd):
                                updarr[ind] = 1

                            # Calculate normalized relevance grade
                            rel = norm_impt(nugg, match)
                            gain += rel

                            # Calculate latency discount
                            latency = latency_discount(nugg["time"], upd["time"])

                            # Calculate latency-penalized gain
                            latency_gain += rel * latency
                            updlat += latency

                            # Number of nuggets matching this update
                            unmatch += 1

                            # Debug and output information
                            printd("\tMatch: I%d R%0.4f NT%0.2f UT%0.2f L%0.4f LEN%0.2f %s" % (nugg["impt"], rel, nugg["time"]/latency_step, upd["time"]/latency_step, latency, nugg["length"], nugg["text"]))
                            if nuggetsh is not None:
                                print >> nuggetsh, "%s\t%s\t%s\t%s\t%d\t%d\t%d" % (qid, tid, rid, match["nid"], nugg["time"], upd["time"], sumwords + supd["text"].count(" ", 0, updst))

                    # Calculate update verbosity
                    verbosity = verbosity_discount(supd["length"], sum(updarr), nuggtots[qid]["length"])
                    updlatgain = latency_gain
                    updgain = gain
                    nmatch += unmatch

                    # Accumulate measures
                    sumgain += updgain
                    sumlatgain += updlatgain
                    sumlat += updlat
                    sumrecall += gain
                    sumlatrecall += latency_gain
                    sumverb += verbosity
                    sumwords += supd["length"]

                    sumconfgain += updgain * upd["conf"]
                    sumconflatgain += updlatgain * upd["conf"]
                    sumconfrecall += gain * upd["conf"]
                    sumconflatrecall += latency_gain * upd["conf"]
                    sumconfverb += verbosity * upd["conf"]
                    sumconflat += updlat * upd["conf"]
                    sumconf += upd["conf"]
                    seen[updid] = 1

                    nupd += 1
                    umeasures = (updgain, updlatgain, supd["length"], verbosity, sumgain, sumlatgain, sumrecall, sumlatrecall, sumverb, nupd, unmatch, upd["time"], otext)
                    gainarr.append(umeasures)
                    printd("Update: %s G%0.4f LG%0.4f L%d V%0.4f SG%0.4f SLG%0.4f SR%0.4f SLR%0.4f SV%0.4f NU%d NM%d T%d %s" % ((updid,) + umeasures))
                    printd("")

                # Calculate run measures
                comphens = 0
                comphenslat = 0
                comphensconf = 0
                comphensconflat = 0
                try:
                    # Calculate comprehensiveness measures
                    comphens = sumrecall / nuggtots[qid]["impt"]
                    comphenslat = sumlatrecall / nuggtots[qid]["impt"]
                    if sumconf > 0:
                        comphensconf = sumconfrecall / (nuggtots[qid]["impt"] * sumconf)
                        comphensconflat = sumconflatrecall / (nuggtots[qid]["impt"] * sumconf)
                except KeyError, err:
                    printd("Match contains QID not in Nuggets File %s" % (err))
                    continue
                expgain = 0
                explatgain = 0
                expverb = 0
                explat = 0
                expconfgain = 0
                expconflatgain = 0
                expconfverb = 0
                expconflat = 0

                # Calculate gain measures if there are updates
                if nupd > 0:
                    tmatch = nmatch
                    sumimpt = 0
                    for impt, nimpt in sorted(nuggtots[qid]["counts"].iteritems(), key=lambda x: x[1], reverse=True):
                      if tmatch <= 0:
                        break
                      num = min(nimpt, tmatch)
                      tmatch -= num
                      sumimpt += impt * num

                    expgain = sumgain / sumverb
                    explatgain = sumlatgain / sumverb
                    expverb = sumverb / nupd
                    if nmatch > 0:
                        explat = sumlat / nmatch

                    if sumconf > 0:
                        expconfgain = sumconfgain / (sumverb * sumconf)
                        expconflatgain = sumconflatgain / (sumverb * sumconf)
                        expconfverb = sumconfverb / (nupd * sumconf)
                        if nmatch > 0:
                            expconflat = sumconflat / (nmatch * sumconf)

                printd("QID %s\tTID %s\tRID %s\tNU %d\tP %0.4f\t LP %0.4f\tC %0.4f\tLC %0.4f\tEV %0.4f\tEL %0.4f\tECG %0.4f\tECLG %0.4f\tCC %0.4f\tCLC %0.4f\tECV %0.4f\t ECL %0.4f\n" % (qid, tid, rid, nupd, expgain, explatgain, comphens, comphenslat, expverb, explat, expconfgain, expconflatgain, comphensconf, comphensconflat, expconfverb, expconflat))

                # Verbose information on missing nuggets
                for nid, nugg in sorted(nuggets[qid].iteritems(), key=lambda x: x[1]["impt"]):
                    if nid not in seen:
                        printd("%s %0.2f %s" % (nid, norm_impt(nugg), nugg["text"]))

                printd("-----------------------------------------------------\n")

                # Store accumulations for Run and Global statistics
                measures = (nupd, expgain, explatgain, comphens, comphenslat, expverb, explat, expconfgain, expconflatgain, comphensconf, comphensconflat, expconfverb, expconflat)
                ostr =  ("%s\t%s\t%s\t" % (qid, tid, rid)) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in measures])
                print ostr
                if qid not in results:
                    results[qid] = []
                trid = "%s-%s" % (tid, rid)
                results[qid].append(measures)
                if trid not in totals:
                    totals[trid] = { "tid": tid, "rid": rid, "metrics": [measures] }
                else:
                    totals[trid]["metrics"].append(measures)

        # Query statistics
        ravg = np.mean(results[qid], 0)
        rstd = np.std(results[qid], 0)
        rmin = np.amin(results[qid], 0)
        rmax = np.amax(results[qid], 0)
        print ("%s\tAVG\t-\t" % (qid)) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in ravg])
        print ("%s\tSTD\t-\t" % (qid)) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rstd])
        print ("%s\tMIN\t-\t" % (qid)) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmin])
        print ("%s\tMAX\t-\t" % (qid)) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmax])

    # Run statistics
    for res in sorted(totals.values(), key=lambda x: x["metrics"][sorter], reverse=True):
        ravg = np.mean(res["metrics"], 0)
        rstd = np.std(res["metrics"], 0)
        rmin = np.amin(res["metrics"], 0)
        rmax = np.amax(res["metrics"], 0)
        print ("AVG\t%s\t%s\t" % (res["tid"], res["rid"])) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in ravg])
        print ("STD\t%s\t%s\t" % (res["tid"], res["rid"])) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rstd])
        print ("MIN\t%s\t%s\t" % (res["tid"], res["rid"])) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmin])
        print ("MAX\t%s\t%s\t" % (res["tid"], res["rid"])) + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmax])

    # Global statistics
    resultsarr = list(itertools.chain.from_iterable(results.itervalues()))
    ravg = np.mean(resultsarr, 0)
    rstd = np.std(resultsarr, 0)
    rmin = np.amin(resultsarr, 0)
    rmax = np.amax(resultsarr, 0)
    print "AVG\tALL\t-\t" + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in ravg])
    print "STD\tALL\t-\t" + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rstd])
    print "MIN\tALL\t-\t" + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmin])
    print "MAX\tALL\t-\t" + "\t".join(["%d" % x if type(x) == "int" else "%0.4f" % x for x in rmax])

# Normalizes the importance score from Real>=0->[0-1], optionally weighting it by the proportion of the nugget matched
# If binary relevance, simple returns 1 if rel > 0
def norm_impt(nugg, match = None):
    if binaryrel:
      return 1 if nugg["impt"] != 0 else 0
    try:
        prop = (match["nuggend"] - match["nuggstart"]) / nugg["length"]
    except Exception:
        prop = 1
    return exp(nugg["impt"])/ exp(max_impt) * prop

def latency_discount(t_gold, t):
    if atan_discount:
        return 1 - (latency_range * (atan((t - t_gold) / latency_step)))
    else:
        return pow(latency_base, (t - t_gold) / latency_step)

def verbosity_discount(u_len, matches_len, avglen):
    return max(0, (u_len - matches_len) / avglen) + 1

# Reads the Nuggets file
# Query_ID Nugget_ID Nugget_Timestamp Nugget_Importance Nugget_Length (...)
def read_nuggets(nuggets_file):
    printd("Reading nuggets from %s" % nuggets_file)
    nuggets = {}
    nuggtots = {}
    with open(nuggets_file) as handle:
        linen = 0
        handle.readline()
        for line in handle:
            linen += 1
            parts = line.split()
            try:
                qid = parts[0]
                nid = parts[1]
                if qid not in nuggets:
                    nuggets[qid] = {}
                    nuggtots[qid] = { "impt": 0, "length": 0, "counts": {} }
                nuggets[qid][nid] = { "time": int(parts[2]), "impt": float(parts[3]), "length": int(parts[4]), "text": " ".join(parts[5:]) }
                impt = norm_impt(nuggets[qid][nid])
                nuggtots[qid]["impt"] += impt
                nuggtots[qid]["length"] += nuggets[qid][nid]["length"]
                if impt not in nuggtots[qid]["counts"]:
                  nuggtots[qid]["counts"][impt] = 1
                else:
                  nuggtots[qid]["counts"][impt] += 1

            except Exception, err:
                print  >> sys.stderr, "Invalid line in %s, line %d: %s" % (nuggets_file, linen, err)
    for qid, nuggs in nuggets.iteritems():
        nuggtots[qid]["length"] /= len(nuggs.keys())

    return (nuggets, nuggtots)

# Reads the Sampled updates file
# Query_ID Update_ID Document_ID Sentence_ID Update_Length (Update_Text)
def read_updates(updates_file):
    printd("Reading updates from %s" % updates_file)
    supdates = {}
    with open(updates_file) as handle:
        handle.readline()
        linen = 0
        for line in handle:
            linen += 1
            parts = line.split()
            try:
                qid    = parts[0]
                updid  = parts[1]
                docid  = parts[2]
                sid    = parts[3]
                if qid not in supdates:
                    supdates[qid] = {}
                #if docid not in supdates[qid]:
                #    supdates[qid][docid] = {}
                if len(parts) > 5:
                    dup = parts[5]
                    if dup == "NULL":
                        dup = None
                    utext = " ".join(parts[6:])
                else:
                    dup = None
                    utext = ""
                supdates[qid][updid] = { "length": int(parts[4]), "duplicate": dup, "text": utext }

            except Exception, err:
                print  >> sys.stderr, "Invalid line in %s, line %d: %s" % (updates_file, linen, err)
    return supdates

# Reads the Runs file(s)
# Query_ID Team_ID Run_ID Document_ID Sentence_ID Decision_Timestamp Confidence_Value (Update_Length)
def read_runs(runs_files):
    runs = {}
    for runs_file in runs_files:
        printd("Reading runs from %s" % runs_file)
        with open(runs_file) as handle:
            linen = 0
            for line in handle:
                linen += 1
                parts = line.split()
                if len(parts) <= 1:
                    continue
                try:
                    qid    = parts[0]
                    teamid = parts[1]
                    runid  = parts[2]
                    docid  = parts[3]
                    sid    = parts[4]
                    if qid not in runs:
                        runs[qid] = {}
                    if teamid not in runs[qid]:
                        runs[qid][teamid] = {}
                    if runid not in runs[qid][teamid]:
                        runs[qid][teamid][runid] = []
                    length = None
                    if len(parts) > 7:
                        length = int(parts[7]) 
                    conf = float(parts[6])
                    if conf == float('inf'):
                        conf = 1000
                    runs[qid][teamid][runid].append({ "did": docid, "sid": sid, "time": int(parts[5]), "conf": conf, "length": length })

                except Exception, err:
                    print  >> sys.stderr, "Invalid line in %s, line %d: %s" % (runs_file, linen, err)
    return runs

# Reads the matches file
# Query_ID Update_ID Nugget_ID Update_Start Update_End
def read_matches(matches_file):
    printd("Reading matches from %s" % matches_file)
    matches = {}
    with open(matches_file) as handle:
        handle.readline()
        linen = 0
        for line in handle:
            linen += 1
            parts = line.split()
            try:
                qid     = parts[0]
                updid   = parts[1]
                nid     = parts[2]
                if qid not in matches:
                    matches[qid] = {}
                if updid not in matches[qid]:
                    matches[qid][updid] = []
                matches[qid][updid].append({ "nid": nid, "updstart": int(parts[3]), "updend": int(parts[4])})

            except Exception, err:
                print  >> sys.stderr, "Invalid line in %s, line %d: %s" % (matches_file, linen, err)
    return matches

def printd(string):
    if debug:
        print >> sys.stderr, string

# Process args, set up globals, and optionally set up nuggets output file
def main(args):
    global debug, binaryrel
    if args.debug:
        debug = True
    if args.binaryrel:
        binaryrel = True
    (nuggets, nuggtots) = read_nuggets(args.nuggets)
    sample = read_updates(args.updates)
    runs = read_runs(args.runs)
    matches = read_matches(args.matches)

    if args.nuggetsfile:
        nuggetsh = open(args.nuggetsfile,'w')
        print >> nuggetsh, "\t".join(("QID", "TID", "RID", "NID", "NTIME", "UTIME","CWORDS"))
    else:
        nuggetsh = None

    calc_metric(nuggets, sample, runs, matches, nuggtots, nuggetsh)

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description='Computes Evaluation Metrics for Temporal Summarization 2013 Track')
    argparser.add_argument('-n', '--nuggets', help='Nuggets File (Default: ../results/nuggets.tsv)', default="../results/nuggets.tsv")
    argparser.add_argument('-u', '--updates', help='Updates File (Default: ../results/pooled_updates.tsv)', default="../results/pooled_updates.tsv")
    argparser.add_argument('-m', '--matches', help='Matches File (Default: ../results/matches.tsv)', default="../results/matches.tsv")
    argparser.add_argument('runs', nargs="+", help='Runs File(s) (SUBMISSION.sus)')
    argparser.add_argument('-d', '--debug', action='store_true', help='Debug mode (lots of output)')
    argparser.add_argument('-o', '--nuggetsfile', help='Create a nuggets matching file as well (Used by nuggets plotting script)')
    argparser.add_argument('-b', '--binaryrel', action='store_true', help='Use binary relevance instead of graded relevance')

    main(argparser.parse_args())

# vim: ts=4 sw=4 expandtab
