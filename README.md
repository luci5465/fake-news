# ( Fake news detection using LLMs )

1. Create the virtual environment : 
python3 -m venv venv
2. Activate the environment (Linux) : 
source venv/bin/activate

pip install -r requirements.txt

# Run the Project :
python main.py


# Choose an Operation:

1-5: Run individual modules (Crawling, Cleaning, Indexing, Graph, Detection).

7. Automatic Pipeline: The recommended way. It runs the entire workflow sequentially:

1 = Crawls data from selected sites.

2 = Cleans and normalizes texts.

3 = Builds the Inverted Index.

4 = Builds the Web Graph & calculates PageRank.

5 = Launches the Fake News Detector interface.
