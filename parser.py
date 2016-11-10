import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from geopy.distance import vincenty

center=(55.7522200, 37.6155600)


def html_stripper(text):
    return re.sub('<[^<]+?>', '', str(text))


def getPrice(flat_page):
    price = flat_page.find('div', attrs={'class': 'object_descr_price'})
    price = re.split('<div>|руб|\W', str(price))
    price = "".join([i for i in price if i.isdigit()][-3:])
    return int(price)


def getCoords(flat_page):
    coords = flat_page.find('div', attrs={'class': 'map_info_button_extend'}).contents[1]
    coords = re.split('&amp|center=|%2C', str(coords))
    coords_list = []
    for item in coords:
        if item[0].isdigit():
            coords_list.append(item)
    lat = float(coords_list[0])
    lon = float(coords_list[1])
    return lat, lon


def getRoom(flat_page):
    rooms = flat_page.find('div', attrs={'class': 'object_descr_title'})
    rooms = html_stripper(rooms)
    room_number = ''
    for i in re.split('-|\n', rooms):
        if 'комн' in i:
            break
        else:
            room_number += i
    room_number = "".join(room_number.split())
    if room_number == "":
        room_number = np.nan
    return float(room_number)


def get_sp(s):
    s = s.strip(' ')
    s = re.split('\xa0', s)
    if '–' in s[0]:
        return np.nan
    if ',' in s[0]:
        s[0] = s[0].replace(',', '.')

    return float(s[0])


def get_metroDist_walk(flat_page):
    w = np.nan
    metro = flat_page.find('span', attrs={'class': 'object_item_metro_comment'})
    metro = html_stripper(metro)

    if '-' in metro:
        return np.nan
    walk = re.split(' ', metro)
    if ('пешком\n' in walk):
        w = 1
    else:
        w = 0
    metro = "".join([i for i in metro if i.isdigit()])
    if metro == '':
        return np.nan, np.nan
    return float(metro), w


def get_roomInfo(flat_page, flatStats):
    info = flat_page.find('div', attrs={'class': 'clearfix'})
    info = html_stripper(info)
    lst = re.split('-|\n', info)
    lst_new = []
    for i in lst:
        if i != '':
            lst_new.append(i)


    for i in range(len(lst_new)):

        if lst_new[i] == 'Этаж:':
            s = lst_new[i + 1]
            s = re.split('\xa0', s)
            if len(s) == 3:
                floor = int(s[0])
                nfloor = int(s[2])
            else:
                floor = int(s[0])
                nfloor = np.nan
            flatStats['Floor'], flatStats['NFloor'] = floor, nfloor

        if lst_new[i] == 'Общая площадь:':
            flatStats['Totsp'] = get_sp(lst_new[i + 1])

        if lst_new[i] == 'Жилая площадь:':
            flatStats['Livesp'] = get_sp(lst_new[i + 1])

        if lst_new[i] == 'Площадь кухни:':
            flatStats['Kitsp'] = get_sp(lst_new[i + 1])

        if lst_new[i] == 'Телефон:':
            tel = {'да': 1, 'нет': 0}
            flatStats['Tel'] = tel[lst_new[i + 1]]

        if lst_new[i] == 'Балкон:':
            if lst_new[i + 1] == 'нет' or lst_new[i + 1] == '–':
                flatStats['Bal'] = 0
            else:
                flatStats['Bal'] = 1

        if lst_new[i] == 'Тип дома:':
            new = {'новостройка': 1, 'вторичка': 0}
            s = lst_new[i + 1].strip(', ')
            flatStats['New'] = new[s]
            if ('монолитный' in lst_new[i + 2]) or ('кирпичн') in lst_new[i + 2]:
                flatStats['Brick'] = 1
            if 'панельный' in lst_new[i + 2] or 'сталинский' in lst_new[i + 2] or 'блочный' in lst_new[
                        i + 2] or 'деревянный' in lst_new[i + 2]:
                flatStats['Brick'] = 0

    return flatStats


def set_flat_nan():
    flatStats = {'District': np.nan}
    flatStats['Price'] = np.nan
    flatStats["Dist"] = np.nan
    flatStats['rooms'] = np.nan
    flatStats['Floor'] = np.nan
    flatStats['NFloor'] = np.nan
    flatStats['Metrdist'] = np.nan
    flatStats['Totsp'] = np.nan
    flatStats['Livesp'] = np.nan
    flatStats['Kitsp'] = np.nan
    flatStats['Tel'] = np.nan
    flatStats['Bal'] = np.nan
    flatStats['New'] = np.nan
    flatStats['Brick'] = np.nan
    flatStats['Walk'] = np.nan

    return flatStats


districts = ['http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=13&district%5B1%5D=14&district%5B2%5'\
             'D=15&district%5B3%5D=16&district%5B4%5D=17&district%5B5%5D=18&district%5B6%5D=19&district%5B7%5D=20'\
             '&district%5B8%5D=21&district%5B9%5D=22&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1'\
             '&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=23&district%5B10%5D=33&district%5B11%5D=34'\
             '&district%5B12%5D=35&district%5B13%5D=36&district%5B14%5D=37&district%5B15%5D=38&district%5B1%5D=24&'\
             'district%5B2%5D=25&district%5B3%5D=26&\district%5B4%5D=27&district%5B5%5D=28&district%5B6%5D=29&district'\
             '%5B7%5D=30&district%5B8%5D=31&district%5B9%5D=32&engine_version=\2&offer_type=flat$p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=39&district%5B10%5D=49&district%5B11%5D=50&district%5B12%5D=51&district%5B13%5D=52&district%5B14%5D=53&district%5B15%5D=54&district%5B16%5D=55&district%5B1%5D=40&district\%5B2%5D=41&district%5B3%5D=42&district%5B4%5D=43&district%5B5%5D=44&district%5B6%5D=45&district%5B7%5D=46&district%5B8%5D=47&district%5B9%5D=48&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=56&district%5B1%5D=57&district%5B10%5D=66&district%5B11%5D=67&district%5B12%5D=68&district%5B13%5D=69&district%5B14%5D=70&district%5B15%5D=71&district%5B2%5D=58&district%5B3%5D=59&district%5B4%5D=60&district%5B5%5D=61&district%5B6%5D=62&district%5B7%5D=63&district%5B8%5D=64&district%5B9%5D=65&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=72&district%5B1%5D=73&district%5B10%5D=82&district%5B11%5D=83&district%5B2%5D=74&district%5B3%5D=75&district%5B4%5D=76&district%5B5%5D=77&district%5B6%5D=78&district%5B7%5D=79&district%5B8%5D=80&district%5B9%5D=81&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=84&district%5B1%5D=85&district%5B10%5D=94&district%5B11%5D=95&district%5B12%5D=96&district%5B13%5D=97&district%5B14%5D=98&district%5B15%5D=99&district%5B2%5D=86&district%5B3%5D\=87&district%5B4%5D=88&district%5B5%5D=89&district%5B6%5D=90&district%5B7%5D=91&district%5B8%5D=92&district%5B9%5D=93&\engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=100&district%5B1%5D=101&district%5B10%5D=110&district%5B11%5D=111&district%5B2%5D=102&district%5B3%5D=103&district%5B4%5D=104&district%5B5%5D=105&district%5B6%5D=106&district%5B7%5D=107&district%5B8%5D=108&district%5B9%5D=109&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=112&district%5B1%5D=113&district%5B10%5D=122&district%5B11%5D=123&district%5B12%5D=124&district%5B13%5D=348&district%5B14%5D=349&district%5B15%5D=350&district%5B2%5D=114&district%5B3%5D=115&district%5B4%5D=116&district%5B5%5D=117&district%5B6%5D=118&district%5B7%5D=119&district%5B8%5D=120&district%5B9%5D=121&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1',
             'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=125&district%5B1%5D=126&district%5B2%5D=127&district%5B3%5D=128&district%5B4%5D=129&district%5B5%5D=130&district%5B6%5D=131&district%5B7%5D=132&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1'
            ]

N = 0
flats = {}
for j in range(len(districts)):
    links = []
    for page in range(1, 31):
        page_url =  districts[j].format(page)

        search_page = requests.get(page_url)
        search_page = search_page.content
        search_page = BeautifulSoup(search_page, 'lxml')
        flat_urls = search_page.findAll('div', attrs={'ng-class':"{'serp-item_removed': offer.remove.state, "
                                                                   "'serp-item_popup-opened': isPopupOpen}"})
        flat_urls = re.split('http://www.cian.ru/sale/flat/|/" ng-class="', str(flat_urls))
        for link in flat_urls:
                if link.isdigit():
                    links.append(link)


    print(j)
    for i in range(len(links)):
        N += 1
        flat_url = 'http://www.cian.ru/sale/flat/' + str(links[i]) + '/'
        flat_page = requests.get(flat_url)
        flat_page = flat_page.content
        flat_page = BeautifulSoup(flat_page, 'lxml')

        flatStats = set_flat_nan()

        flatStats['District'] = j
        flatStats['Price'] = getPrice(flat_page)
        coords = getCoords(flat_page)
        flatStats["Dist"] = vincenty(coords, center).meters/1000
        flatStats['rooms'] = getRoom(flat_page)
        flatStats['Metrdist'], flatStats['Walk'] = get_metroDist_walk(flat_page)[0], get_metroDist_walk(flat_page)[1]
        flatStats = get_roomInfo(flat_page, flatStats)
        flatStats['Link'] = links[i]

        flats[N] = flatStats


df = pd.DataFrame(flats).transpose()
df = df.reset_index()
df.rename(columns={'index': 'N'}, inplace=True)
df.to_csv('cian_result.csv', index=None)