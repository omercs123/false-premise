import json
import re
import jsonlines
import random
import qwikidata
import inflect
import wikipediaapi
import requests
from requests import utils
from qwikidata.sparql import (get_subclasses_of_item,
                              return_sparql_query_results)
from qwikidata.linked_data_interface import get_entity_dict_from_api
from qwikidata.entity import WikidataItem


def father_occupation_query():
    return """
    SELECT DISTINCT ?person_label ?father_label ?fatherOccupation_label 
    WHERE
    {
    FILTER EXISTS {?person wdt:P570 ?date}.
    FILTER EXISTS {?father wdt:P570 ?date2}.
    FILTER regex (str(?person), ("Q0|Q2|Q4|Q6|Q8")).
    ?person wdt:P31 wd:Q5.
    ?person wdt:P22 ?father.
    ?person wdt:P106 ?personOccupation.
    ?father wdt:P106 ?fatherOccupation.
    ?person rdfs:label ?person_label.
    ?father rdfs:label ?father_label.
    ?fatherOccupation rdfs:label ?fatherOccupation_label
    FILTER(LANG(?person_label) = "en").
    FILTER(LANG(?father_label) = "en").
    FILTER(LANG(?fatherOccupation_label) = "en").
    FILTER NOT EXISTS {?person wdt:P106 [wdt:P31/wdt:P279* ?fatherOccupation]}.
    FILTER NOT EXISTS {?person wdt:P106 ?SomeOccupation. ?father wdt:P106 ?SomeOccupation.}.
    } LIMIT 3000
    """

def child_occupation_query():
    return """
    SELECT DISTINCT ?person_label ?father_label ?personOccupation_label 
    WHERE
    {
    FILTER EXISTS {?person wdt:P570 ?date}.
    FILTER EXISTS {?father wdt:P570 ?date2}.
    FILTER regex (str(?person), ("Q1|Q3|Q5|Q7|Q9")).
    ?person wdt:P31 wd:Q5.
    ?person wdt:P22 ?father.
    ?person wdt:P106 ?personOccupation.
    ?person rdfs:label ?person_label.
    ?father rdfs:label ?father_label.
    ?personOccupation rdfs:label ?personOccupation_label
    FILTER(LANG(?person_label) = "en").
    FILTER(LANG(?father_label) = "en").
    FILTER(LANG(?personOccupation_label) = "en").
    } LIMIT 3000
    """

def spouse_occupation_query():
    return """
    SELECT DISTINCT ?person_label ?spouse_label ?spouseOccupation_label
    WHERE
    {
    FILTER NOT EXISTS {?person wdt:P570 ?date}.
    FILTER NOT EXISTS {?spouse wdt:P570 ?date2}.
    FILTER regex (str(?person), ("Q0|Q2|Q4|Q6|Q8")).
    FILTER regex (str(?spouse), ("Q1|Q3|Q5|Q7|Q9")).
    ?person wdt:P31 wd:Q5.
    ?person wdt:P26 ?spouse.
    ?spouse wdt:P26 ?person.
    ?person wdt:P106 ?personOccupation.
    ?spouse wdt:P106 ?spouseOccupation.
    ?person rdfs:label ?person_label.
    ?spouse rdfs:label ?spouse_label.
    ?spouseOccupation rdfs:label ?spouseOccupation_label
    FILTER(LANG(?person_label) = "en").
    FILTER(LANG(?spouse_label) = "en").
    FILTER(LANG(?spouseOccupation_label) = "en").
    FILTER NOT EXISTS {?person wdt:P106 [wdt:P31/wdt:P279* ?spouseOccupation]}.
    FILTER NOT EXISTS {?person wdt:P106 ?SomeOccupation. ?spouse wdt:P106 ?SomeOccupation.}.
    } LIMIT 3000
    """

def non_murdered_father_query():
    # fathers who were not killed of a person who was killed, killers and the person they have killed
    # 203
    return """
    SELECT DISTINCT ?person_label ?father_label ?personKiller_label
    WHERE
    {
    ?person wdt:P31 wd:Q5.
    ?personKiller wdt:P31 wd:Q5.
    ?person wdt:P22 ?father.
    ?person wdt:P157 ?personKiller.
    ?person rdfs:label ?person_label.
    ?father rdfs:label ?father_label.
    ?personKiller rdfs:label ?personKiller_label
    FILTER(LANG(?person_label) = "en").
    FILTER(LANG(?father_label) = "en").
    FILTER(LANG(?personKiller_label) = "en").
    FILTER NOT EXISTS {?father wdt:P157 ?personKiller.}.
    } LIMIT 203
    """


switch_entities = [
    {
        "labels": ["person_label", "father_label", "personKiller_label",],
        "query": non_murdered_father_query(),
        "questions":
        [
            {
                "question": "did <personKiller_label> kill <father_label>",
                "answer": False,
                "title": "<personKiller_label> and <father_label>",
                "passage": ""
            },
            {
                "question": "did <personKiller_label> kill <person_label>",
                "answer": True,
                "title": "<personKiller_label> and <person_label>",
                "passage": ""
            }
        ]
    },
    {
        "labels": ["person_label", "father_label", "fatherOccupation_label",],
        "query": father_occupation_query(),
        "questions":
        [
            {
                "question": "was <person_label> <fatherOccupation_label>",
                "answer": False,
                "title": "<person_label> and <father_label>",
                "passage": ""
            }
        ]
    },
    {
        "labels": ["person_label", "father_label", "personOccupation_label",],
        "query": child_occupation_query(),
        "questions":
        [
            {
                "question": "was <person_label> <personOccupation_label>",
                "answer": True,
                "title": "<person_label> and <father_label>",
                "passage": ""
            }
        ]
    },
    {
        "labels": ["person_label", "spouse_label", "spouseOccupation_label",],
        "query": spouse_occupation_query(),
        "questions":
        [
            {
                "question": "is <person_label> <spouseOccupation_label>",
                "answer": False,
                "title": "<person_label> and <spouse_label>",
                "passage": ""
            },
            {
                "question": "is <spouse_label> <spouseOccupation_label>",
                "answer": True,
                "title": "<person_label> and <spouse_label>",
                "passage": ""
            }
        ]
    },

]


def generate_switch():
    from collections import defaultdict
    import copy
    indefinite_corrector = inflect.engine()
    wiki_wiki = wikipediaapi.Wikipedia('en')
    questions = []
    titles = {}
    bad_item = False
    for entity in switch_entities:
        es = entity['labels']
        query = entity['query']
        qs = entity['questions']
        res = return_sparql_query_results(query)
        print("finished query")
        res = res['results']['bindings']
        len_res = len(res)
        values = defaultdict(list)
        for ind, entity in enumerate(res):
            for e in es:
                name = entity[f'{e}']['value']
                values[e].append(name)
                titles[name] = name
        questionCounter = 0
        for ind, j in enumerate(values[es[0]]):
            for q in qs:
                new_q = copy.deepcopy(q)
                try:
                    if es[2].find('Occupation') == -1:
                        new_q['question'] = q['question'].replace(f'<{es[0]}>', j).\
                            replace(f'<{es[1]}>', values[es[1]][ind]).replace(f'<{es[2]}>', values[es[2]][ind])
                    else:
                        new_q['question'] = q['question'].replace(f'<{es[0]}>', j).\
                            replace(f'<{es[1]}>', values[es[1]][ind]).replace(f'<{es[2]}>', indefinite_corrector.a(values[es[2]][ind]))
                except IndexError:
                    break
                try:
                    new_q['title'] = q['title'].replace(f'<{es[0]}>', j).\
                    replace(f'<{es[1]}>', values[es[1]][ind]).replace(f'<{es[2]}>', values[es[2]][ind])
                    and_location = [m.start() for m in re.finditer(' and ', new_q['title'])]
                    if len(and_location) != 1:
                        continue
                    page1 = wiki_wiki.page(new_q['title'][:and_location[0]])
                    text1 = page1.summary
                    page2 = wiki_wiki.page(new_q['title'][and_location[0]+5:])
                    text2 = page2.summary
                    if random.randint(0,1):
                        wikipage = text1 + " " + text2
                    else:
                        wikipage = text2 + " " + text1
                    new_q['passage'] = wikipage
                    if len(text1) < 100 or len(text2) < 100 or 'may refer to:' in wikipage:
                        continue
                    questions.append(new_q)
                    questionCounter = questionCounter + 1
                    print(f"switch number {questionCounter}.")
                except KeyError:
                    pass

    return questions


if __name__ == "__main__":
    # send any sparql query to the wikidata query service and get full result back
    # here we use an example that counts the number of humans
    # use convenience function to get subclasses of an item as a list of item ids

    import wikipediaapi
    wiki_wiki = wikipediaapi.Wikipedia('en')
    page1 = wiki_wiki.page('Bill Gates')
    text1 = page1.summary
    print(text1.split())
    print(len(text1.split()))
    exit(1) 

    questions = generate_switch()

    questions_len = len(questions)
    random.shuffle(questions)

    with jsonlines.open('trainmix6500b.jsonl', 'w') as f:
        f.write_all(questions[:int(questions_len * 0.8)])
    with jsonlines.open('devmix6500b.jsonl', 'w') as f:
        f.write_all(questions[int(questions_len * 0.8):])


