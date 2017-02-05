#!/bin/bash


directory=$1

function makeplots {
    directory=$1
    track=$2
    mode=$3
    
    if [ "$mode" == "only.push" ]; then
        python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/p-0.[159]_A-${mode}.*tsv
    else
        python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/p-0.[159]_A-${mode}.{300,3600,21600}_*tsv
    fi
    
}

for track in ts13 ts14 mb15 rts16; do
    for mode in only.push only.pull push.pull; do
        makeplots $directory $track $mode;
    done
done

pdftk `find ${directory} -name "*pdf" -print0 | xargs -0 echo` cat output ${directory}.pdf

echo 'DONE!'