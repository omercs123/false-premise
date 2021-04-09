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
    } LIMIT 2
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
    } LIMIT 2
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
    } LIMIT 20
    """

def non_murdered_father_query():
    # fathers who were not killed of a person who was killed, killers and the person they have killed
    # 538
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

def inventor_query():
    return """
    SELECT DISTINCT ?inventor ?inventorLabel ?gadget ?gadgetLabel
    WHERE {
        ?inventor wdt:P31 wd:Q5.
        ?gadget wdt:P61 ?inventor.
        ?gadget wdt:P31/wdt:P279* wd:Q1183543.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 30
    """

def non_inventor_query():
    # non inventors (you can falsely ask what they invented, when they invented, etc.)
    return """
    SELECT DISTINCT ?non_inventor ?non_inventorLabel
    WHERE {
        ?non_inventor wdt:P31 wd:Q5.
        FILTER NOT EXISTS {?non_inventor wdt:P61 wd:Q1183543}.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 30
    """


def murder_query():
    '''
    Use with caution.
    '''
    return """
    SELECT ?dead ?deadLabel ?kill ?killLabel ?date ?dateLabel
    WHERE {
        ?dead wdt:P157 ?kill.
        ?kill wdt:P31 wd:Q5.
        ?dead wdt:P570 ?date
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 13000
    """


def cat_owner_query():
    # cat owners who don't have a dog
    return """
    SELECT DISTINCT ?cat_owner ?cat_ownerLabel
    WHERE {
        ?cat_owner wdt:P31 wd:Q5.
        ?cat_owner wdt:P1429 ?cat. # has a cat
        ?cat wdt:P31/wdt:P279* wd:Q146
        FILTER NOT EXISTS {?cat_owner wdt:P1429 [wdt:P31/wdt:P279* wd:Q144]}. # does not have a dog
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 30
    """


def alive_query():
    # living people
    return """
    SELECT ?alive ?aliveLabel
    WHERE {
        ?alive wdt:P31 wd:Q5.
        FILTER NOT EXISTS {?alive wdt:P570 ?date}.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 10
    """


def unpurchasable_query():
    # unpurchasable things (let's go with animals that don't exist) (but actually that might not be enough to prove they are unpurchasable)
    return """
    SELECT DISTINCT ?animal ?animalLabel
    WHERE {
        ?animal wdt:P31 wd:Q15702752.
        FILTER NOT EXISTS {?instace wdt:P31 ?animal}.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 300
    """




entities = [
    # (["non_inventor"], non_inventor_query(), "What did <non_inventor> invent?"),
    # (["cat_owner"], cat_owner_query(), ["What is the name of <cat_owner>'s dog?"]),
    # (["alive"], alive_query(), ["When did <alive> die?"]),
    # (["animal"], unpurchasable_query(), ["Where can I buy a <animal>?", "How much does a <animal> cost?"]),
    # (["sibling", "killed", "killer"], non_murdered_sibling_query(),
    {
        "labels": ["kill", "dead", "date"],
        "query": murder_query(),
        "questions":
        [
            {
                "question": "did <kill> murder <dead>",
                "answer": True,
                "title": "<dead>",
                "passage": ""

            }
        ]
    },
]

mix_entities = [
    # (["inventor", "gadget"], inventor_query(),
    #  ["When did <inventor> invent <gadget>?"]),
    #(["dead", "kill"], murder_query(), [
    # "When did <kill> murder <dead>?",
    # "Where did <kill> murder <dead>?",
    # "How did <kill> murder <dead>?",
    # "Why did <kill> murder <dead>?"]),
    {
        "labels": ["dead", "kill", "date"],
        "query": murder_query(),
        "questions":
        [
            {
                "question": "did <kill> murder <dead>",
                "answer": False,
                "title": "<dead>",
                "passage": ""
            }
        ]
    },
]

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



def generate_false_questions():
    questions = []
    for (es, query, qs) in entities:
        res = return_sparql_query_results(query)
        res = res['results']['bindings']
        values = []
        for entity in res:
            val = {}
            for e in es:
                val[e] = entity[f'{e}Label']['value']
            values.append(val)

        for val in values:
            print(val)
            for q in qs:
                question = q
                for (k, v) in val.items():
                    question = question.replace(f'<{k}>', v)
                questions.append(question)

    return questions


def generate_mix_questions():
    from collections import defaultdict
    import copy
    wiki_wiki = wikipediaapi.Wikipedia('en')
    questions = []
    titles = {}
    for entity_ind, entity in enumerate(mix_entities):
        es = entity['labels']
        query = entity['query']
        qs = entity['questions']
        res = return_sparql_query_results(query)
        res = res['results']['bindings']
        values = defaultdict(list)
        for entity in res:
            for e in es:
                name = entity[f'{e}Label']['value']
                values[e] += [name]
                q_id = entity[f'{e}']['value'].split('/')[-1]
                if not q_id.startswith('Q'):
                    continue
                try:
                    titles[name] = name
                except KeyError:
                    pass
        
        actives = list(set(values[es[1]]))
        for ind_i, i in enumerate(values[es[0]]):
            print(f"Mix number {ind_i}")
            
            title = titles[i]
            page = wiki_wiki.page(title)
            wikipage = page.summary
            if len(wikipage) < 100 or 'may refer to:' in wikipage:
                continue
            random.shuffle(actives)
            for ind, j in enumerate(actives):
                if j != values[es[1]][ind_i]:
                    if ind > 0:
                        break
                    for q in qs:
                        try:
                            new_q = copy.deepcopy(q)
                            new_q['title'] = title
                            new_q['passage'] = wikipage
                            new_q['question'] = q['question'].replace(f'<{es[0]}>', i).replace(f'<{es[1]}>', j)
                            questions.append(new_q)
                        except KeyError:
                            pass
                        

    return questions

def generate_true_questions():
    from collections import defaultdict
    import copy
    wiki_wiki = wikipediaapi.Wikipedia('en')
    questions = []
    titles = {}
    for entity in entities:
        es = entity['labels']
        query = entity['query']
        qs = entity['questions']
        res = return_sparql_query_results(query)
        res = res['results']['bindings']
        values = defaultdict(list)
        for entity in res:
            for e in es:
                name = entity[f'{e}Label']['value']
                values[e] += [name]
                q_id = entity[f'{e}']['value'].split('/')[-1]
                if not q_id.startswith('Q'):
                    continue
                try:
                    # title = get_entity_dict_from_api(q_id)['labels']['en']['value']
                    titles[name] = name
                except KeyError:
                    pass

        for ind, j in enumerate(values[es[0]]):
            print(f"True number {ind}")
            for q in qs:
                new_q = copy.deepcopy(q)
                new_q['question'] = q['question'].replace(f'<{es[0]}>', j).replace(f'<{es[1]}>', values[es[1]][ind])
                try:
                    new_q['title'] = titles[values[es[1]][ind]] 
                    page = wiki_wiki.page(new_q['title'])
                    wikipage = page.summary
                    new_q['passage'] = wikipage
                    if len(wikipage) < 100 or 'may refer to:' in wikipage:
                        continue
                    questions.append(new_q)
                except KeyError:
                    pass

    return questions

# def generate_switch2():
#     from collections import defaultdict
#     import copy
#     indefinite_corrector = inflect.engine()
#     wiki_wiki = wikipediaapi.Wikipedia('en')
#     questions = []
#     titles = {}
#     bad_item = False
#     for entity in switch_entities:
#         es = entity['labels']
#         query = entity['query']
#         qs = entity['questions']
#         res = return_sparql_query_results(query)
#         print("finished query")
#         res = res['results']['bindings']
#         len_res = len(res)
#         values = defaultdict(list)
#         for ind, entity in enumerate(res):
#             for e in es:
#                 q_id = entity[f'{e}']['value'].split('/')[-1]
#                 if q_id.startswith('Q'):
#                     item = WikidataItem(get_entity_dict_from_api(q_id))
#                     name = item.get_label()
#                 else:
#                     bad_item = True
#                     break
#                 print(F"finished {ind} out of {len_res} titles. item: {name}")
#                 values[e] += [name]
#                 if not q_id.startswith('Q'):
#                     continue
#                 try:
#                     titles[name] = name
#                 except KeyError:
#                     pass
#             if bad_item:
#                 print('bad item found!')
#                 bad_item = False
#                 continue
#         questionCounter = 0
#         for ind, j in enumerate(values[es[0]]):
#             for q in qs:
#                 new_q = copy.deepcopy(q)
#                 try:
#                     new_q['question'] = q['question'].replace(f'<{es[0]}>', j).\
#                         replace(f'<{es[1]}>', values[es[1]][ind]).replace(f'<{es[2]}>', indefinite_corrector.a(values[es[2]][ind]))
#                 except IndexError:
#                     break
#                 try:
#                     new_q['title'] = q['title'].replace(f'<{es[0]}>', j).\
#                     replace(f'<{es[1]}>', values[es[1]][ind])
#                     page1 = wiki_wiki.page(j)
#                     text1 = page1.summary
#                     page2 = wiki_wiki.page(values[es[1]][ind])
#                     text2 = page2.summary
#                     wikipage = text1 + " " + text2
#                     new_q['passage'] = wikipage
#                     if len(text1) < 100 or len(text2) < 100 or 'may refer to:' in wikipage:
#                         continue
#                     questions.append(new_q)
#                     questionCounter = questionCounter + 1
#                     print(f"switch number {questionCounter}.")
#                 except KeyError:
#                     pass

#     return questions

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
    print("Don't use anymore")
    exit(1)
    questions = generate_switch()

    # questions = generate_mix_questions()
    # questions += generate_true_questions()
    questions_len = len(questions)
    random.shuffle(questions)

    with jsonlines.open('trainmix6500b.jsonl', 'w') as f:
        f.write_all(questions[:int(questions_len * 0.8)])
    with jsonlines.open('devmix6500b.jsonl', 'w') as f:
        f.write_all(questions[int(questions_len * 0.8):])

    # Q_RIVER = "Q4022"
    # subclasses_of_river = get_subclasses_of_item(Q_RIVER)

    # #print(subclasses_of_river)

    # for subclass in subclasses_of_river:
    #     print(subclass)
    #     entity = get_entity_dict_from_api(subclass)
    #     item = WikidataItem(entity)
    #     # print(item.get_enwiki_title())
    #     try:
    #         print(item.get_sitelinks()['enwiki']['url'])
    #     except KeyError:
    #         pass
    #     exit(1)


