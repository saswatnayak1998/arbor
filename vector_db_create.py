import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Load the embedding model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def split_entry_to_chunks(entry, section):
    """
    Splits a single entry into smaller chunks for metadata.

    Args:
        entry (dict): The full entry to be split.
        section (str): The section the entry belongs to.

    Returns:
        list: A list of smaller metadata chunks.
    """
    chunks = []
    entry_id = entry.get("id") or entry.get("guide_id") or entry.get("doc_id") or entry.get("code_id")

    # Include primary_product_id for material_alternatives section
    primary_product_id = entry.get("primary_product_id") if section == "material_alternatives" else None

    # Split individual fields into chunks
    for key, value in entry.items():
        if key != "id" and key != "primary_product_id":  # Skip splitting the ID and primary_product_id
            if isinstance(value, dict):  # For nested dictionaries
                chunk = {
                    "section": section,
                    "id": entry_id,
                    "category": entry.get("category", "Unknown"),
                    key: value
                }
                if primary_product_id:
                    chunk["primary_product_id"] = primary_product_id
                chunks.append(chunk)
            elif isinstance(value, list):  # For lists, create a chunk for each item
                for item in value:
                    chunk = {
                        "section": section,
                        "id": entry_id,
                        "category": entry.get("category", "Unknown"),
                        key: item
                    }
                    if primary_product_id:
                        chunk["primary_product_id"] = primary_product_id
                    chunks.append(chunk)
            else:  # For simple key-value pairs
                chunk = {
                    "section": section,
                    "id": entry_id,
                    "category": entry.get("category", "Unknown"),
                    key: value
                }
                if primary_product_id:
                    chunk["primary_product_id"] = primary_product_id
                chunks.append(chunk)

    return chunks

def create_faiss_index(data, index_file, metadata_file):
    """
    Creates a FAISS index with embeddings and saves the metadata.

    Args:
        data (dict): The data to index.
        index_file (str): Path to save the FAISS index.
        metadata_file (str): Path to save the metadata.
    """
    # Initialize lists for embeddings and metadata
    embeddings = []
    metadata = []

    # Process data
    for section, entries in data.items():
        for entry in entries:
            # Split entry into smaller chunks
            entry_chunks = split_entry_to_chunks(entry, section)
            for chunk in entry_chunks:
                # Convert the chunk to a JSON string for embedding
                content = json.dumps(chunk, indent=2)

                # Create an embedding for the content
                embedding = embedding_model.encode(content)

                # Add the chunk to metadata
                metadata.append(chunk)

                # Append the embedding
                embeddings.append(embedding)

    # Convert embeddings to a NumPy array
    embeddings = np.array(embeddings).astype('float32')

    # Create a FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance index
    index.add(embeddings)  # Add embeddings to the index

    # Save the index and metadata
    faiss.write_index(index, index_file)
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"FAISS index saved to '{index_file}'")
    print(f"Metadata saved to '{metadata_file}'")

def main():
    # Load the JSON data
    with open("data/pretty_data.json", "r") as f:
        data = json.load(f)

    # Define file paths
    index_file = "arbor_faiss.index"
    metadata_file = "arbor_metadata.json"

    # Create and save the FAISS index and metadata
    create_faiss_index(data, index_file, metadata_file)

if __name__ == "__main__":
    main()
