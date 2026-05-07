import argparse
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_community.document_loaders import CSVLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from tqdm import tqdm
import os
import csv
import re
import datetime

def extract_metadata_from_content(doc):

    # Extract title from page content
    title_match = re.search(r'title: ([^\n]+)', doc.page_content)
    if title_match:
        doc.metadata['title'] = title_match.group(1)

    # Extract link from page content
    link_match = re.search(r'link: (https?://[^\s]+)', doc.page_content)
    if link_match:
        doc.metadata['link'] = link_match.group(1)

    # Extract date from page content
    date_match = re.search(r'date: (\d{4}-\d{2}-\d{2})', doc.page_content)
    if date_match:
        # Convert date to format DD/MM/YYYY
        date_str = date_match.group(1)
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        doc.metadata['date'] = date_obj.strftime('%d/%m/%Y')
    
    return doc

def load_data(file_path):
    """
    Load data from a CSV file, process each document, and update metadata.
    Metadata has the responsibility to store the date of the document, helping to sort the document by date.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    csv.field_size_limit(10**6)

    loader = CSVLoader(file_path, encoding="utf-8")
    documents = loader.load()
    
    updated_documents = [extract_metadata_from_content(doc) for doc in documents]

    return updated_documents

def create_or_update_chroma_db(documents, persist_directory):
    """
    Create or update a Chroma vector database from documents and save it.
    """
    print("Creating or updating Chroma database...")

    # Split text into smaller chunks for efficient embedding
    text_splitter = CharacterTextSplitter(chunk_size=1024, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    print(f"Documents split successfully. Number of documents after splitting: {len(docs)}")

    # Initialize embeddings using HuggingFace's multilingual model
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("Embeddings loaded successfully.")

    # Create or load Chroma database
    if os.path.exists(persist_directory):
        try:
            chroma_db = Chroma(embedding_function=embeddings, persist_directory=persist_directory)
            print(f"Loaded existing Chroma database from {persist_directory}")
            
            # Add new documents to the existing database with progress tracking using tqdm
            for doc in tqdm(docs, desc="Adding documents to Chroma database"):
                chroma_db.add_documents([doc])
            print("New documents added to the existing Chroma database.")
        except Exception as e:
            print(f"Error loading existing database: {e}. Creating a new one...")
            chroma_db = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=persist_directory)
            print("New Chroma database created.")
    else:
        chroma_db = Chroma.from_documents(documents=docs, embedding=embeddings, persist_directory=persist_directory)
        # Print number of documents in the database
        print(f"Number of documents in the Chroma database: {len(chroma_db.get())}")
        print("New Chroma database created.")
    
    # chroma_db.persist()
    print(f"Chroma database saved to {persist_directory}")

    return chroma_db

def load_existing_chroma_db(persist_directory):
    """
    Load an existing Chroma vector database from the specified directory.
    """
    if not os.path.exists(persist_directory):
        raise FileNotFoundError(f"The directory '{persist_directory}' does not exist.")

    # Initialize embeddings as used during the database creation
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    # Load the saved Chroma database from the specified directory
    chroma_db = Chroma(embedding_function=embeddings, persist_directory=persist_directory)
    print(f"Chroma database loaded from {persist_directory}")

    return chroma_db

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process CSV file and manage Chroma vector database.")
    parser.add_argument("file_path", type=str, help="Path to the CSV file containing data.")
    parser.add_argument("persist_directory", type=str, help="Directory to save or load the Chroma vector database.")
    args = parser.parse_args()

    try:
        # Load and process documents
        documents = load_data(args.file_path)

        # Create or update Chroma vector database
        chroma_db = create_or_update_chroma_db(documents, args.persist_directory)

        # Load existing Chroma vector database
        loaded_db = load_existing_chroma_db(args.persist_directory)
        print(f"Number of documents in the loaded Chroma database: {len(loaded_db.get())}")
    except Exception as e:
        print(f"An error occurred: {e}")
