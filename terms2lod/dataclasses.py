from dataclasses import dataclass, field, InitVar
from typing import ClassVar
from rdflib import Graph, Literal, RDF, RDFS, URIRef, XSD, Namespace


#Namespaces for the termbase
ONTOLEX = Namespace("http://www.w3.org/ns/lemon/ontolex#")
LEXINFO = Namespace("http://www.lexinfo.net/ontology/2.0/lexinfo#")
DECOMP = Namespace("http://www.w3.org/ns/lemon/decomp#")
DCT = Namespace("http://purl.org/dc/terms/")
DBC = Namespace("https://dbpedia.org/page/Category:")
LIME = Namespace("http://www.w3.org/ns/lemon/lime#")

#Namespaces for the corpus
DCTERMS = Namespace("http://purl.org/dc/terms/")
ITSRDF = Namespace("http://www.w3.org/2005/11/its/rdf#")
NIF = Namespace("http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#")
POWLA = Namespace("http://purl.org/powla/powla.owl#")

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
    g.bind("dcterms", DCTERMS)
    g.bind("itsrdf", ITSRDF)
    g.bind("nif", NIF)
    g.bind("powla", POWLA)
    
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

#Dataclasses for the termbase    
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

#dataclasses for the corpus

@dataclass
class NIFContext(Entity):
    isString_str: InitVar[str]
    isString: Literal = field(init=False)
    beginIndex: Literal = field(init=False)
    endIndex: Literal =  field(init=False)

    
    def __post_init__(self, uri_str, isString_str):
        super().__post_init__(uri_str)
        end = len(isString_str)-1
        self.beginIndex = Literal(0, datatype=XSD.nonNegativeInteger)
        self.endIndex = Literal(end, datatype=XSD.nonNegativeInteger)
        self.isString = Literal(isString_str)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, NIF.Context))
        g.add((this, RDF.type, NIF.OffsetBasedString))
        g.add((this, NIF.beginIndex, self.beginIndex))
        g.add((this, NIF.endIndex, self.endIndex))
        g.add((this, NIF.isString, self.isString))
        return g
    
@dataclass
class POWLANode(Entity):
    next: URIRef = field(init=False, default=None)
    previous: URIRef = field(init=False, default=None)
    hasParent: URIRef = field(init=False, default=None)
    string: URIRef = field(init=False, default=None)
    hasChildren: list = field(init=False, default_factory=list)

    def __post_init__(self, uri_str):
        super().__post_init__(uri_str)
        for i, child in enumerate(self.hasChildren):
            if i>0:
                child.previous = self.hasChildren[i-1].uri
            if i<len(self.hasChildren)-1:
                child.next =self.hasChildren[i+1].uri
            child.hasParent = self.uri

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, POWLA.Node))
        if self.next:
            g.add((this, POWLA.next, self.next))
        if self.previous:
            g.add((this, POWLA.previous, self.previous))
        if self.hasParent:
            g.add((this, POWLA.hasParent, self.hasParent))
        if self.string:
            g.add((this, POWLA.string, self.string))
        for child in self.hasChildren:
            g.add((this, POWLA.hasChildren, child.uri))
            g += child.serialize()
        return g

@dataclass
class NIFPhrase(POWLANode):
    uri_str: ClassVar = None
    begin: InitVar[int]
    end: InitVar[int]
    referenceContext: NIFContext
    beginIndex: Literal = field(init=False)
    endIndex: Literal =  field(init=False)
    anchorOf: Literal =  field(init=False)

    def __post_init__(self, begin, end):
        uri_str = self.referenceContext.uri.toPython()
        uri_str += f'#offset_{begin}_{end}'
        super().__post_init__(uri_str)
        
        self.beginIndex = Literal(begin, datatype=XSD.nonNegativeInteger)
        self.endIndex = Literal(end, datatype=XSD.nonNegativeInteger)
        string = self.referenceContext.isString.toPython()[begin: end]
        self.anchorOf = Literal(string)
        self.string = Literal(string)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, RDF.type, NIF.OffsetBasedString))
        g.add((this, RDF.type, NIF.Phrase))
        g.add((this, RDF.type, POWLA.Node))
        g.add((this, NIF.beginIndex, self.beginIndex))
        g.add((this, NIF.endIndex, self.endIndex))
        g.add((this, NIF.referenceContext, self.referenceContext.uri))
        g.add((this, NIF.anchorOf, self.anchorOf))
        g += self.referenceContext.serialize()
        return g
    
@dataclass    
class POWLATerm(POWLANode):
    termAnnotatorsRef_str: InitVar[str]
    termInfoRef_str: InitVar[str]
    termAnnotatorsRef: URIRef = field(init=False)
    termInfoRef: URIRef = field(init=False)
    children: InitVar[list[POWLANode]]

    def __post_init__(self, uri_str, termAnnotatorsRef_str, termInfoRef_str, children):
        self.hasChildren = children
        super().__post_init__(uri_str)
        self.termAnnotatorsRef = URIRef(termAnnotatorsRef_str)
        self.termInfoRef = URIRef(termInfoRef_str)
        string = " ".join([c.anchorOf.toPython() for c in self.hasChildren])
        self.string = Literal(string)

    def serialize(self):
        this, g = self.uri, super().serialize()
        g.add((this, ITSRDF['term'], Literal("yes")))
        g.add((this, ITSRDF.termAnnotatorsRef, self.termAnnotatorsRef))
        g.add((this, ITSRDF.termInfoRef, self.termInfoRef))
        return g

@dataclass 
class POWLATermCollection(POWLANode):
    children: InitVar[list[POWLANode]]
    
    def __post_init__(self, uri_str, children):
        self.hasChildren = children
        super().__post_init__(uri_str)

#Dataclasses for reading jsonl files produced by doccano
from dataclasses import dataclass, field

@dataclass
class Document:
    identifier: int
    string: str

@dataclass
class Phrase:
    identifier: int
    begin: int
    end: int
    string: str = field(init=False)
    label: str
    context: Document = field(repr=False)

    def __post_init__(self):
        self.string = self.context.string[self.begin: self.end]

@dataclass
class Annotation:
    identifier: int
    string: str = field(init=False)
    label: str  = field(init=False)
    begin: str = field(init=False)
    end: str  = field(init=False)
    text: Document = field(repr=False)
    phrases: list[Phrase] = field(repr=False)
 
    def __post_init__(self):
        self.phrases = sorted(self.phrases, key=lambda x: x.begin)
        self.string = ' '.join([p.string for p in self.phrases])
        self.label = self.phrases[0].label
        self.begin = self.phrases[0].begin
        self.end = self.phrases[0].end