import re
import codecs
import pandas as pd
from . import dataclasses
from rdflib import  RDF, Namespace

ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
LEXINFO = Namespace("http://www.lexinfo.net/ontology/2.0/lexinfo#")

subject_dict = {
    "Environment": "Environment",
    "Waste management": "Waste_management",
    "Law": "Law",
    "EU Law": "European_Union_law",
    "Waste management law": "Waste_law",
    "Other": "Other"
}

BASE = "https://example.com/"

def set_uri(uri):
    global BASE
    BASE = uri

def parse_feats(feats):
    keys = re.findall("(?:^|\|)(.*?)=", feats)
    values = re.findall("=(.*?)(?:$|\|)", feats)
    return {k:v for k, v in zip(keys, values)}

def encode_form(form, feats=""):
    uri_form = BASE + "form_" + re.sub(" ", "_", form)
    if feats != "":
        feats = parse_feats(feats)
    else:
        feats = {}
    return dataclasses.Form(uri_form, form, feats)

def encode_sense(lemma, subject):
    sense_uri = BASE + "sense_" + re.sub(" ", "_", lemma)
    subject = subject_dict[subject]
    return dataclasses.LexicalSense(sense_uri, subject)

def encode_concept(concept, subject, sense, ontology_entry):
    concept_uri = BASE + "concept_" + re.sub(" ", "_", concept)
    subject = subject_dict[subject]
    return dataclasses.LexicalConcept(concept_uri, sense, subject,
                                      ontology_entry)

def encode_word(lemma, pos, sense, concept, forms):
    entry_uri = BASE + "entry_" + re.sub(" ", "_", lemma.writtenRep)
    return dataclasses.Word(entry_uri, lemma, pos, sense, concept, forms)

def encode_mwe(lemma, pos, sense, concept, forms, subterms_raw):
    entry_uri = BASE + "entry_" + re.sub(" ", "_", lemma.writtenRep)
    words = lemma.writtenRep.split(" ")
    comps, subterms = list(), list()
    for w in words:
        comp_uri = BASE + "component_" + w
        comps.append(dataclasses.Component(comp_uri))
    if subterms_raw != "":
        for s in subterms_raw.split(";"):
            s = s.strip()
            s_uri = BASE + "entry_" + re.sub(" ", "_", s)
            subterms.append(s_uri)
    return dataclasses.MultiwordExpression(entry_uri, lemma, pos, sense, 
                                           concept, forms, subterms, comps)

def encode_entry(lemma, pos, sense, concept, forms, subterms_raw):
    if " " in lemma.writtenRep:
        return encode_mwe(lemma, pos, sense, concept, forms, subterms_raw)
    else:
        return encode_word(lemma, pos, sense, concept, forms)

def add_variants(graph):
    for concept, _, _ in graph.triples((None, RDF.type, ONTOLEX.LexicalConcept)):
        variants = [o for _, _, o in graph.triples((concept, ONTOLEX.lexicalizedSense, None))]
        for v_1 in variants:
            for v_2 in variants:
                if v_1 == v_2:
                    continue
                graph.add((v_1, LEXINFO.synonym, v_2))
    return graph

def termtable2ontolex(filename, lemma_table, form_table):
    df_forms = pd.read_excel(form_table)
    df_entries = pd.read_excel(lemma_table)
    df_full = df_forms.merge(df_entries, on=["lemma", "pos"])
    df_full = df_full.fillna("")
    groups = df_full.groupby(["lemma", "feats_y", "concept", "domain", "IATE"])

    entries = list()
    for (lemma, lfeats, concept, domain, IATE), data in groups:
        lex_sense = encode_sense(lemma, domain)
        lex_concept = encode_concept(concept, domain, lex_sense, IATE)
        lemma_form = encode_form(lemma, lfeats)
        forms = list()
        for row in data.itertuples():
            if row.form == lemma:
                continue
            forms.append(encode_form(row.form, row.feats_x))
        entry = encode_entry(lemma_form, row.pos, lex_sense, lex_concept, forms, row.subterms)
        entries.append(entry)
    lexicon_uri = BASE + "lexicon"
    lexicon = dataclasses.Lexicon(lexicon_uri, entries, "Italian")
    graph = lexicon.serialize()
    graph = add_variants(graph)
    with codecs.open(filename, "w", "utf8") as fileout:
        fileout.write(graph.serialize(format="turtle"))
