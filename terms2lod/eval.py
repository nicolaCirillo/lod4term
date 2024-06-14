from rdflib import Graph
from tabulate import tabulate

# load the termbase
def _load_graph(filename):
    g = Graph()
    g.parse(filename)
    return g

# retrieve the terms
def _query(graph, query):
  results = graph.query(query)
  return [str(r[0]) for r in list(results)]

def get_forms(graph):
  QUERY = """PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
  SELECT ?repr
  WHERE
  {
    ?form a ontolex:Form.
    ?form ontolex:writtenRep ?repr
  }"""
  return _query(graph, QUERY)

def get_lemmas(graph):
  QUERY = """PREFIX ontolex: <http://www.w3.org/ns/lemon/ontolex#>
  SELECT ?repr
  WHERE
  {
    ?entry ontolex:canonicalForm ?form.
    ?form ontolex:writtenRep ?repr
  }"""
  return _query(graph, QUERY)

# compute metrics
def P_at_K(actual, predicted, k=None):
    if not k:
        k = len(predicted)
    rtp = set(predicted[:k]).intersection(set(actual))
    return len(rtp)/k

def R_at_K(actual, predicted, k=None):
    if not k:
        k = len(predicted)
    rtp = set(predicted[:k]).intersection(set(actual))
    return len(rtp)/len(actual)

def F1_at_K(actual, predicted, k=None):
    if not k:
        k = len(predicted)
    p = P_at_K(actual,predicted, k)
    r = R_at_K(actual,predicted, k)
    return (p*r)/(p+r)

def AVP_at_K(actual, predicted, k=None):
    if not k:
        k = len(predicted)
    sum = 0
    for i in range(1, k+1):
        sum += P_at_K(actual, predicted, k=i)
    return sum/k

# evaluate the list of terms on a dataset
def evaluate(predicted, termbase_file, mode: {'form', 'lemma'} = "form"):
    termbase = _load_graph(termbase_file)
    if mode == 'form':
        actual = get_forms(termbase)
    elif mode == 'lemma':
        actual = get_lemmas(termbase)
    else:
        raise NotImplementedError()
    atp = len(actual)
    rtp = len(predicted)
    table = [['K', 'P@K', 'R@K', 'F1@K', 'AVP@k']]
    for k in [50, 100, 200, 500, atp, rtp]:
        p_k = P_at_K(actual, predicted, k)
        r_k = R_at_K(actual, predicted, k)
        f1_k = F1_at_K(actual, predicted, k)
        avp_k = AVP_at_K(actual, predicted, k)
        str_k = f'{k}'
        if k == atp:
            str_k = str_k + ' (ATP)'
        elif k == rtp:
            str_k = str_k + ' (RTP)'
        row = [str_k, f'{p_k:.2f}', f'{r_k:.2f}', f'{f1_k:.2f}', f'{avp_k:.2f}']
        table.append(row)
    
    print(f"Evaluation on '{termbase_file}'", tabulate(table), sep='\n')


