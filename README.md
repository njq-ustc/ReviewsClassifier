# ReviewsClassifier
This is a text classifier based on LSTM and word2vec to classify book reviews

The data is book reviews which are obtained by using web crawler.
The excel file "parameters recording" is my recording for adjusting parameters.
Limited by my GPU,I'm sorry to I could only use the adam optimizer for efficiency.
At last I use a bagging methon to improve the performance,though the result only be a little better.
New improvement : according to Hownet corpus,add one dimention to the word vectors,which stand for positive or negtive evaluation.The accuracy increased 1.5%.

langconv.py zh_wiki.py：Traditionally converted to a simplified file
textprocess.py：Dataset processing and word2vec model training files
text2vec.py：Word embeding file, convert text to vector and record statement length
RNNs.py：Multilayer LSTM Text Classification Model
driver_bagging.py：Vote-based bagging model and forecasting function
parameters recording：Adjustment record file
