from app.sources.base import BaseSource
from app.sources.hh import HHSource
from app.sources.sj import SJSource

SOURCES: dict[str, BaseSource] = {
    "hh": HHSource(),
    "sj": SJSource(),
}
