import qwikidata
from qwikidata.sparql import (get_subclasses_of_item,
                              return_sparql_query_results)
from qwikidata.linked_data_interface import get_entity_dict_from_api
from qwikidata.entity import WikidataItem


# TODO - filter humanoid inventors only
def inventor_query():
    return """
    SELECT DISTINCT ?inventor ?inventorLabel
    WHERE {
        ?gadget wdt:P61 ?inventor.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    """


entities = [
    ("inventor", inventor_query())
]


if __name__ == "__main__":
    print("Wie geht's?")
    # send any sparql query to the wikidata query service and get full result back
    # here we use an example that counts the number of humans

    for (e, query) in entities:
        res = return_sparql_query_results(query)
        res = res['results']['bindings']
        inventors = [e['inventorLabel']['value'] for e in res]
        # gadgets = [e['gadgetLabel']['value'] for e in res]
        print(inventors)
        # for i, g in zip(inventors, gadgets):
        # print(f'{i}-{g}')

    exit(1)

    # use convenience function to get subclasses of an item as a list of item ids
    Q_RIVER = "Q4022"
    subclasses_of_river = get_subclasses_of_item(Q_RIVER)

    print(subclasses_of_river)

    for subclass in subclasses_of_river:
        entity = get_entity_dict_from_api(subclass)
        item = WikidataItem(entity)
        print(item.get_enwiki_title())
