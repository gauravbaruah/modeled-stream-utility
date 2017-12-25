# Nugget class for encapsulating nugget data

class Nugget(object):
    
    def __init__(self, ngtid, gain, time):
        self.ngtid = ngtid
        self.gain = int(gain)
        self.time = float(time)
        self.alpha = 0

    def __repr__(self):
        return str( (self.ngtid, self.gain, self.time, self.alpha) )

