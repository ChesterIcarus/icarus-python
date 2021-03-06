
from typing import Dict, List

from icarus.parse.events.types import ActivityType
from icarus.parse.events.link import Link


class Activity:
    activities: Dict[str, List]

    __slots__ = ('activity_type', 'start_time', 'end_time', 'link')
    
    def __init__(self, activity_type: ActivityType, link: Link):
        self.link = link
        self.activity_type = activity_type
        self.start_time = None
        self.end_time = None