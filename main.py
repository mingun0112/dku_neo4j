import requests
from bs4 import BeautifulSoup as BS
import pandas as pd
import numpy as np
import re



""" 네이버 랭킹 뉴스 긁어오기 """
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36'}
d_list = []
start_data = 20241201
end_data = 20241202
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



""" 필요 없는 문자 제거 """
def clean_text(row):
    text = row['title']
    pattern = '([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("E-mail제거 : " , text , "\n")
    pattern = '(http|ftp|https)://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("URL 제거 : ", text , "\n")
    pattern = '([ㄱ-ㅎㅏ-ㅣ]+)'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("한글 자음 모음 제거 : ", text , "\n")
    pattern = '<[^>]*>'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("태그 제거 : " , text , "\n")
    pattern = r'\([^)]*\)'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("괄호와 괄호안 글자 제거 :  " , text , "\n")
    pattern = '[^\w\s]'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("특수기호 제거 : ", text , "\n" )
    pattern = '[^\w\s]'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("필요없는 정보 제거 : ", text , "\n" )
    pattern = '["단독"]'
    text = re.sub(pattern=pattern, repl='', string=text)
    pattern = '["속보"]'
    text = re.sub(pattern=pattern, repl='', string=text)
    # print("단독 속보 제거 : ", text , "\n" )
    text = text.strip()
    # print("양 끝 공백 제거 : ", text , "\n" )
    text = " ".join(text.split())
    # print("중간에 공백은 1개만 : ", text )
    return text

df['title_c'] = df.apply(clean_text, axis=1)



""" 키워드 추출 from title """
from konlpy.tag import Kkma
from konlpy.tag import Komoran

kkma = Kkma()
komoran = Komoran()
df['keyword'] = {}


for idx_line in range(len(df)):
    nouns_list = komoran.nouns(df['title_c'].loc[idx_line])
    nouns_list_c = [nouns for nouns in nouns_list if len(nouns) > 1]    # 한글자는 이상한게 많아서 2글자 이상
    df.loc[idx_line, 'keyword'] = ', '.join(nouns_list_c)

df = df[df['media'] != '코리아헤럴드']    # 코리아헤럴드는 영어 제목임
df = df[df['media'] != '주간경향']    # 주간경향은 같은 title이 많음

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



""" 한자와 공백 제거 """
# Neo4j -> Gephi 에서 parsing error의 원인이 될 수 있음
def clean_text_for_neo4j(row):
    text = row['title_c']
    text = re.sub(pattern='[^a-zA-Z0-9ㄱ-ㅣ가-힣]', repl='', string=text)
    # print("영어, 숫자, 한글만 포함 : ", text )
    return text

df['title_c_neo4j'] = df.apply(clean_text_for_neo4j, axis=1)



""" 연결 """
# Neo4j 브라우저에서 설정한 계정의 ID, PASSWORD를 통해 접속
greeter = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))  



""" 입력 """
# Cyper code를 이용,  크롤링한 Data를 DB에 입력
with greeter.session() as session:
    """ make node """
    for idx in range(len(df)):
        ent_keyword = df.iloc[idx]['keyword']  # 'keyword' 열에서 문자열을 가져옴
        nouns_list_c = ent_keyword.split(', ') 
        # print( df.iloc[idx]['title_c'])
        # print(nouns_list_c)
        session.write_transaction(add_article, title=df.iloc[idx]['title_c_neo4j'], date=df.iloc[idx]['date'],
                                  media=df.iloc[idx]['media'], keyword=nouns_list_c)
    session.write_transaction(add_media)
    session.write_transaction(add_keyword)