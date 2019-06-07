# TWITTER SCRAPER using Selenium and BeautifulSoup
# Alex Eng

# This Twitter scraper can extract tweets (& relevant metadata),
# composed BY or AT a specified @username, during a specified time period.

# The extracted tweet metadata include:
# timestamp, Twitter account ID, Twitter @username, Twitter name,
# tweet text, counts of replies, RTs, and favorites.

# The data is saved as a CSV file in the same directory as the .py file.

# The scraper also employs an adjustable cool down period between scrolls.
# Simply adjust the path_to_chromedriver field below, run,
# and enter the parameters when prompted.

# Happy scraping!

from selenium import webdriver
from bs4 import BeautifulSoup
import time
import datetime
import csv
import io
import getpass

# utility function to parse dates
def _to_date(date_str):
    date_split = date_str.split("-")
    return datetime.date(int(date_split[0]), int(date_split[1]), int(date_split[2]))

# start Selenium webdriver with path to Chrome webdriver
options = webdriver.ChromeOptions()
# AGRESSIVE: options.setPageLoadStrategy(PageLoadStrategy.NONE); # https://www.skptricks.com/2018/08/timed-out-receiving-message-from-renderer-selenium.html
options.add_argument("start-maximized") # https://stackoverflow.com/a/26283818/1689770
options.add_argument("enable-automation") # https://stackoverflow.com/a/43840128/1689770
# options.add_argument("--headless") # only if you are ACTUALLY running headless
options.add_argument("--no-sandbox") # https://stackoverflow.com/a/50725918/1689770
options.add_argument("--disable-infobars") # https://stackoverflow.com/a/43840128/1689770
options.add_argument("--disable-dev-shm-usage") # https://stackoverflow.com/a/50725918/1689770
options.add_argument("--disable-browser-side-navigation") # https://stackoverflow.com/a/49123152/1689770
options.add_argument("--disable-gpu") # https://stackoverflow.com/questions/51959986/how-to-solve-selenium-chromedriver-timed-out-receiving-message-from-renderer-exc
driver = webdriver.Chrome(path_to_chromedriver, options = options)

# input & parse scraper parameters
username = input("Enter Twitter username: ")
password = getpass.getpass("Enter Twitter password: ")
screen_name = input("Enter username to analyze (with leading '@'): ")
to_by_select = input("Analyze tweets AT (0) or BY (1) the use: ")
to_by = "to"
if to_by_select == 1:
    to_by = "by"
since_date_unparsed = input("From when? (YYYY-MM-DD): ")
since_date = _to_date(since_date_unparsed)
until_date_unparsed = input("Until when? (YYYY-MM-DD): ")
until_date = _to_date(until_date_unparsed)
url = "https://twitter.com/search?f=tweets&vertical=default&q={}:{}+since:{}+until:{}&src=typd+include:retweets".format(to_by, screen_name, since_date.isoformat(), until_date.isoformat())
print("\nReady to scrape tweets ", to_by, " ", screen_name)
print("\tfrom ", since_date_unparsed, " to ", until_date_unparsed)
print("\tusing account @", username)
print("Proceeding with URL: ", url)

# log into twitter to access historical tweets
def login():
    # open the web page in the browser:
    driver.get("https://twitter.com/login")
    driver.implicitly_wait(4)

    # find the boxes for username and password & fill them
    username_field = driver.find_element_by_class_name("js-username-field")
    password_field = driver.find_element_by_class_name("js-password-field")
    username_field.send_keys(username)
    driver.implicitly_wait(2)
    password_field.send_keys(password)
    driver.implicitly_wait(2)

    # find & click the "Log In" button:
    driver.find_element_by_class_name("EdgeButtom--medium").click()
    driver.implicitly_wait(7)

# scroll through Twitter pages to end and get aggregate HTML file
def tweet_scroller(url):
    driver.get(url)
    # define initial page height for 'while' loop
    lastHeight = driver.execute_script("return document.body.scrollHeight")
    # keep count of scrolls for cool-off periods
    scrollcount = 0

    while(True):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        # update new page height
        newHeight = driver.execute_script("return document.body.scrollHeight")

        # stop if bottom reached, i.e. new & old page heights are the same
        if(newHeight == lastHeight):
            break
        else:
            lastHeight = newHeight

        scrollcount += 1
        # give Twitter's servers a 30s break every 50 scrolls,
        # and a 2-minute break every 200 scrolls
        if((scrollcount % 50 == 0) & (scrollcount % 200 != 0)):
            time.sleep(30)
        elif(scrollcount % 200 == 0):
            time.sleep(120)

    html = driver.page_source
    return html

# parse HTML and extract tweet metadata using BeautifulSoup
def scrapper(url):
    # scroll through pages and get HTML file
    soup = BeautifulSoup(tweet_scroller(url), "html.parser")

    # initialize array of tweet dictionaries (one dictionary per tweet)
    tweets = []

    # process tweet dictionaries
    for li in soup.find_all("li", class_='js-stream-item'):
        # ignore data that isn't a tweet
        if 'data-item-id' not in li.attrs:
            continue
        else:
            tweet = {
                'tweet_id': li['data-item-id'],
                'text': None,
                'user_id': None,
                'user_screen_name': None,
                'user_name': None,
                'created_at': None,
                'retweets': 0,
                'likes': 0,
                'replies': 0
            }

            # Tweet Text
            text_p = li.find("p", class_="tweet-text")
            if text_p is not None:
                tweet['text'] = text_p.get_text()

            # Tweet User ID, User Screen Name, User Name
            user_details_div = li.find("div", class_="tweet")
            if user_details_div is not None:
                tweet['user_id'] = user_details_div['data-user-id']
                tweet['user_screen_name'] = user_details_div['data-screen-name']
                tweet['user_name'] = user_details_div['data-name']

            # Tweet date
            date_span = li.find("span", class_="_timestamp")
            if date_span is not None:
                tweet['created_at'] = float(date_span['data-time-ms'])

            # Tweet Retweets
            retweet_span = li.select("span.ProfileTweet-action--retweet > span.ProfileTweet-actionCount")
            if retweet_span is not None and len(retweet_span) > 0:
                tweet['retweets'] = int(retweet_span[0]['data-tweet-stat-count'])

            # Tweet Likes
            like_span = li.select("span.ProfileTweet-action--favorite > span.ProfileTweet-actionCount")
            if like_span is not None and len(like_span) > 0:
                tweet['likes'] = int(like_span[0]['data-tweet-stat-count'])

            # Tweet Replies
            reply_span = li.select("span.ProfileTweet-action--reply > span.ProfileTweet-actionCount")
            if reply_span is not None and len(reply_span) > 0:
                tweet['replies'] = int(reply_span[0]['data-tweet-stat-count'])

            tweets.append(tweet)

    print("\nParsed ", len(tweets), " tweets.")

    # csv writer function and output file
    writer_csv_3(tweets)
    return

# write CSV file from tweet dictionaries
def writer_csv_3(tweets):
    # rename file based on screen name parameter
    file_out = "tweets_{}_{}_from_{}_to_{}.csv".format(to_by, screen_name, since_date_unparsed, until_date_unparsed)
    with io.open(file_out, "w", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, lineterminator='\n', delimiter=',', quotechar='"')
        for i in tweets:
            if(i['text']):
                newrow = i['created_at'], i['user_id'], i['user_screen_name'], i['user_name'], i['text'], i['replies'], i['retweets'], i['likes']
                writer.writerow(newrow)
            else:
                pass
    print("\nFile successfully written to .py script directory.")

#main
if __name__ == "__main__":
    login()
    scrapper(url)
    driver.quit()
