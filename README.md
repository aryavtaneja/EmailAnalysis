## Email Reply Likelihood Classification

This was a 2-day, approximately 9-hour project to create an LSTM model that could analyze and predict the likelihood of a user replying to an email in their Gmail inbox. The project uses `mailscrape.py` to scrape and save emails in a .parquet file, which is then accepted, preprocessed, and trained by `analysis.ipynb`. The `lessdata.ipynb` and `stackranker.ipynb` files were used to perform experiments on both training an LSTM with less scraped data and stackranking the results of a set of unread emails scraped by `save_latest_unreads.py`. These experiments were ultimately unsuccessful, but have been left in for completeness.

A model trained on 1,740 emails from a volunteer's email, with a resulting accuracy of 76.38%, is also included in the `model` directory, and can be imported into TensorFlow with the line `keras.models.load_model('model')`

Finally, a test of classifying emails with scikit-learn regression and classification models on data which was vectorized by the OpenAI embedding service, with accuracies over 91%, is included in the files `postprocess_embed.ipynb` and `logreg.ipynb`.

**Note: the Google app made for the purpose of scraping emails only has three authorized users in the testing phase, meaning that the scrapers cannot be tested by someone without those emails. If you'd like to be added to this test group, please contact me.**
