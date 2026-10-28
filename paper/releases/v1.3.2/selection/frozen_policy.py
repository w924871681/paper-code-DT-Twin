import numpy as np

def gate(e,s,r,tau,guard):
    ri=e['qaxis'].index(r)
    if guard and s[ri]==0.:return [r],True
    return [q for q in e['F'] if q==r or s[e['qaxis'].index(q)]<=(1-tau)*s[ri]],False

def rank(e,A,s):return min(A,key=lambda q:(s[e['qaxis'].index(q)],tuple(e['keys'][q])))
