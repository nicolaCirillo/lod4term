import json
import codecs
from collections import Counter
from itertools import chain
from collections import defaultdict
import stanza
import pandas as pd
import re
from .dataclasses import Document, Phrase, Annotation

def json2annotations(json_line):
    document = Document(json_line['id'], json_line['text'])
    #Converts entities to Phrases
    all_phrases = dict()
    for entity in json_line['entities']:
        phrase = Phrase(entity['id'], entity['start_offset'], 
                        entity['end_offset'], entity['label'], document)
        all_phrases[entity['id']] = [phrase]
    #Extracts links between entities
    sorted_relations = sorted([(min(rel['from_id'], rel['to_id']), 
                                max(rel['from_id'], rel['to_id']))
                                for rel in json_line['relations']])
    for begin, end in sorted_relations:
        try:
            part_1 = all_phrases.pop(begin)
        except KeyError:
            continue
        all_phrases[end] += part_1
    all_annotations = list()
    for i, phrases in enumerate(all_phrases.values()):
        annotation = Annotation(i, document, phrases)
        all_annotations.append(annotation)
    return all_annotations


def jsonl2termtable(jsonl_file: str, fileout: str, lang: str):
    def get_subterms(target_term, all_terms):
        for term in all_terms:
            if re.search(r'\b' + term + r'\b', target_term) \
                and term != target_term:
                yield term
    with codecs.open(jsonl_file, "r", "utf8") as filein:
        json_list = list(filein)
        data = [json.loads(json_str) for json_str in json_list]
    #get terms from jsonl file
    all_terms = set()
    for line in data:
        annotation_list = json2annotations(line)
        for annotation in annotation_list:
            term = re.sub(r' +', r' ', annotation.string.lower().strip())
            all_terms.add((term, annotation.label))
    #process terms
    nlp = stanza.Pipeline(lang=lang, processors='tokenize,pos,lemma,depparse')
    table = list()
    only_terms = set(list(zip(*all_terms))[0])
    for term, domain in all_terms:
        words = nlp(term).sentences[0].words
        for i, w in enumerate(words):
            if w.head == 0:
                head = w
                break
        term_words = term.split(' ')
    try:
        term_words[i] = head.lemma
    except IndexError:
        pass
    lemma = ' '.join(term_words)
    subterms = '; '.join([t for t in get_subterms(term, only_terms)])
    table.append((term, lemma, head.upos, domain, head.feats,subterms))
    df = pd.DataFrame(table, columns=["form", "lemma", "pos", "domain", "feats", "subterms"])
    df.to_excel(fileout, index=False)
