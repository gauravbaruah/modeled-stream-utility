args <- commandArgs(T)


simulateUser <- function(outfilepre, userno, avg.time.spent, avg.time.away, reading.speed) {

    tspent = c()
    taway = c()    
    
    tsum = 0; #can't spend time beyond query duration
    repeat {
        ts.sample = -log(runif(1)) * avg.time.spent
        ta.sample = -log(runif(1)) * avg.time.away 
        # -->  as per http://preshing.com/20111007/how-to-generate-random-timings-for-a-poisson-process/
        #    - note: rate = 1 / mean 
        #    - therefore, from the website -log(runif(1)) / rate == -log(runif(1)) / (1/mean) == -log(runif(1)) * mean                       
        
        if (tsum + ts.sample > 240*3600) { #no time for a full session  ; exit
            break
        }
        
        tsum = tsum + ts.sample 
        
        if (tsum + ta.sample > 240*3600) { # session completed but so did the query_duration; add remainder
            ta.sample = (240*3600 - tsum) #reset the away time sample to the remaining time            
        }
        tsum = tsum + ta.sample
        
        tspent = c(tspent, ts.sample)
        taway = c(taway, ta.sample)      
        
        if (tsum >= 240*3600) break    
    }
    
    time.trail = data.frame(ssn.durn=tspent, time.away=taway)
    fname = paste(outfilepre, userno, sep="")
    write.table(time.trail, fname, quote=F, sep="\t", row.names=F)
    sum(time.trail)
}

# following wikipedia http://en.wikipedia.org/wiki/Log-normal_distribution#Arithmetic_moments
lognormal.samples <- function(M, S, numSamples) {
    var <- log(S^2/M^2 + 1)
    sigma <- sqrt(var)
    mu <- log(M) - 0.5*sigma^2
    print (paste('for rlnorm', mu,sigma))
    d = rlnorm(numSamples, mu, sigma)
#    print (mean(d))
    print (paste('data mean and std', mean(d), sd(d)))
    return (d)

}

if (length(args) != 7) {
    print ("usage: this.R time.away.mean time.away.stddev time.spent.mean time.spent.stddev output.folder param.set.id num.users");    
    print ("")
    print ("Note: one user model is represented by time.spent reading updates, time.away from the system before re-arrival and a reading.speed.") 
    print ("For 1 user, we sample average.time.spent, average.time.away and reading.speed from 3 'parent' lognormal distributions")
    print ("For every user session, we sample a session duration from a 'child' Exponential distribution parameterized by average.time.spent. Similary for time between sessions we sample from a 'child' Exponential distribution parameterized by average.time.away")
    print ("Parameters for Reading Speed are sourced from the TWS paper");
    stopifnot(length(args) == 7);
}

#TODO: input stddev as fractions rather than values in the same unit

set.seed(1234)

ta_mean = as.numeric(args[1])
ta_sdev = as.numeric(args[2])

ts_mean = as.numeric(args[3])
ts_sdev = as.numeric(args[4])

outpre = args[6] #paste("away", ta_mean, ta_sdev, "spent", ts_mean, ts_sdev, sep="-")
outpre = paste(args[5], outpre, sep="/")

num.users = as.numeric(args[7])

time.spent.parent = lognormal.samples(ts_mean, ts_sdev, num.users)
time.away.parent = lognormal.samples(ta_mean, ta_sdev, num.users)
reading.speed = rlnorm(num.users, meanlog=1.29, sdlog=0.558) # as per [Smucker and Clarke, Time Well Spent, IIiX 2014]

# This could be wrong [it IS wrong]
#~ time.spent.parent = rlnorm(1000, meanlog=log(ts_mean), sdlog=log( 1 + ts_sdev/ts_mean ))
#~ time.away.parent = rlnorm(1000, meanlog=log(ta_mean), sdlog=log( 1 + ta_sdev/ta_mean ))
#~ reading.speed = rlnorm(1000, meanlog=1.29, sdlog=0.558)
#
# This is wrong
#time.spent.parent = rlnorm(1000, meanlog=ts_mean, sdlog=ts_sdev)
#time.away.parent = rlnorm(1000, meanlog=ta_mean, sdlog=ta_sdev)
#reading.speed = rlnorm(1000, meanlog=1.29, sdlog=0.558)

user.params = data.frame(time.spent=time.spent.parent, time.away=time.away.parent, read.speed=reading.speed)
write.table(user.params, paste(outpre, ".user.params", sep=""), quote=F, sep="\t", row.names=F)

ttdir = paste(outpre, ".time-trails", sep="")
dir.create(ttdir)

ttfilepre = paste(ttdir, 'time-trail-user-', sep='/')

for (u in 1:num.users) {
    simulateUser(ttfilepre, u, user.params[u,]$time.spent, user.params[u,]$time.away, user.params[u,]$read.speed) # since taway is in hours
}
