"""Analytics package for the subscription dashboard."""

from .cohorts import *
from .orders import *
from .plots import *
from .subscriptions import *
from .weekly_metrics import *

from .cohorts import __all__ as _cohorts_all
from .orders import __all__ as _orders_all
from .plots import __all__ as _plots_all
from .subscriptions import __all__ as _subscriptions_all
from .weekly_metrics import __all__ as _weekly_metrics_all

__all__ = [
    *_cohorts_all,
    *_orders_all,
    *_plots_all,
    *_subscriptions_all,
    *_weekly_metrics_all,
]
