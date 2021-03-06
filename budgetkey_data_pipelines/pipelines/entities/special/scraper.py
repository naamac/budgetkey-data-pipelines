import time
import itertools
import logging

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from pyquery import PyQuery as pq

from datapackage_pipelines.wrapper import ingest, spew


LOGGER.setLevel(logging.WARNING)

parameters, datapackage, res_iter = ingest()

slugs = {u"\u05ea\u05d0\u05d2\u05d9\u05d3\u05d9 \u05d4\u05d0\u05d6\u05d5\u05e8  (\u05d9\u05d5''\u05e9 )": 'west_bank_corporation',
         u'\u05d0\u05d9\u05d2\u05d5\u05d3\u05d9 \u05e2\u05e8\u05d9\u05dd': 'conurbation',
         u'\u05d0\u05d9\u05d2\u05d5\u05d3\u05d9\u05dd \u05de\u05e7\u05e6\u05d5\u05e2\u05d9\u05d9\u05dd': 'professional_association',
         u'\u05d2\u05d5\u05e4\u05d9\u05dd \u05e2"\u05e4 \u05d3\u05d9\u05df': 'law_mandated_organization',
         u'\u05d4\u05e7\u05d3\u05e9 \u05d1\u05d9\u05ea \u05d3\u05d9\u05df \u05d3\u05ea\u05d9': 'religious_court_sacred_property',
         u'\u05d5\u05d5\u05e2\u05d3\u05d9\u05dd \u05de\u05e7\u05d5\u05de\u05d9\u05d9\u05dd \u05d1\u05d9\u05e9\u05d5\u05d1\u05d9\u05dd': 'local_community_committee',
         u'\u05d5\u05e2\u05d3\u05d5\u05ea \u05de\u05e7\u05d5\u05de\u05d9\u05d5\u05ea \u05dc\u05ea\u05db\u05e0\u05d5\u05df': 'local_planning_committee',
         u'\u05d5\u05e2\u05d3\u05d9 \u05d1\u05ea\u05d9\u05dd': 'house_committee',
         u'\u05d7\u05d1\u05e8\u05d5\u05ea \u05d7\u05d5\u05e5 \u05dc\u05d0 \u05e8\u05e9\u05d5\u05de\u05d5\u05ea': 'foreign_company',
         u'\u05de\u05e9\u05e8\u05d3\u05d9 \u05de\u05de\u05e9\u05dc\u05d4': 'government_office',
         u'\u05e0\u05e6\u05d9\u05d2\u05d5\u05d9\u05d5\u05ea \u05d6\u05e8\u05d5\u05ea': 'foreign_representative',
         u'\u05e7\u05d5\u05e4\u05d5\u05ea \u05d2\u05de\u05dc': 'provident_fund',
         u'\u05e8\u05d5\u05d1\u05e2\u05d9\u05dd \u05e2\u05d9\u05e8\u05d5\u05e0\u05d9\u05d9\u05dd': 'municipal_precinct',
         u'\u05e8\u05e9\u05d5\u05d9\u05d5\u05ea \u05de\u05e7\u05d5\u05de\u05d9\u05d5\u05ea': 'municipality',
         u'\u05e8\u05e9\u05d5\u05d9\u05d5\u05ea \u05e0\u05d9\u05e7\u05d5\u05d6': 'drainage_authority',
         u'\u05e8\u05e9\u05d9\u05de\u05d5\u05ea \u05dc\u05e8\u05e9\u05d5\u05d9\u05d5\u05ea \u05d4\u05de\u05e7\u05d5\u05de\u05d9\u05d5\u05ea': 'municipal_parties',
         u'\u05e9\u05d9\u05e8\u05d5\u05ea\u05d9 \u05d1\u05e8\u05d9\u05d0\u05d5\u05ea': 'health_service',
         u'\u05e9\u05d9\u05e8\u05d5\u05ea\u05d9 \u05d3\u05ea': 'religion_service',
         u'\u05d2\u05de\u05d9\u05dc\u05d5\u05ea \u05d7\u05e1\u05d3\u05d9\u05dd  (\u05d2\u05de\u05d7 )': None
         }

headers = ['kind', 'name', 'id', 'street', 'house_number', 'city', 'zipcode']


scraped_ids = set()


def scrape():

    # Prepare Driver
    driver = webdriver.Remote(
        command_executor='http://tzabar.obudget.org:8910',
        desired_capabilities=DesiredCapabilities.PHANTOMJS)

    driver.set_window_size(1200, 800)

    def prepare():
        logging.info('PREPARING')
        driver.get("http://www.misim.gov.il/mm_lelorasham/firstPage.aspx")
        bakasha = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "RadioBakasha1"))
        )
        bakasha.click()

    prepare()

    # Prepare options
    logging.info('GETTING OPTIONS')
    page = pq(driver.page_source)
    options = [pq(opt) for opt in page.find('#DropdownlistSugYeshut option')]
    options = dict((opt.attr('value'), opt.text()) for opt in options[1:])

    def select_option(selection_):
        logging.info('OPTION %s (%s)', selection_, options[selection_])
        driver.find_element_by_css_selector('option[value="%s"]' % selection_).click()
        driver.find_element_by_id('btnHipus').click()

    for selection in options.keys():
        prepare()
        if slugs.get(options[selection]) is None:
            logging.warning('SKIPPING option #%d (%s)', selection, options[selection])
            continue
        select_option(selection)
        while True:
            try:
                WebDriverWait(driver, 60, poll_frequency=5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#dgReshima tr.row1"))
                )
            except TimeoutException:
                select_option(selection)
                continue

            page = pq(driver.page_source)
            rows = page.find('#dgReshima tr.row1, #dgReshima tr.row2')
            logging.info('GOT %d ROWS', len(rows))
            for row in rows:
                row = ([slugs[options[selection]]] +
                       [pq(x).text() for x in pq(row).find('td')])
                datum = dict(zip(headers, row))
                the_id = datum['id']
                if the_id not in scraped_ids:
                    scraped_ids.add(the_id)
                    yield datum

            if len(page.find('#btnHaba')) > 0:
                next_button = driver.find_element_by_id('btnHaba')
                next_button.click()
                time.sleep(10)
            else:
                break


datapackage['resources'].append({
    'name': 'special-entities',
    'path': 'data/special-entities.csv',
    'schema': {
        'fields': [
            {'name': h, 'type': 'string'} for h in headers
        ]
    }
})

spew(datapackage, itertools.chain(res_iter, [scrape()]))
