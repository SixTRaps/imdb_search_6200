from elasticsearch import Elasticsearch
import os

es = Elasticsearch("http://localhost:9200")
nameDataURL = "./data/name.basics.tsv"
basicDataURL = "./data/title.basics.tsv"
ratingDataURL = "./data/title.ratings.tsv"

# es.options(ignore_status=[400,404]).indices.delete(index='people')
# es.options(ignore_status=[400,404]).indices.delete(index='basic')
# es.options(ignore_status=[400,404]).indices.delete(index='rating')
print("Start indexing...")

whole_config = {
  "settings": {
    "analysis": {
      "analyzer": {
        "keyword_analyzer": {
          "type": "custom",
          "tokenizer": "keyword",
          "filter": "lowercase"
        },
        "stop_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": [
            "lowercase",
            "english_stop"
          ]
        }
      },
      "filter": {
        "english_stop": {
          "type": "stop",
          "stopwords":"_english_"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "title": {
        "type": "text",
        "analyzer": "keyword_analyzer",
        "search_analyzer": "stop_analyzer",
        "search_quote_analyzer": "keyword_analyzer"
      }
    }
  }
}

es.indices.create(index = "people-whole", settings=whole_config["settings"], mappings=whole_config["mappings"])
es.indices.create(index = "basic", settings=whole_config["settings"], mappings=whole_config["mappings"])
es.indices.create(index = "rating")
print("Indices created successfully...")
with open(nameDataURL) as f:
  l = f.readlines()
  l.pop(0)
  counter = 0
  for line in l:
    record = line.split("\t")
    d = {
      "nconst": record[0],
      "primaryName": record[1],
      "birthYear": record[2],
      "deathYear": record[3],
      "primaryProfession": record[4],
      "knownForTitles": record[5].replace("\n", "")
    }
    es.index(index = "people-whole", document = d)
    if counter%50000 == 0:
      print("[People Index] Batch " + str(counter/50000) + " with size 50K complete")
    counter += 1
  print("name.basics.tsv indexing finished")

with open(basicDataURL) as f:
  l = f.readlines()
  l.pop(0)
  counter = 0
  for line in l:
    record = line.split("\t")
    d = {
      "nconst": record[0],
      "titleType": record[1],
      "primaryTitle": record[2],
      "originalTitle": record[3],
      "isAdult": record[4],
      "startYear": record[5],
      "endYear": record[6],
      "runtimeMinutes": record[7],
      "genres": record[8].replace("\n", "")
    }
    es.index(index = "basic", document = d)
    if counter%50000 == 0:
      print("[Basic Index] Batch " + str(counter/50000) + " with size 50K complete")
    counter += 1
  print("title.basics.tsv indexing finished")

with open(ratingDataURL) as f:
  l = f.readlines()
  l.pop(0)
  counter = 0
  for line in l:
    record = line.split("\t")
    d = {
      "nconst": record[0],
      "averageRating": record[1],
      "numVotes": record[2].replace("\n", "")
    }
    es.index(index = "rating", document = d)
    if counter%50000 == 0:
      print("[Rating Index] Batch " + str(counter/50000) + " with size 50K complete")
    counter += 1
  print("title.ratings.tsv indexing finished")


