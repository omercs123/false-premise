from transformers import pipeline
# question_answerer = pipeline('question-answering')
model_name = "deepset/roberta-base-squad2"
question_answerer = pipeline(model=model_name, tokenizer=model_name, task="question-answering")
context = """
Rabin was born in Jerusalem to Jewish immigrants from Eastern Europe and was raised in a Labor Zionist household. He learned agriculture in school and excelled as a student. He led a 27-year career as a soldier. As a teenager he joined the Palmach, the commando force of the Yishuv. He eventually rose through its ranks to become its chief of operations during the 1948 Arab–Israeli War. He joined the newly formed Israel Defense Forces in late 1948 and continued to rise as a promising officer. He helped shape the training doctrine of the IDF in the early 1950s, and led the IDF's Operations Directorate from 1959 to 1963. He was appointed Chief of the General Staff in 1964 and oversaw Israel's victory in the 1967 Six-Day War.

Rabin served as Israel's ambassador to the United States from 1968 to 1973, during a period of deepening U.S.–Israel ties. He was appointed Prime Minister of Israel in 1974, after the resignation of Golda Meir. In his first term, Rabin signed the Sinai Interim Agreement and ordered the Entebbe raid. He resigned in 1977 in the wake of a financial scandal. Rabin was Israel's minister of defense for much of the 1980s, including during the outbreak of the First Intifada.

In 1992, Rabin was re-elected as prime minister on a platform embracing the Israeli–Palestinian peace process. He signed several historic agreements with the Palestinian leadership as part of the Oslo Accords. In 1994, Rabin won the Nobel Peace Prize together with long-time political rival Shimon Peres and Palestinian leader Yasser Arafat. Rabin also signed a peace treaty with Jordan in 1994. In November 1995, he was assassinated by an extremist named Yigal Amir, who opposed the terms of the Oslo Accords. Amir was convicted of Rabin's murder and sentenced to life imprisonment. Rabin was the first native-born prime minister of Israel, the only prime minister to be assassinated and the second to die in office after Levi Eshkol. Rabin has become a symbol of the Israeli–Palestinian peace process.
"""
context = "In November 1995, he was assassinated by an extremist named Yigal Amir, who opposed the terms of the Oslo Accords."
question = "When did Rabin commit suicide?"
res = question_answerer({'question': question, 'context': context})

print(res)