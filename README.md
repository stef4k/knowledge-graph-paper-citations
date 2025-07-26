# Knowledge Graph in Publications Domain

## Project Description
This is a hands-on project focused on building and querying knowledge graphs with GraphDB. It requires the design and implementation of a custom ontology for the research publications domain using RDFLib, covering concepts such as papers, authorship, conferences, journals, and reviews. The project emphasizes best practices in knowledge graph modeling, the use of inference in semantic queries, and crafting expressive SPARQL queries to extract meaningful insights.

Check the important pdf files:
- [Final Report](https://github.com/stef4k/knowledge-graph-paper-citations/blob/main/final-docs/final_report.pdf)
- [Project Description](https://github.com/stef4k/knowledge-graph-paper-citations/blob/main/final-docs/assignment_description.pdf)



## Installation and Execution
Follow these steps to set up the environment:

1. Create a virtual environment:
   ```sh
   python -m venv myenv
   ```

2. Activate virtual environment:
   ```sh
   myenv\Scripts\activate
   ```

3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

4. Run the `tbox_generation.ipynb` notebook

5. Run the `coordinators_generator.py` script:
   ```sh
   python coordinators_generator.py
   ```

6. Run the `abox_generation.ipynb` notebook
