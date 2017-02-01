#!/bin/bash

track=$1
mode=$2
outdir=$3
extra_args=""

if [ $# -gt 3 ]; then
    extra_args="${*:4}"
fi

echo $track, $mode, $outdir, $extra_args

if [ ! -d "$outdir" ]; then
    mkdir -p $outdir
fi

if [ ! -d "$outdir/$track" ]; then
    mkdir -p $outdir/$track
fi

datafolder="../data/ts-2013"
poolfile="pooled_updates.tsv"
topicsfile="topics_masked.xml"
if [ "$track" == "ts14" ]; then
    datafolder="../data/ts-2014"
    poolfile="updates_sampled.tsv"
    topicsfile="trec2014-ts-topics-test.xml"
fi

qrelfile='qrels.txt'
clustersfile='clusters-2015.json'
tweet2dayepochfile='tweet2dayepoch.txt'

if [ "$track" == "mb15" ]; then
    datafolder="../data/mb-2015"
fi

if [ "$track" == "rts16" ]; then
    datafolder="../data/rts-2016"
    qrelfile="rts2016-batch-qrels.txt"
    clustersfile="rts2016-batch-clusters.json"
    tweet2dayepochfile="rts2016-batch-tweets2dayepoch.txt"
fi


# cython init
python setup.py build_ext --inplace


outfiles=""


function runeval {
    p=$1
    away=$2
    if [ "$track" == "ts13" ] || [ "$track" == "ts14" ]; then

        echo "python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1   ${extra_args} --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${track} ${mode} ${datafolder}/submitted-runs/* > ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv"

        time  python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1  ${extra_args} --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${track} ${mode} ${datafolder}/submitted-runs/* > ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv 2>>${outdir}/${track}.log

        outfiles="$outfiles ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv"    

    elif  [ "$track" == "mb15" ] || [ "$track" == "rts16" ] ; then

        echo "python modeled_stream_utility_push-ranked_order.py --matchesFile ${datafolder}/qrels/${qrelfile} --nuggetsFile ${datafolder}/qrels/${clustersfile} --tweetEpochFile ${datafolder}/qrels/${tweet2dayepochfile} -u 1 --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${extra_args}  ${track} ${mode} ${datafolder}/submitted-runs-scenario-A/* > ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv 2>>${outdir}/${track}.log"

        time python modeled_stream_utility_push-ranked_order.py --matchesFile ${datafolder}/qrels/${qrelfile} --nuggetsFile ${datafolder}/qrels/${clustersfile} --tweetEpochFile ${datafolder}/qrels/${tweet2dayepochfile} -u 1 --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${extra_args}  ${track} ${mode} ${datafolder}/submitted-runs-scenario-A/* > ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv 2>>${outdir}/${track}.log
        
        outfiles="$outfiles ${outdir}/${track}/p-${p}_A-${mode}.${away}_L-1.0_V-4.25_gmp.tsv"    

    fi

}

if [ "$mode" == "only.push" ] ; then

    for p in 0.1 0.3 0.5 0.7 0.9;
    do
        away=$((6*60*60))
        runeval $p $away
    done

    #python pareto-frontiers.py ${track} ${outfiles} --plot_output_folder ${outdir}/${track}/  > ${outdir}/${track}/${mode}.fronfrac.tsv
    #pdftk ${outfiles//tsv/pdf} cat output ${outdir}/${track}/${mode}_plots.pdf

fi

if [ "$mode" == "only.pull" ]; then

    for p in 0.1 0.5 0.9 ; 
    do
        outfiles=""
        for away in 5 10 20 30 60 120 180 360;
        do 
            away=$(($away*60))
            runeval $p $away
        done

        #python pareto-frontiers.py ${track} ${outfiles} --plot_output_folder ${outdir}/${track}/ --multiple_pareto_fronts ${mode}.P-${p}_multi-pareto.pdf > ${outdir}/${track}/${mode}.P-${p}.fronfrac.tsv
        #pdftk ${outfiles//tsv/pdf} cat output ${outdir}/${track}/${mode}.P-${p}_plots.pdf

    done

fi


if [ "$mode" == "push.pull" ]; then

    for p in 0.1 0.5 0.9 ; 
    do
        outfiles=""
        for away in 5 10 20 30 60 120 180 360;
        do 
            away=$(($away*60))
            runeval $p $away
        done

        #python pareto-frontiers.py ${track} ${outfiles} --plot_output_folder ${outdir}/${track}/ --multiple_pareto_fronts ${mode}.P-${p}_multi-pareto.pdf > ${outdir}/${track}/${mode}.P-${p}.fronfrac.tsv
        #pdftk ${outfiles//tsv/pdf} cat output ${outdir}/${track}/${mode}.P-${p}_plots.pdf

    done

fi

echo 'DONE!'