#!/usr/bin/perl -w

use strict;

# Check a TREC 2013 Value Tracking Task submission for various
# common errors:
#      * extra fields
#      * extraneous and missing topics
#      * invalid retrieved documents (approximate check)
#      * invalid time stamps for retrived events
#      * invalid attribute string
#      * invalid attribute values
#      * invalid confidence values
# Messages regarding submission are printed to an error log
#
# Results input file is in the form
#     qid, tid, runid, docno, sid, time, attrib, val, con
#
# where
#
# docno must match the KBA doc-id pattern.
# sid must be a non-negative integer.
#
# time is a numeric string ([0-9]+) which when cast as an
# usigned long is between the start and end times of the event,
# inclusive. 
#
# attrib is one of the set of strings:
# {deaths, injuries, displaced, financialimpact, location}
#
# val is a positive real number or a comma-separated pair of real
# numbers denoting latitude and longitude
#
# con is a positive real number.


# Change here put error log in some other directory
my $errlog_dir = ".";

# If more than 25 errors, then stop processing; something drastically
# wrong with the file.
my $MAX_ERRORS = 25; 

# time_range{qid} = start_time:end_time
my %time_range = (
    1, "1329910380:1330774380",
    2, "1347368400:1348232400",
    3, "1342766280:1343630280",
    4, "1344180300:1345044300",
    5, "1346170800:1347034800",
    6, "1351090800:1351954800",
    7, "1340982000:1341846000",
    8, "1354286700:1355150700",
    9, "1352306147:1353170147",
    10, "1353492000:1354356000",
    );

my %topics = (
    1, 0,
    2, 0,   
    3, 0,
    4, 0,
    5, 0,
    6, 0,
    7, 0,   
    8, 0,
    9, 0,
    10, 0,
    );

my $results_file;		# input file to be checked (input param)
my $line;			# current input line
my $line_num;			# current input line number
my $errlog;			# file name of error log
my $num_errors;			
my $runid_ = "";                # holds previous runid
my ($qid, $tid, $runid, $docno, $sid, $time, $attrib, $val, $con);
my %ATTRIB = ( "deaths" => 1,
	       "injuries" => 1,
	       "displaced" => 1,
	       "financialimpact" => 1,
	       "locations" => 1
    );

my $usage = "Usage: $0 resultsfile\n";
$#ARGV == 0 || die $usage;
$results_file = $ARGV[0];

open RESULTS, "<$results_file" ||
	die "Unable to open results file $results_file: $!\n";

my @path = split "/", $results_file;
my $base = pop @path;
$errlog = $errlog_dir . "/" . $base . ".errlog";
open ERRLOG, ">$errlog" ||
	die "Cannot open error log for writing\n";
$num_errors = 0;
$line_num = 0;

# Process submission file line by line
while ($line = <RESULTS>) {
    $line_num++;
    chomp $line;
    
    # Make sure the 'location' attribute value has no spaces around
    # the commas.
    $line =~ s/\,\s+/\,/g;

    next if ($line =~ /^\s*$/);

    if ($line =~ /^\s*#/) { # pass comments through to output
	next;
    }

    my @fields = split " ", $line;
	
    if (scalar(@fields) == 9) {
       ($qid, $tid, $runid, $docno, $sid, $time, $attrib, $val, $con) = @fields
    } else {
        &error("Wrong number of fields (expecting 9)");
        exit 255;
    }

    if (int($qid) < 1 || int($qid) > 10) {
	&error("$qid is not a valid topic id.");
	next;
    }

    # check if topic id is valid, and update a hash to note down
    # existing topic id's and catch the missing ones outside this
    # while loop.
    if (int($qid) < 1 || int($qid) > 10) {
	&error("$qid is not a valid topic id.");
	next;
    }
    else {
	$topics{$qid} = 1;
    }

    # make sure runid matches the pattern and isn't inconsistent
    if (! $runid_) { 	# first line --- remember tag 
    	$runid_ = $runid;
    	if ($runid_ !~ /^[A-Za-z0-9]{1,15}$/) {
    	    &error("Run ID `$runid_' is malformed");
    	    next;
    	}
    }
    else { # otherwise just make sure one runid used
    	if ($runid ne $runid_) {
    	    &error("Run ID inconsistent (`$runid' and `$runid_')");
    	    next;
    	}
    }

    # make sure DOCNO known
    # check is only partial (i.e. you can construct cases where
    # check_input won't complain but in fact it is invalid)
    my $docid = "";
    (undef,$docid) = split "-", $docno;
    if ($docid && $docid !~ /^[0-9a-f]{32}$/) {
	&error("Unknown document `$docno'");
	next;
    }

    if ((int($sid) != $sid) || $sid < 0) {
	&error("Sentence identifier must be a non-negative integer, not $sid");
	next;
    }

    # Check the timestamp. Integers for a 32-bit version of Perl, that
    # is to be found on most systems, are wide enough to hold the time
    # stamps. The signed integer range is [-2^53, 2^53]. 
    # See http://www.perlmonks.org/?node_id=718414 for more info.
    (my $bef, my $aft) = split ":", $time_range{int($qid)};
    if (int($time) < $bef || int($time) > $aft) {
	&error("For event $qid, the time $time, does not lie in [$bef, $aft].");
	next;
    }

    # Is the attribute one of the strings 'deaths', 'injuries',
    # 'displaced', 'financialimpact', 'location'?
    if (not exists $ATTRIB{$attrib}) {
    	&error("Unknown attribute, haven't ever seen $attrib.");
    	next;
    }

    # Check the attribute in the 7th. field. If the attribute is
    # 'locations' then the comma-separated (latitude,longitude) values
    # in field 8 need to be taken care of. Otherwise, the value is in
    # R+.

    if ($attrib eq 'locations') {
	my $lat = 360.0;
	my $long = 360.0;

	($lat, $long) = split ",", $val;

	if(!$lat && !$long) {
	    &error("Wrong value following 'locations' attribute; missing latitutde-longituede pair (?,?).\n");
	    next;
	}
	elsif(!$lat) {
	    &error("Wrong value following 'locations' attribute; missing latitude (?,$long)");
	    next;
	}
	elsif(!$long) {
	    &error("Wrong value following 'locations' attribute; missing longitude ($lat,?)");
	    next;
	}

	if ($lat && ($lat < -90.0 || $lat > 90.0)) {
	    &error("Latitude must be in [-90.0, 90.0], not $lat.");
	    next;
	}
	if ($long && ($long < -180.0 || $lat > 180.0)) {
	    &error("Longitude must be in [-180.0, 180.0], not $long.");
	    next;
	}
    }
    else {
	if ($val < 0.0) {
	    &error("Attribute value must be in R+, not $val.");
	    next;
	}
    }
    
    if ($con <= 0.0) {
    	&error("Confidence value must be in R+, not $con.");
    	next;
    }
}

# Check for missing topics
foreach my $k (keys %topics) {
    if ($topics{$k} == 0) {
	&error("topic $k is missing from the results.");
    }
}

print ERRLOG "Finished processing $results_file\n";
close ERRLOG || die "Close failed for error log $errlog: $!\n";

if ($num_errors) { exit 255; }
exit 0;

# print error message, keeping track of total number of errors
sub error {
   my $msg_string = pop(@_);

    print ERRLOG 
    "run $results_file: Error on line $line_num --- $msg_string\n";

    $num_errors++;
    if ($num_errors > $MAX_ERRORS) {
        print ERRLOG "$0 of $results_file: Quit. Too many errors!\n";
        close ERRLOG ||
		die "Close failed for error log $errlog: $!\n";
	exit 255;
    }
}
