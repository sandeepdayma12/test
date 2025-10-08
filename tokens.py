
import nltk
nltk.download('punkt')  # This only needs to be run once

from nltk.tokenize import sent_tokenize

text = "Hello there. How are you doing?"
tokens = sent_tokenize(text)
print(tokens)
