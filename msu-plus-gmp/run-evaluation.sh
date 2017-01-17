#!/bin/bash

track=$1
mode=$2

echo "only_push --> time away does not matter"

datafolder="../data/ts-2013"
poolfile="pooled_updates.tsv"
topicsfile="topics_masked.xml"
if [ "$track" == "ts14" ]; then
    datafolder="../data/ts-2014"
    poolfile="updates_sampled.tsv"
    topicsfile="trec2014-ts-topics-test.xml"
fi

outfiles=""

if [ "$mode" == "only_push" ]; then

    for p in 0.1 0.3 0.5 0.7 0.9;
    do
        away=$((0*60*60))
        echo "python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1 --only_push --restrict_runs_to_pool --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${track} ${datafolder}/submitted-runs/* > under-development/${track}/p-${p}_A-onpush_L-1.0_V-4.25_gmp.tsv"

        time python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1 --only_push --restrict_runs_to_pool --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean 10800 ${track} ${datafolder}/submitted-runs/* > under-development/${track}/p-${p}_A-onpush_L-1.0_V-4.25_gmp.tsv 2>>under-development/${track}.log

        outfiles="$outfiles under-development/${track}/p-${p}_A-onpush_L-1.0_V-4.25_gmp.tsv"    
    done

    python pareto-frontiers.py ${track} ${outfiles} --plot_output_folder under-development/${track}/ > under-development/${track}/only_push.fronfrac.tsv
    pdftk ${outfiles//tsv/pdf} cat output under-development/${track}/only_push_plots.pdf

fi

if [ "$mode" == "with_sessions" ]; then
    for A in 3 6 12 24;
    do
        for p in 0.1 0.3 0.5 0.7 0.9;
        do
            away=$(($A*60*60))
            echo "python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1 --restrict_runs_to_pool --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${track} ${datafolder}/submitted-runs/* > under-development/${track}/p-${p}_A-${away}_L-1.0_V-4.25_gmp.tsv"

            time python modeled_stream_utility_push-ranked_order.py -n ${datafolder}/qrels/nuggets.tsv -m ${datafolder}/qrels/matches.tsv --poolFile ${datafolder}/qrels/${poolfile} -t ${datafolder}/qrels/${topicsfile} -l ${datafolder}/update-lengths/ -u 1 --restrict_runs_to_pool --user_persistence ${p} --user_reading_mean 4.25 --user_time_away_mean ${away} ${track} ${datafolder}/submitted-runs/* > under-development/${track}/p-${p}_A-${away}_L-1.0_V-4.25_gmp.tsv 2>>under-development/${track}.log

            outfiles="$outfiles under-development/${track}/p-${p}_A-${away}_L-1.0_V-4.25_gmp.tsv"    
        done
    done

    python pareto-frontiers.py ${track} ${outfiles} --plot_output_folder under-development/${track}/ > under-development/${track}/${mode}.fronfrac.tsv
    pdftk ${outfiles//tsv/pdf} cat output under-development/${track}/${mode}_plots.pdf

fi

