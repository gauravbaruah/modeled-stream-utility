# script to plot avg(gain) vs avg(pain) for runs

import sys
import os
import argparse
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict

from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes, inset_axes
from mpl_toolkits.axes_grid1.inset_locator import mark_inset

import numpy as np

def plot_graph(points, colorcodes, title_text, frontier):
    fig = plt.figure()
    #ax = fig.add_subplot(111)

    #plt.tight_layout()

    plot_x, plot_y, rnames = zip(*points)

    plt.plot(plot_x, plot_y, colorcodes)
    plt.ylabel('gain')
    plt.xlabel('pain')
    plt.title(title_text)

    fX, fY, fnames = zip(*frontier)
    plt.plot(fX, fY)
    for i, fname in enumerate(fnames):
        plt.text(fX[i], fY[i], fname.replace('input.', ''), fontsize=10, verticalalignment='top')
    plt.tight_layout()
    return fig

def plot_multiple_pareto_frontiers(multi_fronts, colorcodes):
    fig = plt.figure()
    

    plt.ylabel('gain')
    plt.xlabel('pain')

    track = multi_fronts[0][1][:multi_fronts[0][1].index(': ')]

    plt.title( track + ": " + 'Pareto frontiers')

    multi_fronts.sort(key=lambda x: int(x[1].split(';')[1].split('.')[2]))

    for frontier, paramstring in multi_fronts:
        fX, fY, fnames = zip(*frontier)
        paramstring = paramstring.replace(track +': ', '')
        p, A, L, V = paramstring.split(';')
        A = 'A=' + A.split('.')[-1]
        plt.plot(fX, fY, marker='o', label='; '.join([p,A]) )
        #plt.plot(fX, fY, colorcodes)
        for i, fname in enumerate(fnames):
            plt.text(fX[i], fY[i], fname.replace('input.', ''), fontsize=8, verticalalignment='top')
    plt.legend(loc='lower right')
    plt.tight_layout()
    return fig


def draw_inset_plot(ax, inset_frontier, mode, track):
    zoom = 2
    if track == 'TS14':
        zoom = 1.25
    elif track == 'TS13':
        zoom = 1.75
    elif track == 'MB15':
        zoom = 3


    ax_inset = zoomed_inset_axes(ax, zoom, loc=7)

    frontier, paramstring = inset_frontier
            
    fX, fY, fnames = zip(*frontier)

    paramstring = paramstring.replace(track +': ', '')
    p, A, L, V = paramstring.split(';')
    A = 'A=' + A.split('.')[-1]
    legendlabel = '; '.join([p,A])

    if mode == 'only.push':
        legendlabel = p

    ax_inset.plot(fX, fY, marker='o', linestyle='solid', color='orange', label= legendlabel)

    for i, fname in enumerate(fnames):
        ax_inset.text(fX[i], fY[i], fname.replace('input.', ''), fontsize=10, verticalalignment='top', color='orange')
    
    x1, x2, y1, y2 = 0, 0, 0, 0
    xstep, ystep = 0,0
    if track == 'RTS16':
        x1, x2, y1, y2 = 0, 3, 0, .4
        xstep = 1
        ystep = 0.1
    elif track == 'MB15':
        x1, x2, y1, y2 = 0, 6, 0, 1.6
        xstep = 1
        ystep = 0.5
    elif track == 'TS14':
        x1, x2, y1, y2 = 0, 60, 0, 15
        xstep = 10
        ystep = 5
    elif track == 'TS13':
        x1, x2, y1, y2 = 0, 25, 0, 11
        xstep = 5
        ystep = 2
    
    print  track, x1, x2, y1, y2 

    ax_inset.set_xlim(x1, x2)
    ax_inset.set_ylim(y1, y2)
    ax_inset.set_xticks(np.arange(x1, x2+.1, xstep))
    ax_inset.set_yticks(np.arange(y1, y2+.1, ystep))
    ax_inset.plot([0, y2], [0, y2], c='blue', ls='dotted')


def make_paper_plots(multi_fronts, mode):

    fig = plt.figure()

    plt.ylabel('gain')
    plt.xlabel('pain')

    track = multi_fronts[0][1][:multi_fronts[0][1].index(': ')]

    plt.title( track + ": {} ".format(mode) + 'Pareto frontiers')

    multi_fronts.sort(key=lambda x: (float(x[1].split(';')[0].split('=')[1]), int(x[1].split(';')[1].split('.')[2])))

    colors = ['orange', 'green', 'black']
    linestyles = ['solid', 'dashed', 'dotted']
    if mode == 'only.push':
        linestyles = ['solid'] * 3

    lsi = 0
    for frontier, paramstring in multi_fronts:

        # print paramstring
        # print len(frontier)

                
        fX, fY, fnames = zip(*frontier)
        # print fnames

        paramstring = paramstring.replace(track +': ', '')
        p, A, L, V = paramstring.split(';')
        A = 'A=' + A.split('.')[-1]
        legendlabel = '; '.join([p,A])

        # if '300' in legendlabel and '0.9' in legendlabel:
        #     lsi += 1
        #     continue

        if mode == 'only.push':
            legendlabel = p

        plt.plot(fX, fY, marker='o', linestyle=linestyles[lsi%3], color=colors[ lsi%3 if mode == 'only.push' else lsi/3 ], label= legendlabel)

        for i, fname in enumerate(fnames):
            plt.text(fX[i], fY[i], fname.replace('input.', ''), fontsize=10, verticalalignment='top', color=colors[ lsi%3 if mode == 'only.push' else lsi/3 ])
            # print '{:.3f}\t{:.3f}\t{}\t{}'.format(fY[i], fX[i], fY[i] >= fX[i], fname)
        lsi += 1
    
    xmin, xmax = plt.xlim()
    if xmax > 250:
        plt.xlim( 0, 250 )
    #plt.ylim( 0, 25 )

    ymin, ymax = plt.ylim()

    plt.plot([0, ymax-1e-8], [0, ymax], c='blue', ls='dotted')
    
    plt.legend(loc='upper left')

    

    ax = plt.gca()
    
    # ax_inset = inset_axes(ax, width='30%', height='30%', loc=4)
    draw_inset_plot(ax, multi_fronts[0], mode, track)
   
        
    plt.tight_layout()
    
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
    ap.add_argument('track', choices=['ts13', 'ts14', 'mb15', 'rts16'])
    ap.add_argument('--topic', help='produce frontier for given topic', default='AVG')
    ap.add_argument('--multiple_pareto_fronts', help="output filename for plot with multiple pareto frontiers for various parameter settings")
    ap.add_argument("--mode", choices=['only.push', 'only.pull', 'push.pull'])
    ap.add_argument("--paper_plots", action="store_true", help="plots for the paper")
    ap.add_argument('gain_vs_pain_input_files', nargs='+')
    args = ap.parse_args()

    print args

    if args.paper_plots:
        args_error = False
        if not args.mode:
            print 'ERROR: --mode needed with --paper_plots'
            args_error = True
        if args.mode == 'only.push' and len(args.gain_vs_pain_input_files) != 3:
            print 'ERROR: --mode only.push needs 3 gain_vs_pain_input_files {0.1 0.5 0.9}'
            args_error = True
        if args.mode in ['only.pull', 'push.pull'] and len(args.gain_vs_pain_input_files) != 9:
            print 'ERROR: --mode {} needs 9 gain_vs_pain_input_files {0.1 0.5 0.9} x {5m, 1h, 6h}'.format(args.mode)
            args_error = True
        if args_error:
            sys.exit()
        args.gain_vs_pain_input_files.sort()


    frontier_fractions = {}

    multi_fronts = []

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
                print p, g, run
                if run not in frontier_fractions:
                    frontier_fractions[run] = [1, g, p, 1]
                else:
                    frontier_fractions[run][0] += 1
                    frontier_fractions[run][1] += g
                    frontier_fractions[run][2] += p
                    frontier_fractions[run][3] += 1

            plot_title, plot_output_file = get_plot_data(gvp_file, args.track, args.plot_output_folder)

            if args.multiple_pareto_fronts:
                multi_fronts.append( (frontier, plot_title) ) # the frontier and the param settings in the plot_title

            if args.plot_output_folder and not args.multiple_pareto_fronts:               
                
                if 'only.push' in plot_title:
                    plot_title = plot_title.replace('.21600', '')                           

                gvp_plot = plot_graph(gain_pain_points, 'go', plot_title, frontier)

                pp = PdfPages(plot_output_file)
                pp.savefig(gvp_plot)
                pp.close()

    if args.multiple_pareto_fronts:

        multi_front_plot = plot_multiple_pareto_frontiers(multi_fronts, 'go')
        if args.paper_plots:
            multi_front_plot = make_paper_plots(multi_fronts, args.mode)
        pp = PdfPages(os.path.join(args.plot_output_folder, args.multiple_pareto_fronts))
        pp.savefig(multi_front_plot)
        pp.close()

    num_param_sets = float(len(args.gain_vs_pain_input_files))
    front_avg = dict(map(lambda x: (x[0], [x[1][0]/num_param_sets, x[1][1]/x[1][3], x[1][2]/x[1][3]]), frontier_fractions.items()))

    print '{}\t{}\t{}\t{}'.format('run', 'front_frac', 'avg_front_gain', 'avg_front_pain')
    for run, data in sorted(front_avg.iteritems(), key=lambda x: (-x[1][0], -x[1][1], x[1][2])):
        frontfrac, ave_g, ave_p = data
        print '{}\t{:.3f}\t{:.3f}\t{:.3f}'.format(run, frontfrac, ave_g, ave_p)

