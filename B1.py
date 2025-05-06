from rdflib import Graph, Namespace
from rdflib.namespace import RDF, RDFS
from rdflib import Graph, Namespace, RDF, RDFS

# For Classes and properties 
DBO = Namespace("http://dbpedia.org/ontology/")

g = Graph()
g.bind("dbo", DBO)

# Defining the classes with schema-level triples:
g.add((DBO.Author, RDF.type, RDFS.Class))
g.add((DBO.Paper, RDF.type, RDFS.Class))

g.add((DBO.Conference, RDF.type, RDFS.Class))
g.add((DBO.ConferenceEdition, RDF.type, RDFS.Class))
g.add((DBO.Workshop, RDF.type, RDFS.Class))
g.add((DBO.WorkshopEdition, RDF.type, RDFS.Class))
g.add((DBO.EventEdition, RDF.type, RDFS.Class))

g.add((DBO.Journal, RDF.type, RDFS.Class))
g.add((DBO.JournalVolume, RDF.type, RDFS.Class))

g.add((DBO.Reviewer, RDF.type, RDFS.Class))
g.add((DBO.Review, RDF.type, RDFS.Class))
g.add((DBO.ConferenceChair, RDF.type, RDFS.Class))
g.add((DBO.JournalEditor, RDF.type, RDFS.Class))
g.add((DBO.Person, RDF.type, RDFS.Class))
g.add((DBO.Coordinator, RDF.type, RDFS.Class))

g.add((DBO.City, RDF.type, RDFS.Class))
g.add((DBO.Year, RDF.type, RDFS.Class))
g.add((DBO.Keyword, RDF.type, RDFS.Class))

# Now the properties:
# Paper -is_written-> Author
g.add((DBO.is_written, RDF.type, RDF.Property))
g.add((DBO.is_written, RDFS.domain, DBO.Paper))
g.add((DBO.is_written, RDFS.range, DBO.Author))
# Paper -is_corresponding_author-> Author
g.add((DBO.is_corresponding_author, RDF.type, RDF.Property))
g.add((DBO.is_corresponding_author, RDFS.range, DBO.Author))
g.add((DBO.is_corresponding_author, RDFS.domain, DBO.Paper))
# Paper -presentedAt-> EventEdition
g.add((DBO.presentedAt , RDF.type, RDF.Property))
g.add((DBO.presentedAt , RDFS.domain, DBO.Paper))
g.add((DBO.presentedAt , RDFS.range, DBO.EventEdition))
# Paper -published_in-> JournalVolume
g.add((DBO.published_in , RDF.type, RDF.Property))
g.add((DBO.published_in , RDFS.domain, DBO.Paper))
g.add((DBO.published_in , RDFS.range, DBO.JournalVolume))
# ConferenceEdition -is_edition_of_conf-> Conference
g.add((DBO.is_edition_of_conf , RDF.type, RDF.Property))
g.add((DBO.is_edition_of_conf , RDFS.domain, DBO.ConferenceEdition))
g.add((DBO.is_edition_of_conf , RDFS.range, DBO.Conference))
# WorkshopEdition -is_edition_of_workshop-> Workshop
g.add((DBO.is_edition_of_workshop , RDF.type, RDF.Property))
g.add((DBO.is_edition_of_workshop , RDFS.domain, DBO.WorkshopEdition))
g.add((DBO.is_edition_of_workshop , RDFS.range, DBO.Workshop))
# EventEdition -held_in_city-> City
g.add((DBO.held_in_city , RDF.type, RDF.Property))
g.add((DBO.held_in_city , RDFS.domain, DBO.EventEdition))
g.add((DBO.held_in_city , RDFS.range, DBO.City))
# EventEdition -held_in_year-> Year
g.add((DBO.held_in_year , RDF.type, RDF.Property))
g.add((DBO.held_in_year , RDFS.domain, DBO.EventEdition))
g.add((DBO.held_in_year , RDFS.range, DBO.Year))
# JournalVolume -is_volume_of-> Journal
g.add((DBO.is_volume_of , RDF.type, RDF.Property))
g.add((DBO.is_volume_of , RDFS.domain, DBO.JournalVolume))
g.add((DBO.is_volume_of , RDFS.range, DBO.Journal))
# JournalVolume -of_year-> Year
g.add((DBO.of_year , RDF.type, RDF.Property))
g.add((DBO.of_year , RDFS.domain, DBO.JournalVolume))
g.add((DBO.of_year , RDFS.range, DBO.Year))
# Paper -cites-> Paper
g.add((DBO.cites, RDF.type, RDF.Property))
g.add((DBO.cites, RDFS.domain, DBO.Paper))
g.add((DBO.cites, RDFS.range, DBO.Paper))
# Paper -is_about-> Keyword
g.add((DBO.is_about, RDF.type, RDF.Property))
g.add((DBO.is_about, RDFS.domain, DBO.Paper))
g.add((DBO.is_about, RDFS.range, DBO.Keyword))
# ConferenceChair -organizes_conference-> Conference
g.add((DBO.organizes_conference, RDF.type, RDF.Property))
g.add((DBO.organizes_conference, RDFS.domain, DBO.ConferenceChair))
g.add((DBO.organizes_conference, RDFS.range, DBO.Conference))
# ConferenceChair -organizes_workshop-> Workshop
g.add((DBO.organizes_workshop, RDF.type, RDF.Property))
g.add((DBO.organizes_workshop, RDFS.domain, DBO.ConferenceChair))
g.add((DBO.organizes_workshop, RDFS.range, DBO.Workshop))
# JournalEditor -edits-> Journal
g.add((DBO.edits, RDF.type, RDF.Property))
g.add((DBO.edits, RDFS.domain, DBO.JournalEditor))
g.add((DBO.edits, RDFS.range, DBO.Journal))
# Review -is_assigned_by-> Coordinator
g.add((DBO.is_assigned_by, RDF.type, RDF.Property))
g.add((DBO.is_assigned_by, RDFS.domain, DBO.Review))
g.add((DBO.is_assigned_by, RDFS.range, DBO.Coordinator))
# Review -review_written_by-> Reviewer
g.add((DBO.review_written_by, RDF.type, RDF.Property))
g.add((DBO.review_written_by, RDFS.domain, DBO.Review))
g.add((DBO.review_written_by, RDFS.range, DBO.Reviewer))
# Review -corresponds_to_paper-> Paper
g.add((DBO.corresponds_to_paper, RDF.type, RDF.Property))
g.add((DBO.corresponds_to_paper, RDFS.domain, DBO.Review))
g.add((DBO.corresponds_to_paper, RDFS.range, DBO.Paper))  

# Next the subproperties and subclasses:
# is_corresponding_author -subPropertyOf-> is_written
g.add((DBO.is_corresponding_author, RDFS.subPropertyOf, DBO.is_written))
# Author -subClassOf-> Person
g.add((DBO.Author, RDFS.subClassOf, DBO.Person))
# Reviewer -subClassOf-> Author
g.add((DBO.Reviewer, RDFS.subClassOf, DBO.Author))
# Coordinator-subClassOf-> Person
g.add((DBO.Coordinator, RDFS.subClassOf, DBO.Person))
# ConferenceChair-subClassOf-> Coordinator
g.add((DBO.ConferenceChair, RDFS.subClassOf, DBO.Coordinator))
# JournalEditor-subClassOf-> Coordinator
g.add((DBO.JournalEditor, RDFS.subClassOf, DBO.Coordinator))
# ConferenceEdition -subClassOf-> EventEdition
g.add((DBO.ConferenceEdition, RDFS.subClassOf, DBO.EventEdition))
# WorkshopEdition -subClassOf-> EventEdition
g.add((DBO.WorkshopEdition, RDFS.subClassOf, DBO.EventEdition))

g.serialize("output_files/ontology.ttl", format="turtle")
