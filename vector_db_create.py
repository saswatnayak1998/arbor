import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

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

    primary_product_id = entry.get("primary_product_id") if section == "material_alternatives" else None

    for key, value in entry.items():
        if key != "id" and key != "primary_product_id":  
            if isinstance(value, dict): 
                chunk = {
                    "section": section,
                    "id": entry_id,
                    "category": entry.get("category", "Unknown"),
                    key: value
                }
                if primary_product_id:
                    chunk["primary_product_id"] = primary_product_id
                chunks.append(chunk)
            elif isinstance(value, list):  
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
            else:  
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
    embeddings = []
    metadata = []

    for section, entries in data.items():
        for entry in entries:
            entry_chunks = split_entry_to_chunks(entry, section)
            for chunk in entry_chunks:
                content = json.dumps(chunk, indent=2)

                embedding = embedding_model.encode(content)

                metadata.append(chunk)

                embeddings.append(embedding)

    embeddings = np.array(embeddings).astype('float32')

    # Create a FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)  # L2 distance index
    index.add(embeddings) 

    faiss.write_index(index, index_file)
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"FAISS index saved to '{index_file}'")
    print(f"Metadata saved to '{metadata_file}'")

def main():
    with open("data/pretty_data.json", "r") as f:
        data = json.load(f)

    index_file = "data/arbor_faiss.index"
    metadata_file = "data/arbor_metadata.json"

    create_faiss_index(data, index_file, metadata_file)

if __name__ == "__main__":
    main()
