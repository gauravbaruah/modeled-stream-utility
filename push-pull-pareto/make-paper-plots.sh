#!/bin/bash


directory=$1 # the results folder "results/no.verb_unrestricted.runs_push.above-0.7"
mode=$2

debug=""
paperFolder="$HOME/HOME/large-local-work/github.com/lintool/fourdrinier/papers/SIGIR2018/push-pull-pareto/"

function makeplots {
    directory=$1
    track=$2
    mode=$3

    echo -e "\nMaking plots for ${mode} ${track} ..."
        
    if [ "$mode" == "only.push" ]; then
        
        # multi front plot
        $debug python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/norm_p-0.[159]_A-${mode}.*tsv
        
        # single front plot for p = 0.5
        $debug python pareto-frontiers.py ${track} --plot_output_folder ${directory}  ${directory}/${track}/norm_p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.tsv

        $debug mv ${directory}/norm_p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf ${directory}/${track}-p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf

    else
        $debug python pareto-frontiers.py ${track} --plot_output_folder ${directory}/${track} --paper_plots --mode ${mode} --multiple_pareto_fronts ${mode}-multi.front.pdf ${directory}/${track}/p-0.[159]_A-${mode}.{300,3600,21600}_*tsv
    fi
    
}

echo -e "\nGenerating Plots ..."
for track in ts13 ts14 mb15 rts16; do
    # we only have the only.push mode for SIGIR2017 short submission
    #for mode in only.push only.pull push.pull; do
    #    makeplots $directory $track $mode;
    #done
  
    #makeplots $directory $track only.push
    makeplots $directory $track ${mode} 

done

echo -e "\nCollating all plots into one .pdf ..."
pdftk `find ${directory} -name "*pdf" -print0 | xargs -0 echo` cat output ${directory}.pdf

echo -e "\nCopying plots into paperFolder/figures ..."

pushd ${directory}

    for f in `find . -name "*pdf"`; do
        fname=`echo $f | sed 's_^./__g' | sed 's_/_-_g'`;        
        cp $f ${paperFolder}/figures/$fname
    done

popd

cp ${directory}/*-p-0.5_A-only.push.21600_L-1.0_V-4.25_gmp.pdf ${paperFolder}/figures/  

echo 'DONE!'