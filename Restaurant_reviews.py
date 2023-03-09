import time
import os
import csv
from selenium import webdriver
from selenium.webdriver import ChromeOptions, ActionChains
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from scrapy import Selector
from selenium.webdriver.support.wait import WebDriverWait
import boto3
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv

options = ChromeOptions()
options.add_argument("--disable-blink-features")
options.add_argument("start-maximized")
options.add_argument("--incognito")
options.add_argument("--disable-images")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument('--no-sandbox')
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(options=options)

def configure():
        load_dotenv()

s3_output_bucket = 'sureter-reviews-bucket'
s3 = boto3.resource('s3',aws_access_key_id=f'{os.getenv("aws_access_key")}',aws_secret_access_key=f'{os.getenv("aws_secret_key")}')

index = 1


def get_reviews(soup2):
    output = ""
    try:
        reviews = soup2.select("div.rev_wrap.ui_columns.is-multiline div.ui_column.is-9")[:10]
        for r in reviews:
            reviews_temp = r.select_one("div.prw_rup.prw_reviews_text_summary_hsx")
            reviews_temp_1 = reviews_temp.select_one("div.entry p.partial_entry")
            if output == "":
                output = reviews_temp_1.text.replace("\n", " ")
            else:
                output = output + " " + reviews_temp_1.text.replace("\n", " ")
    except Exception as e:
        pass
    return output


def get_name(soup2):
    restaurant_name = ""
    try:
        restaurant_name = soup2.select_one("h1.HjBfq")
        if restaurant_name:
            restaurant_name = restaurant_name.text
        else:
            restaurant_name = ""
    except Exception as e:
        pass
    return restaurant_name


def get_address(soup2):
    restaurant_address = ""
    try:
        restaurant_address = soup2.select("a.AYHFM")
        if restaurant_address:
            restaurant_address = restaurant_address[1].text
        else:
            restaurant_address = ""
    except Exception as e:
        pass
    return restaurant_address


def tripadvisor_restaurant(row):
    global driver, index
    url = row['restaurant_url']
    print(index, url)
    driver.get(url)
    time.sleep(1)
    try:
        link = driver.find_element(By.XPATH, "//*/div/div[2]/div[2]/div/p/span[2]")

        if link:
            actions = ActionChains(driver)
            actions.click(link)
            actions.perform()

    except Exception as e:
        pass
    soup2 = BeautifulSoup(driver.page_source, "html.parser")
    tripadvisor_reviews = get_reviews(soup2)
    name = get_name(soup2)
    address = get_address(soup2)
    if name and address:
        google_reviews = google_restaurant(name, address)
    else:
        google_reviews = ""

    out = [index, tripadvisor_reviews + " " + google_reviews]
    with open('AI_input.csv', 'a', encoding="utf8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(out)
    index += 1


def google_restaurant(restaurant_name, restaurant_add):
    review_text = ""
    hotel_name = restaurant_name.replace(",", " ")
    restaurant_address = restaurant_add.replace(",", " ")
    driver.get("https://www.google.com/")
    try:
        driver.find_element(By.NAME, "q")
        search_query = f"{hotel_name} {restaurant_address}"
        search_query = search_query.replace(' ', '+')
        search_url = f"https://www.google.com/search?q={search_query}"
        driver.get(search_url)
        WebDriverWait(driver, 1)
        try:
            driver.find_element(By.XPATH, "//*[@class='hqzQac']").click()
            time.sleep(1.5)
        except:
            try:
                driver.find_element(By.XPATH, "//*[@class='qB0t4']").click()
                time.sleep(1.5)
            except:
                pass
        try:
            driver.find_element(By.XPATH, "//*[@data-sort-id='newestFirst']").click()
            time.sleep(1.5)
            resp = Selector(text=driver.page_source)
            restaurant_review = resp.css('div.Jtu6Td > span >span:nth-child(-n+10)::text')
            review_text = [review.get().strip() if review is not None else '' for review in restaurant_review]
            for review in restaurant_review:
                if review is not None:
                    if review_text == "":
                        review_text = review.get().strip()
                    else:
                        review_text = review_text + " " + review.get().strip()
            print('Reviews: ', review_text)
        except:
            pass
    except:
        pass
    return review_text


def main():
    global index
    with open('input.csv', 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            tripadvisor_restaurant(row)

if __name__ == "__main__":
    main()
    file_name = 'Restaurant-reviews-' + time.strftime("%Y-%m-%d") + '.csv'
    s3.meta.client.upload_file('./AI_input.csv', s3_output_bucket,file_name)
    # google_restaurant()

