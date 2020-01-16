from bs4 import BeautifulSoup
import requests
import json
from datetime import datetime
import smtplib

FROM_EMAIL = 'less.secure.app.enabled@gmail.com'
PASSWORD = 'password'
TO_EMAIL = 'your.mail@gmail.com'


def get_product_info_of(ids):
    ''' Takes in a list of product IDs to track and returns a list of products with their ID, Name, Price and Url.
        [
            {
                "ID" : "Product1 ID",
                "Name" : "Product1 Name",
                "Price" : "Product1 Price",
                "Url" : "Product1 Url"
            },
            {
                "ID" : "Product2 ID",
                "Name" : "Product2 Name",
                "Price" : "Product2 Price",
                "Url" : "Product2 Url"
            },
            .
            .
        ]
    '''
    products = list()

    for id in ids:
        product_info = dict()
        product_url = f'https://www2.hm.com/en_in/productpage.{id}.html'

        # HnM blocks requests with headers
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:66.0) Gecko/20100101 Firefox/66.0'}
        response = requests.get(product_url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')

            tag = soup.find('h1', class_='primary product-item-headline')
            # tag.stripped_strings returns only one string.
            for product_name in tag.stripped_strings:
                product_info['Name'] = product_name

            tag = soup.find('span', class_='price-value')
            # tag.stripped_strings returns only one string.
            for product_price in tag.stripped_strings:
                # Doing my best to extract out 'wxyz' from 'Rs. w,xyz'
                product_info['Price'] = int(
                    product_price.split(' ')[-1].replace(',', ''))
            
            for img in soup.find_all('img'):
                try:
                    if product_info['Name'] in img['alt']:
                        product_info['Img'] = img['src']
                except KeyError:
                    pass

            # Just adding some extra info.
            product_info['Url'] = product_url
            product_info['ID'] = id

            products.append(product_info)

    return products


def write_to_file(products):
    ''' Dumps the current price and current timestamp of each product in a csv file. Can be later used to find trends. '''

    date_time = datetime.now()
    for p in products:
        # I really hope that HnM will keeps (and will continue to keep) product names unique, else
        # p["ID"] will have to be used a filename.
        with open(f'{p["Name"]}.csv', 'a') as f:
            # Timestamp format: HH AM/PM - dd mm yyyy
            f.write(
                f'{date_time.strftime("%I %p - %d %b %Y")}, {p["Price"]}\n')


def check_for_price_drop(products):
    ''' As the name suggests, check if the price has dropped form last recorded value.
        Returns a list of products with info whose price has dropped. '''

    drop_list = list()

    # Try, because on first run old_prices.json won't be present.
    try:
        # Note: old_prices.json contains data of all the products, but only from last run.
        with open('old_prices.json', 'r') as f:
            old_prices = json.load(f)
            for old in old_prices:
                for p in products:
                    if p["ID"] == old["ID"]:
                        old_price = old["Price"]
                        current_price = p["Price"]

                        if old_price > current_price:
                            # Before adding this product to drop_list add the old price.
                            # This will be used while sending notification mail.
                            p["Old Price"] = old_price
                            drop_list.append(p)

    except FileNotFoundError:
        print('Unable to locate old_prices.json. Creating for the first time')

    # Now that we have completed price check for each product being tracked,
    # it is time to overwrite the old_prices.json file with current data.
    with open('old_prices.json', 'w') as f:
        json.dump(products, f)

    return drop_list


def notify_price_drop(drop_list):
    ''' Takes in a list of products with price drop and sends an email for each product. '''
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(FROM_EMAIL, PASSWORD)

    for product in drop_list:
        message = f'''Subject: Price Drop Alert!!!
        \n\nHey, price for {product["Name"]} has dropped to Rs.{product["Price"]}.
        \nOld Price: Rs.{product["Old Price"]}
        \n\nCheck it out at: {product["Url"]}'''

        server.sendmail(FROM_EMAIL,
                        TO_EMAIL, message)

    server.quit()


if __name__ == '__main__':
    # Example usage. This can be wrapped in an infinite loop with time delay.
    # Or this scripted can be called from cron job.
    tracking_list = ['0669091001', '0772570002', '0497640026']
    products = get_product_info_of(tracking_list)
    write_to_file(products)
    drop_list = check_for_price_drop(products)
    notify_price_drop(drop_list)
