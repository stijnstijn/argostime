#!/usr/bin/env python3
"""
    crawler/etos.py

    Crawler for etos.nl

    Copyright (c) 2022 Martijn <martijn [at] mrtijn.nl>

    This file is part of Argostimè.

    Argostimè is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Argostimè is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Argostimè. If not, see <https://www.gnu.org/licenses/>.
"""

from asyncio import exceptions
import json
import logging

import requests
from bs4 import BeautifulSoup

from argostime.exceptions import CrawlerException
from argostime.exceptions import PageNotFoundException

from argostime.crawler.crawl_utils import CrawlResult
from argostime.crawler.crawl_utils import parse_promotional_message

def crawl_etos(url: str) -> CrawlResult:
    """Crawler for etos.nl"""
    response: requests.Response = requests.get(url)

    if response.status_code != 200:
        logging.debug(
            "Got status code %d while getting url %s",
            response.status_code,
            url
            )
        raise PageNotFoundException(url)

    soup = BeautifulSoup(response.text, "html.parser")

    result: CrawlResult = CrawlResult(url=url)

    try:
        raw_product_json = soup.find(
            "div",
            attrs= {
                "class": "js-product-detail",
            }
        ).get("data-gtm-event")
    except AttributeError as exception:
        logging.error("Could not find a product detail json")
        raise CrawlerException from exception

    try:
        product_dict = json.loads(raw_product_json)
    except json.decoder.JSONDecodeError as exception:
        logging.error("Could not decode JSON %s, raising CrawlerException", raw_product_json)
        raise CrawlerException from exception

    logging.debug(product_dict)

    try:
        result.product_name = product_dict["ecommerce"]["detail"]["products"][0]["name"]
    except KeyError as exception:
        logging.error("No key name found in json %s parsed as %s", raw_product_json, product_dict)
        raise CrawlerException from exception

    try:
        result.product_code = product_dict["ecommerce"]["detail"]["products"][0]["id"]
    except KeyError as exception:
        logging.error("No key sku found in json %s", raw_product_json)
        raise CrawlerException from exception

    try:
        promotion_message: str = product_dict["ecommerce"]["detail"]["products"][0]["dimension20"]
        promotion: float = parse_promotional_message(promotion_message)
        logging.info("Found promotional message %s", promotion_message)
        # Try to parse this promotion
        if promotion != -1.0:
            result.discount_price = product_dict["ecommerce"]["detail"]["products"][0]["price"] * promotion
        else:
            # Couldn't parse the promotion!
            logging.error("Couldn't parse promotion %s, assuming no discount", promotion_message)
            result.normal_price = product_dict["ecommerce"]["detail"]["products"][0]["price"]
    except KeyError as exception:
        logging.info("No promotion found, assuming no discount")
        try:
            result.normal_price = product_dict["ecommerce"]["detail"]["products"][0]["price"]
        except KeyError as inner_exception:
            logging.error("No price found in json %s", raw_product_json)
            raise CrawlerException from inner_exception

    return result
