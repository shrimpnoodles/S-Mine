from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary
from selenium.webdriver.common.by import By
import time
import pandas as pd
import csv
from tqdm import tqdm
import boto3
import os

def getProfileListWeb(url):
    profiles = []
    options= Options()
    options.add_argument("-headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("enable-automation")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Firefox(options=options)
    
    try:
        driver.execute_script(f"location.href='{url}';")
    except:
        print("error getting page: ", url)
        return profiles
            
    resp = None
    timer = time.time() + 8
    while not resp or "CommonPageFrame_footerWrapper" not in resp or "result-placeholder" in resp and (time.time()< timer):
        time.sleep(.1)
        try:
            resp = driver.page_source
        except:
            print("retrying page, ", url)
        if "Too Many Requests" in resp:
            print("429")
            time.sleep(3)
            driver.execute_script(f"location.href='{url}';")
    soup = BeautifulSoup(resp)

    driver.close()

    profile_links = soup.find_all("a", {"class": "ResultList_resultItem__G1fpN"})

    #profiles = list(filter(lambda href: 'add' in href, [element.get('href') for element in profs]))
    
    for element in profile_links:
        href=element.get('href')
        if "add" in href:
            profiles.append((href, ))

    return profiles

def parseProfilePage(url):
    options= Options()
    options.add_argument("-headless")
    options.add_argument("--no-sandbox")
    options.add_argument("-headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("enable-automation")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Firefox(options=options)
 
    try:
         driver.execute_script(f"location.href='{url}';")
    except:
         print("error getting page: ", url)
         return None, None, None
     
    resp = None
    timer = time.time() + 6
    while not resp or "PublicProfileDetailsCard_container" not in resp and (time.time()< timer):
         time.sleep(.1)
         try:
             resp = driver.page_source
         except:
             print("retrying page, ", url)
         if "Too Many Requests" in resp:
             time.sleep(3)
             driver.execute_script(f"location.href='{url}';")
    soup = BeautifulSoup(resp)
 
    driver.close()
 
    profile_box = soup.find("div", {"class": "PublicProfileDetailsCard_container__RpWZ0"})
 
    #check sub count
    try:
         subs_count, unit = getProfileSubscriberCount(profile_box)
    except:
         return None, None, None
         
    if isValidProfile(subs_count, unit):
         #get profile username
         username = getProfileUsername(url)
         
         #subs count string
         subs_count = str(subs_count)+unit
         
         #get badge bool
         verified = isVerified(profile_box)

         return username, subs_count, verified
    else:
         return None, None, None


def getProfileUsername(url):
    username = url[29:]
    return username


def getProfileSubscriberCount(profile_box):
    subs_count = -1
    unit = ""
    subsElem = profile_box.find("div", {"data-testid": "subscribersCountText"})
    try:
        subsString = subsElem.get_text()
    except:
        subsString = ""
    
    if "m" in subsString:
        unit = "m"
        m_index = subsString.find('m')
        subs_count = float(subsString[:m_index])
    elif "k" in subsString:
        unit = "k"
        k_index = subsString.find('k')
        subs_count = float(subsString[:k_index])

    return subs_count, unit


def isValidProfile(subs_count, unit):
    valid = False
    
    if subs_count >= 40.0 or unit == 'm':
        valid = True
        
    return valid


def isVerified(profile_box):
    verified = False
    tag = profile_box.find("div", {"class" : "PublicProfileDetailsCard_inlineIcon__SFBQe"})
    if tag.find('svg'):
        verified = True

    return verified


def writeToCSV(list_, *column_names, file_name):
    csv_filename = file_name

    #append mode
    with open(csv_filename, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
    
        #headers if the file is empty
        if csvfile.tell() == 0:
            csv_writer.writerow(column_names)  #column headers
    
        csv_writer.writerows(list_)
        #csv_filename.to_csv(f"{s3://snap-mine-bucket-1}/{filename}")


#get sample of df to try
#s3_client = boto3.client('s3')
#bucket = os.getenv("snap-mine-bucket-1")
#key = "snapmine_words.csv"
def main():
    print("file read")
    search_words_df = pd.read_csv("s3://snap-mine-bucket-1/snap-mine-demo-dummy.csv")
#    search_words_df = pd.read_csv("snapmine_words.csv")
#search_words_df = pd.read_csv(f"s3://{bucket}/{key}")
#search_words_csv = "S3://snap-mine-bucket-1/snapmine_words.csv"
#search_words_df = pd.read_csv(search_words_csv)

 
    search_words_df = search_words_df[["Words"]]
    search_words_df.head()
 
 
    search_sample = search_words_df[:10]
    search_sample.head()
    
    print("urls start")

    profile_list = []
    for index, row in tqdm(search_sample.iterrows(), total = search_sample.shape[0]):
        url = 'https://www.snapchat.com/explore/'+ str(row["Words"]) +'/profiles'
        profile_list.extend(getProfileListWeb(url))
        #if index % 100 == 0:
            #writeToCSV(profile_list, "urls", file_name = "profile_urls_k_AWS-1.csv")
    profile_urls_df = pd.DataFrame(profile_list, columns = ["urls"])
    #print(df_test)

    print("reading url csv")

    #profile_urls_df = pd.read_csv("profile_urls_k_AWS-1.csv")
    profile_urls_df.head()
 
    profile_urls_df = profile_urls_df.drop_duplicates(ignore_index=True)
    print(len(profile_urls_df))
 
    print("going thru profiles")

    profile_page_info = []
    for index, row in tqdm(profile_urls_df.iterrows(), total = profile_urls_df.shape[0]):
        res = parseProfilePage(row["urls"])
        if res != (None, None, None):
            profile_page_info.append(res)
         
        #if index % 100 == 0:
            #writeToCSV(profile_page_info, "username", "subscriber count", "verified", file_name = "profile_results_k_AWS-1.csv")
 
    #profile_results_df = pd.read_csv("profile_results_k_AWS-1.csv")
    profile_results_df = pd.DataFrame(profile_page_info, columns = ["username", "subscriber count", "verified"])
    profile_results_df['link'] = profile_results_df.apply(lambda x: f"snapchat.com/add/{x['username']}", axis=1)
    profile_results_df.head()

    print(len(profile_results_df))
    print("uploading file to bucket")
    profile_results_df.to_csv("s3://snap-mine-bucket-1/profile_results_demo.csv")

def dum():
    print("test")

if __name__ == '__main__':
    main()
