#!/usr/bin/env python

from config import *
from util import notify_slack
from citadels import check_citadels
from pos import check_pos


if __name__ == '__main__':
    messages = []
    try:
    	messages += check_citadels()
    	messages += check_pos()
    except Exception, e:
        if DEBUG:
            raise
    	if e.message:
    		messages.append(e.message)
    	else:
    		raise
    if messages:
    	messages.insert(0, ' Upcoming {} Structure Maintenence Tasks'.format(CORPORATION_NAME))
    	notify_slack(sorted(messages))


