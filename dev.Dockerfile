FROM python:3.7

WORKDIR /app

VOLUME ["/app"]

COPY requirements.txt .

RUN pip3 install -r requirements.txt
RUN echo 'export PS1="[graphql-dev] # "' >> /etc/bash.bashrc
RUN python3 -m spacy download en_core_web_sm
RUN python3 -m spacy download de_core_news_sm
# RUN python3 -m spacy download zh_core_web_sm
# RUN python3 -m spacy download da_core_news_sm
# RUN python3 -m spacy download nl_core_news_sm
# RUN python3 -m spacy download fr_core_news_sm
# RUN python3 -m spacy download el_core_news_sm
# RUN python3 -m spacy download it_core_news_sm
# RUN python3 -m spacy download ja_core_news_sm
# RUN python3 -m spacy download pl_core_news_sm
# RUN python3 -m spacy download pt_core_news_sm
# RUN python3 -m spacy download ru_core_news_sm
# RUN python3 -m spacy download es_core_news_sm
# RUN python3 -m spacy download xx_ent_wiki_sm

COPY / .

CMD [ "/usr/local/bin/uvicorn", "--host", "0.0.0.0", "--port", "80", "app:app", "--reload" ]
