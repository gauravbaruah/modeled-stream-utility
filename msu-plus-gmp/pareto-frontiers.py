# script to plot avg(gain) vs avg(pain) for runs

import sys
import os
import argparse
import matplotlib.pyplot as plt 
from matplotlib.backends.backend_pdf import PdfPages  

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
    ap.add_argument('track', choices=['ts13', 'ts14'])
    ap.add_argument('gain_vs_pain_input_files', nargs='+')
    ap.add_argument('-frac', '--compute_frontier_fractions', action='store_true')
    ap.add_argument('--topic', help='produce frontier for given topic', default='AVG')

    args = ap.parse_args()

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
            
            if args.plot_output_folder:
                plot_title, plot_output_file = get_plot_data(gvp_file, args.track, args.plot_output_folder)
                
                gvp_plot = plot_graph(gain_pain_points, 'go', plot_title, frontier)

                pp = PdfPages(plot_output_file)
                pp.savefig(gvp_plot)
                pp.close()

    
