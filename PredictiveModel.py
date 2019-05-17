from SequenceEncoder import SequenceEncoder
from TextTransformers import LDATransformer, PVTransformer, BoNGTransformer, NBLogCountRatioTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import pandas as pd
import time
import numpy as np

class PredictiveModel():

    def __init__(self, nr_events, case_id_col, label_col, encoder_kwargs, transformer_kwargs, cls_kwargs, text_col=None,
                 text_transformer_type=None, cls_method="rf"):
        
        self.text_col = text_col
        self.case_id_col = case_id_col
        self.label_col = label_col
        
        self.encoder = SequenceEncoder(nr_events=nr_events, case_id_col=case_id_col, label_col=label_col, **encoder_kwargs)
        
        if text_transformer_type is None:
            self.transformer = None
        elif text_transformer_type == "LDATransformer":
            self.transformer = LDATransformer(**transformer_kwargs)
        elif text_transformer_type == "BoNGTransformer":
            self.transformer = BoNGTransformer(**transformer_kwargs)
        elif text_transformer_type == "NBLogCountRatioTransformer":
            self.transformer = NBLogCountRatioTransformer(**transformer_kwargs)
        elif text_transformer_type == "PVTransformer":
            self.transformer = PVTransformer(**transformer_kwargs)

        else:
            print("Transformer type not known")
        
        if cls_method == "logit":
            self.cls = LogisticRegression(**cls_kwargs) 
        elif cls_method == "rf":
            self.cls = RandomForestClassifier(**cls_kwargs)
        else:
            print("Classifier method not known")
        
        self.hardcoded_prediction = None
        self.test_encode_time = None
        self.test_preproc_time = None
        self.test_time = None
        self.nr_test_cases = None
        

    def fit(self, dt_train):
        preproc_start_time = time.time()
        print('dt_train ',dt_train)
        train_encoded = self.encoder.fit_transform(dt_train)
        print('train_encoded  ',train_encoded)
        train_X = train_encoded.drop([self.case_id_col, self.label_col], axis=1)
        train_y = train_encoded[self.label_col]
        
        if self.transformer is not None:
            text_cols = [col for col in train_X.columns.values if col.startswith(self.text_col)]
            for col in text_cols:
                train_X[col] = train_X[col].astype('str')
            print('train_X  ',train_X)    
            print('train_X[text_cols]:')
            print(train_X[text_cols])
            train_text = self.transformer.fit_transform(train_X[text_cols], train_y)
            print('train_text  ',train_text)
            train_X = pd.concat([train_X.drop(text_cols, axis=1), train_text], axis=1)
        self.train_X = train_X
        preproc_end_time = time.time()
        self.preproc_time = preproc_end_time - preproc_start_time
        
        cls_start_time = time.time()
        if len(train_y.unique()) < 2: # less than 2 classes are present
            self.hardcoded_prediction = train_y.iloc[0]
            self.cls.classes_ = train_y.unique()
        else:
            self.cls.fit(train_X, train_y)
        cls_end_time = time.time()
        self.cls_time = cls_end_time - cls_start_time

        
    def predict_proba(self, dt_test):
        encode_start_time = time.time()
        test_encoded = self.encoder.transform(dt_test)
        encode_end_time = time.time()
        self.test_encode_time = encode_end_time - encode_start_time
        
        test_preproc_start_time = time.time()
        test_X = test_encoded.drop([self.case_id_col, self.label_col], axis=1)
        
        if self.transformer is not None:
            text_cols = [col for col in test_X.columns.values if col.startswith(self.text_col)]
            for col in text_cols:
                test_encoded[col] = test_encoded[col].astype('str')
            test_text = self.transformer.transform(test_encoded[text_cols])
            test_X = pd.concat([test_X.drop(text_cols, axis=1), test_text], axis=1)
        
        
        self.test_case_names = test_encoded[self.case_id_col]
        self.test_X = test_X
        self.test_y = test_encoded[self.label_col]
        test_preproc_end_time = time.time()
        self.test_preproc_time = test_preproc_end_time - test_preproc_start_time
        
        test_start_time = time.time()
        if self.hardcoded_prediction is not None: # e.g. model was trained with one class only
            predictions_proba = np.array([1.0,0.0]*test_X.shape[0]).reshape(test_X.shape[0],2)
        else:
            predictions_proba = self.cls.predict_proba(test_X)
        test_end_time = time.time()
        self.test_time = test_end_time - test_start_time
        self.nr_test_cases = len(predictions_proba)
        
        return predictions_proba
