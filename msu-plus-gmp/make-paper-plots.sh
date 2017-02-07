#!/bin/bash


directory="results/no.verb_unrestricted.runs_push.above-0.7"

function makeplots {
    directory=$1
    track=$2
    mode=$3
    
    if [ "$mode" == "only.push" ]; then
        python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/p-0.[159]_A-${mode}.*tsv

        python pareto-frontiers.py ${track} --plot_output_folder results/  ${directory}/${track}/p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.tsv
        mv results/p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf results/${track}-p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf

    else
        python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/p-0.[159]_A-${mode}.{300,3600,21600}_*tsv
    fi
    
}

for track in ts13 ts14 mb15 rts16; do
    # we only have the only.push mode for SIGIR2017 short submission
    #for mode in only.push only.pull push.pull; do
    #    makeplots $directory $track $mode;
    #done
    
    makeplots $directory $track only.push

done

pdftk `find ${directory} -name "*pdf" -print0 | xargs -0 echo` cat output ${directory}.pdf

pushd ${directory}

    for f in `find . -name *pdf`; do
        fname=`echo $f | sed 's_^./__g' | sed 's_/_-_g'`;
        cp $f ~/HOME/large-local-work/TREC-Microblog-papers-Jimmy/papers/SIGIR2017/ts-eval/figures/$fname
    done

popd

cp results/*-p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf ~/HOME/large-local-work/TREC-Microblog-papers-Jimmy/papers/SIGIR2017/ts-eval/figures/  

echo 'DONE!'