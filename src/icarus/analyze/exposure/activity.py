
from icarus.analyze.exposure.types import ActivityType
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Activity:
    __slots__ = ('id', 'type', 'parcel', 'start', 
        'end', 'link', 'exposure')

    def __init__(self, uuid: int, kind: ActivityType, parcel: Parcel,
            start: int, end: int, link: Link):
        self.id = uuid
        self.parcel = parcel
        self.type = kind
        self.start = start
        self.end = end
        self.link = link
        self.exposure: float = None


    def calculate_exposure(self) -> float:
        self.exposure = self.parcel.get_exposure(self.start, self.end)
        return self.exposure

    
    def export(self, agent: int, idx: int):
        return (
            self.id,
            agent,
            idx,
            self.type.value,
            self.link.id,
            self.start,
            self.end,
            self.end - self.start,
            self.exposure 
        )
