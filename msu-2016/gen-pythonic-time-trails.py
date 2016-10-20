# this will generate time trails as done by the R code for user simulation
# Objective is to use analysis/get-trail-means.R to check if means are reasonable

import argparse
import sys
import os

from population_model import LognormalPopulationModel
from user_model import UserModel


if __name__ == "__main__":
	ap = argparse.ArgumentParser(description="generate time trails for users")
	ap.add_argument("mean_away", type=float, help="in seconds")
	ap.add_argument("stdev_away", type=float, help="in seconds")
	ap.add_argument("mean_session", type=float, help="in seconds")
	ap.add_argument("stdev_session", type=float, help="in seconds")
	ap.add_argument("id", help="identifier for parameter set")
	ap.add_argument("num_users", help="number of samples", type=int)
	ap.add_argument("outfolder")
	
	args = ap.parse_args()
	
	if not os.path.exists(args.outfolder):
		os.makedirs(args.outfolder)
		
	popModel = LognormalPopulationModel(1234, args.mean_away, args.stdev_away, args.mean_session, args.stdev_session, 0.5)
	
	print 'away mean', popModel.lnorm_away.mean_mu, ', stddev', popModel.lnorm_away.stddev_sigma
	print 'session mean', popModel.lnorm_session.mean_mu, ', stddev', popModel.lnorm_session.stddev_sigma
	
	time_spent = []
	time_away = []
	read_speed = []
	
	with open(os.path.join(args.outfolder, args.id + '.user.params'), 'w') as upf:
		print >> upf, '\t'.join(["time.spent", "time.away", "read.speed"])
		for i in xrange(args.num_users):
			A, D, V, L = popModel.generate_user_params()
			print >> upf, '\t'.join(map(str,[D, A, V]))
			time_spent.append(D)
			time_away.append(A)
			read_speed.append(V)
			
			
	# make user time trails
	timetrail_folder = os.path.join(args.outfolder, args.id + '.time-trails')
	if not os.path.exists(timetrail_folder):
		os.mkdir(timetrail_folder)
		
	for i in xrange(args.num_users):
		uid = str(i+1)
		uttfile = 'time-trail-user-' + uid
		userModel = UserModel(time_away[i], time_spent[i], read_speed[i], 0.5)
		with open(os.path.join(timetrail_folder, uttfile), 'w') as uttf:
			print >> uttf, '\t'.join(map(str,["ssn.durn", "time.away"]))			
			for ssn_durn, away_durn in userModel.generate_session_away_lengths(240*3600):
				print >> uttf, '\t'.join(map(str,[ssn_durn, away_durn]))