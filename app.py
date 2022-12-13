from flask import Flask, render_template, url_for, request
from elasticsearch import Elasticsearch
import wikipedia
from google_images_download import google_images_download

app = Flask(__name__)
es = Elasticsearch("http://localhost:9200")
gid = google_images_download.googleimagesdownload()

def google_image_api(queryString):
  params = {
    "keywords": queryString,
    "limit": 1,
    "print_urls": True,
    "no_download": True,
    "size": "medium"
  }
  print("[debug] url: {}".format(queryString))
  return gid.download(params)[0][queryString][0]

def sort_Tuple(tup):
  lst = len(tup)
  for i in range(0, lst):
    for j in range(0, lst-i-1):
      if (tup[j][1] < tup[j + 1][1]):
        temp = tup[j]
        tup[j]= tup[j + 1]
        tup[j + 1]= temp
  return tup

@app.route('/', methods=['POST', 'GET'])
def index():
  if request.method == 'POST':
    task_content = request.form['content']
    flag = False
    people_flag = False
    title_flag = False
    # search for both person and title
    resp_people = es.search(index="people-whole", query={"match": {"primaryName": task_content}})
    resp_title = es.search(index="basic", query={"match": {"primaryTitle": task_content}})

    # no data
    if len(resp_people["hits"]["hits"]) == 0 and len(resp_title["hits"]["hits"]) == 0:
      return render_template("index.html", start = False, hasData=False)

    # if we have title data, preprocessing for all
    if resp_title["hits"]["max_score"] is not None:
      title_flag = True
      print("[Searching Title] Displaying data from:")
      print(resp_title)
      title_rating = []
      title_type = {}
      title_nconst = {}
      nconst_title = {}

      for record in resp_title["hits"]["hits"]:
        nconst = record["_source"]["nconst"]
        titleType = record["_source"]["titleType"]
        primaryTitle = record["_source"]["primaryTitle"]
        avgRating = "-1"
        print("[debug] {} - {}".format(nconst, primaryTitle))
        ratingSearchResp = es.search(index="rating", query={"match": {"nconst": nconst}})
        if len(ratingSearchResp["hits"]["hits"]) != 0:
          avgRating = ratingSearchResp["hits"]["hits"][0]["_source"]["averageRating"]

        title_rating.append((primaryTitle, avgRating))
        title_type[primaryTitle] = titleType
        nconst_title[nconst] = "{}-{}".format(nconst, primaryTitle)
        title_nconst[primaryTitle] = nconst
      
      title_rating = sort_Tuple(title_rating)
      titles = []

      print(title_rating)

      deliveries = []
      for tup in title_rating:
        deliveries.append((title_nconst[tup[0]], tup[0], tup[1]))

      print("[debug]: ")
      print(deliveries)
      print(nconst_title)
      for tup in deliveries:
        intro = ""
        try:
          intro = wikipedia.page("{} {}".format(tup[1], title_type[tup[1]])).content
          intro = intro[0:intro.find("==")].strip()
        except wikipedia.exceptions.PageError:
          intro = "[Lack of work introduction data]"
        imageURL = google_image_api("{} poster".format(tup[1]))
        res = ""
        for key in nconst_title:
          if nconst_title[key] == "{}-{}".format(key, tup[1]):
            res = key
            del nconst_title[key]
            print("[debug] " + res)
            break
        print("{} - {}".format(res, tup[1]))
        titles.append({"primaryTitle": tup[1], "rating": tup[2], "introduction": intro, "url": imageURL, "nconst": res})

    # check if we have people data
    if resp_people["hits"]["max_score"] is not None:
      title_flag = True
  
    # if we have people data
    if title_flag:
      person = resp_people['hits']['hits'][0]['_source']
      print("[debug] person name: {}".format(person["primaryName"]))
      # blur answer. display suggestions
      print("[debug] task_content: {}".format(task_content))
      if person["primaryName"].lower() != task_content.lower():  
        people = resp_people["hits"]["hits"]
        print("[Searching People] Blur answer. Displaying data from:")
        print(people)

        # if we have both people and title data
        if title_flag:
          return render_template("index.html", start = False, hasData=True, blurPeople=True, people=people, flag=title_flag, titles=titles)
        # if we don't have title data
        else:
          return render_template("index.html", start = False, hasData=True, blurPeople=True, people=people, flag=title_flag)

      # accurate answer
      else:
        print("[Searching People] Accurate answer. Displaying data:")
        print(person)
        knownForTitles = person['knownForTitles'].split(",")
        titlesTmp = []
        for title in knownForTitles:
          resp = es.search(index='basic', query={"match": {"nconst": title}})
          titleName = resp["hits"]["hits"][0]["_source"]["primaryTitle"]
          resp = es.search(index="rating", query={"match": {"nconst": title}})
          avgRating = -1
          if len(resp["hits"]["hits"]) != 0:
            avgRating = resp["hits"]["hits"][0]["_source"]["averageRating"]
          titlesTmp.append((titleName, avgRating))
        titlesTmp = sort_Tuple(titlesTmp)
        # Sort the knownForTitles by ratings
        knownFor = []
        for title in titlesTmp:
          knownFor.append(title[0])
        # retrieve this person's wiki intro
        personIntro = ""
        try:
          personIntro = wikipedia.page(task_content).content
          personIntro = personIntro[0:personIntro.find("==")].strip()
        except wikipedia.exceptions.PageError:
          personIntro = "Lack of biography data"
        if personIntro == "Lack of biography data":
          try:
            personIntro = wikipedia.summary(task_content, auto_suggest=False)
          except wikipedia.exceptions.PageError:
            personIntro = "Lack of biography data"
        # retrieve a photo of this person
        personPhotoURL = google_image_api(task_content)
        urls = []
        # retrieve images of the person's works
        for title in knownFor:
          imageURL = google_image_api("{} {} poster".format(task_content, title))
          urls.append(imageURL)

        # if we have both people and title data
        if title_flag:
          return render_template('index.html', start = False, hasData=True, blurPeople=False, person=person, knownForTitles=knownFor, 
            intro=personIntro, photo=personPhotoURL, urls=urls, flag=title_flag, titles=titles)
        else:
          return render_template('index.html', start = False, hasData=True, blurPeople=False, person=person, knownForTitles=knownFor, 
            intro=personIntro, photo=personPhotoURL, urls=urls, flag=title_flag)

    # pick the title basic index
    # if users search for a title, even given a blur text, he would like to see the 
    # results be presented from the highest rating to lowest, which is very different
    # from searching for a person

    # we don't have people data but we have title data
    else:
      return render_template("index.html", start = False, hasData=True, titles=titles, flag=title_flag)
  else: 
    return render_template('index.html', start = True, hasData=True)

if __name__ == "__main__":
  app.run(debug=True) 