# Update class for encapsulating update data

from nugget import Nugget

class Update:
    def __init__(self, qid, updid, updtime, updconf, updlen, numngts, ngtstr):
        self.qid = qid
        self.updid = updid
        self.time = float(updtime)
        self.conf = float(updconf)
        self.wlen = int(updlen)
        self.numngts = int(numngts) 
        self.nuggets = [] 
        if ngtstr or self.numngts: 
            for ngts in ngtstr.split():
                self.nuggets.append(Nugget(*ngts.split(',')))

    def __repr__(self): 
        return str( (self.qid, self.updid, self.time, self.conf,
            self.wlen, self.numngts, [str(n) for n in self.nuggets]))

