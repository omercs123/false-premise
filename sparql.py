import json
import qwikidata
import wikipediaapi
from qwikidata.sparql import (get_subclasses_of_item,
                              return_sparql_query_results)
from qwikidata.linked_data_interface import get_entity_dict_from_api
from qwikidata.entity import WikidataItem


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
    } LIMIT 4
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


def non_murdered_sibling_query():
    # siblings who were not killed of a person who was killed (American), killers and the person they have killed
    return """
    SELECT DISTINCT ?sibling ?siblingLabel ?killed ?killedLabel ?killer ?killerLabel
    WHERE
    {
        ?killed wdt:P27 wd:Q30. # American(?)
        ?killed wdt:P31 wd:Q5. # People
        ?killed wdt:P157 ?killer.
        ?killed wdt:P3373 ?sibling
        # the siblings were not killed by someone killed
        FILTER NOT EXISTS {?sibling wdt:P157 ?someone}.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    } LIMIT 30
    """


entities = [
    # (["non_inventor"], non_inventor_query(), "What did <non_inventor> invent?"),
    # (["cat_owner"], cat_owner_query(), ["What is the name of <cat_owner>'s dog?"]),
    # (["alive"], alive_query(), ["When did <alive> die?"]),
    # (["animal"], unpurchasable_query(), ["Where can I buy a <animal>?", "How much does a <animal> cost?"]),
    # (["sibling", "killed", "killer"], non_murdered_sibling_query(),
    #  ["When did <killer> murder <sibling>?", "When was <sibling> murdered?"])
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
        "labels": ["kill", "dead", "date"],
        "query": murder_query(),
        "questions":
        [
            {
                "question": "did <kill> murder <dead>",
                "answer": False,
                "title": "<dead>",
                "wikipage": "<dead>"

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
    for entity in mix_entities:
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
                item = WikidataItem(get_entity_dict_from_api(q_id))
                try:
                    titles[name] = item.get_enwiki_title()
                except KeyError:
                    pass

        for i in values[es[0]]:
            for ind, j in enumerate(values[es[0]]):
                if j != i:
                    for q in qs:
                        new_q = copy.deepcopy(q)
                        new_q['question'] = q['question'].replace(f'<{es[0]}>', i).replace(f'<{es[1]}>', values[es[1]][ind])
                        try:
                            new_q['title'] = titles[values[es[1]][ind]] 
                            page = wiki_wiki.page(new_q['title'])
                            new_q['wikipage'] = page.summary
                            questions.append(new_q)
                        except KeyError:
                            pass

    return questions


if __name__ == "__main__":
    # send any sparql query to the wikidata query service and get full result back
    # here we use an example that counts the number of humans

    # questions = generate_false_questions()
    questions = generate_mix_questions()

    print(questions)
    with open('questions.json', 'w') as f:
        json.dump(questions, f)
    exit(1)

    # use convenience function to get subclasses of an item as a list of item ids
    Q_RIVER = "Q4022"
    subclasses_of_river = get_subclasses_of_item(Q_RIVER)

    #print(subclasses_of_river)

    for subclass in subclasses_of_river:
        entity = get_entity_dict_from_api(subclass)
        item = WikidataItem(entity)
        # print(item.get_enwiki_title())
        try:
            print(item.get_sitelinks()['enwiki']['url'])
        except KeyError:
            pass
