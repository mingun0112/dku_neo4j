import requests
from bs4 import BeautifulSoup as BS
import pandas as pd
import numpy as np
import re

from konlpy.tag import Kkma
from konlpy.tag import Komoran


print("크롤링 네이버 뉴스")
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'}
d_list = []
start_data = 20241201
end_data = 20241207
for date_int in range(start_data, end_data):
    date = str(date_int)
    url = "https://news.naver.com/main/ranking/popularDay.nhn?date=" + date
    html = requests.get(url, headers=headers).text
    soup = BS(html, 'html.parser')
    ranking_total = soup.find_all(class_='rankingnews_box')

    for item in ranking_total:
        media = item.a.strong.text
        news = item.find_all(class_="list_content")
        for new in news:
            d = {}
            d['media'] = media
            d['src'] = "https://news.naver.com/" + new.a['href']
            d['title'] = new.a.text
            d['date'] = date
            d_list.append(d)
df = pd.DataFrame(d_list)


def clean_text(row):
    text = row['title']
    pattern = '([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '(http|ftp|https)://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '([ㄱ-ㅎㅏ-ㅣ]+)'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '<[^>]*>'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = r'\([^)]*\)'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '[^\w\s]'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '[^\w\s]'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '["단독"]'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '["속보"]'
    text = re.sub(pattern=pattern, repl='', string=text)
    text = text.strip()
    text = " ".join(text.split())
    return text

df['title_c'] = df.apply(clean_text, axis=1)



kkma = Kkma()
komoran = Komoran()
df['keyword'] = {}


for idx_line in range(len(df)):
    nouns_list = komoran.nouns(df['title_c'].loc[idx_line])
    nouns_list_c = [nouns for nouns in nouns_list if len(nouns) > 1] 
    df.loc[idx_line, 'keyword'] = ', '.join(nouns_list_c)
    print("키워드", nouns_list_c)

df = df[df['media'] != '코리아헤럴드'] 
df = df[df['media'] != '주간경향']  

from neo4j import GraphDatabase


""" make node & relationship"""
def add_article(tx, title, date, media, keyword):
    tx.run("MERGE (a:Article {title: $title , date: $date, media: $media, keyword: $keyword})",
           title=title, date=date, media=media, keyword=keyword)


def add_media(tx):
    tx.run("MATCH (a:Article) "
           "MERGE (b:Media {name:a.media}) "
           "MERGE (a)<-[r:Publish]-(b)")


def add_keyword(tx):
    tx.run("MATCH (a:Article) "
           "UNWIND a.keyword as k "
           "MERGE (b:Keyword {name:k}) "
           "MERGE (a)-[r:Include]->(b)")


def get_common_keywords(tx):
    query = """
    MATCH (a:Media)-[:Publish]->(:Article)-[:Include]->(k:Keyword)<-[:Include]-(:Article)<-[:Publish]-(b:Media)
    WHERE a.name='KBS' AND b.name='MBC'
    RETURN DISTINCT k.name AS keyword
    """
    result = tx.run(query)
    common_keywords = [record["keyword"] for record in result]
    return common_keywords

def clean_text_for_neo4j(row):
    text = row['title_c']
    text = re.sub(pattern='[^a-zA-Z0-9ㄱ-ㅣ가-힣]', repl='', string=text)
    return text

df['title_c_neo4j'] = df.apply(clean_text_for_neo4j, axis=1)

greeter = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))  

with greeter.session() as session:
    """ make node """
    for idx in range(len(df)):
        ent_keyword = df.iloc[idx]['keyword'] 
        nouns_list_c = ent_keyword.split(', ') 
        # print( df.iloc[idx]['title_c'])
        # print(nouns_list_c)
        session.execute_write(add_article, title=df.iloc[idx]['title_c_neo4j'], date=df.iloc[idx]['date'],
                                  media=df.iloc[idx]['media'], keyword=nouns_list_c)
    session.execute_write(add_media)
    session.execute_write(add_keyword)

    common_keywords = session.execute_write(get_common_keywords)
print("")
print("")
print("")
print("")
print("")
print("")
print("")
print("")

print("KBS와 MBC에서 겹치는 키워드들:")
print("-" * 40) 
for keyword in common_keywords:
    print(f"- {keyword}")
print("-" * 40) 

