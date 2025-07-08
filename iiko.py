import urlfetch
import requests
import json

from dotenv import load_dotenv
import os

load_dotenv()
IIKO_API_KEY = os.getenv('IIKO_API_KEY')


def login_iiko():
    url_api = 'https://burgerkit-co.iiko.it:443/resto/api/auth?login=kitapi&pass=' + str(IIKO_API_KEY)
    token = urlfetch.fetch(url_api).text
    return token



def logout_iiko(token):
    url_bye = 'https://burgerkit-co.iiko.it:443/resto/api/logout?key=' + str(token)
    urlfetch.fetch(url_bye)


def get_iiko_average_check_inhouse(date_from, date_to):

    try:
        token_iiko = login_iiko()
        url_param = 'https://burgerkit-co.iiko.it:443/resto/api/v2/reports/olap?key=' + str(token_iiko)
        params = {"reportType":"SALES",
                  "buildSummary":"false",
                  "groupByRowFields": ["RestorauntGroup"],
                  "aggregateFields": ["DishDiscountSumInt.average"],
                  "filters":{
                      "OpenDate.Typed":{
                          "filterType": "DateRange",
                          "periodType": "CUSTOM",
                          # "from": "2021-09-01T00:00:00.000",
                          "from": "{}T00:00:00.000".format(date_from),
                          # "to": "2021-09-02T00:00:00.000"
                           "to": "{}T00:00:00.000".format(date_to)
                      },
                      "DeletedWithWriteoff": {
                          "filterType": "IncludeValues",
                          "values": ["NOT_DELETED"]
                      },
                      "OrderDeleted": {
                          "filterType": "IncludeValues",
                          "values": ["NOT_DELETED"]
                      },
                      "OrderType": {
                          "filterType": "ExcludeValues",
                          "values": ["Доставка курьером", "Доставка самовывоз", "Доставка Яндекс.Еда"]
                      },
                      "PayTypes": {
                          "filterType": "IncludeValues",
                          "values": ["Наличные", "Visa", "SBRF"]
                      },
                      "Storned": {
                          "filterType": "IncludeValues",
                          "values": ["FALSE"]
                      },
                      "DiscountPercent": {
                          "filterType": "Range",
                          "from": 0,
                          "to": 1,
                      }
                  }
            }
        # print(params)
        response = requests.post(url_param, json=params)
        result = response.json()
        # print(result['data'])
        logout_iiko(token_iiko)

        return result['data']
    except RuntimeError:
        print('\n get_iiko_revenue error \n')
        return None


