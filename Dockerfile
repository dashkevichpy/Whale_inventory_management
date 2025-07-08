FROM tensorflow/tensorflow
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev python-dev
COPY . .
RUN pip install -r requirements.txt
CMD python main.py