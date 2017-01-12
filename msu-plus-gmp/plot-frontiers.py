# script to plot avg(gain) vs avg(pain) for runs

import sys
import argparse
import matplotlib.pyplot as plt 
from matplotlib.backends.backend_pdf import PdfPages  

def plot_graph(points, colorcodes, title_text):
    fig = plt.figure()
    #ax = fig.add_subplot(111)

    plot_y, plot_x, rnames = zip(*points)

    plt.plot(plot_x, plot_y, colorcodes)
    plt.ylabel('avg. gain')
    plt.xlabel('avg. pain')
    plt.title(title_text)

    for i, rname in enumerate(rnames):
        plt.text(plot_x[i], plot_y[i], rname, rotation='vertical', horizontalalignment='center', verticalalignment='bottom', fontsize=8)
    return fig


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='plotting script')
    ap.add_argument('gain_vs_pain_input_file')
    ap.add_argument('plot_output_file')
    ap.add_argument('title_text')

    args = ap.parse_args()

    with open(args.gain_vs_pain_input_file) as inf:
        lines = inf.readlines()
        avglines = filter(lambda x: 'AVG' in x, lines)

        gain_pain_points = []
        for line in avglines:
            r, t, g, p = line.strip().split('\t')
            gain_pain_points.append( (float(g), float(p),  r) )

        gain_pain_points.sort()

        gvp_plot = plot_graph(gain_pain_points, 'g^', args.title_text)

        pp = PdfPages(args.plot_output_file)
        pp.savefig(gvp_plot)
        pp.close()

    
