#Average citations made to a paper by year and by publication type

"""PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dbo: <http://sdm_upc.org/ontology/>

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
      ?other dbo:cites ?node .
      ?node dbo:presentedAt ?x .
      ?x dbo:conference_year ?year .
      ?x dbo:is_edition_of_conf ?conf .
      ?conf dbo:is_workshop ?type .

      BIND(IF(?type = true, "Workshop", "Conference") AS ?typeLabel)
    }
    GROUP BY ?node ?typeLabel ?year}
 UNION
{SELECT ?node ?typeLabel ?year (COUNT(?other) AS ?edgeCount)
WHERE {
      ?other dbo:cites ?node .
      ?node dbo:published_in ?x .
      ?x dbo:volume_year ?year .
      ?x dbo:is_volume_of ?conf .

  BIND("Journal" AS ?typeLabel)
}
GROUP BY  ?node ?typeLabel ?year}
  }
}
GROUP BY ?typeLabel ?year
ORDER BY ?year"""