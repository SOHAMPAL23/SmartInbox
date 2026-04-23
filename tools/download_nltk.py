import nltk
import os

def download_nltk_resources():
    resources = [
        'punkt',
        'stopwords',
        'wordnet',
        'omw-1.4'
    ]
    
    print("Starting NLTK resource download...")
    for resource in resources:
        print(f"Downloading {resource}...")
        nltk.download(resource)
    print("NLTK resource download complete.")

if __name__ == "__main__":
    download_nltk_resources()
