# Failed items

Edit the 'Diagnosis' lines. (Re-running the evaluation overwrites this file.)

## Config A / L2 (lookup)

**Question:** Which paper was written in 1899?

- Problem (automatic): Failed: SyntaxError: error at 1:88: expected one of Prefix not found, ['%'], ['-' | '0' ..= '9' | '\u{00B7}' | '\u{0300}'..='\u{036F}' | '\u{203F}'..='\u{2040}'], ['.']
- Diagnosis (suggested, edit if you disagree): Used rdf:type without a PREFIX rdf: line; pyoxigraph rejects it and config A has no retry. Fixed by the examples (config B).

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/> SELECT ?paper ?title WHERE { ?paper rdf:type sdm:Paper ; sdm:title ?title ; sdm:year_written 1899 . } LIMIT 100
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?title WHERE {
  ?paper sdm:year_written 1899 ;
         sdm:title ?title .
}
```

## Config A / A1 (aggregation)

**Question:** For each publication type (Conference, Workshop, Journal) and each year from 2000 to 2022, what is the average number of citations received by the papers of that type and year that are cited at least once? Use the conference edition year for conference and workshop papers and the volume year for journal papers, and give 0 when there are no such papers.

- Problem (automatic): Wrongly refused: The schema does not support calculating complex conditional averages over citations grouped by dynamic publication types and years with zero-filling.
- Diagnosis (suggested, edit if you disagree): Wrong refusal: the model judged the per-type/per-year average with zero-filling impossible, although the schema supports it.

Generated query:
```sparql
(none)
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?typeLabel ?year (COALESCE(AVG(?edgeCount), 0) AS ?citesAvg)
WHERE {
  VALUES ?typeLabel { "Workshop" "Conference" "Journal" }
  VALUES ?year {
    2000 2001 2002 2003 2004 2005 2006 2007 2008
    2009 2010 2011 2012 2013 2014 2015 2016 2017
    2018 2019 2020 2021 2022
  }
  OPTIONAL
  {
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:presentedAt ?x .
      ?x sdm:conference_year ?year .
      ?x sdm:is_edition_of_conf ?conf .
      ?conf sdm:is_workshop ?type .
      BIND(IF(?type = true, "Workshop", "Conference") AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
    UNION
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:published_in ?x .
      ?x sdm:volume_year ?year .
      ?x sdm:is_volume_of ?conf .
      BIND("Journal" AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
  }
}
GROUP BY ?typeLabel ?year
ORDER BY ?year
```

## Config A / A2 (aggregation)

**Question:** For each keyword, which paper about that keyword is cited the most? Give the 15 keyword-paper pairs with the highest citation counts: the keyword name, the paper title and the number of citations.

- Problem (automatic): Wrong result: 15 rows, gold has 15 rows.
- Diagnosis (suggested, edit if you disagree): Ranked all (keyword, paper) pairs globally instead of keeping the most cited paper per keyword; LIMIT 15 also cuts a tie at 17. Valid and plausible, but a different question.

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/> SELECT ?keywordName ?paperTitle (COUNT(?citingPaper) AS ?citationCount) WHERE { ?keyword a sdm:Keyword ; sdm:keyword_name ?keywordName . ?paper a sdm:Paper ; sdm:title ?paperTitle ; sdm:is_about ?keyword . ?citingPaper sdm:cites ?paper . } GROUP BY ?keywordName ?paperTitle ORDER BY DESC(?citationCount) LIMIT 15
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?keyword_name ?paper_title ?citationCount
WHERE {
  {
    # Subquery 1: citation count per (paper, keyword)
    SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?citationCount)
    WHERE {
      ?paper sdm:is_about ?keyword .
      ?citingPaper sdm:cites ?paper .
    }
    GROUP BY ?keyword ?paper
  }
  {
    # Subquery 2: maximum citation count per keyword
    SELECT ?keyword (MAX(?count) AS ?maxCount)
    WHERE {
      SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?count)
      WHERE {
        ?paper sdm:is_about ?keyword .
        ?citingPaper sdm:cites ?paper .
      }
      GROUP BY ?keyword ?paper
    }
    GROUP BY ?keyword
  }
  FILTER(?citationCount = ?maxCount)
  ?paper sdm:title ?paper_title .
  ?keyword sdm:keyword_name ?keyword_name .
}
ORDER BY DESC(?citationCount)
LIMIT 15
```

## Config A / I2 (inference)

**Question:** How many persons are there in the graph?

- Problem (automatic): Failed: SyntaxError: error at 1:111: expected one of Prefix not found, ['%'], ['-' | '0' ..= '9' | '\u{00B7}' | '\u{0300}'..='\u{036F}' | '\u{203F}'..='\u{2040}'], ['.'
- Diagnosis (suggested, edit if you disagree): Used rdf:type without a PREFIX rdf: line; pyoxigraph rejects it and config A has no retry. Fixed by the examples (config B).

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/> SELECT (COUNT(DISTINCT ?person) AS ?count) WHERE { ?person rdf:type sdm:Person }
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT (COUNT(?person) AS ?persons) WHERE {
  ?person a sdm:Person .
}
```

## Config A / I3 (inference)

**Question:** Who are the authors of the paper 'Attention is All you Need'? Give their names.

- Problem (automatic): Failed: SyntaxError: error at 1:96: expected one of Prefix not found, ['%'], ['-' | '0' ..= '9' | '\u{00B7}' | '\u{0300}'..='\u{036F}' | '\u{203F}'..='\u{2040}'], ['.']
- Diagnosis (suggested, edit if you disagree): Used rdf:type without a PREFIX rdf: line; pyoxigraph rejects it and config A has no retry. Fixed by the examples (config B).

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/> SELECT DISTINCT ?author_name WHERE { ?paper rdf:type sdm:Paper ; sdm:title 'Attention is All you Need' ; sdm:is_written ?author . ?author sdm:name ?author_name } LIMIT 100
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?name WHERE {
  ?paper sdm:title "Attention is All you Need" ;
         sdm:is_written ?author .
  ?author sdm:name ?name .
}
```

## Config B / A1 (aggregation)

**Question:** For each publication type (Conference, Workshop, Journal) and each year from 2000 to 2022, what is the average number of citations received by the papers of that type and year that are cited at least once? Use the conference edition year for conference and workshop papers and the volume year for journal papers, and give 0 when there are no such papers.

- Problem (automatic): Wrongly refused: The schema does not provide a direct way to compute the total citations received per paper in a single query with average grouping by dynamic publication types and years with a default of 0.
- Diagnosis (suggested, edit if you disagree): Wrong refusal: the model judged the per-type/per-year average with zero-filling impossible, although the schema supports it.

Generated query:
```sparql
(none)
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?typeLabel ?year (COALESCE(AVG(?edgeCount), 0) AS ?citesAvg)
WHERE {
  VALUES ?typeLabel { "Workshop" "Conference" "Journal" }
  VALUES ?year {
    2000 2001 2002 2003 2004 2005 2006 2007 2008
    2009 2010 2011 2012 2013 2014 2015 2016 2017
    2018 2019 2020 2021 2022
  }
  OPTIONAL
  {
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:presentedAt ?x .
      ?x sdm:conference_year ?year .
      ?x sdm:is_edition_of_conf ?conf .
      ?conf sdm:is_workshop ?type .
      BIND(IF(?type = true, "Workshop", "Conference") AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
    UNION
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:published_in ?x .
      ?x sdm:volume_year ?year .
      ?x sdm:is_volume_of ?conf .
      BIND("Journal" AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
  }
}
GROUP BY ?typeLabel ?year
ORDER BY ?year
```

## Config B / A2 (aggregation)

**Question:** For each keyword, which paper about that keyword is cited the most? Give the 15 keyword-paper pairs with the highest citation counts: the keyword name, the paper title and the number of citations.

- Problem (automatic): Wrong result: 15 rows, gold has 15 rows.
- Diagnosis (suggested, edit if you disagree): Ranked all (keyword, paper) pairs globally instead of keeping the most cited paper per keyword; LIMIT 15 also cuts a tie at 17. Valid and plausible, but a different question.

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?keyword_name ?title (COUNT(?citation) AS ?citations) WHERE {
  ?keyword sdm:keyword_name ?keyword_name .
  ?paper sdm:is_about ?keyword ;
         sdm:title ?title .
  OPTIONAL { ?citation sdm:cites ?paper . }
}
GROUP BY ?keyword ?keyword_name ?paper ?title
ORDER BY DESC(?citations)
LIMIT 15
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?keyword_name ?paper_title ?citationCount
WHERE {
  {
    # Subquery 1: citation count per (paper, keyword)
    SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?citationCount)
    WHERE {
      ?paper sdm:is_about ?keyword .
      ?citingPaper sdm:cites ?paper .
    }
    GROUP BY ?keyword ?paper
  }
  {
    # Subquery 2: maximum citation count per keyword
    SELECT ?keyword (MAX(?count) AS ?maxCount)
    WHERE {
      SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?count)
      WHERE {
        ?paper sdm:is_about ?keyword .
        ?citingPaper sdm:cites ?paper .
      }
      GROUP BY ?keyword ?paper
    }
    GROUP BY ?keyword
  }
  FILTER(?citationCount = ?maxCount)
  ?paper sdm:title ?paper_title .
  ?keyword sdm:keyword_name ?keyword_name .
}
ORDER BY DESC(?citationCount)
LIMIT 15
```

## Config C / A1 (aggregation)

**Question:** For each publication type (Conference, Workshop, Journal) and each year from 2000 to 2022, what is the average number of citations received by the papers of that type and year that are cited at least once? Use the conference edition year for conference and workshop papers and the volume year for journal papers, and give 0 when there are no such papers.

- Problem (automatic): Wrongly refused: The schema does not provide a direct way to compute the total citations received per paper in a single query with average grouping by dynamic publication types and years with a default of 0.
- Diagnosis (suggested, edit if you disagree): Wrong refusal: the model judged the per-type/per-year average with zero-filling impossible, although the schema supports it.

Generated query:
```sparql
(none)
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?typeLabel ?year (COALESCE(AVG(?edgeCount), 0) AS ?citesAvg)
WHERE {
  VALUES ?typeLabel { "Workshop" "Conference" "Journal" }
  VALUES ?year {
    2000 2001 2002 2003 2004 2005 2006 2007 2008
    2009 2010 2011 2012 2013 2014 2015 2016 2017
    2018 2019 2020 2021 2022
  }
  OPTIONAL
  {
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:presentedAt ?x .
      ?x sdm:conference_year ?year .
      ?x sdm:is_edition_of_conf ?conf .
      ?conf sdm:is_workshop ?type .
      BIND(IF(?type = true, "Workshop", "Conference") AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
    UNION
    {SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
    WHERE {
      ?other sdm:cites ?node .
      ?node sdm:published_in ?x .
      ?x sdm:volume_year ?year .
      ?x sdm:is_volume_of ?conf .
      BIND("Journal" AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
  }
}
GROUP BY ?typeLabel ?year
ORDER BY ?year
```

## Config C / A2 (aggregation)

**Question:** For each keyword, which paper about that keyword is cited the most? Give the 15 keyword-paper pairs with the highest citation counts: the keyword name, the paper title and the number of citations.

- Problem (automatic): Wrong result: 15 rows, gold has 15 rows.
- Diagnosis (suggested, edit if you disagree): Ranked all (keyword, paper) pairs globally instead of keeping the most cited paper per keyword; LIMIT 15 also cuts a tie at 17. Valid and plausible, but a different question.

Generated query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?keyword_name ?title (COUNT(?citation) AS ?citations) WHERE {
  ?keyword sdm:keyword_name ?keyword_name .
  ?paper sdm:is_about ?keyword ;
         sdm:title ?title .
  OPTIONAL { ?citation sdm:cites ?paper . }
}
GROUP BY ?keyword ?keyword_name ?paper ?title
ORDER BY DESC(?citations)
LIMIT 15
```
Gold query:
```sparql
PREFIX sdm: <http://sdm_upc.org/ontology/>
SELECT ?keyword_name ?paper_title ?citationCount
WHERE {
  {
    # Subquery 1: citation count per (paper, keyword)
    SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?citationCount)
    WHERE {
      ?paper sdm:is_about ?keyword .
      ?citingPaper sdm:cites ?paper .
    }
    GROUP BY ?keyword ?paper
  }
  {
    # Subquery 2: maximum citation count per keyword
    SELECT ?keyword (MAX(?count) AS ?maxCount)
    WHERE {
      SELECT ?keyword ?paper (COUNT(?citingPaper) AS ?count)
      WHERE {
        ?paper sdm:is_about ?keyword .
        ?citingPaper sdm:cites ?paper .
      }
      GROUP BY ?keyword ?paper
    }
    GROUP BY ?keyword
  }
  FILTER(?citationCount = ?maxCount)
  ?paper sdm:title ?paper_title .
  ?keyword sdm:keyword_name ?keyword_name .
}
ORDER BY DESC(?citationCount)
LIMIT 15
```
