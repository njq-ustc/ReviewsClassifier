import tensorflow as tf
import numpy as np
import os
from tensorflow.contrib import rnn
X_embedding_file = r'C:\Users\njq\Desktop\data\X_embedding_2and5.npy'
Y_vec_file = r'C:\Users\njq\Desktop\data\Y_vec_2and5.npy'
length_sentence_file=r'C:\Users\njq\Desktop\data\length_2and5.npy'
model_path=r'C:\Users\njq\Desktop\data\models'

class config(object):
    n_classes=2
    n_features=128
    dropout_keep=1.0
    batch_size=256
    n_layers=3
    n_time_steps=50
    l2_loss_rate= 10e-6
    n_epoches=20
    data_rate_train=0.8

class LSTMClassifier(object):
    def __init__(self):
        self.config=config()
        self.add_placeholders()
        self.pred = self.add_prediction_op()
        self.loss, self.accuracy = self.add_loss_op(self.pred)
        self.train_op = self.add_training_op(self.loss)
        self.saver = tf.train.Saver(max_to_keep=20)
        # self.save_path = os.path.abspath(os.path.join(os.path.curdir, 'models'))
        # if not os.path.exists(self.save_path):
        #     os.makedirs(self.save_path)

    def add_placeholders(self):
        self.input_placeholders=tf.placeholder(tf.float32,[None,self.config.n_time_steps,self.config.n_features])
        self.label_placeholders=tf.placeholder(tf.float32,[None,self.config.n_classes])
        self.length_placeholders = tf.placeholder(tf.int32, [None])

    def create_feed_dict(self,input_batch,label_batch,length_sentence):
        feed_dict={self.input_placeholders:input_batch,self.label_placeholders:label_batch,self.length_placeholders:length_sentence}
        return feed_dict

    def add_prediction_op(self):
        x=self.input_placeholders
        def lstm_cell():
            lstm = rnn.BasicLSTMCell(self.config.n_features)
            drop = rnn.DropoutWrapper(lstm,output_keep_prob=self.config.dropout_keep)
            return drop
        cell = rnn.MultiRNNCell([lstm_cell() for _ in range(self.config.n_layers)])
        output_lstm,_ = tf.nn.dynamic_rnn(cell,x,dtype=tf.float32,sequence_length=self.length_placeholders)
        #extract the vector in the time step of the last word
        h=[]
        #This cycle seem to consume lots of time ,but I don't find a more efficient way
        #probabally we can transform the length to a one-hot vector and then use the matrix multiply to solve this problem
        for i in range(self.config.batch_size) :
            h.append(output_lstm[i][self.length_placeholders[i]-1])
        self.W=tf.Variable(tf.truncated_normal([self.config.n_features,self.config.n_classes],stddev=0.1),dtype=tf.float32)
        self.b=tf.Variable(tf.constant(0.1,shape=[self.config.n_classes]),dtype=tf.float32)
        pred=tf.nn.xw_plus_b(h,self.W,self.b)
        # For convenience to use the tensorflow function,we return the values which can be transformed to y_hat only by a softmax function
        return pred

    def add_loss_op(self,pred):
        #Here we use softmax repeatedly,but the n_class is so small that the wasted time is too little.
        l2_loss=tf.nn.l2_loss(self.W)+tf.nn.l2_loss(self.b)
        loss=tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred,labels=self.label_placeholders))
        loss+=self.config.l2_loss_rate*l2_loss
        prediction=tf.equal(tf.argmax(pred,axis=1),tf.argmax(self.label_placeholders,axis=1))
        accuracy = tf.reduce_mean(tf.cast(prediction, tf.float32))
        return loss,accuracy

    def add_training_op(self,loss):
        adam_op=tf.train.AdamOptimizer()
        train_op=adam_op.minimize(loss)
        return train_op

    def train_on_batch(self,sess,inputs_batch,labels_batch,length_batch):
        feed=self.create_feed_dict(inputs_batch,labels_batch,length_batch)
        _,loss,accuracy=sess.run([self.train_op,self.loss,self.accuracy],feed_dict=feed)
        return loss,accuracy

    def test(self,sess,inputs,labels,length_sentence):
        accuracy_list=[]
        data_size = len(labels)
        n_batches = int((data_size - 1) / self.config.batch_size)
        for iter in range(n_batches):
            start=iter*self.config.batch_size
            end=min(start+self.config.batch_size,data_size)
            feed=self.create_feed_dict(inputs[start:end],labels[start:end],length_sentence[start:end])
            accuracy=sess.run([self.accuracy],feed_dict=feed)
            accuracy_list.append(accuracy)
        accuracy = np.mean(accuracy_list)
        return accuracy

    def run(self,inputs,labels,length):
        data_size=len(labels)
        assert data_size == len(inputs), 'inputs_size not equal to labels_size'
        #To keep the matching of inputs and lables ,we should use the shuffle index
        shuffle_index = np.random.permutation(np.arange(data_size))
        inputs_shuffle = inputs[shuffle_index]
        labels_shuffle = labels[shuffle_index]
        length_shuffle = length[shuffle_index]
        # 0.8 as a training set and 0.2 as a test set
        index_split=int(data_size*self.config.data_rate_train)
        inputs_train=inputs_shuffle[:index_split]
        labels_train=labels_shuffle[:index_split]
        length_train=length_shuffle[:index_split]
        inputs_test=inputs_shuffle[index_split:]
        labels_test=labels_shuffle[index_split:]
        length_test=length_shuffle[index_split:]
        print('inputs_train:',inputs_train.shape,'labels_train:',labels_train.shape)
        #Only in this model I abandon the last several sentences.I don't find a way to get the dynamic n_batches to build the cycle in prediction.
        n_batches = int((index_split - 1) / self.config.batch_size)
        self.session=tf.Session()
        with self.session as sess:
            sess.run(tf.global_variables_initializer())
            print('There are {0} epoches'.format(self.config.n_epoches), 'each epoch has {0} steps'.format(n_batches))
            #20 iterations
            for iteration_epoch in range(self.config.n_epoches):
                print('epoch {0} =========================================================================='.format(iteration_epoch+1))
                train_loss=[]
                train_accuracy=[]
                #training set iterations
                for iteration_batch in range(n_batches):
                    start=iteration_batch*self.config.batch_size
                    end = min(start + self.config.batch_size, data_size)
                    loss,accuracy=self.train_on_batch(sess,inputs_train[start:end],labels_train[start:end],length_train[start:end])
                    iteration_batch+=1
                    if (iteration_batch % 50) == 0 :
                        print('training step:{0}'.format(iteration_batch))
                    train_loss.append(loss)
                    train_accuracy.append(accuracy)
                #The loss in train is the mean value of all loss on batches.
                train_loss_epoch=np.mean(train_loss)
                train_accuracy_epoch=np.mean(train_accuracy)
                print('loss_train:{:.3f}'.format(train_loss_epoch),'accuracy_train:{:.3f}'.format(train_accuracy_epoch))
                #self.saver.save(sess,os.path.join(self.save_path,'model'),global_step=(iteration_epoch))
                accuracy_test=self.test(sess,inputs_test,labels_test,length_test)
                if accuracy_test>accuracy_max :
                    accuracy_max=accuracy_test
                    print(self.saver.save(sess,self.save_path))
                print('the accuracy in test :{:.3f}'.format(accuracy_test))

    def fit(self,inputs,labels,length,model_position):
        print('this a text classifier using LSTMs ')
        self.save_path = os.path.abspath(os.path.join(model_path, model_position))
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)
        self.save_path = os.path.abspath(os.path.join(self.save_path, 'model'))
        inputs=np.array(inputs)
        labels=np.array(labels)
        length=np.array(length)
        print('the shape of inputs:',inputs.shape)
        print('the shape of labels:',labels.shape)
        print('the shape of length of sentence:',length.shape)
        self.run(inputs,labels,length)

    # load a saved model and return the predict index
    def pred_test(self, inputs, length, model_position):
        self.save_path = os.path.abspath(os.path.join(model_path, model_position))
        session=tf.Session()
        with session as sess:
            self.saver.restore(sess=sess, save_path=os.path.join(self.save_path, 'model'))
            data_size = len(length)
            pred = []
            n_batches = int((data_size - 1) / self.config.batch_size) + 1
            for iter in range(n_batches):
                start = iter * self.config.batch_size
                end = min(start + self.config.batch_size, data_size)
                feed_dict = {self.input_placeholders: inputs[start:end],self.length_placeholders: length[start:end]}
                pred_batch = sess.run([self.pred], feed_dict=feed_dict)
                pred_batch = np.squeeze(np.array(pred_batch), axis=0)
                pred.extend(np.argmax(pred_batch, axis=1).tolist())
        predict = np.array(pred, dtype=int)
        print(predict.shape)
        return predict

def main():
    model=LSTMClassifier()
    inputs=np.load(X_embedding_file)
    labels=np.load(Y_vec_file)
    length_sentence=np.load(length_sentence_file)
    model.fit(inputs,labels,length_sentence,'model0')

if __name__ == '__main__':
    main()