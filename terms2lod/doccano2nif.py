import json
import codecs
from itertools import chain
from pynif import NIFCollection
import pandas as pd
import re
from . import terms2lod


from pynif import NIFPhrase, NIFContext
from pynif.prefixes import ITSRDF, NIFPrefixes

from rdflib import Namespace, RDF, Literal, URIRef, Graph

POWLA = Namespace("http://purl.org/powla/powla.owl#")
TERMS = Namespace("http://example.com/terms#")

class MyPhrase(NIFPhrase):
    def __init__(self, phrase):
        super().__init__(context = phrase.context,
            annotator = phrase.annotator,
            mention = phrase.mention,
            beginIndex = phrase.beginIndex,
            endIndex = phrase.endIndex,
            score = phrase.score,
            taIdentRef = phrase.taIdentRef,
            taIdentRefLabel = phrase.taIdentRefLabel,
            taClassRef = phrase.taClassRef,
            taMsClassRef = phrase.taMsClassRef,
            uri = phrase.uri,
            is_hash_based_uri = phrase.isContextHashBasedString,
            source = phrase.source)
        self.parents = list()
        self.next = None
        self.previous = None
    
    def triples(self):
        for triple in super().triples():
            yield triple
        yield (self.uri, RDF.type, POWLA.Node)
        for p in self.parents:
            yield (self.uri, POWLA.hasParent, TERMS[p])
        if self.next:
            yield (self.uri, POWLA.next, URIRef(self.next))
        if self.previous:
            yield (self.uri, POWLA.previous, URIRef(self.previous))

class Term:
    def __init__(self, id, string, term_uri, annotator=None) -> None:
        self.id = id
        self.string = string
        self.childs = list()
        self.term_uri = term_uri
        self.uri = TERMS[self.id]
        self.annotator = annotator
    
    def triples(self):
        yield (self.uri, RDF.type, POWLA.Node)
        yield (self.uri, POWLA.string, Literal(self.string))
        for c in self.childs:
            yield (self.uri, POWLA.hasChild, URIRef(c))
        yield (self.uri, ITSRDF["term"], Literal("yes"))
        yield (self.uri, ITSRDF.termInfoRef, URIRef(self.term_uri))
        yield (self.uri, ITSRDF.termAnnotatorsRef, URIRef(self.annotator))

def get_next_uri(phrases, b):
    ordered  = sorted([(p.beginIndex, p.uri) for p in phrases 
                       if p.beginIndex>b])
    if ordered:
        return ordered[0][1]
    else:
        return False

def get_previous_uri(phrases, b):
    ordered  = sorted([(p.beginIndex, p.uri) for p in phrases 
                       if p.beginIndex<b], reverse=True)
    if ordered:
        return ordered[0][1]
    else:
        return False

def get_phrase_idx(phrases, b, e):
    for i, p, in enumerate(phrases):
        if p.beginIndex == b and p.endIndex == e:
            return i

def get_graph(collection):
        graph = Graph()
        for triple in collection.triples():
            graph.add(triple)

        graph.namespace_manager = NIFPrefixes().manager
        graph.namespace_manager.bind("powla", "http://purl.org/powla/powla.owl#")
        graph.namespace_manager.bind("terms","http://example.com/terms#")
        return graph



def term2uri(form_table, lemma_table, base_uri):
    df_forms = pd.read_excel(form_table)
    df_entries = pd.read_excel(lemma_table)
    df_full = df_forms.merge(df_entries, on=["lemma", "pos"])
    df_full = df_full.fillna("")
    uri_dict = dict()
    for row in df_full.itertuples():
        uri = base_uri + "sense_" + re.sub(" ", "_", row.lemma)
        uri_dict[row.form, row.domain] = uri
    return uri_dict

def doccano2nif(file_out: str, jsonl_file: str, collection_uri: str, 
                form_table: str, lemma_table: str, lexicon_uri: str,
                annotator:str):
    with codecs.open(jsonl_file, "r", "utf8") as filein:
        json_list = list(filein)
    data = [json.loads(json_str) for json_str in json_list]

    collection = NIFCollection(uri=collection_uri)
    for i, doc in enumerate(data):
        text = doc["text"]
        context = collection.add_context(
            uri=f"{collection_uri}/doc{i+1}", mention=text)
        terms, _ = terms2lod.get_terms(doc)
        spans = list(chain.from_iterable([terms2lod.get_word_span(t) 
                                          for t in terms]))
        for b, e in set(spans):
            p_uri = f"{context.uri.split('#')[0]}#offset_{b}_{e}"
            phrase = context.add_phrase(beginIndex=b,
                                        endIndex=e,
                                        uri=p_uri
                                        )
            context.phrases[-1] = MyPhrase(phrase)
        all_terms = list()
        uri_dict = term2uri(form_table, lemma_table, lexicon_uri)
        for j, t in enumerate(terms):
            term_uri = uri_dict.get(t[:2], None)
            if not term_uri:
                print(f"term {t[:2]} is not in the termbase")
                continue
            node = Term(f"term{i+1}_{j+1}", t[0], term_uri, annotator)
            wspans = terms2lod.get_word_span(t)
            for b, e in wspans:
                idx = get_phrase_idx(context.phrases, b, e)
                context.phrases[idx].parents.append(f"term{i+1}_{j+1}")
                next_node = get_next_uri(context.phrases, b)
                if next_node:
                    context.phrases[idx].next = next_node
                node.childs.append(context.phrases[idx].uri)
                previous = get_previous_uri(context.phrases, b)
                if previous:
                    context.phrases[idx].previous = previous
            all_terms.append(node)
        context.phrases += all_terms
        return get_graph(collection)