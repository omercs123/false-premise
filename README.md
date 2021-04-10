# false-premise

Code for generating a question-label-paragraph dataset with verifiable and unverifiable premises.

Generating the dataset:
```bash
$ pip install -r requirements.txt
$ python dataset.py
```

This will create two files - `train.jsonl` and `dev.jsonl`.
Those can be used with the provided jupyter notebook to train a question answering model.
