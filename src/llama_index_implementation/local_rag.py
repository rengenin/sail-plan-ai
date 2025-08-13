from llama_index.core import SimpleDirectoryReader, VectorStoreIndex


reader = SimpleDirectoryReader(
    input_files=["./data/current_stations.csv"]
)


docs = reader.load_data()
print(f"Loaded {len(docs)} docs")
print(docs)