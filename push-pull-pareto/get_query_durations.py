# given a topic-test.xml file for the temporal summarization track
# - this script produces a topic_query_duration file

import argparse
import xml.etree.ElementTree as ET


def get_topic_query_durations(topicfile):
    tree = ET.parse(topicfile)
    events = tree.getroot()
    tqd = dict()
    for event in events:
        id, start, end = None, None, None
        for child in event:
            if child.tag == 'id':
                #print child.text
                id = child.text
            if child.tag == 'start':
                #print child.text
                start = child.text
            if child.tag == 'end':
                #print child.text
                end = child.text
        tqd[id] = (float(start), float(end))
    return tqd
        
 
if __name__ == "__main__":
    ap = argparse.ArgumentParser("description creates a topic_query_duration file required for computing MSU")
    ap.add_argument("topic_test_xml_file")
    
    args = ap.parse_args()
    
    topic_query_durations = get_topic_query_durations(args.topic_test_xml_file)
    
    for qid, times in topic_query_durations.iteritems():
        print (qid, times[0], times[1])