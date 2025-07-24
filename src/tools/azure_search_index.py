import os
import json
import logging
import numpy as np

import time
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from azure.search.documents.indexes.models import (
    ExhaustiveKnnAlgorithmConfiguration, ExhaustiveKnnParameters, SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, SearchIndex, SearchField, VectorSearch, HnswAlgorithmConfiguration, HnswParameters, SemanticSearch, VectorSearch, VectorSearchAlgorithmKind, VectorSearchProfile, SearchIndex, SemanticConfiguration, SemanticPrioritizedFields, SearchField, SearchFieldDataType, SimpleField, SearchableField, VectorSearch, ExhaustiveKnnParameters, SearchIndex, SearchField, SearchFieldDataType, SimpleField, SearchableField, SearchIndex, SearchField, SemanticConfiguration, SemanticField, VectorSearch,  HnswParameters, VectorSearch, VectorSearchAlgorithmKind, VectorSearchAlgorithmMetric, VectorSearchProfile
)
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
# from azure.search.documents.indexes.models import (
#     SearchIndex,
#     SimpleField,
#     SearchableField,
#     SearchFieldDataType,
#     SemanticConfiguration,
#     SemanticField,
# )
from azure.search.documents.models import (
    VectorizedQuery
)
from langchain_community.document_loaders import CSVLoader
from sentence_transformers import SentenceTransformer
from langchain_openai import AzureOpenAIEmbeddings

from dotenv import load_dotenv

load_dotenv()

# Get Azure Search credentials from environment variables
# search_service = os.getenv("AZURE_SEARCH_SERVICE")
# admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
# index_name = "sql-examples-index"

service_endpoint = os.getenv("AZURE_AI_ENDPOINT")
key = os.getenv("AZURE_AI_KEY")
model_name = os.getenv("AZURE_AI_MODEL_NAME")
model_type = os.getenv("AZURE_AI_MODEL_TYPE")
length = os.getenv("AZURE_AI_MODEL_LENGTH")
index_name = os.getenv("AZURE_AI_INDEX_NAME")
credential = AzureKeyCredential(key)
# print(service_endpoint)

if model_type != 'openai':
   model = SentenceTransformer(model_name)
else:
    model = AzureOpenAIEmbeddings(model=model_name)


# Define a custom JSON encoder for numpy types
class NumpyEncoder(json.JSONEncoder):
    """
    Special json encoder for numpy types.
    """

    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)
    
# Define the index with semantic search capabilities
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True,sortable=True, filterable=True, facetable=True),
    SearchableField(name="question", type=SearchFieldDataType.String, searchable=True),
    SearchableField(name="sql", type=SearchFieldDataType.String, retrievable=True),
    SearchableField(name="explanation", type=SearchFieldDataType.String, searchable=True),
    SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="myHnswProfile",
            )

]

# Create semantic configuration
semantic_config = SemanticConfiguration(
    name="my-semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
                    # title_field=None,
                    content_fields=[SemanticField(field_name="question"),
                                    SemanticField(field_name="sql"),
                                    SemanticField(field_name="explanation"),
                 ]
    )
)



#-- Create a vector embeddings
def create_embeddings(inputfilepathname):
        """
        Create embeddings for the input data.

        Args:
            inputfilepathname (str): Path to the input file.
        """
        
        try:
            metadata_cols = ['question', 'sql', 'explanation']
            content_columns = ['question', 'sql', 'explanation']

            # Load the CSV file using CSVLoader
            loader = CSVLoader(inputfilepathname, metadata_columns=metadata_cols,
                               content_columns=content_columns)

            data = loader.load()
            lines = [text.page_content for text in data]

            #If the model type is not OpenAI, use SentenceTransformer
            if model_type != 'openai':
                embeddings = model.encode(lines)
                counter = 0               
                input_data = []
                for line in lines:
                    d = {}  # Initialize dictionary here
                    d['id'] = str(counter)
                    # d['line'] = line
                    d['embedding'] = embeddings[counter]
                    d['sql'] = data[counter].metadata.get("sql", "")
                    d['question'] = data[counter].metadata.get("question", "")
                    d['explanation'] = data[counter].metadata.get("explanation", "")
                    # d['tables_required'] = data[counter].metadata.get("tables_required", "")

                    counter += 1
                    input_data.append(d)

                # Output embeddings to schemaVector.json file
                with open(f"schemaVectors.json", "w") as f:
                    json.dump(input_data, f, cls=NumpyEncoder)

            else:
                # For OpenAI models with retry logic
                @retry(
                    wait=wait_exponential(multiplier=1, min=2, max=60),
                    stop=stop_after_attempt(5),
                    retry=retry_if_exception_type(Exception)
                )
                def embed_batch_with_retry(batch):
                    try:
                        return model.embed_documents(batch)
                    except Exception as e:
                        if "429" in str(e):
                            print(f"Rate limit hit, waiting before retry: {e}")
                            time.sleep(2)  # Force some delay
                        raise e

                # Process in smaller batches to avoid rate limits
                batch_size = 5  # Adjust based on your rate limits
                all_embeddings = []
                
                print(f"Processing {len(lines)} lines in batches of {batch_size}")
                for i in range(0, len(lines), batch_size):
                    batch = lines[i:i+batch_size]
                    batch_end = min(i+batch_size, len(lines))
                    print(f"Processing batch {i//batch_size + 1}/{(len(lines) + batch_size - 1)//batch_size} (lines {i}-{batch_end-1})")
                    
                    # Get embeddings with retry logic
                    batch_embeddings = embed_batch_with_retry(batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    # Add a delay between batches to prevent rate limiting
                    if i + batch_size < len(lines):  # If not the last batch
                        print("Pausing between batches to avoid rate limits...")
                        time.sleep(1)
                
                # Create documents with embeddings
                counter = 0
                input_data = []
                for line in lines:
                    d = {}  # Initialize dictionary
                    d['id'] = str(counter)
                    # d['line'] = line
                    d['embedding'] = all_embeddings[counter]
                    d['question'] = data[counter].metadata.get("question", "")
                    d['sql'] = data[counter].metadata.get("sql", "")
                    d['explanation'] = data[counter].metadata.get("explanation", "")
                    # d['tables_required'] = data[counter].metadata.get("tables_required", "")

                    counter += 1
                    input_data.append(d)

                # Output embeddings to schemaVector.json file
                with open("schemaVectors.json", "w") as f:
                    json.dump(input_data, f)

            logging.info("Vector Embeddings created!")
            print("Vector Embeddings created!")
            return input_data

        except Exception as e:
            logging.error(f"Failed to create vector embeddings: {e}")
            print(f"Error creating embeddings: {e}")
            return None

def create_vector_index():
        """
        Create a vector index from the schemaVector.json file.
        """
        try:
            # index_client = SearchIndexClient(
            #     endpoint=service_endpoint,
            #     credential=credential
            # )


            fields = [
                SimpleField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    sortable=True,
                    filterable=True,
                    facetable=True
                ),
                # SearchableField(
                #     name="line",
                #     type=SearchFieldDataType.String
                # ),
                SearchableField(
                    name="question",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    facetable=True
                ),
                SearchableField(
                    name="sql",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    facetable=True
                ),
                SearchableField(
                    name="explanation",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    facetable=True
                ),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(
                        SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="myHnswProfile"
                )
            ]

            #------ Configure the vector search configuration-2 algorithms
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="myHnsw",
                        kind=VectorSearchAlgorithmKind.HNSW,
                        parameters=HnswParameters(
                            m=4,
                            ef_construction=400,
                            ef_search=500,
                            metric=VectorSearchAlgorithmMetric.COSINE
                        )
                    ),
                    ExhaustiveKnnAlgorithmConfiguration(
                        name="myExhaustiveKnn",
                        kind=VectorSearchAlgorithmKind.EXHAUSTIVE_KNN,
                        parameters=ExhaustiveKnnParameters(
                            metric=VectorSearchAlgorithmMetric.COSINE
                        )
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw",
                    ),
                    VectorSearchProfile(
                        name="myExhaustiveKnnProfile",
                        algorithm_configuration_name="myExhaustiveKnn",
                    )
                ]
            )

            # ---create a semantic configuration which tells Azure which fields to use for semantic search
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                content_fields=[
                    SemanticField(field_name="question"),
                    SemanticField(field_name="sql"),
                    SemanticField(field_name="explanation"),
                ],
                # keywords_fields=[
                #     # SemanticField(field_name="tables_required")
                # ]
                )
            )

            # Create the semantic settings with the configuration
            semantic_search = SemanticSearch(configurations=[semantic_config])

            # ----Create the search index with the semantic settings
            index = SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            # Create the index client
            index_client = SearchIndexClient(
                endpoint=service_endpoint,
                credential=credential
            )
            result = index_client.create_or_update_index(index)
            logging.info(f'Index {result.name} created.')
            print(f'Index {result.name} created.')

            # Upload some documents to the index
            with open('schemaVectors.json', 'r') as file:
                documents = json.load(file)


            #create a search client
            search_client = SearchClient(
                endpoint=service_endpoint,
                index_name=index_name,
                credential=credential
            )

            result = search_client.upload_documents(documents)
            logging.info(f"Uploaded {len(documents)} documents")
            print(f"Uploaded {len(documents)} documents")

        except Exception as e:
            logging.error(f"Failed to create Azure AI Index: {e}")


# if __name__ == "__main__":
 
#     input_file = "examples.csv"  # Replace with your actual file path
#     embeddings = create_embeddings(input_file)

#     create_vector_index = create_vector_index()
   
def initialize_search_index(input_file="updated_examples.csv"):
    """
    Initialize the Azure Search index with embeddings from the given input file.
    
    Args:
        input_file (str): Path to the CSV file containing updated_examples
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"Creating embeddings from {input_file}...")
        embeddings = create_embeddings(input_file)
        if not embeddings:
            print("Failed to create embeddings")
            return False
            
        print("Creating vector index...")
        create_vector_index()
        
        print("Search index initialization complete!")
        return True
    except Exception as e:
        print(f"Error initializing search index: {str(e)}")
        return False





