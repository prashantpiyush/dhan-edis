"""
This file contains the logic to authorize edis for a given isin and qty.

Specifically for dhan, the following APIs are called in order:
1. https://api.dhan.co/edis/form
    On browser this page when loaded immediately submits a hidden form and loads the "verifyDIS" page
    sometimes the "TransDtls" value on this page contains a "\" at the end, when manually calling the
    API, ignore it
2. https://edis.cdslindia.com/eDIS/VerifyDIS/
    This is the page which asks for tpin
3. https://edis.cdslindia.com/EDIS/VerifyPin
    When tpin is entered, the otp verification page is opened
4. https://edis.cdslindia.com/EDIS/VerifyOTP
    "trandDtls" value returned contains unicode hex characters,
    if required convert them using
        ```
        import html
        html.unescape(input)
        ```
5. https://txn.dhan.co/txnws/ReturnUrl/edis
    Lastly, this is a callback to dhan to complete the transaction
"""
import logging
import os
import time
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from utils import gmail, dhan

logger = logging.getLogger(__name__)


def _get_form_input_field_values(html_page: str) -> dict:
    soup = BeautifulSoup(html_page, 'html.parser')
    input_fields = {}
    for tag in soup.findAll('input'):
        if tag['type'] == 'hidden':
            input_fields[tag['name']] = tag['value']
    return input_fields


def _call_dhan_for_edis_form(isin: str, qty: int) -> dict:
    url = "https://api.dhan.co/edis/form"
    payload = {
        "isin": isin,
        "qty": qty,
        "exchange": "NSE",
        "segment": "EQ",
        "bulk": True
    }
    headers = {
        'access-token': os.getenv('DHAN_ACCESS_TOKEN'),
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, json=payload)
    response.raise_for_status()
    edis_form_html = response.json()['edisFormHtml']
    return _get_form_input_field_values(edis_form_html)


def _call_verify_edis_page(txn_details: dict) -> dict:
    url = "https://edis.cdslindia.com/eDIS/VerifyDIS/"

    payload = urlencode(txn_details)
    headers = {
        'authority': 'edis.cdslindia.com',
        'content-type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    return _get_form_input_field_values(response.text)


def _verify_tpin(tpin_txn_details):
    url = "https://edis.cdslindia.com/EDIS/VerifyPin"

    payload = urlencode({'userPin': os.getenv('DHAN_TPIN'), **tpin_txn_details})
    headers = {
        'authority': 'edis.cdslindia.com',
        'content-type': 'application/x-www-form-urlencoded'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    return _get_form_input_field_values(response.text)


def _verify_otp(otp_txn_details, otp):
    url = "https://edis.cdslindia.com/EDIS/VerifyOTP"
    payload = urlencode({'OTP': otp, **otp_txn_details})
    headers = {
        'authority': 'edis.cdslindia.com',
        'content-type': 'application/x-www-form-urlencoded',
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    return _get_form_input_field_values(response.text)


def dhan_callback(txn_details_for_dhan_callback) -> str:
    url = "https://txn.dhan.co/txnws/ReturnUrl/edis"

    payload = urlencode(txn_details_for_dhan_callback)
    headers = {
        'authority': 'txn.dhan.co',
        'content-type': 'application/x-www-form-urlencoded'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response.raise_for_status()
    return response.text


def _run_edis_authorization_flow(isin: str, qty: int, max_tries=5):
    try:
        txn_details = _call_dhan_for_edis_form(isin, qty)
        logger.info("Got txn details for isin=%s", isin)

        tpin_txn_details = _call_verify_edis_page(txn_details)
        logger.info("Got tpin txn details for isin=%s", isin)

        otp_txn_details = _verify_tpin(tpin_txn_details)
        logger.info("Tpin verified, got otp txn details for isin=%s", isin)

        time.sleep(60)

        otp = gmail.get_otp_from_email()

        txn_details_for_dhan_callback = _verify_otp(otp_txn_details, otp)
        logger.info("Otp verified, got txn details for dhan callback for isin=%s", isin)

        dhan_callback_response_page = dhan_callback(txn_details_for_dhan_callback)
        if 'Your EDIS is Complete.' in dhan_callback_response_page:
            logger.info("Completed dhan callback for isin=%s, Your EDIS is Complete.", isin)
        else:
            logger.error("Error in dhan callback: didn't find the text I was looking for. isin=%s", isin)

        # The OTP email is no longer required, delete it
        gmail.delete_email()
        return
    except Exception as e:
        logger.exception("Failed to complete api calls for edis auth", e)

    if max_tries <= 0:
        logger.error("Failed to edis auth for isin=%s", isin)
        exit(1)

    logger.warning("Re-trying edis auth for isin=%s", isin)
    _run_edis_authorization_flow(isin, qty, max_tries=max_tries - 1)


if __name__ == '__main__':
    try:
        _isinList = dhan.get_holdings()

        if len(_isinList) == 0:
            logger.info("No holdings found, exiting")
            exit(0)

        # only one isin code is required for bulk edis auth
        logger.info("Starting edis auth in bulk mode using isin=%s", _isinList[0][0])
        _run_edis_authorization_flow(_isinList[0][0], _isinList[0][1])

        _edis_inquery_response = dhan.edis_inquiry(isin='ALL')
        logger.info("Status of edis: %s - %s", _edis_inquery_response['status'], _edis_inquery_response['remarks'])

        statuses = {}
        for _row in _edis_inquery_response['data']:
            statuses[_row['isin']] = (_row['status'], _row['remarks'])
        for _isin, _ in _isinList:
            if _isin not in statuses:
                logger.error("edis failed isin=%s not found in edis status response", _isin)
            if statuses[_isin][0] != 'SUCCESS':
                logger.error("edis failed for isin=%s, status=%s, remarks=%s",
                             _isin, statuses[_isin][0], statuses[_isin][1])

    except Exception as exp:
        logger.exception("Error in edis flow", exp)
        exit(1)
