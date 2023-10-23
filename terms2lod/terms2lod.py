import json
import codecs
from collections import Counter
from itertools import chain
from collections import defaultdict
import stanza
import pandas as pd
import re


def get_entities(ents, text):
    out = dict()
    for e in ents:
        beg, end = e["start_offset"], e["end_offset"]
        out[e["id"]] = (text[beg:end].strip().lower(), e["label"], [(beg, end)])
    return out

def join_ents(ents, rels):
    #rels = sorted(rels, key=lambda x:x["from_id"])
    for r in rels:
        try:
            beg, end = r["from_id"], r["to_id"]
            t1, l, span1 = ents.pop(beg)
            t2, _, span2 = ents.pop(end)            
            if span1[0][0] < span2[0][0]:
                t = t1 + " " + t2 
                ents[end] = (t, l, span1 + span2)
            else:
                t = t2 + " " + t1
                ents[beg] = (t, l, span2 + span1)
        except KeyError:
            pass
    return ents

def only_longest(ents):
    filtered = dict()
    all_spans = [(spans[0][0], spans[-1][1]) for _, _, spans in ents.values()]
    for k, v in ents.items():
        spans = v[-1]
        b, e = spans[0][0], spans[-1][1]
        if not any((b >= bb and e < ee) or (b > bb and e <= ee) for bb, ee in all_spans):
            filtered[k] = v
    return filtered            


def get_subterms(ents):
    subs = dict()
    for e, _ , spans in ents.values():
        beg, end = spans[0][0], spans[-1][-1]
        sub_terms = list()
        for e1, _, spans in ents.values():
            beg1, end1 = spans[0][0], spans[-1][-1]
            if beg1>=beg and end1<=end and len(e1.split(" "))<len(e.split(" ")):
                sub_terms.append(e1)
        subs[e] = sub_terms
    return subs

def get_terms(doc):
    text = doc["text"]
    ents = get_entities(doc["entities"], text)
    ents = join_ents(ents, doc["relations"])
    subs = get_subterms(ents)
    return list(ents.values()), subs

def get_word_span(term):
    t, _, spans = term
    words, wspans = list(), list()
    for beg, end in spans:
        subt = t[:end-beg]
        t = t[end+1-beg:]
        matches = re.finditer(r"\b\S+?\b", subt)
        for m in matches:
            words.append(m.group(0))
            wspans.append((m.span()[0]+beg, m.span()[1]+beg))
    return wspans


def jsonl2counter(filename: str) -> Counter:
    with codecs.open(filename, "r", "utf8") as filein:
        json_list = list(filein)
    data = [json.loads(json_str) for json_str in json_list]
    terms, _sub_terms = zip(*[get_terms(d) for d in data])
    terms = Counter([(t, l) for t, l, _ in chain.from_iterable(terms)])
    sub_terms = defaultdict(set)
    for s in _sub_terms:
        for k, v in s.items():
            sub_terms[k] = set.union(sub_terms[k], set(v))
    return terms, sub_terms

def term_table(terms: list, subterms: list, fileout: str):
    def get_triple(tokens):
        text = " ".join(t.text for t in tokens)
        lemma = " ".join(t.lemma for t in tokens)
        upos = " ".join(t.upos for t in tokens)
        return text, lemma, upos
    nlp = stanza.Pipeline(lang='it', processors='tokenize,pos,lemma')
    lemmas = defaultdict(list)
    for t in terms:
        (term, domain), _ = t
        tokens = nlp(term).sentences[0].words
        _, lemma, _ = get_triple(tokens)
        pos, feats = tokens[0].upos, tokens[0].feats
        lemmas[lemma].append((term, pos, domain, feats))
    data = list()
    for lemma, forms in lemmas.items():
        if len(forms)==1:
            lemma = forms[0][0]
        elif lemma in list(zip(*forms))[0]:
            lemma = lemma
        else:
            head = lemma.split(" ")[0]
            for f, *_ in forms:
                if f.split(" ")[0] == head:
                    lemma = f
                    break
        for f, pos, domain, feats in forms:
            subs = "; ".join(subterms[f])
            data.append((f, lemma, pos, domain, feats, subs))
    df = pd.DataFrame(data, columns=["form", "lemma", "pos", "domain", "feats", "subterms"])
    df.to_excel(fileout, index=False)