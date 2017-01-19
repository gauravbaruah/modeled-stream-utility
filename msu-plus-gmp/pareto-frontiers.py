# script to plot avg(gain) vs avg(pain) for runs

import sys
import os
import argparse
import matplotlib.pyplot as plt 
from matplotlib.backends.backend_pdf import PdfPages  
from collections import defaultdict

def plot_graph(points, colorcodes, title_text, frontier):
    fig = plt.figure()
    #ax = fig.add_subplot(111)

    plot_x, plot_y, rnames = zip(*points)

    plt.plot(plot_x, plot_y, colorcodes)
    plt.ylabel('gain')
    plt.xlabel('pain')
    plt.title(title_text)

    fX, fY, fnames = zip(*frontier)
    plt.plot(fX, fY)
    for i, fname in enumerate(fnames):        
        plt.text(fX[i], fY[i], fname.replace('input.', ''), fontsize=10, verticalalignment='top')
    return fig

def get_pareto_frontier(points):
    # http://math.stackexchange.com/questions/101125/how-to-compute-the-pareto-frontier-intuitively-speaking/101141
    
    points.sort()
    frontier = [points[0]]
    for i in xrange(1, len(points)):
        if points[i][1] > frontier[-1][1]:
            frontier.append(points[i])
    return frontier

def get_plot_data(gvp_file_name, track, plot_out_path):
    param_str = os.path.splitext(os.path.basename(gvp_file_name))[0]
    plot_file_name = os.path.join(plot_out_path, param_str + '.pdf')
    param_str = param_str.replace('_gmp', '')
    param_str = param_str.replace('_', '; ')
    param_str = param_str.replace('-', '=')
    param_str = track.upper() + ': ' +  param_str
    return param_str, plot_file_name
    

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='computes and plots pareto frontiers')
    ap.add_argument('--plot_output_folder', help='will produce one plot per gain-vs-pain-input-file in plot_output_folder')
    ap.add_argument('track', choices=['ts13', 'ts14', 'mb15'])
    ap.add_argument('gain_vs_pain_input_files', nargs='+')    
    ap.add_argument('--topic', help='produce frontier for given topic', default='AVG')

    args = ap.parse_args()

    frontier_fractions = {}

    for gvp_file in args.gain_vs_pain_input_files:

        with open(gvp_file) as inf:
            lines = inf.readlines()
            tpclines = filter(lambda x: args.topic in x, lines)

            gain_pain_points = []
            for line in tpclines:
                r, t, g, p = line.strip().split('\t')
                gain_pain_points.append( (float(p), float(g),  r) )

            gain_pain_points.sort()
            
            frontier = get_pareto_frontier(gain_pain_points)
            for p, g, run in frontier:
                if run not in frontier_fractions:
                    frontier_fractions[run] = [1, g, p, 1]    
                else:
                    frontier_fractions[run][0] += 1
                    frontier_fractions[run][1] += g
                    frontier_fractions[run][2] += p
                    frontier_fractions[run][3] += 1

            
            if args.plot_output_folder:
                plot_title, plot_output_file = get_plot_data(gvp_file, args.track, args.plot_output_folder)
                
                gvp_plot = plot_graph(gain_pain_points, 'go', plot_title, frontier)

                pp = PdfPages(plot_output_file)
                pp.savefig(gvp_plot)
                pp.close()

    num_param_sets = float(len(args.gain_vs_pain_input_files))
    front_avg = dict(map(lambda x: (x[0], [x[1][0]/num_param_sets, x[1][1]/x[1][3], x[1][2]/x[1][3]]), frontier_fractions.items()))

    print '{}\t{}\t{}\t{}'.format('run', 'front_frac', 'avg_front_gain', 'avg_front_pain')    
    for run, data in sorted(front_avg.iteritems(), key=lambda x: (-x[1][0], -x[1][1], x[1][2])):
        frontfrac, ave_g, ave_p = data        
        print '{}\t{:.3f}\t{:.3f}\t{:.3f}'.format(run, frontfrac, ave_g, ave_p)
    
