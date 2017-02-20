import argparse
import sys

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description='find all unique relevant items returned by runs')
    ap.add_argument('track', choices=["ts13", "ts14", "mb15", "rts16"])

    ap.add_argument('findable_items_list')
    ap.add_argument('eval_results_file', help='file containing the unnormalized msu and pain')

    args = ap.parse_args()

    findables = {}
    with open(args.findable_items_list) as ff:
        lines = [ line.strip().split('\t') for line in ff.readlines() ]
        findables = dict( [ (qid, int(count)) for qid, count in lines] )

    print >> sys.stderr, findables

    with open(args.eval_results_file) as ef:
        average_norm_gain = 0.0
        average_pain = 0.0
        average_gain = 0.0
        for line in ef:
            run, qid, gain, pain = line.strip().split('\t')

            if qid != 'AVG':
                if args.track == 'mb15':
                    qid = 'MB' + qid
                                
                if qid not in findables:
                    # print >> sys.stderr, '{} not in findables'.format(qid)
                    continue

            if qid == 'AVG':
                print '{}\t{}\t{:.4f}\t{:.4f}\t{:.4f}\t{:.4f}'.format(run, qid, 
                                        average_norm_gain/len(findables), average_pain/len(findables), 
                                        average_gain/len(findables), average_pain/len(findables) )
                average_norm_gain = 0.0
                average_pain = 0.0
                average_gain = 0.0
            else:
                print '{}\t{}\t{:.4f}\t{:.4f}\t{:.4f}\t{:.4f}'.format(run, qid, float(gain)/findables[qid], float(pain), float(gain), float(pain) )
                average_norm_gain += float(gain)/findables[qid]
                average_gain += float(gain)
                average_pain += float(pain)