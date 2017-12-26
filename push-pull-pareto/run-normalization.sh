
track=$1

datafolder=""
findable='findable.clusters.tsv'

if [ "$track" == "rts16" ]; then
    datafolder='rts-2016'
elif [ "$track" == "mb15" ]; then
    datafolder='mb-2015'
elif [ "$track" == "ts14" ]; then
    datafolder='ts-2014'
    findable='findable.nuggets.tsv'
else
    datafolder='ts-2013'
    findable='findable.nuggets.tsv'
fi

echo $track, $datafolder

for p in 1 5 9; 
do 
    python normalize-gain-pain.py $track ../data/$datafolder/qrels/$findable results/no.verb_unrestricted.runs_push.above-0.7/$track/p-0.${p}_A-only.push.21600_L-1.0_V-4.25_gmp.tsv > results/no.verb_unrestricted.runs_push.above-0.7/$track/norm_p-0.${p}_A-only.push.21600_L-1.0_V-4.25_gmp.tsv; 
done
