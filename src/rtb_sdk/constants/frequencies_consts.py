from datetime import timedelta
from dateutil.relativedelta import relativedelta
from rtb_sdk.schemas import FrequencyLimits, Granularity
from .general_constants import INT_INFINITY



INFINITY_FREQUENCIES: FrequencyLimits = {
    '__type': 'FrequencyLimits',
    'value': {
        "w": INT_INFINITY,
        "d": INT_INFINITY,
        "h": INT_INFINITY,
        "m": INT_INFINITY,
        "t": INT_INFINITY,
    },
}

GranResolution: dict[Granularity, dict[Granularity, float]] = {
    't' : {
        't' : 1,
        'h' : 6,
        'd' : 144,
        'w' : 6*168,
        'm' : 6*730,
    },
    'h' : {
        't' : 1/6,
        'h' : 1,
        'd' : 24,
        'w' : 168,
        'm' : 730,
    },
    'd' : {
        't' : 1/(144),
        'h' : 1/24,
        'd' : 1,
        'w' : 7,
        'm' : 730/24,
    },
    'w' : {
        't' : 1/(144*7),
        'h' : 1/(24*7),
        'd' : 1/7,
        'w' : 1,
        'm' : 730/168,
    },
    'm' : {
        't' : 1/(6*730),
        'h' : 1/730,
        'd' : 24/730,
        'w' :168/730,
        'm' : 1, 
    }
}

GRAN_TO_TIMEDELTA = {
    't': timedelta(minutes=10),
    'h': timedelta(hours=1),
    'd': timedelta(days=1),
    'w': timedelta(days=7),
    'm': relativedelta(months=1),
}

GRAN_TO_PL_TIMEDELTA = {
    't': "10m",
    'h': "1h",
    'd': "1d",
    'w': "7d",
    'm': "1mo",
}

TIMEDELTA_TO_GRAN = {
    timedelta(minutes=10): 't',
    timedelta(hours=1): 'h',
    timedelta(days=1): 'd',
    timedelta(days=7): 'w',
    relativedelta(months=1): 'm',
}

GRAN_TO_PROPHET_FREQ = {
    't': "10min",
    'h': "H",
    'd': "D",
    'w': "W",
    'm': "M",
}
