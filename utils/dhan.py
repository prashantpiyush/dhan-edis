"""
This module contains functions to interact with the Dhan API.
"""

import logging
import os
from typing import List, Tuple

from dhanhq import dhanhq

logger = logging.getLogger(__name__)

_dhan = dhanhq(str(os.getenv('DHAN_CLIENT_ID')), str(os.getenv('DHAN_ACCESS_TOKEN')))


def get_holdings() -> List[Tuple[str, int]]:
    """
    Returns a list of tuples of (isin, qty) for all holdings.
    """
    holdings = _dhan.get_holdings()

    if not holdings.get('data', None):
        logger.warning("No holdings found...")
        return []

    isin_list = []
    for item in holdings['data']:
        isin_list.append((item['isin'], item['totalQty']))
    return isin_list


def edis_inquiry(isin='ALL') -> dict:
    """
    Returns the edis inquiry for the given isin.
    """
    return _dhan.edis_inquiry(isin)
