from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from rdflib import Graph, Literal, RDF, RDFS, URIRef, Namespace
from rdflib.namespace import NamespaceManager


ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
LEXINFO = Namespace("http://www.lexinfo.net/ontology/2.0/lexinfo#")
DECOMP = Namespace("http://www.w3.org/ns/lemon/decomp#")
DCT = Namespace("http://purl.org/dc/terms/")
DBC = Namespace("https://dbpedia.org/page/Category:")
LIME = Namespace("http://www.w3.org/ns/lemon/lime#")


LANG = "it"
POS_DICT = {
    "ADJ": LEXINFO.adjective,
    "ADP": LEXINFO.adposition,
    "ADV": LEXINFO.adverb,
    "AUX": LEXINFO.auxiliary,
    "CCONJ": LEXINFO.coordinatingConjunction,
    "DET": LEXINFO.determiner,
    "INTJ": LEXINFO.interjection,
    "NOUN": LEXINFO.noun,
    "NUM": LEXINFO.numeral,
    "PART": LEXINFO.particle,
    "PRON": LEXINFO.pronoun,
    "PROPN": LEXINFO.properNoun,
    "PUNCT": LEXINFO.punctuation,
    "SCONJ": LEXINFO.subordinatingConjunction,
    "SYM": LEXINFO.symbol,
    "VERB": LEXINFO.verb
}
GENDER_DICT = {"Masc": LEXINFO.masculine, "Fem": LEXINFO.feminine}
NUMBER_DICT = {"Sing": LEXINFO.singular, "Plur": LEXINFO.plural}

def initGraph():
    g = Graph()
    g.bind("ontolex", ONTOLEX)
    g.bind("lexinfo", LEXINFO)
    g.bind("dct", DCT)
    g.bind("decomp", DECOMP)
    g.bind("dbc", DBC)
    g.bind("lime", LIME)
    return g

@dataclass
class Entity():
    uri_str: InitVar[str]
    uri: URIRef = field(init=False)

    def __post_init__(self, uri_str):
        self.uri = URIRef(uri_str)
    
    def serialize(self):
        g = initGraph()
        return g
        

@dataclass
class Form(Entity):
    writtenRep: str
    morphSynProp: dict = field(default_factory=dict)

    def serialize(self):
        gender, number = self.morphSynProp.get("Gender", None), self.morphSynProp.get("Number", None)
        this, g =self.uri,  super().serialize()
        g.add((this, RDF.type, ONTOLEX.Form))
        g.add((this, ONTOLEX.writtenRep, Literal(self.writtenRep, lang=LANG)))
        if gender:
            g.add((this, LEXINFO.gender, GENDER_DICT[gender]))
        if number:
            g.add((this, LEXINFO.number, NUMBER_DICT[number]))
        return g

@dataclass
class LexicalSense(Entity):
    subject_str: InitVar[str]
    # reference
    subject: URIRef = field(init=False)

    def __post_init__(self, uri_str, subject_str):
        super().__post_init__(uri_str)
        if subject_str == "Other":
            self.subject = Literal("Other")
        else:
            self.subject = getattr(DBC, subject_str)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, ONTOLEX.LexicalSense))
        g.add((this, DCT.subject, self.subject))
        return g


@dataclass
class LexicalConcept(Entity):
    lexicalizedSense: LexicalSense
    subject_str: InitVar[str] #dcterm:subject URI
    concept_str: InitVar[str] = None #URI
    subject: URIRef = field(init=False)
    concept: URIRef = field(init=False, default=None)

    def __post_init__(self, uri_str, subject_str, concept_str=None):
        super().__post_init__(uri_str)
        if subject_str == "Other":
            self.subject = Literal("Other")
        else:
            self.subject = getattr(DBC, subject_str)
        if concept_str:
            self.concept = URIRef(concept_str)
    
    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, ONTOLEX.LexicalConcept))
        g.add((this, DCT.subject, self.subject))
        g.add((this, ONTOLEX.lexicalizedSense, self.lexicalizedSense.uri))
        g.add((self.lexicalizedSense.uri, ONTOLEX.isLexicalizedSenseOf, this))
        g.add((self.lexicalizedSense.uri, ONTOLEX.reference, this))
        g += self.lexicalizedSense.serialize()
        if self.concept:
            g.add((this, ONTOLEX.concept, self.concept))
        return g


@dataclass
class LexicalEntry(Entity):
    canonicalForm: Form
    partOfSpeech: str
    #denotes: str
    sense: LexicalSense
    evokes: LexicalConcept
    otherForms: list[Form] = field(default_factory=list)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, ONTOLEX.canonicalForm, self.canonicalForm.uri))
        g.add((this, RDFS.label, Literal(self.canonicalForm.writtenRep, LANG)))
        g += self.canonicalForm.serialize()
        g.add((this, ONTOLEX.evokes, self.evokes.uri))
        g += self.evokes.serialize()
        g.add((self.evokes.uri, ONTOLEX.isEvokedBy, this))
        g.add((this, ONTOLEX.sense, self.sense.uri))
        g.add((self.sense.uri, ONTOLEX.isSenseOf, this))
        g += self.sense.serialize()
        for f in self.otherForms:
            g.add((this, ONTOLEX.otherForm, f.uri))
            g += f.serialize()
        return g

@dataclass
class Word(LexicalEntry):
    
    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, ONTOLEX.Word))
        return g

@dataclass
class MultiwordExpression(LexicalEntry):
    subterms: list[str] = field(default_factory=list)
    constituents: list[Component] = field(default_factory=list)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, ONTOLEX.MultiwordExpression))
        for s in self.subterms:
            s = URIRef(s)
            g.add((this, DECOMP.subterm, s))
        for i, c in enumerate(self.constituents):
            g.add((this, DECOMP.constituent, c.uri))
            g.add((this, getattr(RDF, "_{}".format(i+1)), c.uri))
            g += c.serialize()
        return g
    
@dataclass
class Component(Entity):
    correspondsTo: LexicalEntry = None

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, DECOMP.Component))
        if self.correspondsTo:
            g.add((this, DECOMP.correspondsTo, self.correspondsTo.uri))
            g += self.correspondsTo.serialize()
        return g

@dataclass
class Lexicon(Entity):
    entries: list[LexicalEntry]
    language: str

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, LIME.Lexicon))
        for e in self.entries:
            g.add((this, LIME.entry, e.uri))
            g += e.serialize()
        g.add((this, LIME.language, Literal(self.language)))
        g.add((this, LIME.lexicalEntries, Literal(len(self.entries))))
        return g